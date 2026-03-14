"""Emit Phase 4 Markdown: api_catalog.md, workflows.md, and optionally workflow_narratives.md."""

from pathlib import Path
from typing import Any, List, Optional, Tuple


def _format_entities(entities: List[Any]) -> str:
    if not entities:
        return ""
    return ", ".join(str(e) for e in entities)


def write_api_catalog(
    catalog: List[Tuple[str, List[dict[str, Any]]]],
    output_dir: Path,
) -> Path:
    """Write api_catalog.md with sections by category."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "# API Catalog (Phase 4)",
        "",
        "Endpoints grouped by category. For full response schemas see Phase 2 `api_surface.md`.",
        "",
    ]
    for category, rows in catalog:
        title = category.capitalize()
        lines.append(f"## {title}")
        lines.append("")
        lines.append("| Method | Path | Count | Entities | Returns |")
        lines.append("|--------|------|-------|----------|---------|")
        for r in rows:
            entities_str = _format_entities(r.get("entities") or [])
            lines.append(
                f"| {r['method']} | `{r['normalized_path']}` | {r['request_count']} | {entities_str} | {r.get('schema_summary', '—')} |"
            )
        lines.append("")
    path = output_dir / "api_catalog.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_workflows(
    workflows: List[Tuple[str, List[dict[str, Any]]]],
    output_dir: Path,
) -> Path:
    """Write workflows.md with sections by workflow_hint."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Workflows (Phase 4)",
        "",
        "Endpoints grouped by workflow hint.",
        "",
    ]
    for name, rows in workflows:
        title = name if name != "Other" else "Other (no workflow hint)"
        lines.append(f"## {title}")
        lines.append("")
        lines.append("| Method | Path | Category | Entities |")
        lines.append("|--------|------|----------|----------|")
        for r in rows:
            entities_str = _format_entities(r.get("entities") or [])
            lines.append(
                f"| {r['method']} | `{r['normalized_path']}` | {r.get('category', '')} | {entities_str} |"
            )
        lines.append("")
    path = output_dir / "workflows.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_workflow_narratives(content: str, output_dir: Path) -> Path:
    """Write workflow_narratives.md with LLM-generated content."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "workflow_narratives.md"
    path.write_text(content, encoding="utf-8")
    return path
