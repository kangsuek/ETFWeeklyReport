# Agent Guide for ETF Weekly Report

## Terminology

- **web** — Web server/web app related (main branch: backend, frontend, API, etc.)
- **mac app** — Mac app (feature/macos-app branch, `macos/` folder, Electron/DMG)
- **windows app** — Windows app (feature/windows-app branch, `windows/` folder)

Branch policy: [docs/BRANCHES.md](docs/BRANCHES.md)

## Commands

**just (project root, recommended):**
- `just` / `just --list` — List available commands
- `just setup` — Configure dependencies and .env
- `just db` — Initialise database
- `just dev` — Start backend and frontend servers simultaneously
- `just backend` / `just frontend` — Run servers individually
- `just test` — Backend + frontend tests
- `just test-backend` / `just test-frontend` / `just lint` etc.

**Backend (from `backend/`): uv-only**
- Test all: `uv run pytest` or `just test-backend`
- Test single: `uv run pytest tests/test_api.py::TestHealthCheck::test_health_check`
- Coverage: `uv run pytest --cov=app --cov-report=html` or `just test-backend-cov`
- Lint: `uv run flake8 app/` (max-line-length: 100)
- Run: `uv run uvicorn app.main:app --reload --port 8000` or `just backend`

**Frontend (from `frontend/`):**
- Test all: `npm test` or `just test-frontend`
- Test single: `npm test -- --run ErrorBoundary.test.jsx`
- Coverage: `npm run test:coverage` or `just test-frontend-cov`
- Lint: `npm run lint` or `just lint-frontend`
- Dev: `npm run dev` (port 5173) or `just frontend`

## Code Style

**Python:** PEP 8, 4-space indentation, type hints required, async/await for I/O, docstrings for all functions, snake_case variables, PascalCase classes, UPPER_CASE constants, imports sorted by isort (black profile), line length 100

**JavaScript/React:** 2-space indentation, functional components + hooks, PropTypes required, camelCase variables, PascalCase components, UPPER_CASE constants, ESLint rules enforced

**Error Handling:** Use try/except with specific exceptions (Python), try/catch with proper error boundaries (React)

**Testing:** Class-based organisation (`TestClassName`), Given-When-Then pattern, 100% coverage required before moving to next phase, use fixtures for database setup (Python), use msw for API mocking (React)

**Documentation:** Korean for business logic comments, English for technical terms, update API_SPECIFICATION.md for new endpoints, update DATABASE_SCHEMA.md for schema changes

**Number Formatting:** Always apply thousands separators to all numbers displayed to the user (prices, volumes, counts, etc.). Use `f"{value:,}"` in Python and `toLocaleString()` or `Intl.NumberFormat` in JavaScript/React. Example: `1234567` → `1,234,567`.

**Critical Rules:** Read CLAUDE.md first, all tests must pass before merging (see DEVELOPMENT_GUIDE.md for test policy), respond in Korean
