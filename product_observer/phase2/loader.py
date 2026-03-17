"""Load Phase 1 raw request JSON files from a directory."""

from __future__ import annotations

import gzip
import json
import logging
from pathlib import Path
from typing import Any, Iterator, Optional

logger = logging.getLogger("product_observer.phase2")


def _load_file(filepath: Path) -> Optional[tuple[dict[str, Any], Any]]:
    """Load a single .json or .json.gz file. Returns (metadata, response_body) or None on error."""
    try:
        if filepath.suffix == ".gz":
            with gzip.open(filepath, "rt", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = json.loads(filepath.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.warning("Skipping %s: %s", filepath.name, e)
        return None

    if not isinstance(data, dict):
        logger.warning("Skipping %s: root is not an object", filepath.name)
        return None

    metadata = data.get("metadata")
    response_body = data.get("response_body")

    if metadata is None:
        logger.warning("Skipping %s: missing metadata", filepath.name)
        return None

    if not isinstance(metadata, dict):
        logger.warning("Skipping %s: metadata is not an object", filepath.name)
        return None

    return (metadata, response_body)


def load_raw_requests(
    input_dir: Path,
) -> Iterator[tuple[dict[str, Any], Any]]:
    """Scan input_dir for request_*.json and request_*.json.gz; yield (metadata, response_body) per file.

    Files are processed in sorted order by name. Corrupt or invalid files are skipped with a warning.
    """
    input_dir = Path(input_dir)
    if not input_dir.is_dir():
        raise NotADirectoryError(str(input_dir))

    paths: list[Path] = []
    for p in input_dir.iterdir():
        if not p.is_file():
            continue
        if p.name.startswith("request_") and (p.suffix == ".json" or (p.suffix == ".gz" and p.stem.endswith(".json"))):
            paths.append(p)

    paths.sort(key=lambda p: p.name)

    for filepath in paths:
        result = _load_file(filepath)
        if result is not None:
            yield result
