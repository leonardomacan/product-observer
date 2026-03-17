"""Endpoint clustering: normalize paths and group requests by (method, normalized_path)."""

import re
from collections import defaultdict
from pathlib import Path
from typing import Any

# Segment is numeric (digits only)
_NUMERIC_RE = re.compile(r"^\d+$")
# UUID (8-4-4-4-12 hex, case-insensitive)
_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
# Long hex string (e.g. 24+ hex chars, no dashes)
_HEX_LONG_RE = re.compile(r"^[0-9a-fA-F]{24,}$")


def _is_id_like(segment: str) -> bool:
    """Return True if the path segment looks like an ID (numeric, UUID, or long hex)."""
    if _NUMERIC_RE.match(segment):
        return True
    if _UUID_RE.match(segment):
        return True
    if _HEX_LONG_RE.match(segment):
        return True
    return False


def normalize_path(path: str) -> str:
    """Replace ID-like path segments with a single placeholder {id}.

    Examples:
        /api/v2/orders/123 -> /api/v2/orders/{id}
        /api/users/550e8400-e29b-41d4-a716-446655440000 -> /api/users/{id}
    """
    if not path or not path.startswith("/"):
        return path
    parts = path.split("/")
    normalized = []
    for part in parts:
        if part == "":
            normalized.append("")
            continue
        if _is_id_like(part):
            # Use a single placeholder so all IDs collapse to one
            normalized.append("{id}")
        else:
            normalized.append(part)
    return "/".join(normalized)


def endpoint_key(method: str, path: str) -> tuple[str, str]:
    """Return (method, normalized_path) for use as endpoint key."""
    return (method.upper().strip(), normalize_path(path))


def cluster_requests(
    records: list[tuple[dict[str, Any], Any]],
) -> dict[tuple[str, str], list[tuple[dict[str, Any], Any]]]:
    """Group records by (method, normalized_path). Each group is a list of (metadata, response_body)."""
    groups: dict[tuple[str, str], list[tuple[dict[str, Any], Any]]] = defaultdict(list)
    for metadata, response_body in records:
        method = metadata.get("method") or "GET"
        path = metadata.get("path") or "/"
        key = endpoint_key(method, path)
        groups[key].append((metadata, response_body))
    return dict(groups)
