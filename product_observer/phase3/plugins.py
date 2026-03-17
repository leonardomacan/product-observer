"""Discover and invoke domain plugins. Runner does not depend on a specific domain."""

from typing import Any, Callable, List

# Plugin contract: annotate(endpoints: list[dict]) -> list[dict]
# Returns one annotation dict per endpoint (same length). Annotation may include:
# category, domain_hint, entities, workflow_hint, purpose
Annotator = Callable[[List[dict[str, Any]]], List[dict[str, Any]]]


def get_domain_annotator(domain_name: str) -> Annotator:
    """Return the annotate function for a domain module. Raises if domain unknown."""
    if domain_name == "wms":
        from product_observer.domains.wms import annotate
        return annotate
    if domain_name == "ecommerce":
        from product_observer.domains.ecommerce import annotate
        return annotate
    if domain_name == "erp":
        from product_observer.domains.erp import annotate
        return annotate
    raise ValueError(f"Unknown domain: {domain_name}")


def merge_annotations(
    endpoints: List[dict[str, Any]],
    annotation_lists: List[List[dict[str, Any]]],
) -> List[dict[str, Any]]:
    """Merge per-endpoint annotations from multiple plugins. Later non-empty values override."""
    n = len(endpoints)
    merged: List[dict[str, Any]] = [{} for _ in range(n)]
    for ann_list in annotation_lists:
        if len(ann_list) != n:
            continue
        for i in range(n):
            for k, v in ann_list[i].items():
                if v is None or (isinstance(v, list) and len(v) == 0):
                    continue
                if k == "entities" and k in merged[i] and isinstance(merged[i][k], list):
                    merged[i][k] = list(set(merged[i][k]) | set(v)) if isinstance(v, list) else v
                else:
                    merged[i][k] = v
    return merged
