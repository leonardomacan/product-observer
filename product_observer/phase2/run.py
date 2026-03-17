"""CLI entry point for Phase 2: load, cluster, infer schemas, write report."""

import argparse
import logging
import sys
from pathlib import Path

from product_observer.phase2.clustering import cluster_requests
from product_observer.phase2.loader import load_raw_requests
from product_observer.phase2.report import build_report, write_report


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase 2 — API Intelligence: cluster endpoints and infer response schemas from Phase 1 data.",
    )
    parser.add_argument(
        "--input",
        "-i",
        type=Path,
        default=Path("data/raw_requests"),
        help="Input directory containing request_*.json (and optional .json.gz) files (default: data/raw_requests)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("data/phase2"),
        help="Output directory for endpoints.json and optional api_surface.md (default: data/phase2)",
    )
    parser.add_argument(
        "--no-markdown",
        action="store_true",
        help="Do not write api_surface.md",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose (debug) logging",
    )
    return parser.parse_args()


def main() -> int:
    """Run Phase 2 pipeline: load -> cluster -> report. Returns 0 on success."""
    args = _parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(message)s",
    )
    logger = logging.getLogger("product_observer.phase2")

    try:
        records = list(load_raw_requests(args.input))
    except NotADirectoryError as e:
        logger.error("Input is not a directory: %s", e)
        return 1

    if not records:
        logger.warning("No request files found in %s", args.input)
        return 0

    logger.info("Loaded %d requests from %s", len(records), args.input)
    groups = cluster_requests(records)
    logger.info("Clustered into %d endpoints", len(groups))
    report = build_report(groups)
    write_report(report, args.output, write_markdown=not args.no_markdown)
    logger.info("Wrote %s/endpoints.json", args.output)
    if not args.no_markdown:
        logger.info("Wrote %s/api_surface.md", args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
