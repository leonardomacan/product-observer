"""Load Phase 2 endpoints.json."""

import json
from pathlib import Path
from typing import Any, List


def load_endpoints(input_path: Path) -> List[dict[str, Any]]:
    """Load Phase 2 endpoints from a JSON file (e.g. data/phase2/endpoints.json)."""
    path = Path(input_path)
    if not path.is_file():
        raise FileNotFoundError(f"Phase 2 input not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("Phase 2 endpoints.json must be a JSON array")
    return data
