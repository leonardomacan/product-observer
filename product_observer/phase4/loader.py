"""Load Phase 3 annotated_endpoints.json."""

import json
from pathlib import Path
from typing import Any, List


def load_annotated_endpoints(input_path: Path) -> List[dict[str, Any]]:
    """Load Phase 3 annotated endpoints from a JSON file. Ensures each entry has an annotations dict."""
    path = Path(input_path)
    if not path.is_file():
        raise FileNotFoundError(f"Phase 3 input not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("Phase 3 annotated_endpoints.json must be a JSON array")
    out: List[dict[str, Any]] = []
    for i, ep in enumerate(data):
        if not isinstance(ep, dict):
            raise ValueError(f"Endpoint at index {i} is not an object")
        entry = dict(ep)
        if "annotations" not in entry or not isinstance(entry.get("annotations"), dict):
            entry["annotations"] = {}
        out.append(entry)
    return out
