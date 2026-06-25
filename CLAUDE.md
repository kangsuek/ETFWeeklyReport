# CLAUDE.md

이 파일은 이 저장소에서 작업할 때 Claude Code(claude.ai/code)에게 가이드를 제공합니다.

# ETF Weekly Report

한국 고성장 섹터 **ETF 및 주식**을 위한 종합 분석 웹 애플리케이션입니다.

이 프로젝트는 ETF 리포트/분석 애플리케이션으로 웹(main), Mac 앱(feature/macos-app, Electron/DMG), Windows 앱(feature/windows-app)으로 구성됩니다. 코드베이스는 JavaScript(프론트엔드)와 Python(백엔드)을 사용합니다. 기능을 찾을 때는 두 가지 명명 규칙을 모두 확인하세요.

## 명령어 (Commands)

명령어는 프로젝트 루트에서 [`just`](justfile)로 실행합니다. `just --list`로 전체 레시피를 확인할 수 있습니다. 백엔드는 **uv**만 사용하고(순수 `pip`/`python` 사용 금지), 프론트엔드는 **npm**을 사용합니다.

**설정 및 실행 (기본 SQLite 워크플로, Docker 불필요):**
- `just setup` — 백엔드(uv venv) + 프론트엔드 의존성 설치, `.env.example`에서 `.env` 복사
- `just db` — SQLite 데이터베이스 초기화/리셋 (멱등)
- `just dev` — 백엔드(8000) + 프론트엔드(5173) 동시 실행; 개별 실행은 `just backend` / `just frontend`
- `just stop` — 실행 중인 개발 서버 종료

**테스트:**
- `just test` — 백엔드 + 프론트엔드; 개별 실행은 `just test-backend` / `just test-frontend`
- 백엔드 단일 테스트: `cd backend && uv run pytest tests/test_api.py::TestHealthCheck::test_health_check`
- 백엔드 빠른 피드백: `-x` 옵션을 붙이거나 단일 파일만 지정 — 전체 `uv run pytest`는 5분 이상 걸릴 수 있음(스크래퍼/수집기 네트워크 모킹)
- 프론트엔드 단일 테스트: `cd frontend && npm test -- --run ErrorBoundary.test.jsx`
- 커버리지: `just test-backend-cov` / `just test-frontend-cov`

**린트 및 빌드:**
- `just lint` (백엔드 flake8 max-line-length=100 + 프론트엔드 eslint)
- 프론트엔드 빌드: `cd frontend && npm run build`

**PostgreSQL (선택, Docker):** `just pg-dev`는 5432 포트의 Postgres로 실행됩니다; `just test-postgres-full`은 5433 테스트 컨테이너를 띄우고 `tests/test_postgres_specific.py`를 실행한 뒤 종료합니다. DB 백엔드는 런타임에 `DATABASE_URL` 환경 변수로 선택됩니다(미설정 시 SQLite).

## 사용자 선호 (User Preferences)
사용자의 이름은 강석(kangsuek)입니다. 사용자가 한글로 작성하면 한글로 소통하세요. 코드 주석과 커밋 메시지는 별도 요청이 없으면 영어를 기본으로 합니다.

## Git 워크플로 (Git Workflow)
코드를 커밋할 때는 작업에 맞는 브랜치를 사용하세요: **main** = 웹 전용; **feature/macos-app** = Mac 앱(`macos/` 폴더); **feature/windows-app** = Windows 앱(`windows/` 폴더). [docs/BRANCHES.md](docs/BRANCHES.md)를 참고하세요. git 작업 전에는 항상 `git status`와 `git branch`를 확인하세요.

## 테스트 및 검증 (Testing & Verification)
여러 파일을 변경한 후에는 커밋 전에 항상 빌드/테스트 스위트를 실행해 깨진 것이 없는지 확인하세요. 프론트엔드는 빌드 명령을, 백엔드 Python 코드는 기존 테스트를 실행하세요.

## 작업 스타일 (Working Style)
구현 작업 시에는 간결하게, 신속하게 행동하세요. 과도하게 설명하거나 작업 시작 전에 코드베이스 탐색에 지나치게 많은 시간을 쓰지 마세요. 사용자가 계획 문서를 제공했다면 그대로 따르세요.

## 숫자 표기 (Number Formatting)
사용자에게 보여주는 모든 숫자(가격, 거래량, 개수 등)에는 항상 천 단위 구분 기호를 표시하세요. 쉼표 사용: `1,234,567`. Python에서는 `f"{value:,}"`, JavaScript/React에서는 `toLocaleString()` 또는 `Intl.NumberFormat`을 사용하세요.

## 아키텍처 (큰 그림)

