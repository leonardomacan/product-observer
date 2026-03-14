# Product Observer

A **domain-agnostic** browser instrumentation tool for **system observation and reverse-engineering** of any web-based application (WMS, ERP, ecommerce, dashboards).

When backend access is restricted or APIs are undocumented, the UI is often the only reliable interface. This tool analyzes the system **from the outside** using a browser: it reuses an authenticated session and observes how the system behaves.

## Phase 1: Network Observability

Phase 1 implements a minimal but functional **network observer** for any web app. It:

- Launches a Playwright browser
- Allows you to log in manually
- Captures all API-like network requests
- Logs endpoints with method, status, and size
- Saves responses locally for offline analysis

No domain modeling or documentation generation yet—just **observe and capture**. Domain specializations (e.g. WMS, ecommerce, ERP) live under `product_observer/domains/` and will be used in later phases.

## Safety Guarantees

**This tool is read-only and passive.**

- **Never modifies requests** — No request interception or alteration
- **Never injects or replays API calls** — Observation only
- **Only passively observes** — Does not drive or automate UI actions beyond opening the initial URL

The toolkit does not change any network traffic. It simply records what the browser sends and receives.

## Architecture Overview

```
main.py                    # Entry point (Phase 1 capture)
product_observer/
├── config.py              # Settings (Pydantic + dotenv)
├── logging_config.py      # Rich-based logging
├── utils/delays.py        # Human-like delay helper
├── models/network.py      # NetworkEvent model
├── storage/file_store.py  # Persist responses to disk
├── browser/controller.py  # Playwright persistent context
├── network/observer.py    # Request filtering, capture, logging
├── phase2/                # Phase 2: load, cluster, infer schemas, report
└── domains/               # Placeholder for domain specializations (wms, ecommerce, erp)
```

## Documentation

- **[docs/architecture.md](docs/architecture.md)** — Architectural vision, principles, components, repository structure, and data flow.
- **[docs/phases.md](docs/phases.md)** — Evolution phases (Network Observation → API Intelligence → Domain Discovery → Knowledge Generation) and current scope.
- **[docs/agent-context.md](docs/agent-context.md)** — Context for AI agents and tooling working on this codebase.

## Installation

### 1. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Install Playwright browsers

```bash
playwright install
```

### 4. Configure environment

```bash
cp .env.example .env
# Edit .env and set TARGET_URL to your target web application URL
```

## How to Run

### Phase 1 — Capture network traffic

```bash
python main.py
```

1. A browser window opens and navigates to your target URL
2. Log in manually
3. Interact with the app as needed
4. API traffic is captured and logged in real time
5. Press **Ctrl+C** to stop

### Phase 2 — Analyze captured data (endpoint clustering + schema inference)

After capturing requests with Phase 1, run Phase 2 to cluster endpoints and infer response schemas:

```bash
python -m product_observer.phase2
```

- **Input** (default: `data/raw_requests/`): directory containing `request_*.json` (or `.json.gz`) from Phase 1.
- **Output** (default: `data/phase2/`): writes `endpoints.json` and `api_surface.md`. Use `--input DIR` and `--output DIR` to override; use `--no-markdown` to skip the markdown report.

### Phase 3 — Domain discovery (annotate endpoints)

After Phase 2, run Phase 3 to annotate endpoints using domain plugins (category, domain_hint, entities):

```bash
python -m product_observer.phase3
```

- **Input** (default: `data/phase2/endpoints.json`): path to Phase 2 endpoints JSON.
- **Output** (default: `data/phase3/`): writes `annotated_endpoints.json`. Use `--input PATH` and `--output DIR` to override.
- **Domains** (default: `wms`): which plugins to run. Use `--domains wms ecommerce erp` to run all. Ecommerce and ERP are stubs by default.

### Phase 4 — Knowledge & documentation (API catalog, workflows, narratives)

After Phase 3, run Phase 4 to generate the API catalog, workflow view, and optional LLM-generated workflow narratives:

```bash
python -m product_observer.phase4
```

- **Input** (default: `data/phase3/annotated_endpoints.json`): path to Phase 3 annotated endpoints JSON.
- **Output** (default: `data/phase4/`): writes `api_catalog.md`, `workflows.md`, and (if enabled) `workflow_narratives.md`. Use `--input PATH` and `--output DIR` to override.
- **Narratives**: Set `ANTHROPIC_API_KEY` to enable LLM-generated workflow narratives. Use `--no-llm` to skip narrative generation.
- **Context for LLM**: Place `.md` or `.txt` files in `docs/phase4_context/` (or set `PHASE4_CONTEXT_DIR`) to give the LLM extra context for the narrative.

## Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TARGET_URL` | Yes | — | Base URL of the target web application |
| `BROWSER_PROFILE_DIR` | No | `./browser_profile` | Persistent browser profile (cookies, sessions) |
| `OUTPUT_DIR` | No | `data/raw_requests` | Directory for saved responses |
| `DELAY_MIN_MS` | No | 300 | Min delay before navigation (ms) |
| `DELAY_MAX_MS` | No | 1500 | Max delay before navigation (ms) |
| `MAX_REQUESTS_PER_SESSION` | No | (none) | Stop after this many captures |
| `FILTER_DOMAIN` | No | true | Only capture requests from target host |
| `COMPRESS_RESPONSES` | No | false | Gzip saved response files |
| `LARGE_RESPONSE_THRESHOLD_BYTES` | No | 1000000 | Warn when response exceeds this size |
| `ANTHROPIC_API_KEY` | No (Phase 4) | — | Required for Phase 4 workflow narratives; omit or use `--no-llm` to skip |
| `PHASE4_CONTEXT_DIR` | No | `docs/phase4_context` | Directory of `.md`/`.txt` files used as context for the narrative LLM |

## Example Output

### Console logs

```
GET /api/tasks -> 200 (12.3 KB) [saved to request_001.json]
POST /api/putaway/start -> 201 (0.5 KB) [saved to request_002.json]
GET /api/locations -> 200 (45.2 KB) [saved to request_003.json]
```

### Saved file structure (`data/raw_requests/request_001.json`)

```json
{
  "metadata": {
    "id": "001",
    "timestamp": "2025-03-06T12:00:00.000000",
    "method": "GET",
    "url": "https://app.example.com/api/tasks",
    "path": "/api/tasks",
    "status_code": 200,
    "response_time_ms": 142.5,
    "response_size_bytes": 12580,
    "resource_type": "fetch"
  },
  "response_body": { ... }
}
```

## Future Roadmap

- **Phase 2** – Implemented: endpoint clustering and schema inference on captured data (`python -m product_observer.phase2`).
- **Phase 3** – Domain/entity discovery (domains/wms, ecommerce, erp: endpoint patterns, entity extractors, workflow rules).
- **Phase 4** – Documentation and knowledge generation (templates per domain).
- HTML/DOM introspection

## Technical Stack

- Python 3.9+
- Playwright (browser automation)
- Pydantic (configuration and models)
- python-dotenv (environment loading)
- Rich (console logging)
