"""ERP domain placeholder. Implements annotate() for Phase 3 plugin contract."""

from typing import Any, List


def annotate(endpoints: List[dict[str, Any]]) -> List[dict[str, Any]]:
    """Return empty annotations (stub). Override with ERP patterns when needed."""
    return [{} for _ in endpoints]
