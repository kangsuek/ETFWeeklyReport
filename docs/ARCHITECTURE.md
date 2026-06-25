# 시스템 아키텍처

## 전체 구조

```
┌─────────────────┐         ┌──────────────────┐
│   Web Browser   │ ◄─────► │  React Frontend   │
│   (User)        │         │  (Vite, Port 5173)│
└─────────────────┘         └───────────────────┘
                                      │
┌───────────────────────────────────┐ │ HTTP/REST (Base: /api)
│  External Clients (SDK / MCP)     │ │
│  · OpenAPI Python SDK (sdk/)      │─┤
│  · MCP Server (mcp-server/)       │ │
│    └─ Claude Code / Desktop 등    │ │
└───────────────────────────────────┘ │
                                      │
                            ┌─────────▼──────────┐
                            │  FastAPI Backend   │
                            │  (Port 8000)       │
                            └─────────┬──────────┘
                                      │
        ┌─────────────────────────────┼─────────────────────────────┐
        │                             │                             │
┌───────▼────────┐  ┌────────────────▼────────────────┐  ┌──────────▼──────────┐
│ Data Collector │  │  Scheduler (APScheduler)         │  │  News Scraper       │
│ · 가격/매매동향  │  │  · 주기 수집 (N분 간격)          │  │  (Naver Search API) │
│ · 분봉/펀더멘털  │  │  · 일일 수집 (평일 15:30 KST)    │  ├─────────────────────┤
│ · 시장 지수      │  │  · 종목 목록 수집 (주간)         │  │  Perplexity AI      │
│ (Naver Finance) │  │                                  │  │  (sonar, 분석 리포트)│
└───────┬────────┘  └────────────────┬────────────────┘  └─────────────────────┘
        │                             │
        └──────────────┬──────────────┘
                        │
              ┌─────────▼───────────┐   ┌──────────────────┐
              │  Database           │   │  Config           │
              │  SQLite / PostgreSQL│   │  stocks.json      │
              │  (가격, 뉴스, 매매동향,│   │  (종목 목록)       │
              │   분봉, 펀더멘털, 알림) │   │  api-keys.json    │
              └─────────────────────┘   └──────────────────┘
```

---

## 백엔드 구조

```
backend/app/
├── main.py              # FastAPI 앱 진입점, CORS, Rate Limit, 라우터 등록
├── config.py            # 설정 (환경 변수, stocks.json 로드)
├── database.py          # DB 연결 풀 (SQLite/PostgreSQL)
├── models.py            # Pydantic 요청/응답 모델
├── dependencies.py      # 의존성 주입 (API Key 등)
├── exceptions.py        # 커스텀 예외
├── constants.py         # 상수 (캐시 TTL, 에러 메시지 등)
├── routers/
│   ├── etfs.py          # /api/etfs — 종목 목록, 가격, 매매동향, 지표, 인사이트, 비교, 배치요약, 분봉, 펀더멘털, AI 프롬프트
│   ├── news.py          # /api/news — 뉴스 조회·수집
│   ├── data.py          # /api/data — 일괄 수집, 백필, 펀더멘털 수집, 상태, 스케줄러 상태, 캐시, DB 초기화
│   ├── settings.py      # /api/settings — 종목 CRUD, 검색, 검증, 순서 변경, 종목 목록 수집, API 키 관리
│   ├── alerts.py        # /api/alerts — 알림 규칙 CRUD, 트리거 기록, 이력 조회
│   ├── scanner.py      # /api/scanner — 조건 검색, 테마 탐색, 추천, 데이터 수집
│   ├── simulation.py    # /api/simulation — 일시투자, 적립식(DCA), 포트폴리오 시뮬레이션
│   └── market.py        # /api/market — KOSPI/KOSDAQ 지수 현황·일별 차트 (네이버 모바일 API)
├── services/
│   ├── data_collector.py              # 가격·매매동향 수집 (Naver Finance)
│   ├── naver_finance_scraper.py       # 네이버 금융 스크래핑 공통 모듈
│   ├── intraday_collector.py          # 분봉 수집
│   ├── news_scraper.py                # 뉴스 수집 (Naver Search API)
│   ├── news_analyzer.py               # 뉴스 분석
│   ├── insights_service.py            # 인사이트 생성 (전략, 핵심 포인트)
│   ├── comparison_service.py          # 종목 비교 (정규화 가격, 통계, 상관관계)
│   ├── simulation_service.py          # 투자 시뮬레이션 (일시/적립식/포트폴리오)
│   ├── etf_fundamentals_collector.py  # ETF 펀더멘털 수집 (NAV/AUM, 구성종목, 분배금, 리밸런싱)
│   ├── stock_fundamentals_collector.py# 주식 펀더멘털 수집 (PER/PBR/ROE, 실적, 배당)
│   ├── perplexity_service.py          # Perplexity AI 분석 프롬프트 생성·리포트 (sonar 모델)
│   ├── catalog_data_collector.py      # 스크리닝용 카탈로그 데이터 수집 (가격·수급)
│   ├── progress.py                    # 백그라운드 작업 진행률 관리
│   ├── scheduler.py                   # 주기/일일/백필/종목목록 수집 스케줄
│   ├── ticker_scraper.py              # 티커 검증 (네이버 스크래핑)
│   └── ticker_catalog_collector.py    # 코스피/코스닥/ETF 종목 목록 수집
├── middleware/
│   ├── auth.py          # API Key 검증
│   └── rate_limit.py    # SlowAPI 기반 Rate Limit
└── utils/
    ├── cache.py         # 메모리 캐시 (LRU)
    ├── stocks_manager.py # stocks.json 읽기/쓰기, DB 동기화
    ├── structured_logging.py
    ├── date_utils.py, retry.py, rate_limiter.py, data_collection.py
    └── ...
```

