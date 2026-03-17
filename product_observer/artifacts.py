from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from .datasets import DatasetLayout, ensure_parent_dirs


@dataclass
class EndpointStats:
    path: str
    method: str
    count: int = 0
    first_seen: datetime | None = None
    last_seen: datetime | None = None


def _load_phase2_endpoints(path: Path) -> List[dict]:
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "endpoints" in data and isinstance(data["endpoints"], list):
        return data["endpoints"]
    return []


def update_artifacts_for_run(layout: DatasetLayout) -> None:
    """Update target-system artifacts after a single run.

    This function is intentionally simple for v1 and focuses on aggregating
    endpoint counts from Phase 2 output into endpoint_inventory.json.
    """
    endpoints_path = layout.phase2_dir / "endpoints.json"
    endpoints = _load_phase2_endpoints(endpoints_path)
    if not endpoints:
        return

    key_to_stats: Dict[tuple, EndpointStats] = {}
    for ep in endpoints:
        path = str(ep.get("path") or ep.get("normalized_path") or ep.get("url") or "")
        method = str(ep.get("method", "GET")).upper()
        if not path:
            continue
        key = (method, path)
        stats = key_to_stats.get(key)
        if stats is None:
            stats = EndpointStats(path=path, method=method, count=0)
            key_to_stats[key] = stats
        stats.count += 1

    inventory_path = layout.artifacts_root / "endpoint_inventory.json"
    ensure_parent_dirs(inventory_path)

    # Merge with any existing inventory by summing counts.
    existing: Dict[tuple, EndpointStats] = {}
    if inventory_path.is_file():
        raw = json.loads(inventory_path.read_text(encoding="utf-8"))
        for item in raw:
            key = (item.get("method", "GET").upper(), item.get("path", ""))
            existing[key] = EndpointStats(
                path=item.get("path", ""),
                method=item.get("method", "GET").upper(),
                count=int(item.get("count", 0)),
            )

    for key, stats in key_to_stats.items():
        if key in existing:
            existing[key].count += stats.count
        else:
            existing[key] = stats

    serialized = [
        {"method": s.method, "path": s.path, "count": s.count}
        for _, s in sorted(existing.items(), key=lambda kv: (kv[0][0], kv[0][1]))
    ]
    inventory_path.write_text(json.dumps(serialized, indent=2), encoding="utf-8")

