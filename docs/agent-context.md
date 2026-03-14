# Project Context

## Project Overview

**Product Observer** is a domain-agnostic browser instrumentation tool for **system observation and reverse-engineering** of any web-based application (WMS, ERP, ecommerce, dashboards). When backend access is restricted or APIs are undocumented, it analyzes the system from the outside using a browser: reuses an authenticated session and passively observes API traffic.

**Phase 1** delivers a minimal network observer: launch browser → manual login → capture API-like requests → log and save responses for offline analysis. No domain modeling or doc generation yet.

## Architecture

- **Entry**: `main.py` builds settings, storage, browser, and network observer; runs async loop until Ctrl+C.
- **Browser**: Playwright **persistent context** (profile dir) so cookies/sessions persist across runs.
- **Network**: Observer attaches to browser context; filters by resource type (xhr/fetch) and optional domain; blocklists noise (analytics, static assets); records request start time for response-time; on response, builds `NetworkEvent`, saves via `FileStorage`, logs.
- **Storage**: Responses written to disk as JSON (metadata + `response_body`); optional gzip; filenames `request_001.json` (or `.json.gz`).
- **Domains**: `product_observer/domains/` holds placeholders (wms, ecommerce, erp) for future phase specialization.

**Design decisions**: Read-only and passive (no request modification or injection). Config via Pydantic + `.env`. Rich for console logging.

## Tech Stack

- **Language**: Python 3.9+
- **Browser**: Playwright (async)
- **Config/Models**: Pydantic v2, python-dotenv
- **Logging**: Rich
- **Storage**: JSON files on disk (optional gzip)

## Important Files

| Path | Purpose |
|------|--------|
| `main.py` | Entry point; wires config, storage, browser, observer; asyncio run loop |
| `product_observer/config.py` | `Settings` (Pydantic), `get_settings()` cached; loads from env |
| `product_observer/logging_config.py` | Rich handler, project logger `product_observer` |
| `product_observer/browser/controller.py` | `BrowserController`: launch persistent context, open target URL, stop |
| `product_observer/network/observer.py` | `NetworkObserver`: filter API-like requests, capture response, save, log; `attach(context)` |
| `product_observer/storage/file_store.py` | `FileStorage`: save `NetworkEvent` + body to JSON (or gzip) |
| `product_observer/models/network.py` | `NetworkEvent` Pydantic model; `to_metadata_dict()` |
| `product_observer/utils/delays.py` | Human-like delay before navigation |
| `product_observer/domains/*` | Placeholder packages for future domain logic |
| `.env` / `.env.example` | Env vars; `TARGET_URL` required |
| `requirements.txt` | playwright, pydantic, python-dotenv, rich |
| `README.md` | User-facing docs, config table, roadmap |

## Current State

- **Implemented and working**: Phase 1 network observer; Playwright persistent context; env-based config; API-like request filtering (xhr/fetch, optional same-host, blocklist); response capture and JSON file storage; Rich logging; session limit `MAX_REQUESTS_PER_SESSION`; large-response warning; optional gzip.

## Current Task

- None specified. Project is in steady state after Phase 1.

## Constraints / Rules

- **Safety**: Tool is read-only and passive. Never modify or inject requests; only observe and record.
- **Config**: All tunables via environment/`.env`; use `get_settings()`.
- **Paths**: `output_dir`, `browser_profile_dir` resolved to absolute paths.
- **Conventions**: Async entry in `main.py`; observer receives storage, settings, logger; browser exposes `context` for observer `attach`.

## Known Issues

- None documented. Domain packages are empty placeholders.

## Next Steps

- Align with README roadmap: Phase 2 (endpoint clustering, schema inference), Phase 3 (domain/entity discovery), Phase 4 (documentation generation), or HTML/DOM introspection as needed.

## Agent Notes

- **Updating this file**: When the user says **"update agent context"**, read the current project state (code, README, config, recent changes), then update this file: keep it concise (~200–300 lines max), remove outdated info, preserve architecture and constraints, refresh **Current State**, **Current Task**, **Next Steps**, and **Agent Notes** so a new AI session can continue without chat history.
- **Run**: `python main.py` from repo root; set `TARGET_URL` in `.env`; run `playwright install` once.
