# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Comprehensive analysis/reporting app for Korean high-growth sector **ETFs and stocks**. It ships in three forms from one codebase: **web** (main), **Mac app** (`feature/macos-app`, Electron/DMG), and **Windows app** (`feature/windows-app`). Backend is Python/FastAPI; frontend is JavaScript/React. When searching for a feature, check both languages.

## User Preferences

- The user's name is 강석 (kangsuek). **Communicate in Korean** when the user writes in Korean. Default to English for code comments and commit messages unless asked otherwise.
- **Number formatting:** always show thousands separators for numbers shown to the user (prices, volumes, counts). Python `f"{value:,}"`; JS/React `toLocaleString()` or `Intl.NumberFormat` → `1,234,567`.
- **Working style:** be concise and act quickly on implementation tasks. Don't over-explain or over-explore before starting. If a plan document is provided, follow it directly.

## Git Workflow

Commit on the branch that matches the work — see [docs/BRANCHES.md](docs/BRANCHES.md):
- **main** = web only (`backend/`, `frontend/`)
- **feature/macos-app** = Mac app (`macos/` folder)
- **feature/windows-app** = Windows app (`windows/` folder)

Run `git status` and `git branch` before any git operations.

## Commands

Use `just` from the project root (`just --list` for all). Backend is **uv-only** (never call `pip`/`python` directly).

```
just setup            # install backend + frontend deps, copy .env
just db               # initialize database
just dev / just start # backend (8000) + frontend (5173) together
just backend / just frontend
just test             # backend + frontend tests
just lint
```

**Backend** (from `backend/`):
- Test all: `uv run pytest`
- Single test: `uv run pytest tests/test_api.py::TestHealthCheck::test_health_check`
- Coverage: `uv run pytest --cov=app --cov-report=html`
- Lint: `uv run flake8 app/` (max-line-length 100)
- Run: `uv run uvicorn app.main:app --reload --port 8000`

**Frontend** (from `frontend/`):
- Test all: `npm test` — single: `npm test -- --run ErrorBoundary.test.jsx`
- Coverage: `npm run test:coverage`
- Lint: `npm run lint` (ESLint, `--max-warnings 0`)
- Build (verify before committing multi-file FE changes): `npm run build`
- Dev: `npm run dev` (port 5173)

After multi-file changes, run the relevant build/test suite before committing (per AGENTS.md, tests must pass before merging).

## Architecture

**Backend — layered FastAPI** (`backend/app/`):
- `main.py` mounts routers under `/api/*` and, on startup: initializes DB, runs migrations, syncs `config/stocks.json` → DB, and starts the background scheduler.
- `routers/` — HTTP endpoints, one file per domain: `etfs`, `news`, `data`, `settings`, `alerts`, `scanner`, `simulation`. Each router prefix mirrors the frontend page of the same name.
- `services/` — business logic. Data is **scraped from Naver Finance** (`naver_finance_scraper.py`, `data_collector.py`, `intraday_collector.py`, `ticker_catalog_collector.py`, fundamentals collectors) and enriched (`insights_service.py`, `comparison_service.py`, `simulation_service.py`, `news_analyzer.py`). `scheduler.py` runs periodic collection; `progress.py` backs the scanner progress-polling endpoints.
- `utils/` — cross-cutting: `cache.py` (in-memory cache; cleared per-request when the `X-No-Cache: true` header is present), `rate_limiter.py`, `retry.py`, `stocks_manager.py` (stocks.json ↔ DB sync), `structured_logging.py`.
- `database.py` — **DB abstraction over SQLite and PostgreSQL**, selected at import time by `DATABASE_URL` (defaults to SQLite at `backend/data/etf_data.db`). Both go through a `ConnectionPool`; always use `get_db_connection()` + `get_cursor()` and `run_migrations()` rather than raw connections so both backends stay supported. Update [docs/DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md) on schema changes.
- `middleware/` — `auth.py` (X-API-Key), `rate_limit.py` (slowapi).

**Frontend — React 18 + Vite** (`frontend/src/`): `pages/` (Dashboard, ETFDetail, Comparison, Portfolio, Screening, Simulation, Alerts, Settings) map 1:1 to backend router domains. `services/api.js` is the single API client; `contexts/` holds Settings/Alert/Toast state; TanStack Query for data fetching, Recharts for charts, Tailwind for styling.

**Desktop apps:** `macos/` and `windows/` are Electron wrappers that bundle and spawn the Python backend as a child process on a dedicated port (e.g. Mac uses **18000** to avoid clashing with the dev server on 8000), health-check it, then load the built frontend. Build config in `macos/electron-builder.yml` and `macos/scripts/`.

**External interfaces** (both generated from / calling the FastAPI app):
- `sdk/` — type-safe Python client generated from the OpenAPI spec (`bash sdk/generate.sh`).
- `mcp-server/` — MCP server exposing ETF data as tools for Claude/MCP clients.

New endpoints: update [docs/API_SPECIFICATION.md](docs/API_SPECIFICATION.md).

## Code Style (see AGENTS.md for full detail)

- **Python:** PEP 8, 4-space indent, type hints, async/await for I/O, docstrings, isort (black profile), line length 100.
- **JS/React:** 2-space indent, functional components + hooks, PropTypes required.
- **Tests:** class-based (`TestClassName`), Given-When-Then; pytest fixtures for DB, msw for API mocking (React).
- **Comments:** Korean for business logic, English for technical terms.

## Key Documentation

- [README.md](./README.md) — overview, quick start, API summary
- [AGENTS.md](./AGENTS.md) — commands, code style, testing conventions
- [docs/FEATURES.md](./docs/FEATURES.md) · [docs/DEVELOPMENT_GUIDE.md](./docs/DEVELOPMENT_GUIDE.md) · [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)
- [docs/API_SPECIFICATION.md](./docs/API_SPECIFICATION.md) · [docs/API_MANUAL.md](./docs/API_MANUAL.md) · [docs/DATABASE_SCHEMA.md](./docs/DATABASE_SCHEMA.md) · [docs/TECH_STACK.md](./docs/TECH_STACK.md)
- [docs/SDK_MCP_SETUP_GUIDE.md](./docs/SDK_MCP_SETUP_GUIDE.md) · [docs/BRANCHES.md](./docs/BRANCHES.md) · [frontend/DEPLOYMENT.md](./frontend/DEPLOYMENT.md)