**레이어**: Router(HTTP) → Service(비즈니스 로직) → DB / 외부 API

**설정**: 환경 변수는 **프로젝트 루트**의 `.env` 한 파일만 사용. 종목 목록은 `backend/config/stocks.json` + DB 동기화. 외부 API 키(Naver, Perplexity)는 Settings 화면에서 `backend/config/api-keys.json`으로 관리하며, 시작·저장 시 `os.environ`으로 로드됨.

---

## SDK / MCP 서버 구조

```
ETFWeeklyReport/
├── sdk/
│   ├── openapi.json        # FastAPI에서 추출한 OpenAPI 스펙 (52개 경로)
│   ├── config.yaml         # openapi-python-client 생성 설정
│   ├── generate.sh         # 스펙 추출 + 클라이언트 재생성 스크립트
│   └── python/             # 자동 생성된 Python 클라이언트 (sdk/generate.sh로 생성)
└── mcp-server/
    ├── src/etf_report_mcp/
    │   ├── __init__.py
    │   └── server.py       # MCP 서버 구현 (12개 tool)
    ├── pyproject.toml
    └── README.md
```

- **OpenAPI Python SDK**: `openapi-python-client`로 FastAPI `/openapi.json` 에서 타입 안전 클라이언트 자동 생성. `bash sdk/generate.sh`로 재생성.
- **MCP 서버**: FastAPI에 HTTP 요청을 MCP 도구로 래핑. `ETF_REPORT_BASE_URL`로 연결 대상 설정.

---

## 프론트엔드 구조

