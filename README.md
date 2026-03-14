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
main.py                    # Entry point
product_observer/
├── config.py              # Settings (Pydantic + dotenv)
├── logging_config.py      # Rich-based logging
├── utils/delays.py        # Human-like delay helper
├── models/network.py      # NetworkEvent model
├── storage/file_store.py  # Persist responses to disk
├── browser/controller.py   # Playwright persistent context
├── network/observer.py    # Request filtering, capture, logging
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

```bash
python main.py
```

1. A browser window opens and navigates to your target URL
2. Log in manually
3. Interact with the app as needed
4. API traffic is captured and logged in real time
5. Press **Ctrl+C** to stop

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

- **Phase 2** – Endpoint clustering and schema inference
- **Phase 3** – Domain/entity discovery (domains/wms, ecommerce, erp: endpoint patterns, entity extractors, workflow rules)
- **Phase 4** – Documentation and knowledge generation (templates per domain)
- HTML/DOM introspection

## Technical Stack

- Python 3.9+
- Playwright (browser automation)
- Pydantic (configuration and models)
- python-dotenv (environment loading)
- Rich (console logging)
