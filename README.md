# ETF Weekly Report Web Application

한국 고성장 섹터 **ETF·주식**에 대한 종합 분석 및 리포팅 웹 애플리케이션입니다.  
종목은 **설정**에서 자유롭게 추가·수정·삭제할 수 있으며, 포트폴리오(매입가·수량)를 입력하면 투자 현황과 기여도까지 한눈에 볼 수 있습니다.

---

## 주요 기능

| 기능 | 설명 |
|------|------|
| **대시보드** | 상단 **히트맵**(전체 현황·일간 변동률, 투자/관심 종목 구분) + 하단 **카드 그리드**(종가, 등락률, 미니 차트, 매매동향, 뉴스). 정렬(설정순·타입·이름·테마·커스텀), 드래그앤드롭 순서 변경, 자동/수동 갱신 |
| **종목 상세** | 투자 전략·핵심 포인트, 가격/통계, 가격·매매동향·RSI·MACD 차트, 분봉, 지지/저항선, 뉴스 타임라인 |
| **종목 비교** | 2~6종목 선택, 정규화 가격 차트(시작일=100), 수익률·변동성·MDD·샤프 비율 비교 테이블 |
| **포트폴리오** | 총 투자금·평가금·손익·수익률, 비중 파이차트, 일별 추이 차트, 종목별 기여도 테이블, 포트폴리오 분석 리포트 |
| **종목 발굴** | ETF 조건 검색(주간수익률·수급 필터), 히트맵/테이블 뷰, 테마 탐색, 데이터 수집·진행률 표시 |
| **시뮬레이션** | 일시 투자(그때 샀다면?), 적립식(DCA) 투자, 포트폴리오 시뮬레이션 — 과거 데이터 기반 수익률 차트·테이블 |
| **알림** | 종목별 목표가 알림 규칙 설정 (상한/하한), 알림 이력 조회 |
| **설정** | 다크 모드, 자동 갱신 간격, 기본 날짜 범위, **종목 추가/수정/삭제**, 데이터 수집·DB 초기화·캐시 관리 |

---

## 대상 종목 (예시)

종목은 **설정 > 종목 관리**에서 추가·삭제할 수 있습니다.  
초기 설치 시 `backend/config/stocks.json`에 등록된 종목이 사용되며, 예시는 다음과 같습니다.

- **ETF**: K-반도체, 글로벌반도체, KODEX 200미국채혼합, 로봇액티브, K방산, 조선TOP3, AI전력핵심설비, 양자컴퓨팅, 글로벌원자력, 금채굴기업, 자동차, 커버드콜 등
- **주식**: HD현대일렉트릭 등

매입가·수량을 입력한 종목은 **투자 종목**, 미입력 종목은 **관심 종목**으로 구분되어 대시보드 히트맵과 포트폴리오에 반영됩니다.

---

## 로컬 실행 가이드 (Quick Start)

### 사전 요구사항

| 요구사항 | 버전 | 확인 명령어 |
|---------|------|------------|
| **uv** | 최신 | `uv --version` (백엔드 필수) |
| **just** | 최신 | `just --version` (명령 러너, 권장) |
| Node.js | 18+ | `node --version` |
| npm | 9+ | `npm --version` |
| Git | 최신 | `git --version` |

uv 설치: `curl -LsSf https://astral.sh/uv/install.sh | sh` 또는 `brew install uv`  
just 설치: https://github.com/casey/just#installation (예: `brew install just`)

### 한 번에 설정·실행

상세 절차는 **[docs/SETUP_GUIDE.md](./docs/SETUP_GUIDE.md)**를 따르세요. 요약:

1. `backend`에서 `uv venv` → `uv pip install -r requirements-dev.txt`  
2. 프로젝트 루트에서 `cp .env.example .env` (필요 시 편집)  
3. `backend`에서 `uv run python -m app.database` (DB 초기화)  
4. `frontend`에서 `npm install`  
5. 프로젝트 루트에서 `./scripts/start-servers.sh` (백엔드 8000 + 프론트 5173)

- **백엔드**: http://localhost:8000 (API 문서: `/docs`)
- **프론트엔드**: http://localhost:5173

---

## just 명령 (권장)

프로젝트 루트에 `justfile`이 있습니다. `just --list`로 전체 명령을 볼 수 있습니다.

| 명령 | 설명 |
|------|------|
| `just dev` / `just start` | 백엔드(8000) + 프론트(5173) 동시 시작 |
| `just stop` | 실행 중인 서버 종료 |
| `just setup` | 백엔드·프론트 의존성 설치 및 .env 복사 |
| `just db` | DB 초기화 |
| `just backend` | 백엔드만 실행 |
| `just frontend` | 프론트엔드만 실행 |
| `just test` | 백엔드 + 프론트엔드 테스트 |
| `just run` | run.sh 실행 (의존성 설치 포함 전체 실행) |

