"""Build workflow structure: group endpoints by workflow_hint."""

from typing import Any, List, Tuple


def build_workflows(endpoints: List[dict[str, Any]]) -> List[Tuple[str, List[dict[str, Any]]]]:
    """
    Group endpoints by annotations.workflow_hint. Returns a list of (workflow_name, endpoint_rows).
    workflow_name is the hint string or "Other" for missing. Sorted by workflow name then method+path.
    """
    buckets: dict[str, List[dict[str, Any]]] = {}
    for ep in endpoints:
        ann = ep.get("annotations") or {}
        hint = ann.get("workflow_hint")
        name = str(hint).strip() if hint else "Other"
        if name not in buckets:
            buckets[name] = []
        row = {
            "method": ep.get("method", ""),
            "normalized_path": ep.get("normalized_path", ""),
            "category": (ann.get("category") or "other").lower(),
            "entities": ann.get("entities") or [],
        }
        buckets[name].append(row)
    # Sort workflows: "Other" last, then alphabetically; within each, sort by method+path
    order = sorted(buckets.keys(), key=lambda w: (w == "Other", w))
    result: List[Tuple[str, List[dict[str, Any]]]] = []
    for name in order:
        rows = buckets[name]
        rows.sort(key=lambda r: (r["method"], r["normalized_path"]))
        result.append((name, rows))
    return result