```
frontend/src/
├── main.jsx             # React 진입점
├── App.jsx               # 라우팅 (/, /etf/:ticker, /compare, /portfolio, /scanner, /simulation, /alerts, /settings)
├── constants.js          # 캐시 TTL, API 타임아웃 등
├── pages/
│   ├── Dashboard.jsx    # 대시보드 (히트맵 + 카드 그리드)
│   ├── ETFDetail.jsx    # 종목 상세 (인사이트, 가격, 차트, 분봉, 뉴스)
│   ├── Comparison.jsx   # 종목 비교 (정규화 차트, 비교 테이블)
│   ├── Portfolio.jsx    # 포트폴리오 (요약, 비중, 추이, 기여도, 분석 리포트)
│   ├── Screening.jsx    # 종목 발굴 (조건 검색, 히트맵/테이블, 테마 탐색)
│   ├── Simulation.jsx   # 시뮬레이션 (일시투자, 적립식, 포트폴리오)
│   ├── Alerts.jsx       # 알림 (목표가 규칙 관리, 이력)
│   └── Settings.jsx     # 설정 (종목 관리, 일반 설정, 데이터 관리)
├── components/
│   ├── layout/          # Header, Footer
│   ├── dashboard/       # DashboardFilters, ETFCardGrid, PortfolioHeatmap, MarketOverview, MarketIndexModal, RecommendationCards
│   ├── etf/             # ETFCard, ETFHeader, ETFCharts, StrategySummary, InsightSummary, StatsSummary, PriceTable, PriceTargetPanel
│   ├── charts/          # PriceChart, TradingFlowChart, RSIChart, MACDChart, IntradayChart, DateRangeSelector, ChartSkeleton
│   ├── comparison/      # TickerSelector, NormalizedPriceChart, ComparisonTable, CorrelationHeatmap, RiskReturnScatter, InvestmentSimulation
│   ├── portfolio/       # PortfolioSummaryCards, AllocationPieChart, PortfolioTrendChart, ContributionTable, PortfolioAnalysisReport, AIInvestmentReport
│   ├── screening/       # ScreeningFilters, ScreeningTable, ScreeningHeatmap, ThemeExplorer
│   ├── simulation/      # LumpSumSimulation, DCASimulation, PortfolioSimulation
│   ├── settings/        # TickerManagementPanel, TickerForm, GeneralSettingsPanel, DataManagementPanel, TickerDeleteConfirm, ApiKeysPanel
│   ├── news/            # NewsTimeline
│   └── common/          # PageHeader, Spinner, LoadingIndicator, ErrorBoundary, ErrorFallback, Toast, ToastContainer, InfoTooltip, ETFCardSkeleton
├── contexts/             # SettingsContext, ToastContext, AlertContext
├── hooks/                # useContainerWidth, useWindowSize, useAlertChecker
├── services/             # api.js (etfApi, newsApi, dataApi, settingsApi, alertApi, scannerApi, simulationApi, marketApi)
├── utils/                # format, formatters, chartUtils, dateRange, portfolio, portfolioAnalysis, returns, technicalIndicators, validation, insights, newsAnalyzer
├── styles/               # index.css (Tailwind)
└── test/                 # Vitest setup, mocks (MSW), polyfills, utils
```

**패턴**: Page → Components → Hooks / Context → services(api) → Backend

**상태**: TanStack React Query(서버 상태), React Context(설정·토스트·알림), LocalStorage(설정 유지).

---

## 데이터 흐름

### 데이터 수집
1. **주기 수집**: 스케줄러가 N분(설정값)마다 실행 — 가격, 매매동향, 뉴스 수집.
2. **일일 수집**: 평일 15:30 KST — 당일 데이터 일괄 수집.
3. **수동**: `POST /api/data/collect-all`(가격·매매동향·뉴스·펀더멘털), `POST /api/etfs/{ticker}/collect` 등.
4. **분봉**: 종목 상세 페이지 요청 시 데이터 없으면 자동 수집 가능. 또는 `POST /api/etfs/{ticker}/collect-intraday`.
5. **펀더멘털**: `POST /api/data/collect-fundamentals`(전체) 또는 `POST /api/etfs/{ticker}/collect-fundamentals` — STOCK은 실적/배당, ETF는 NAV/구성종목/분배금.
6. **시장 지수**: `GET /api/market/overview`·`/index/{code}/chart` — 네이버 모바일 API에서 KOSPI/KOSDAQ을 온디맨드 조회(30초~5분 캐시).

### AI 분석
- **Perplexity AI**: `GET /api/etfs/{ticker}/ai-prompt`·`POST /api/etfs/ai-prompt-multi`로 분석 프롬프트를 생성하고, `perplexity_service`가 sonar 모델로 리포트를 생성. `prompt/perplexity.md` 템플릿 사용, `PERPLEXITY_API_KEY` 필요(Settings의 API 키 관리에서 입력).

### API 요청 흐름
```
Frontend (TanStack Query / Axios) → FastAPI Router → Service → DB 또는 외부 API → 응답
```
- 대시보드: `GET /api/etfs` + `POST /api/etfs/batch-summary` 로 N+1 방지. 상단 시장 지수는 `GET /api/market/overview`.
- 종목 상세: 가격, 매매동향, 인사이트, 분봉, 뉴스, 펀더멘털 등 개별 또는 병렬 요청.

---

## 배포

| 환경     | Backend      | Frontend     | DB        |
|----------|-------------|-------------|-----------|
| 개발     | localhost:8000 | localhost:5173 | SQLite (로컬) |
| 프로덕션  | Render 등   | Vercel/Netlify 등 | PostgreSQL 권장 |

- 상세: [RENDER_DEPLOYMENT.md](./RENDER_DEPLOYMENT.md)
