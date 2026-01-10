# Agent Guide for ETF Weekly Report

## Commands

**Backend (from `backend/`):**
- Test all: `pytest` or `pytest -v`
- Test single: `pytest tests/test_api.py::TestHealthCheck::test_health_check`
- Coverage: `pytest --cov=app --cov-report=html`
- Lint: `flake8 app/` (max-line-length: 100)
- Run: `uvicorn app.main:app --reload --port 8000`

**Frontend (from `frontend/`):**
- Test all: `npm test`
- Test single: `npm test -- ErrorBoundary.test.jsx`
- Coverage: `npm run test:coverage`
- Lint: `npm run lint`
- Dev: `npm run dev` (port 5173)

## Code Style

**Python:** PEP 8, 4-space indent, type hints required, async/await for I/O, docstrings for all functions, snake_case variables, PascalCase classes, UPPER_CASE constants, imports sorted by isort (black profile), line length 100

**JavaScript/React:** 2-space indent, functional components + hooks, PropTypes required, camelCase variables, PascalCase components, UPPER_CASE constants, ESLint rules enforced

**Error Handling:** Use try/except with specific exceptions (Python), try/catch with proper error boundaries (React)

**Testing:** Class-based organization (`TestClassName`), Given-When-Then pattern, 100% coverage required before moving to next phase, use fixtures for DB setup (Python), use msw for API mocking (React)

**Documentation:** Korean for business logic comments, English for technical terms, update API_SPECIFICATION.md for new endpoints, update DATABASE_SCHEMA.md for schema changes

**Critical Rules:** Read CLAUDE.md first, all tests must pass 100% before next phase (see DEFINITION_OF_DONE.md), update TODO.md when completing tasks, respond in Korean