FastAPI 백엔드(`backend/app/`) + React/Vite 프론트엔드(`frontend/src/`)가 루트의 단일 `.env`를 공유합니다. 프론트엔드는 `/api` 기본 경로 아래의 REST로 백엔드와 통신합니다. 동일한 API를 소비하는 두 외부 클라이언트가 있습니다: 자동 생성되는 OpenAPI Python SDK(`sdk/`)와 MCP 서버(`mcp-server/`). 전체 다이어그램은 [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)에 있습니다.

**백엔드 레이어: Router(HTTP) → Service(비즈니스 로직) → DB / 외부 API.**
- `app/routers/` — API 영역별 라우터(`etfs`, `news`, `data`, `settings`, `alerts`, `scanner`, `simulation`, `market`). 엔드포인트는 여기에 추가하고 `docs/API_SPECIFICATION.md`를 갱신하세요.
- `app/services/` — 수집기 및 분석기. 시장 데이터(가격/매매동향/분봉/펀더멘털)는 **네이버 금융**에서, KOSPI/KOSDAQ 지수는 **네이버 모바일 API**에서, 뉴스는 **네이버 검색 API**에서 가져옵니다(`NAVER_*` 키 필요, 선택 — 없으면 뉴스 비활성화). AI 분석 리포트는 `perplexity_service`가 **Perplexity sonar** 모델로 생성합니다(`PERPLEXITY_API_KEY` 필요). 외부 API 키는 Settings 화면에서 `backend/config/api-keys.json`으로 관리합니다.
- `app/services/scheduler.py` — APScheduler가 주기 수집(N분마다), 일일 수집(평일 15:30 KST), 주간 종목 목록 수집을 구동합니다.
- `app/database.py` — `DATABASE_URL`에 따라 SQLite 또는 PostgreSQL을 투명하게 대상으로 하는 커넥션 풀. 스키마 변경은 `docs/DATABASE_SCHEMA.md`에 반영하세요.
- 거래 종목 목록은 `backend/config/stocks.json`에 있으며 `app/utils/stocks_manager.py`를 통해 DB에 동기화됩니다.

**프론트엔드 패턴: Page → Components → Hooks/Context → `services/api.js` → 백엔드.** 서버 상태는 TanStack React Query, 앱 상태는 React Context(설정/토스트/알림), 영속화는 LocalStorage로 처리합니다. 페이지는 라우트와 1:1로 매핑됩니다(`/`, `/etf/:ticker`, `/compare`, `/portfolio`, `/scanner`, `/simulation`, `/alerts`, `/settings`).

**성능 참고:** 대시보드는 `GET /api/etfs`와 `POST /api/etfs/batch-summary`를 결합해 N+1을 방지합니다.

**멀티 플랫폼:** 웹 앱은 `main`, Electron/DMG Mac 앱(`macos/`)은 `feature/macos-app`, Windows 앱(`windows/`)은 `feature/windows-app`에 있습니다. 작업하는 폴더에 맞는 브랜치에 커밋하세요.

## 핵심 문서 (필수)

1. **[README.md](./README.md)** - 프로젝트 개요, 자산 설정, 빠른 시작 가이드
2. **[FEATURES.md](./docs/FEATURES.md)** - 제공 기능 상세(백엔드 API, 프론트엔드)
3. **[DEVELOPMENT_GUIDE.md](./docs/DEVELOPMENT_GUIDE.md)** - 개발 가이드, 테스트 전략(AGENTS.md 참고)

## 참고 문서 (Reference Documents)

### 기술 문서
- **[ARCHITECTURE.md](./docs/ARCHITECTURE.md)** - 시스템 아키텍처
- **[API_SPECIFICATION.md](./docs/API_SPECIFICATION.md)** - REST API 명세
- **[API_MANUAL.md](./docs/API_MANUAL.md)** - REST API 상세 매뉴얼
- **[DATABASE_SCHEMA.md](./docs/DATABASE_SCHEMA.md)** - 데이터베이스 스키마
- **[TECH_STACK.md](./docs/TECH_STACK.md)** - 기술 스택

### SDK & MCP
- **[SDK_MCP_SETUP_GUIDE.md](./docs/SDK_MCP_SETUP_GUIDE.md)** - OpenAPI Python SDK 및 MCP 서버 설정 가이드

### 상세 기능
- **[detail_features/3-7.IntradayChart.md](./docs/detail_features/3-7.IntradayChart.md)** - 분봉 차트 조회 및 수집

### 개발, 설정, 배포
- **[frontend/DEPLOYMENT.md](./frontend/DEPLOYMENT.md)** - Render.com 배포(환경 변수 포함)


중요: 이 컨텍스트는 작업과 관련이 있을 수도, 없을 수도 있습니다. 작업에 매우 관련이 있는 경우가 아니라면 이 컨텍스트에 응답하지 마세요.
