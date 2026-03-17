"""CLI entry point for Phase 4: load annotated endpoints, build catalog and workflows, write docs and optional narratives."""

import argparse
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from product_observer.phase4.catalog import build_catalog
from product_observer.phase4.loader import load_annotated_endpoints
from product_observer.phase4.narrative import generate_narratives, load_context
from product_observer.phase4.report import (
    write_api_catalog,
    write_workflow_narratives,
    write_workflows,
)
from product_observer.phase4.workflows import build_workflows


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase 4 — Knowledge & Documentation: generate API catalog, workflows, and optional LLM narratives.",
    )
    parser.add_argument(
        "--input",
        "-i",
        type=Path,
        default=Path("data/phase3/annotated_endpoints.json"),
        help="Path to Phase 3 annotated_endpoints.json (default: data/phase3/annotated_endpoints.json)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("data/phase4"),
        help="Output directory for api_catalog.md, workflows.md, workflow_narratives.md (default: data/phase4)",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Skip LLM-generated workflow narratives (no ANTHROPIC_API_KEY required)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose (debug) logging",
    )
    return parser.parse_args()


def _context_dir() -> Path:
    env = os.environ.get("PHASE4_CONTEXT_DIR", "").strip()
    if env:
        return Path(env)
    return Path("docs/phase4_context")


def main() -> int:
    """Run Phase 4 pipeline. Returns 0 on success."""
    load_dotenv()
    args = _parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(message)s",
    )
    logger = logging.getLogger("product_observer.phase4")

    try:
        endpoints = load_annotated_endpoints(args.input)
    except (FileNotFoundError, ValueError) as e:
        logger.error("%s", e)
        return 1

    if not endpoints:
        logger.warning("No endpoints in %s", args.input)
        return 0

    logger.info("Loaded %d endpoints from %s", len(endpoints), args.input)

    catalog = build_catalog(endpoints)
    workflows = build_workflows(endpoints)

    p1 = write_api_catalog(catalog, args.output)
    logger.info("Wrote %s", p1)
    p2 = write_workflows(workflows, args.output)
    logger.info("Wrote %s", p2)

    if not args.no_llm:
        context = load_context(_context_dir())
        if context.strip():
            logger.info("Loaded context from %s", _context_dir())
        narrative_md = generate_narratives(catalog, workflows, context)
        if narrative_md:
            p3 = write_workflow_narratives(narrative_md, args.output)
            logger.info("Wrote %s", p3)
        else:
            if not os.environ.get("ANTHROPIC_API_KEY", "").strip():
                logger.warning(
                    "Skipping workflow narratives: set ANTHROPIC_API_KEY to enable, or use --no-llm to suppress this message.",
                )
            else:
                logger.warning("Skipping workflow narratives: API call did not return content.")
    else:
        logger.info("Skipping workflow narratives (--no-llm).")

    return 0


if __name__ == "__main__":
    sys.exit(main())
