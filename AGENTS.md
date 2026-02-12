# Agent Guide for ETF Weekly Report

## 용어 (Terminology)

- **web** — 웹서버/웹 앱 관련 (main 브랜치: 백엔드, 프론트엔드, API 등)
- **mac app** — Mac 앱 (feature/macos-app 브랜치, `macos/` 폴더, Electron/DMG)
- **windows app** — Windows 앱 (feature/windows-app 브랜치, `windows/` 폴더)

브랜치 정책: [docs/BRANCHES.md](docs/BRANCHES.md)

## Commands

**just (프로젝트 루트, 권장):**
- `just` / `just --list` — 사용 가능한 명령 목록
- `just setup` — 의존성·.env 설정
- `just db` — DB 초기화
- `just dev` — 백엔드+프론트 서버 동시 시작
- `just backend` / `just frontend` — 서버 개별 실행
- `just test` — 백엔드+프론트 테스트
- `just test-backend` / `just test-frontend` / `just lint` 등

**Backend (from `backend/`): uv 전용**
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

**Python:** PEP 8, 4-space indent, type hints required, async/await for I/O, docstrings for all functions, snake_case variables, PascalCase classes, UPPER_CASE constants, imports sorted by isort (black profile), line length 100

**JavaScript/React:** 2-space indent, functional components + hooks, PropTypes required, camelCase variables, PascalCase components, UPPER_CASE constants, ESLint rules enforced

**Error Handling:** Use try/except with specific exceptions (Python), try/catch with proper error boundaries (React)

**Testing:** Class-based organization (`TestClassName`), Given-When-Then pattern, 100% coverage required before moving to next phase, use fixtures for DB setup (Python), use msw for API mocking (React)

**Documentation:** Korean for business logic comments, English for technical terms, update API_SPECIFICATION.md for new endpoints, update DATABASE_SCHEMA.md for schema changes

**Critical Rules:** Read CLAUDE.md first, all tests must pass before merging (see DEVELOPMENT_GUIDE.md for test policy), respond in Korean
