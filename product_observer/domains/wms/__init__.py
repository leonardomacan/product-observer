"""WMS domain: endpoint patterns and entity extractors for warehouse-style applications."""

from typing import Any, List

# Path substrings that suggest auth/session (domain-agnostic labels)
_AUTH_PATTERNS = (
    "authorization",
    "get_login",
    "get_lang",
    "login_info",
    "get_my_menu",
    "get_my_perm",
    "enable_tob_login",
)
# Path substrings that suggest config
_CONFIG_PATTERNS = (
    "config",
    "configuration",
    "get_dev_conf",
    "get_conf_list",
    "get_apollo_config",
    "enums",
)
# Path substrings that suggest WMS inbound / ASN
_WMS_INBOUND_PATTERNS = (
    "inbound",
    "poasn",
    "po_asn",
    "asn",
    "returninbound",
    "pomassputaway",
    "posorting",
    "parcelcounting",
    "transferinbound",
    "purchaseinbound",
    "reprocess",
    "labourplanning",
    "groupactivity",
)
# Schema keys that suggest entities (from response_schema)
_ENTITY_HINTS = ("asn", "sku", "task", "warehouse", "location", "order", "shipment", "putaway", "sorting")


def annotate(endpoints: List[dict[str, Any]]) -> List[dict[str, Any]]:
    """Annotate each endpoint with category, domain_hint, and entities (heuristic)."""
    result: List[dict[str, Any]] = []
    for ep in endpoints:
        path = (ep.get("normalized_path") or "").lower()
        method = (ep.get("method") or "GET").upper()
        ann: dict[str, Any] = {}

        # Category: auth, config, or business
        if any(p in path for p in _AUTH_PATTERNS):
            ann["category"] = "auth"
        elif any(p in path for p in _CONFIG_PATTERNS):
            ann["category"] = "config"
        else:
            ann["category"] = "business"

        # Domain hint: wms if path suggests warehouse/inbound
        if any(p in path for p in _WMS_INBOUND_PATTERNS):
            ann["domain_hint"] = "wms"
            ann["workflow_hint"] = "inbound"

        # Entities from path and schema keys
        entities: List[str] = []
        for hint in _ENTITY_HINTS:
            if hint in path or f"/{hint}" in path or hint in path.replace("-", "_"):
                entities.append(hint.title())
        schema = ep.get("response_schema") or {}
        props = schema.get("properties") or {}
        if isinstance(props, dict):
            for key in props:
                key_lower = key.lower()
                for h in _ENTITY_HINTS:
                    if h in key_lower and h.title() not in entities:
                        entities.append(h.title())
        if entities:
            ann["entities"] = sorted(set(entities))

        result.append(ann)
    return result
