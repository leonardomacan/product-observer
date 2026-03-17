"""Schema inference: merge JSON response bodies per endpoint and infer minimal types."""

from typing import Any

# Limit recursion depth for nested objects to avoid huge schemas
_MAX_DEPTH = 10

_TYPE_STR = "string"
_TYPE_NUM = "number"
_TYPE_BOOL = "boolean"
_TYPE_ARRAY = "array"
_TYPE_OBJECT = "object"
_TYPE_MIXED = "mixed"
_TYPE_BINARY = "binary"


def _infer_leaf_type(value: Any) -> str:
    """Return a single type for a scalar or container root."""
    if value is None:
        return _TYPE_STR
    if isinstance(value, bool):
        return _TYPE_BOOL
    if isinstance(value, int):
        return _TYPE_NUM
    if isinstance(value, float):
        return _TYPE_NUM
    if isinstance(value, str):
        if value.startswith("<binary:") and "bytes>" in value:
            return _TYPE_BINARY
        return _TYPE_STR
    if isinstance(value, list):
        return _TYPE_ARRAY
    if isinstance(value, dict):
        return _TYPE_OBJECT
    return _TYPE_STR


def _merge_types(a: str, b: str) -> str:
    """Merge two type strings; return 'mixed' if they differ."""
    if a == b:
        return a
    if a == _TYPE_MIXED or b == _TYPE_MIXED:
        return _TYPE_MIXED
    return _TYPE_MIXED


def _infer_schema_from_value(value: Any, depth: int) -> dict[str, Any]:
    """Recursively build a minimal schema (keys + types) from a JSON value."""
    if depth > _MAX_DEPTH:
        return {"type": _TYPE_OBJECT, "truncated": True}

    if value is None:
        return {"type": _TYPE_STR}
    if isinstance(value, bool):
        return {"type": _TYPE_BOOL}
    if isinstance(value, (int, float)):
        return {"type": _TYPE_NUM}
    if isinstance(value, str):
        if value.startswith("<binary:") and "bytes>" in value:
            return {"type": _TYPE_BINARY, "note": "binary response"}
        return {"type": _TYPE_STR}
    if isinstance(value, list):
        if not value:
            return {"type": _TYPE_ARRAY, "items": {"type": _TYPE_STR}}
        item_schemas = [_infer_schema_from_value(item, depth + 1) for item in value[:5]]
        # Merge item types into one representative
        item_type = item_schemas[0].get("type", _TYPE_STR)
        for s in item_schemas[1:]:
            t = s.get("type", _TYPE_STR)
            if t != item_type:
                item_type = _TYPE_MIXED
                break
        return {"type": _TYPE_ARRAY, "items": {"type": item_type}}
    if isinstance(value, dict):
        props: dict[str, Any] = {}
        for k, v in value.items():
            props[k] = _infer_schema_from_value(v, depth + 1)
        return {"type": _TYPE_OBJECT, "properties": props}
    return {"type": _TYPE_STR}


def _merge_schemas(s1: dict[str, Any], s2: dict[str, Any], depth: int) -> dict[str, Any]:
    """Merge two inferred schemas (union of keys; merge types)."""
    if depth > _MAX_DEPTH:
        return s1

    t1 = s1.get("type", _TYPE_STR)
    t2 = s2.get("type", _TYPE_STR)

    if t1 != t2:
        return {"type": _TYPE_MIXED}

    if t1 == _TYPE_OBJECT and "properties" in s1 and "properties" in s2:
        all_keys = set(s1["properties"]) | set(s2["properties"])
        merged_props: dict[str, Any] = {}
        for k in all_keys:
            p1 = s1["properties"].get(k, {"type": _TYPE_STR})
            p2 = s2["properties"].get(k, {"type": _TYPE_STR})
            merged_props[k] = _merge_schemas(p1, p2, depth + 1)
        return {"type": _TYPE_OBJECT, "properties": merged_props}

    if t1 == _TYPE_ARRAY and "items" in s1 and "items" in s2:
        merged_items = _merge_schemas(s1["items"], s2["items"], depth + 1)
        return {"type": _TYPE_ARRAY, "items": merged_items}

    return s1


def infer_response_schema(
    records: list[tuple[dict[str, Any], Any]],
) -> dict[str, Any]:
    """Infer a minimal response schema from a list of (metadata, response_body) records.

    JSON dict/list bodies are merged; non-JSON or binary are summarized as string/binary.
    """
    if not records:
        return {"type": _TYPE_STR, "note": "no samples"}

    schemas: list[dict[str, Any]] = []
    non_json_count = 0

    for _metadata, response_body in records:
        if response_body is None:
            non_json_count += 1
            continue
        if isinstance(response_body, str):
            if response_body.startswith("<binary:") and "bytes>" in response_body:
                schemas.append({"type": _TYPE_BINARY, "note": "binary response"})
            else:
                schemas.append({"type": _TYPE_STR})
            continue
        if isinstance(response_body, (dict, list)):
            schemas.append(_infer_schema_from_value(response_body, 0))
            continue
        non_json_count += 1

    if not schemas:
        return {"type": _TYPE_STR, "note": "no JSON samples", "non_json_count": non_json_count}

    result = schemas[0]
    for s in schemas[1:]:
        result = _merge_schemas(result, s, 0)

    if non_json_count > 0:
        result["non_json_count"] = non_json_count
    return result
