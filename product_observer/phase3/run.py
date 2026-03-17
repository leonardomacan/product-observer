"""CLI entry point for Phase 3: load Phase 2 output, run domain plugins, write annotated endpoints."""

import argparse
import logging
import sys
from pathlib import Path

from product_observer.phase3.loader import load_endpoints
from product_observer.phase3.plugins import get_domain_annotator, merge_annotations
from product_observer.phase3.report import write_annotated_endpoints


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase 3 — Domain Discovery: annotate endpoints using domain plugins.",
    )
    parser.add_argument(
        "--input",
        "-i",
        type=Path,
        default=Path("data/phase2/endpoints.json"),
        help="Path to Phase 2 endpoints.json (default: data/phase2/endpoints.json)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("data/phase3"),
        help="Output directory for annotated_endpoints.json (default: data/phase3)",
    )
    parser.add_argument(
        "--domains",
        "-d",
        nargs="+",
        default=["wms"],
        help="Domain plugins to run (default: wms). Options: wms, ecommerce, erp",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose (debug) logging",
    )
    return parser.parse_args()


def main() -> int:
    """Run Phase 3 pipeline. Returns 0 on success."""
    args = _parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(message)s",
    )
    logger = logging.getLogger("product_observer.phase3")

    try:
        endpoints = load_endpoints(args.input)
    except (FileNotFoundError, ValueError) as e:
        logger.error("%s", e)
        return 1

    if not endpoints:
        logger.warning("No endpoints in %s", args.input)
        return 0

    logger.info("Loaded %d endpoints from %s", len(endpoints), args.input)
    annotation_lists: list = []
    for name in args.domains:
        try:
            annotator = get_domain_annotator(name.strip().lower())
            ann = annotator(endpoints)
            annotation_lists.append(ann)
            logger.info("Ran domain plugin: %s", name)
        except ValueError as e:
            logger.error("%s", e)
            return 1

    if not annotation_lists:
        logger.warning("No domain plugins produced annotations")
        annotations = [{} for _ in endpoints]
    else:
        annotations = merge_annotations(endpoints, annotation_lists)

    out_path = write_annotated_endpoints(endpoints, annotations, args.output)
    logger.info("Wrote %s", out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
