# 개발 계획서

> **대상**: `docs/requirments.md` 기반 3단계 로드맵  
> **타겟 사용자**: 초보~중급 주식 투자자  
> **현재 스택**: FastAPI + SQLite/PostgreSQL / React + Vite + TailwindCSS + Recharts  
> **작성일**: 2026-02-09  
> **최종 갱신**: 2026-02-11
>
> ### 구현 상태 범례
> - ✅ 구현 완료
> - 🔧 부분 구현 (계획과 다른 방식으로 구현됨)
> - ⬜ 미구현

---

## 목차

- [1단계: 실시간 / 준실시간 데이터](#1단계-실시간--준실시간-데이터)
- [2단계: 경쟁력 확보](#2단계-경쟁력-확보)
  - [2-1. 알림 / 푸시 기능](#2-1-알림--푸시-기능--부분-구현)
  - [2-2. 비교 페이지 고도화](#2-2-비교-페이지-고도화--구현-완료)
  - [2-3. 종목 발굴 / 스크리닝](#2-3-종목-발굴--스크리닝--미구현)
- [3단계: 차별화 / 가치 제고](#3단계-차별화--가치-제고)
- [공통 인프라](#공통-인프라)
- [일정 요약](#일정-요약)
- [리스크 및 의존성](#리스크-및-의존성)

---

## 1단계: 실시간 / 준실시간 데이터 ⬜ 미구현

> **목표**: 네이버 금융 스크래핑 의존을 탈피하고, 정규 데이터 소스 기반 준실시간 데이터를 제공한다.

### 1-1. 한국투자증권 Open API 연동 ⬜

| 항목 | 내용 |
|------|------|
| **현재** | 네이버 금융 웹스크래핑 (BeautifulSoup + Selenium), 장 마감 후 15:50 배치 수집 |
| **목표** | 한국투자증권 Open API로 교체, 장중 1~5분 간격 준실시간 가격 |
| **선정 이유** | 무료 개인 계좌 기반, REST + WebSocket 모두 지원, 국내 주식/ETF 커버리지 충분 |

#### 백엔드 작업

| # | 작업 | 상세 | 영향 범위 |
|---|------|------|----------|
| 1 | **API 클라이언트 모듈** | `backend/app/services/kis_client.py` 신규 생성. OAuth 토큰 발급/갱신, 호출 래퍼 | 신규 |
| 2 | **가격 수집기 교체** | `data_collector.py`의 `collect_prices()` 내부에서 네이버 → KIS API 호출로 교체. 기존 `etfApi.getPrices()` 응답 스키마 유지 | `services/data_collector.py` |
| 3 | **매매동향 수집기 교체** | 투자자별 매매동향 API 연동. 기존 `collect_trading_flow()` 교체 | `services/data_collector.py` |
| 4 | **분봉 수집기 교체** | `intraday_collector.py`에서 Selenium 제거, KIS 분봉 API 사용 | `services/intraday_collector.py` |
| 5 | **스케줄러 갱신 주기** | 장중(09:00~15:30) 5분 간격 수집 추가. 기존 15:50 일일 수집은 유지 | `services/scheduler.py` |
| 6 | **환경 변수 추가** | `.env`에 `KIS_APP_KEY`, `KIS_APP_SECRET`, `KIS_ACCOUNT_NO` 추가 | `config.py`, `.env.example` |
| 7 | **폴백(Fallback)** | KIS API 장애 시 네이버 스크래핑으로 자동 폴백. 기존 코드를 삭제하지 않고 `fallback_collector.py`로 리네임 | `services/` |

#### 1-2. WebSocket 실시간 스트리밍 ⬜

| # | 작업 | 상세 | 영향 범위 |
|---|------|------|----------|
| 8 | **WebSocket 엔드포인트** | `backend/app/routers/ws.py` 신규. FastAPI WebSocket, 종목별 채널 구독 | 신규 |
| 9 | **KIS WebSocket 수신** | KIS 실시간 체결가 WebSocket → 내부 브로드캐스트 | `services/kis_client.py` |
| 10 | **프론트엔드 훅** | `frontend/src/hooks/useRealtimePrice.js` 신규. WebSocket 연결 + 재연결 로직 | 신규 |
| 11 | **ETF 상세 반영** | `ETFDetail.jsx`의 최근 가격 영역에 실시간 가격 표시 (기존 API 폴링과 병행) | `pages/ETFDetail.jsx` |
| 12 | **대시보드 반영** | 대시보드 카드에 실시간 가격 뱃지 (선택적 활성화) | `components/etf/ETFCard.jsx` |

#### 프론트엔드 작업

| # | 작업 | 상세 | 영향 범위 |
|---|------|------|----------|
| 13 | **실시간 표시 UI** | 가격 변동 시 깜빡임 애니메이션, 실시간/지연 뱃지 | 공통 컴포넌트 |
| 14 | **설정 연동** | Settings에 "실시간 데이터 사용" 토글 추가 (트래픽 절약) | `GeneralSettingsPanel.jsx`, `SettingsContext.jsx` |

#### DB 변경

- 스키마 변경 **없음**. 기존 `prices`, `trading_flow`, `intraday_prices` 테이블 그대로 사용.
- 수집 주기만 변경(일 1회 → 장중 5분).

#### 의존성 추가

```
# backend/requirements.txt
websockets==12.0        # FastAPI WebSocket + KIS WebSocket
```

```
# frontend/package.json - 추가 없음 (브라우저 네이티브 WebSocket 사용)
```

#### 테스트

| 항목 | 내용 |
|------|------|
| KIS API Mock | `tests/test_kis_client.py` — 토큰 발급, 가격 조회, 에러 처리 |
| WebSocket | `tests/test_ws.py` — 구독/해제, 브로드캐스트 |
| 폴백 | KIS 장애 시 네이버 폴백 동작 확인 |
| 프론트엔드 | `useRealtimePrice` 훅 테스트 (연결/재연결/메시지 파싱) |

---

## 2단계: 경쟁력 확보

### 2-1. 알림 / 푸시 기능 🔧 부분 구현

> **목표**: 앱을 열지 않아도 가격 목표, 급등/급락, 수급 변화를 알려준다.

#### DB 변경 ✅ 구현 완료

```sql
-- ✅ 구현됨 (계획보다 확장된 스키마로 구현)
-- alert_type: 'buy' | 'sell' | 'price_change' | 'trading_signal'
-- direction: 'above' | 'below' | 'both'
CREATE TABLE alert_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    alert_type TEXT NOT NULL,
    direction TEXT NOT NULL,
    target_price REAL NOT NULL,      -- 목표가(buy/sell) 또는 임계%(price_change) 또는 0(trading_signal)
    memo TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_triggered_at TIMESTAMP,
    FOREIGN KEY (ticker) REFERENCES etfs(ticker)
);

-- ✅ 구현됨
CREATE TABLE alert_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_id INTEGER NOT NULL,
    ticker TEXT NOT NULL,
    alert_type TEXT NOT NULL,
    message TEXT,
    triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (rule_id) REFERENCES alert_rules(id)
);
```

#### 백엔드 작업

| # | 작업 | 상세 | 영향 범위 | 상태 |
|---|------|------|----------|------|
| 1 | **알림 라우터** | `backend/app/routers/alerts.py` 신규. CRUD + 트리거 기록 + 이력 조회 | 신규 | ✅ |
| 2 | **알림 서비스** | 프론트엔드 `useAlertChecker` 훅에서 직접 감지하는 방식으로 구현 (백엔드 평가 엔진 대신) | `hooks/useAlertChecker.js` | 🔧 |
| 3 | **알림 체크 스케줄** | 프론트엔드에서 분봉/매매동향 갱신 시 자동 체크 (백엔드 스케줄러 연동은 미구현) | - | 🔧 |
| 4 | **브라우저 푸시** | Web Push (VAPID 키 기반). `services/push_service.py` | 신규 | ⬜ |
| 5 | **이메일 알림** | SMTP 연동 (선택). `services/email_service.py` | 신규 | ⬜ |
| 6 | **카카오 알림톡** | 카카오 비즈니스 API (3단계로 미룰 수도 있음) | 신규 | ⬜ |

#### 프론트엔드 작업

| # | 작업 | 상세 | 영향 범위 | 상태 |
|---|------|------|----------|------|
| 7 | **알림 설정 UI** | 종목 상세 '오늘의 가격 흐름' 하단에 3탭 패널 (목표가/급등급락/매매시그널). ±% 퀵버튼 + 직접 입력, 매수/매도 분류, 활성/비활성 토글 | `components/etf/PriceTargetPanel.jsx` | ✅ |
| 7-1 | **목표가 차트 시각화** | 설정된 목표가를 분봉 차트(IntradayChart)에 빨간(매수)/파란(매도) 점선으로 표시 | `components/charts/IntradayChart.jsx` | ✅ |
| 7-2 | **알림 감지 훅** | 분봉 갱신 시 3종 알림 자동 감지 + 토스트 팝업(5초) + 백엔드 이력 기록 | `hooks/useAlertChecker.js` | ✅ |
| 7-3 | **전역 알림 저장소** | AlertContext로 세션 내 알림 이력 관리 | `contexts/AlertContext.jsx` | ✅ |
| 8 | **알림 목록 페이지** | `/alerts` 신규 라우트. 활성 규칙 목록, 이력, 토글 | 신규 페이지 | ⬜ |
| 9 | **알림 뱃지** | 헤더에 벨 아이콘 + 미확인 알림 개수 빨간 배지 + 클릭 시 이력 드롭다운 | `components/layout/Header.jsx` | ✅ |
| 10 | **Service Worker** | 브라우저 푸시 수신용 SW 등록. PWA 기반 | 신규 (`public/sw.js`) | ⬜ |
| 11 | **푸시 구독** | `navigator.serviceWorker` + `PushManager` 구독. 토큰 서버 전송 | `services/push.js` | ⬜ |

#### 의존성 추가

```
# backend - 현재 추가 의존성 없음 (브라우저 푸시 미구현)
# pywebpush==2.0.0    # ⬜ Web Push (미구현)
# py-vapid==1.9.1     # ⬜ VAPID 키 생성 (미구현)

# frontend - 없음 (브라우저 네이티브 Push API)
```

#### 2-1 구현 요약

> **구현된 것**: DB 스키마(alert_rules, alert_history), 백엔드 CRUD+트리거 API, 프론트 알림 설정 UI(3탭: 목표가/급등급락/매매시그널), ±% 빠른 설정, 분봉 차트 목표가 시각화, 3종 알림 자동 감지(useAlertChecker), 토스트 알림, 헤더 벨 배지+이력 드롭다운  
> **미구현**: 브라우저 Web Push(Service Worker), 이메일/카카오 알림, 독립 알림 페이지(/alerts), 백엔드 스케줄러 연동 평가 엔진

---

### 2-2. 비교 페이지 고도화 ✅ 구현 완료

> **목표**: 비교 페이지에 투자 시뮬레이션, 위험-수익 산점도, 상관관계 히트맵을 추가하여 초보 투자자도 직관적으로 종목을 비교할 수 있게 한다.

#### 백엔드 변경: 없음

- `correlation_matrix`는 기존 비교 API 응답에 이미 포함
- `statistics`에 `period_return`, `volatility` 등 필요 데이터 모두 포함

#### 프론트엔드 작업

| # | 작업 | 상세 | 영향 범위 | 상태 |
|---|------|------|----------|------|
| 1 | **투자 시뮬레이션 카드** | 100만원 기준 종목별 평가액·수익률 카드 그리드 + 한줄 요약(최고 수익/최저 변동성) | `components/comparison/InvestmentSimulation.jsx` (신규) | ✅ |
| 2 | **위험-수익 산점도** | Recharts ScatterChart (X: 변동성, Y: 수익률) + 사분면 기준선 + 설명 범례 | `components/comparison/RiskReturnScatter.jsx` (신규) | ✅ |
| 3 | **상관관계 히트맵** | CSS Grid N×N 테이블, 상관계수 색상 그라데이션(파랑0→빨강1), 다크모드 반응형 | `components/comparison/CorrelationHeatmap.jsx` (신규) | ✅ |
| 4 | **비교 페이지 배치** | 5개 섹션 순서 배치: 시뮬레이션 → 산점도 → 히트맵 → 가격차트 → 성과테이블 | `pages/Comparison.jsx` | ✅ |

#### 배치 순서

1. 투자 시뮬레이션 카드 + 한줄 요약 (상단)
2. 위험-수익 산점도
3. 상관관계 히트맵
4. 정규화 가격 추이 차트 (기존)
5. 성과 비교 테이블 (기존)

---

### 2-3. 종목 발굴 / 스크리닝 ⬜ 미구현

> **목표**: 등록 종목 이외에도 전체 시장에서 조건에 맞는 ETF를 탐색·추천한다.

#### DB 변경

```sql
-- stock_catalog 테이블에 컬럼 추가 (스크리닝 데이터)
ALTER TABLE stock_catalog ADD COLUMN close_price REAL;
ALTER TABLE stock_catalog ADD COLUMN daily_change_pct REAL;
ALTER TABLE stock_catalog ADD COLUMN volume INTEGER;
ALTER TABLE stock_catalog ADD COLUMN weekly_return REAL;
ALTER TABLE stock_catalog ADD COLUMN foreign_net INTEGER;
ALTER TABLE stock_catalog ADD COLUMN institutional_net INTEGER;
ALTER TABLE stock_catalog ADD COLUMN catalog_updated_at TIMESTAMP;
```

#### 백엔드 작업

| # | 작업 | 상세 | 영향 범위 |
|---|------|------|----------|
| 1 | **스크리닝 API** | `GET /api/screening` — 조건 필터(수익률, 변동성, 수급 등), 정렬, 페이지네이션 | 신규 라우터 |
| 2 | **테마 탐색 API** | `GET /api/screening/themes` — 테마별 ETF 목록 (stock_catalog.sector 기반 그룹핑) | 신규 |
| 3 | **추천 API** | `GET /api/screening/recommendations` — 외국인 매수 급증, 주간 수익률 상위 등 프리셋 | 신규 |
| 4 | **카탈로그 데이터 수집** | 스케줄러에 일일 1회 `stock_catalog` 가격/수급 업데이트 추가 (ETF만, 약 500~700종목) | `services/ticker_catalog_collector.py` |

#### 프론트엔드 작업

| # | 작업 | 상세 | 영향 범위 |
|---|------|------|----------|
| 5 | **스크리닝 페이지** | `/screening` 신규 라우트. 필터 패널 + 결과 테이블 + "내 종목에 추가" 버튼 | 신규 페이지 |
| 6 | **테마 탐색 탭** | 스크리닝 페이지 내 탭 (테마별 그리드 뷰) | 신규 컴포넌트 |
| 7 | **추천 카드** | 대시보드 하단에 "이번 주 주목 ETF" 카드 섹션 | `pages/Dashboard.jsx` |
| 8 | **헤더 메뉴 추가** | 네비게이션에 "종목 발굴" 메뉴 | `components/layout/Header.jsx` |

---

## 3단계: 차별화 / 가치 제고

### 3-1. AI 기반 분석 ⬜ 미구현

> **목표**: 룰 기반 인사이트를 LLM 기반으로 업그레이드하여, 초보자도 이해할 수 있는 자연어 분석을 제공한다.

#### 백엔드 작업

| # | 작업 | 상세 | 영향 범위 |
|---|------|------|----------|
| 1 | **LLM 서비스** | `backend/app/services/llm_service.py` 신규. OpenAI/Claude API 래퍼, 프롬프트 관리, 응답 캐싱 | 신규 |
| 2 | **종목 AI 분석 API** | `GET /api/etfs/{ticker}/ai-analysis` — 가격+수급+뉴스 데이터를 LLM에 전달, 종합 분석 반환 | `routers/etfs.py` |
| 3 | **뉴스 감성 분석** | 뉴스 수집 시 LLM으로 감성 점수 (긍정/부정/중립) 부여. `news` 테이블에 `sentiment` 컬럼 추가 | `services/news_analyzer.py` |
| 4 | **자연어 질의 API** | `POST /api/ai/ask` — "이 종목 지금 사도 될까요?" 등 질의 → LLM 응답 | 신규 라우터 |
| 5 | **포트폴리오 AI 코치** | `GET /api/portfolio/ai-advice` — 포트폴리오 데이터 기반 리밸런싱/리스크 제안 | 신규 라우터 |
| 6 | **응답 캐싱** | LLM 호출 비용 절약. 동일 종목+기간 조합 1시간 캐시 | `utils/cache.py` 확장 |
| 7 | **비용 제어** | 일일 LLM 호출 한도 설정 (사용자별, 전체), 초과 시 룰 기반 폴백 | `services/llm_service.py` |

#### DB 변경

```sql
-- news 테이블에 감성 분석 컬럼 추가
ALTER TABLE news ADD COLUMN sentiment TEXT;          -- 'positive' | 'negative' | 'neutral'
ALTER TABLE news ADD COLUMN sentiment_score REAL;    -- -1.0 ~ 1.0

-- AI 분석 캐시 테이블
CREATE TABLE ai_analysis_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    analysis_type TEXT NOT NULL,   -- 'summary' | 'ask' | 'portfolio'
    input_hash TEXT NOT NULL,      -- 입력 데이터 해시 (캐시 키)
    response TEXT NOT NULL,        -- LLM 응답 (JSON)
    model TEXT,                    -- 사용된 모델명
    tokens_used INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP
);
CREATE INDEX idx_ai_cache_lookup ON ai_analysis_cache(ticker, analysis_type, input_hash);
```

#### 프론트엔드 작업

| # | 작업 | 상세 | 영향 범위 |
|---|------|------|----------|
| 8 | **AI 분석 섹션** | ETF 상세 페이지에 "AI 종합 분석" 카드 (InsightSummary 상단 또는 대체) | `pages/ETFDetail.jsx` |
| 9 | **감성 뱃지** | 뉴스 타임라인 각 항목에 감성 아이콘 (긍정🟢/부정🔴/중립⚪) | `components/news/NewsTimeline.jsx` |
| 10 | **자연어 질의 UI** | ETF 상세에 "AI에게 물어보기" 입력 + 대화형 응답 | 신규 컴포넌트 |
| 11 | **포트폴리오 AI 코치** | 포트폴리오 분석 리포트에 "AI 조언" 섹션 추가 | `components/portfolio/PortfolioAnalysisReport.jsx` |

#### 의존성 추가

```
# backend
openai==1.12.0       # OpenAI API (GPT-4o)
tiktoken==0.6.0      # 토큰 카운트 (비용 추정)
# 또는
anthropic==0.18.0    # Claude API (대안)
```

---

### 3-2. 백테스팅 / 투자 시뮬레이션 강화 ⬜ 미구현

> **목표**: 과거 데이터 기반으로 "그때 샀다면?" / "매월 적립했다면?" 시뮬레이션을 제공한다.

#### 백엔드 작업

| # | 작업 | 상세 | 영향 범위 |
|---|------|------|----------|
| 1 | **백테스트 서비스** | `backend/app/services/backtest_service.py` 신규 | 신규 |
| 2 | **일시 투자 API** | `POST /api/backtest/lump-sum` — 특정 날짜 매수 → 현재 수익률, 최대 수익/손실 구간 | 신규 라우터 |
| 3 | **적립식 API** | `POST /api/backtest/dca` — 매월 N만원씩 → 누적 투자금 vs 평가금 추이 | 신규 라우터 |
| 4 | **포트폴리오 백테스트** | `POST /api/backtest/portfolio` — 비중 조합 → 기간 성과, 리밸런싱 효과 | 신규 라우터 |
| 5 | **데이터 충분성 검증** | 백테스트 요청 시 데이터 부족하면 자동 수집 후 실행 (기존 온디맨드 수집 활용) | `services/backtest_service.py` |

**요청/응답 예시 (적립식)**

```json
// POST /api/backtest/dca
{
  "ticker": "487240",
  "monthly_amount": 300000,
  "start_date": "2024-01-01",
  "end_date": "2026-01-31",
  "buy_day": 1
}

// Response
{
  "ticker": "487240",
  "total_invested": 7200000,
  "total_valuation": 8150000,
  "total_return_pct": 13.19,
  "monthly_data": [
    { "date": "2024-01-02", "buy_price": 12500, "shares_bought": 24, "cumulative_invested": 300000, "cumulative_valuation": 300000 },
    ...
  ]
}
```

#### 프론트엔드 작업

| # | 작업 | 상세 | 영향 범위 |
|---|------|------|----------|
| 6 | **백테스트 페이지** | `/backtest` 신규 라우트. 탭 3개 (일시투자 / 적립식 / 포트폴리오) | 신규 페이지 |
| 7 | **일시투자 폼** | 종목 선택, 매수일, 금액 입력 → 수익 차트 + 요약 | 신규 컴포넌트 |
| 8 | **적립식 폼** | 종목, 월 금액, 기간, 매수일 → 누적 투자 vs 평가 Area 차트 | 신규 컴포넌트 |
| 9 | **포트폴리오 백테스트** | 종목+비중 조합 설정 → 기간 성과 라인 차트 + 통계 테이블 | 신규 컴포넌트 |
| 10 | **비교 페이지 연동** | 기존 InvestmentSimulation에 "상세 시뮬레이션" 링크 → `/backtest`로 이동 | `components/comparison/InvestmentSimulation.jsx` |
| 11 | **헤더 메뉴** | "백테스트" 메뉴 추가 | `components/layout/Header.jsx` |

---

## 공통 인프라

모든 단계에서 필요하지만, 각 단계와 병행하여 점진적으로 구축하는 항목.

### 라우팅 변경 요약

```jsx
// App.jsx 최종 라우트 (신규 추가분)
<Route path="/alerts" element={<Alerts />} />         // 2-1
<Route path="/screening" element={<Screening />} />   // 2-3
<Route path="/backtest" element={<Backtest />} />      // 3-2
```

### 헤더 네비게이션 최종

```
대시보드 | 종목 발굴 | 비교 | 백테스트 | 포트폴리오 | 알림 | 설정
```

### 환경 변수 추가 (`.env.example` 갱신)

```bash
# 1단계: 한국투자증권 API
KIS_APP_KEY=
KIS_APP_SECRET=
KIS_ACCOUNT_NO=

# 2단계: 브라우저 푸시
VAPID_PUBLIC_KEY=
VAPID_PRIVATE_KEY=
VAPID_SUBJECT=mailto:admin@example.com

# 2단계: 이메일 (선택)
SMTP_HOST=
SMTP_PORT=
SMTP_USER=
SMTP_PASSWORD=

# 3단계: AI
OPENAI_API_KEY=
# 또는
ANTHROPIC_API_KEY=
LLM_DAILY_LIMIT=100     # 일일 LLM 호출 한도
```

### 테스트 전략

| 영역 | 도구 | 커버리지 목표 |
|------|------|-------------|
| 백엔드 단위 | pytest + httpx | 각 신규 서비스 80%+ |
| 백엔드 통합 | pytest + TestClient | 신규 API 엔드포인트 전수 |
| 프론트엔드 | Vitest + RTL + MSW | 신규 컴포넌트·페이지 |
| E2E (선택) | Playwright | 핵심 유저 플로우 (알림 설정, 스크리닝, 백테스트) |

---

## 일정 요약

```
1단계: 실시간 데이터 ⬜ ───────────────────────────────
  │
  ├─ [1주차] KIS API 클라이언트 + 토큰 관리 + 가격 수집기 교체
  ├─ [2주차] 매매동향/분봉 수집기 교체 + 스케줄러 + 폴백
  ├─ [3주차] WebSocket 엔드포인트 + 프론트 훅 + UI 반영
  ├─ [4주차] 테스트 + 설정 UI + 통합 검증
  │
  총 예상: 4주
  ─────────────────────────────────────────────────────

2단계: 경쟁력 확보 🔧 (일부 구현) ───────────────────
  │
  ├─ 2-1. 알림 (3주) → 🔧 인앱 알림 구현 완료, 브라우저 푸시 미구현
  │   ├─ [1주차] DB 스키마 + 알림 라우터/서비스 + 규칙 평가 엔진  ✅
  │   ├─ [2주차] 브라우저 푸시 (VAPID + SW) + 프론트 알림 UI      🔧 (인앱만)
  │   └─ [3주차] 알림 페이지 + 이력 + 헤더 뱃지 + 테스트          🔧 (헤더 뱃지만)
  │
  ├─ 2-2. 비교 페이지 고도화 (1주) ✅ 구현 완료
  │   └─ 투자 시뮬레이션 + 산점도 + 히트맵 + 배치 순서 변경
  │
  ├─ 2-3. 스크리닝 (3주) ⬜
  │   ├─ [1주차] stock_catalog 확장 + 일일 수집 + 스크리닝 API
  │   ├─ [2주차] 테마 탐색 + 추천 API + 프론트 스크리닝 페이지
  │   └─ [3주차] 대시보드 추천 카드 + 테스트 + 통합 검증
  │
  총 예상: 7주 (2-1~2-3 순차 진행 시)
  ─────────────────────────────────────────────────────

3단계: 차별화 ⬜ ──────────────────────────────────────
  │
  ├─ 3-1. AI 분석 (4주) ⬜
  │   ├─ [1주차] LLM 서비스 + 프롬프트 설계 + 캐싱 + 비용 제어
  │   ├─ [2주차] 종목 AI 분석 API + 뉴스 감성 분석
  │   ├─ [3주차] 자연어 질의 + 포트폴리오 AI 코치
  │   └─ [4주차] 프론트 UI (AI 카드, 감성 뱃지, 질의 UI) + 테스트
  │
  ├─ 3-2. 백테스팅 (3주) ⬜
  │   ├─ [1주차] 백테스트 서비스 + 일시투자/적립식 API
  │   ├─ [2주차] 포트폴리오 백테스트 API + 데이터 충분성 검증
  │   └─ [3주차] 프론트 백테스트 페이지 (3탭) + 비교 페이지 연동
  │
  총 예상: 7주 (3-1과 3-2를 순차 진행 시)
  ─────────────────────────────────────────────────────

전체 총 예상: 약 17주 (4개월)
```

---

## 리스크 및 의존성

| 리스크 | 영향 | 대응 |
|--------|------|------|
| **KIS API 계정 발급 지연** | 1단계 전체 블로킹 | 사전 신청 필수. 계좌 개설 → API 신청 → 승인(1~3영업일) |
| **KIS API 호출 제한** | 초당 10건, 일 10만건 | Rate limiter 적용, 캐시 활용, 불필요한 호출 제거 |
| **네이버 스크래핑 차단** | 폴백 불가 | 1단계에서 KIS 전환 완료 전까지 User-Agent 로테이션 유지 |
| **LLM 비용 초과** | 3단계 운영비 상승 | 일일 한도, 캐싱(1시간), 간단한 질의는 룰 기반 유지 |
| **Web Push 브라우저 제한** | iOS Safari 지원 제한적 | PWA + 이메일 알림 병행 |
| **데이터 정합성** | 수집 소스 변경 시 과거 데이터와 불일치 | 전환 시점 기록, 과거 데이터는 그대로 유지 + 소스 태깅 |

---

## 단계별 산출물

| 단계 | 산출물 | 상태 |
|------|--------|------|
| **1단계** | KIS API 연동, WebSocket 실시간, Selenium 제거, 폴백 체계 | ⬜ 미구현 |
| **2단계** | 알림 시스템(브라우저 푸시), 비교 페이지 고도화, 종목 스크리닝 | 🔧 2-1 인앱 알림 구현, 2-2 비교 고도화 완료 |
| **3단계** | AI 종합 분석, 뉴스 감성 분석, 자연어 질의, 백테스팅 3종 | ⬜ 미구현 |

---

## 구현 현황 상세 (2026-02-11 기준)

### ✅ 구현 완료 항목

| 영역 | 파일 | 설명 |
|------|------|------|
| DB | `backend/app/database.py` | `alert_rules`, `alert_history` 테이블 + 인덱스 생성 |
| 모델 | `backend/app/models.py` | `AlertRuleCreate`, `AlertRuleUpdate`, `AlertRuleResponse` Pydantic 모델 |
| API | `backend/app/routers/alerts.py` | CRUD(GET/POST/PUT/DELETE) + 트리거 기록(POST /trigger) + 이력 조회(GET /history/{ticker}) |
| API 등록 | `backend/app/main.py` | `/api/alerts` 프리픽스로 라우터 등록 |
| API 서비스 | `frontend/src/services/api.js` | `alertApi` — CRUD + `recordTrigger` + `getHistory` |
| 알림 감지 | `frontend/src/hooks/useAlertChecker.js` | 3종 알림 자동 감지 (목표가/급등급락/매매시그널) + 세션 중복 방지 |
| 전역 상태 | `frontend/src/contexts/AlertContext.jsx` | 알림 이력 관리 + 미읽음 카운트 |
| 앱 래핑 | `frontend/src/App.jsx` | `AlertProvider` 래핑 |
| 알림 설정 UI | `frontend/src/components/etf/PriceTargetPanel.jsx` | 3탭(목표가/급등급락/매매시그널) + ±% 퀵버튼 + 3자리 콤마 입력 |
| 차트 시각화 | `frontend/src/components/charts/IntradayChart.jsx` | 목표가 ReferenceLine 표시 |
| 헤더 뱃지 | `frontend/src/components/layout/Header.jsx` | 벨 아이콘 + 미읽음 배지 + 이력 드롭다운 |
| 페이지 연동 | `frontend/src/pages/ETFDetail.jsx` | `useAlertChecker` 훅 연동, alertRules를 차트에 전달 |
| 투자 시뮬레이션 | `frontend/src/components/comparison/InvestmentSimulation.jsx` | 100만원 기준 카드 그리드 + 한줄 요약 (최고 수익/최저 변동성) |
| 위험-수익 산점도 | `frontend/src/components/comparison/RiskReturnScatter.jsx` | Recharts ScatterChart + 사분면 기준선/설명 |
| 상관관계 히트맵 | `frontend/src/components/comparison/CorrelationHeatmap.jsx` | CSS Grid N×N, 상관계수 색상 그라데이션, 다크모드 반응형 |
| 비교 페이지 배치 | `frontend/src/pages/Comparison.jsx` | 5개 섹션 순서 배치 + subtitle 업데이트 |

### ⬜ 미구현 항목

| 영역 | 설명 |
|------|------|
| 1단계 전체 | KIS API 연동, WebSocket 실시간 스트리밍, 스케줄러 갱신 |
| 2-1 브라우저 푸시 | Web Push (Service Worker + VAPID), 이메일, 카카오 알림톡 |
| 2-1 알림 페이지 | `/alerts` 독립 라우트 (전체 알림 규칙 관리 + 이력 페이지) |
| 2-1 백엔드 평가 엔진 | `alert_service.py` (서버사이드 규칙 평가, 스케줄러 연동) |
| 2-3 전체 | 종목 발굴 / 스크리닝 |
| 3-1 전체 | AI 기반 분석 |
| 3-2 전체 | 백테스팅 / 투자 시뮬레이션 강화 |

---

> **다음 단계**: 2-1 인앱 알림 + 2-2 비교 페이지 고도화가 구현 완료되었습니다. 이후 진행 순서:
> 1. 2-1 나머지: 브라우저 푸시 + 독립 알림 페이지
> 2. 1단계: KIS API 연동 (데이터 소스 전환)
> 3. 2-3: 종목 발굴/스크리닝
> 4. 3단계: AI 분석 + 백테스팅
