# Phases

This document defines the evolution phases of the Product Observer project.

---

## Current phase

**The project is currently in Phase 1 — Network Observation.**

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

**Planned scope:**

- Endpoint clustering and grouping of similar requests.
- Schema inference from request/response payloads.
- Optional use of domain-specific patterns from the `domains/` layer to improve classification.

---

## Phase 3 — Domain Discovery

**Planned scope:**

- Domain and entity discovery from captured data.
- Activation of the **domain layer** (`domains/wms`, `domains/ecommerce`, `domains/erp`) with:
  - Endpoint patterns
  - Entity extractors
  - Workflow rules

---

## Phase 4 — Knowledge & Documentation Generation

**Planned scope:**

- Documentation generation from observed behavior and domain models.
- Knowledge artifacts (e.g. API catalogs, workflow descriptions) and optional templates per domain.

---

## Evolutionary pipeline

The intended progression is:

**Network Capture → API Intelligence → Domain Discovery → Knowledge Generation**

Each phase consumes or extends the outputs of the previous phase without replacing the core observation and capture capability established in Phase 1.
