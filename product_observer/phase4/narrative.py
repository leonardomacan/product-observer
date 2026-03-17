"""Load context files and generate workflow narratives via Anthropic API."""

import logging
import os
from pathlib import Path
from typing import Any, List, Optional, Tuple

logger = logging.getLogger(__name__)


def load_context(context_dir: Path) -> str:
    """
    Read all .md and .txt files from context_dir, concatenate with file labels.
    Returns empty string if dir does not exist or has no matching files.
    """
    path = Path(context_dir)
    if not path.is_dir():
        return ""
    parts: List[str] = []
    for f in sorted(path.rglob("*")):
        if not f.is_file():
            continue
        if f.suffix.lower() not in (".md", ".txt"):
            continue
        try:
            text = f.read_text(encoding="utf-8")
            parts.append(f"--- {f.name} ---\n{text}")
        except Exception:
            continue
    return "\n\n".join(parts) if parts else ""


def _serialize_for_prompt(catalog: List[Tuple[str, List[dict]]], workflows: List[Tuple[str, List[dict]]]) -> str:
    """Produce a concise text representation of catalog and workflows for the LLM."""
    lines = ["# Catalog by category", ""]
    for category, rows in catalog:
        lines.append(f"## {category}")
        for r in rows[:20]:  # cap per section to avoid token overflow
            entities = r.get("entities") or []
            lines.append(f"- {r['method']} {r['normalized_path']} (entities: {entities})")
        if len(rows) > 20:
            lines.append(f"... and {len(rows) - 20} more")
        lines.append("")
    lines.append("# Workflows")
    for name, rows in workflows:
        lines.append(f"## {name}")
        for r in rows[:15]:
            lines.append(f"- {r['method']} {r['normalized_path']} [{r.get('category', '')}]")
        if len(rows) > 15:
            lines.append(f"... and {len(rows) - 15} more")
        lines.append("")
    return "\n".join(lines)


def generate_narratives(
    catalog: List[Tuple[str, List[dict[str, Any]]]],
    workflows: List[Tuple[str, List[dict[str, Any]]]],
    context: str,
) -> Optional[str]:
    """
    Call Anthropic API to generate workflow narrative markdown. Returns None if
    ANTHROPIC_API_KEY is not set or the API call fails.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key or not api_key.strip():
        return None

    try:
        from anthropic import Anthropic
    except ImportError:
        return None

    data_block = _serialize_for_prompt(catalog, workflows)
    user_content = (
        "Below is structured data from an API discovery pipeline: endpoints grouped by category and by workflow. "
        "Optional context from the project is also provided.\n\n"
        "Write a short Markdown document titled \"Workflow Narratives\" (or \"Discovery Map\") that: "
        "1) summarizes what workflows and capabilities were observed; "
        "2) describes each workflow (e.g. inbound) in one or two paragraphs, referencing the endpoints that support it; "
        "3) is suitable as the final \"map\" of discoveries. Use clear headings and bullet points.\n\n"
        "--- Structured data ---\n\n"
        f"{data_block}\n\n"
    )
    if context.strip():
        user_content += "--- Project context (use to enrich the narrative) ---\n\n" + context.strip() + "\n\n"

    try:
        client = Anthropic(api_key=api_key.strip())
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            messages=[{"role": "user", "content": user_content}],
        )

        # Log token usage and rough cost (based on public pricing) for visibility.
        usage = getattr(message, "usage", None)
        if usage is not None:
            input_tokens = getattr(usage, "input_tokens", None)
            output_tokens = getattr(usage, "output_tokens", None)
            if input_tokens is not None and output_tokens is not None:
                # Approximate pricing for Sonnet 4.x (USD per 1M tokens).
                input_rate = 3.0   # $3 per 1M input tokens
                output_rate = 15.0  # $15 per 1M output tokens
                cost = (input_tokens / 1_000_000.0) * input_rate + (output_tokens / 1_000_000.0) * output_rate
                logger.info(
                    "Phase 4 LLM usage: input_tokens=%s, output_tokens=%s, estimated_cost_usd=%.6f",
                    input_tokens,
                    output_tokens,
                    cost,
                )
            else:
                logger.info("Phase 4 LLM usage: usage object present but token fields missing: %r", usage)

        if message.content and len(message.content) > 0:
            block = message.content[0]
            if hasattr(block, "text"):
                return block.text
            if isinstance(block, dict) and block.get("type") == "text":
                return block.get("text", "")
            if isinstance(block, dict) and "text" in block:
                return block["text"]
        logger.warning("Anthropic API returned empty or unexpected content structure")
        return None
    except Exception as e:
        logger.warning("Anthropic API call failed: %s", e)
        return None