## 스크립트

| 명령 | 설명 |
|------|------|
| `./scripts/start-servers.sh` | 백엔드(8000) + 프론트(5173) 동시 시작 |
| `./scripts/stop-servers.sh` | 실행 중인 서버 종료 |

---

## 테스트

- **한 번에**: `just test` (백엔드 + 프론트)
- **백엔드**: `just test-backend` 또는 `cd backend && uv run pytest` (상세: [SETUP_GUIDE.md](./docs/SETUP_GUIDE.md))
- **프론트엔드**: `just test-frontend` 또는 `cd frontend && npm test` / `npm run test:coverage`

---

## 주요 API (요약)

| 구분 | 엔드포인트 예시 |
|------|-----------------|
| 종목 | `GET /api/etfs`, `GET /api/etfs/{ticker}`, `GET /api/etfs/{ticker}/prices`, `GET /api/etfs/{ticker}/trading-flow`, `GET /api/etfs/{ticker}/metrics`, `GET /api/etfs/{ticker}/insights`, `GET /api/etfs/{ticker}/intraday` |
| 배치·비교 | `POST /api/etfs/batch-summary`, `GET /api/etfs/compare?tickers=...` |
| 뉴스 | `GET /api/news/{ticker}` |
| 데이터 | `POST /api/data/collect-all`, `GET /api/data/scheduler-status`, `GET /api/data/stats`, `DELETE /api/data/reset` |
| 설정 | `GET/POST /api/settings/stocks`, `PUT/DELETE /api/settings/stocks/{ticker}`, `GET /api/settings/stocks/search`, `POST /api/settings/stocks/reorder`, `POST /api/settings/ticker-catalog/collect` |
| 알림 | `GET /api/alerts/{ticker}`, `POST /api/alerts/`, `PUT /api/alerts/{rule_id}`, `DELETE /api/alerts/{rule_id}` |
| 종목 발굴 | `GET /api/scanner`, `GET /api/scanner/themes`, `POST /api/scanner/collect-data`, `GET /api/scanner/collect-progress`, `POST /api/scanner/cancel-collect` |
| 시뮬레이션 | `POST /api/simulation/lump-sum`, `POST /api/simulation/dca`, `POST /api/simulation/portfolio` |

상세 스펙은 [docs/API_SPECIFICATION.md](./docs/API_SPECIFICATION.md) 및 [docs/FEATURES.md](./docs/FEATURES.md)를 참고하세요.

---

## 기술 스택

상세: [docs/TECH_STACK.md](./docs/TECH_STACK.md)  
Backend: FastAPI, Python 3.11+, uv(필수), SQLite/PostgreSQL · Frontend: React 18, Vite 5, Tailwind CSS, TanStack Query, Recharts

---

## 문서

| 문서 | 설명 |
|------|------|
| [CLAUDE.md](./CLAUDE.md) | 문서 인덱스 |
| [docs/FEATURES.md](./docs/FEATURES.md) | 제공 기능 상세 |
| [docs/SETUP_GUIDE.md](./docs/SETUP_GUIDE.md) | 환경 설정·실행·Pre-commit |
| [docs/DEVELOPMENT_GUIDE.md](./docs/DEVELOPMENT_GUIDE.md) | 개발 가이드 |
| [docs/API_SPECIFICATION.md](./docs/API_SPECIFICATION.md) | REST API 명세 |
| [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) | 시스템 아키텍처 |
| [docs/PROJECT_STRUCTURE.md](./docs/PROJECT_STRUCTURE.md) | 파일 구조 (표준 정합성) |
| [docs/DATABASE_SCHEMA.md](./docs/DATABASE_SCHEMA.md) | DB 스키마 |
| [docs/INTRADAY.md](./docs/INTRADAY.md) | 분봉 차트 조회·수집 |
| [docs/TECH_STACK.md](./docs/TECH_STACK.md) | 기술 스택 |
| [docs/RENDER_DEPLOYMENT.md](./docs/RENDER_DEPLOYMENT.md) | Render.com 배포 |
| [docs/SECURITY_CHECKLIST.md](./docs/SECURITY_CHECKLIST.md) | 보안 체크리스트 |

---

## 데이터 소스

- **네이버 금융**: 가격, 투자자별 매매 동향, 분봉
- **네이버 검색 API**: 뉴스 (선택, API 키 필요)

---

## 라이센스

MIT License
