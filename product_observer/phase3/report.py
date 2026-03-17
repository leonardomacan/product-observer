"""Write Phase 3 annotated endpoints to disk."""

import json
from pathlib import Path
from typing import Any, List


def write_annotated_endpoints(
    endpoints: List[dict[str, Any]],
    annotations: List[dict[str, Any]],
    output_dir: Path,
) -> Path:
    """Add annotation fields to each endpoint and write annotated_endpoints.json."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    if len(annotations) != len(endpoints):
        raise ValueError("annotations length must match endpoints length")
    out: List[dict[str, Any]] = []
    for ep, ann in zip(endpoints, annotations):
        entry = dict(ep)
        if ann:
            entry["annotations"] = ann
        out.append(entry)
    path = output_dir / "annotated_endpoints.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, default=str)
    return path
