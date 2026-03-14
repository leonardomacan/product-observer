# Phases

This document defines the evolution phases of the Product Observer project.

---

## Current phase

**The project is currently in Phase 1 (capture), Phase 2 (API intelligence), Phase 3 (domain discovery), and Phase 4 (knowledge & documentation) — all implemented.**

Phase 1 captures network traffic; Phase 2 analyzes captured data (endpoint clustering and schema inference); Phase 3 annotates endpoints using domain plugins; Phase 4 generates API catalog, workflow view, and optional LLM-generated workflow narratives. See implementation sections below.

---

## Phase 1 — Network Observation

**Scope:**

- Launch Playwright browser (persistent context).
- Allow manual login in the browser.
- Observe network traffic (request/response events).
- Capture request/response data for API-like calls (e.g. XHR/fetch or URLs containing `/api/`).
- Persist raw network data to disk (e.g. JSON files per request, optional gzip).
- Console logging of captured events (method, URL, status, size).

**Out of scope for Phase 1:**

- API clustering
- Schema inference
- Domain modeling
- Workflow reconstruction
- LLM usage
- Documentation generation

---

## Phase 2 — API Intelligence

**Scope (implemented):**

- Endpoint clustering and grouping of similar requests (path normalization: ID-like segments → `{id}`).
- Schema inference from response payloads (merge JSON bodies per endpoint; infer types).
- Output: `data/phase2/endpoints.json` (machine-readable) and `data/phase2/api_surface.md` (human-readable).
- Optional use of domain-specific patterns from the `domains/` layer remains for a later iteration.

### Phase 2 implementation

Run Phase 2 analysis on captured Phase 1 data:

```bash
python -m product_observer.phase2
```

- **Input**: `data/raw_requests/` (default); use `--input DIR` to override.
- **Output**: `data/phase2/` (default); use `--output DIR` to override. Writes `endpoints.json` and `api_surface.md` (use `--no-markdown` to skip the markdown file).
- Requires Phase 1 capture data (e.g. `request_001.json`, …) in the input directory.

---

## Phase 3 — Domain Discovery

**Scope (implemented):**

- Domain and entity discovery from Phase 2 output.
- Activation of the **domain layer** (`domains/wms`, `domains/ecommerce`, `domains/erp`) with:
  - Endpoint patterns (e.g. auth, config, business; domain_hint wms)
  - Entity extractors (from path and response_schema)
  - Workflow hints (e.g. inbound)
- Output: `data/phase3/annotated_endpoints.json` (each endpoint gains an `annotations` object).

### Phase 3 implementation

Run Phase 3 annotation on Phase 2 data:

```bash
python -m product_observer.phase3
```

- **Input** (default: `data/phase2/endpoints.json`): path to Phase 2 endpoints JSON. Use `--input PATH` to override.
- **Output** (default: `data/phase3/`): directory for `annotated_endpoints.json`. Use `--output DIR` to override.
- **Domains** (default: `wms`): comma-separated or space-separated list of plugins: `wms`, `ecommerce`, `erp`. Use `--domains wms ecommerce erp` to run all. Ecommerce and ERP are stubs that return empty annotations until implemented.

---

## Phase 4 — Knowledge & Documentation Generation

**Scope (implemented):**

- Documentation generation from observed behavior and domain models.
- Knowledge artifacts: API catalog (`api_catalog.md`), workflow list (`workflows.md`), and optional LLM-generated workflow narratives (`workflow_narratives.md`, “discovery map”).
- Optional context files in `docs/phase4_context/` (or `PHASE4_CONTEXT_DIR`) for the LLM; Anthropic API for narrative generation.

### Phase 4 implementation

Run Phase 4 documentation generation on Phase 3 data:

```bash
python -m product_observer.phase4
```

- **Input** (default: `data/phase3/annotated_endpoints.json`): path to Phase 3 annotated endpoints JSON. Use `--input PATH` to override.
- **Output** (default: `data/phase4/`): directory for `api_catalog.md`, `workflows.md`, and (when enabled) `workflow_narratives.md`. Use `--output DIR` to override.
- **Narratives**: Set `ANTHROPIC_API_KEY` to enable LLM-generated workflow narratives. Use `--no-llm` to skip.
- **Context**: Place `.md` or `.txt` files in `docs/phase4_context/` (or set `PHASE4_CONTEXT_DIR`) to provide the LLM with extra context for the narrative.

**Implementation plan:** See [phase4-implementation-plan.md](phase4-implementation-plan.md) for the full design.

---

## Evolutionary pipeline

The intended progression is:

**Network Capture → API Intelligence → Domain Discovery → Knowledge Generation**

Each phase consumes or extends the outputs of the previous phase without replacing the core observation and capture capability established in Phase 1.
