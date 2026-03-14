"""Build API catalog structure: group endpoints by category."""

from typing import Any, List, Tuple

CATEGORY_ORDER = ("auth", "config", "business", "other")


def _schema_summary(schema: Any) -> str:
    """Return a short summary of response_schema for display (e.g. top-level keys)."""
    if not schema or not isinstance(schema, dict):
        return "—"
    props = schema.get("properties")
    if isinstance(props, dict) and props:
        keys = list(props.keys())[:8]
        return ", ".join(keys) + (" …" if len(props) > 8 else "")
    kind = schema.get("type", "object")
    return str(kind)


def build_catalog(endpoints: List[dict[str, Any]]) -> List[Tuple[str, List[dict[str, Any]]]]:
    """
    Group endpoints by annotations.category. Returns a list of (category, endpoints)
    in fixed order: auth, config, business, other. Endpoints sorted by method then path.
    """
    buckets: dict[str, List[dict[str, Any]]] = {c: [] for c in CATEGORY_ORDER}
    for ep in endpoints:
        ann = ep.get("annotations") or {}
        cat = (ann.get("category") or "other").lower()
        if cat not in buckets:
            buckets[cat] = []
        # Add a display summary for response_schema
        row = {
            "method": ep.get("method", ""),
            "normalized_path": ep.get("normalized_path", ""),
            "request_count": ep.get("request_count", 0),
            "entities": ann.get("entities") or [],
            "workflow_hint": ann.get("workflow_hint"),
            "schema_summary": _schema_summary(ep.get("response_schema")),
        }
        buckets.setdefault(cat, []).append(row)
    result: List[Tuple[str, List[dict[str, Any]]]] = []
    for cat in CATEGORY_ORDER:
        rows = buckets.get(cat, [])
        rows.sort(key=lambda r: (r["method"], r["normalized_path"]))
        result.append((cat, rows))
    return result
