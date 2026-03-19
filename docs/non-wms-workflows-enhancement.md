# Non-WMS workflows: domain annotations enhancement (Plan Notes)

## Goal (Option B)

You want **high-quality “workflows / categories / entities” for non-WMS sites**. That primarily means improving the **Phase 3 domain annotation layer**, because Phase 4 structures its output based on Phase 3 annotations.

## Why “domains” matter (where they feed into outputs)

### Phase 3: annotation plugins

Phase 3 runs domain plugins to annotate each endpoint:

- `product_observer/phase3/plugins.py` defines the plugin contract and maps domain names (`wms`, `ecommerce`, `erp`) to modules.
- `product_observer/phase3/run.py` accepts `--domains` and (by default) runs `["wms"]`.

Each plugin provides:

- `annotate(endpoints) -> list[dict]` (one annotation dict per endpoint)
- Supported annotation fields used downstream:
  - `category`
  - `domain_hint`
  - `entities`
  - `workflow_hint`
  - (optionally) `purpose`

### Phase 4: grouping uses those annotations

Phase 4 generates docs by grouping endpoints using annotation fields:

- `product_observer/phase4/catalog.py` groups endpoints by `annotations.category`
- `product_observer/phase4/workflows.py` groups endpoints by `annotations.workflow_hint`

So if Phase 3 yields empty annotations, Phase 4 will have weak/“Other”/low-signal sections.

## What exists today in this repo

- `product_observer/domains/wms/__init__.py` has real logic:
  - heuristics to infer `category` (auth/config/business)
  - heuristics for `domain_hint` + `workflow_hint` (e.g. “inbound”)
  - heuristic entity extraction from URL/path + `response_schema` keys
- `product_observer/domains/ecommerce/__init__.py` is a stub:
  - returns `{}` (empty annotations) for all endpoints
- `product_observer/domains/erp/__init__.py` is a stub:
  - returns `{}` (empty annotations) for all endpoints

## One important v1 caveat

Even if you want “non-WMS,” the current v1 orchestrator typically biases toward WMS because Phase 3’s default domain list is `["wms"]` unless v1 passes an explicit `--domains` selection into Phase 3.

## Recommended implementation strategy (for Option B)

### Step 1: Add a generic, domain-agnostic plugin

Create a new plugin (e.g. `product_observer/domains/generic/`) that does best-effort annotations for *any* web app by using broad heuristics:

- `category`:
  - detect auth/config/business using general URL/path keywords (not WMS-specific)
- `entities`:
  - extract entity-like tokens from:
    - path/segments (tokenization)
    - response schema keys (similar to the existing WMS approach)
- `workflow_hint`:
  - infer coarse phases using common HTTP/API verbs or path verbs:
    - e.g. login/auth, list/get, create/post, update/put/patch, submit/approve/start/complete
  - fall back to `"Other"` when unknown

This gives Phase 4 a baseline of structure even when the app is not a known domain.

### Step 2: Let v1 orchestrator choose plugins

Expose `--domains` in the v1 CLI (e.g. `observe run ... --domains generic wms ...`) and pass it through to Phase 3 orchestration.

This enables:

- `--domains wms` for warehouse apps
- `--domains generic` for unknown apps / non-WMS apps
- later: real `ecommerce` / `erp` plugins when implemented

### Step 3 (optional): add Phase 4 fallbacks if hints are missing

If `workflow_hint` ends up missing or empty, Phase 4 could group by a fallback signal, such as:

- top-level normalized path segment
- endpoint clustering group identifiers

For now, this is optional; the best initial leverage is improving Phase 3 annotations.

## Quick decision question (before implementation)

Choose the target quality:

1. **Best-effort structure**:
   - Accept “coarse but useful” workflows for non-WMS sites (generic plugin first)
2. **More accurate workflows**:
   - Requires domain-specific plugins or richer inference (generic may still be the starting point)

## Notes for future work

- The domain layer should remain an *optional labeling layer*:
  - The core observation and capture remains domain-agnostic.
- Obsidian sync and dataset structure improvements are independent of the domain plugin quality.

