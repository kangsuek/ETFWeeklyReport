# API 명세 (API Specification)

ETF Weekly Report 백엔드(FastAPI)가 제공하는 REST API 전체 명세입니다.

- **Base URL**: `http://localhost:8000`
- **API Prefix**: 모든 업무 API는 `/api` 하위에 있습니다.
- **대화형 문서**: 서버 실행 후 `/docs`(Swagger UI), `/redoc`에서도 확인할 수 있습니다.
- 이 문서는 `backend/app/routers/`, `backend/app/models.py`, `backend/app/middleware/` 소스를 기준으로 정리되었습니다.

---

## 공통 사항 (Conventions)

### 인증 (Authentication)

- 인증 방식: **API Key** — 요청 헤더 `X-API-Key: <API_KEY>`.
- 보호 대상: **데이터 변경/삭제/수집** 계열 엔드포인트만 보호됩니다(아래 표의 🔒 표시). 읽기 전용 GET은 대부분 공개입니다.
- 키 값은 서버 환경 변수 `API_KEY`로 설정합니다.
  - `API_KEY` 미설정 + 로컬(개발) 환경: 인증 없이 허용(`dev-mode`).
  - `API_KEY` 미설정 + 프로덕션(`RENDER`/`RAILWAY_ENVIRONMENT`/`FLY_APP_NAME` 감지) 환경: `503`으로 요청 거부.
- 실패 응답: 키 누락/오류 시 `401 Unauthorized`.

### Rate Limiting

클라이언트 IP 기준으로 제한하며, 초과 시 `429 Too Many Requests`(`Retry-After: 60`)를 반환합니다. 표기 없는 엔드포인트는 별도 제한이 없습니다.

| 등급 | 제한 | 적용 예시 |
|------|------|-----------|
| `READ_ONLY` | 200/min | `/api/data/*` 상태·통계 조회 |
| `DEFAULT` | 100/min | 종목 생성/순서변경 |
| `SEARCH` | 30/min | 종목 검색 |
| `DATA_COLLECTION` | 10/min | 데이터 수집/백필 |
| `DANGEROUS` | 5/min | 캐시 삭제, DB 초기화, 카탈로그 수집 |

### 날짜 · 숫자 형식

- 날짜: `YYYY-MM-DD` (ISO 8601). 일부 응답의 시각은 ISO datetime.
- 기본 날짜 범위: 미지정 시 대부분 `end_date=오늘`, `start_date=오늘-N일`.
- 조회 최대 기간: 1년(365일).

### 캐싱

- 인메모리 TTL 캐시. 데이터 종류별 TTL이 다릅니다(가격 30초, 지표/뉴스 1분, 정적 데이터 5분 등).
- 요청 헤더 `X-No-Cache: true` 를 보내면 서버 캐시를 클리어합니다.

### 공통 상태 코드

| 코드 | 의미 |
|------|------|
| 200 | 성공 |
| 201 | 생성됨 |
| 400 | 잘못된 요청(파라미터/검증 오류) |
| 401 | 인증 실패 |
| 404 | 리소스 없음 |
| 429 | 요청 한도 초과 |
| 500 | 서버 내부 오류 |
| 503 | 외부 데이터 소스(스크래퍼) 오류 / 서버 구성 오류 |

---

## 엔드포인트 요약 (Endpoint Overview)

- 🔒 = `X-API-Key` 필요
- † = **프론트엔드 미사용**(백엔드/SDK/MCP/스케줄러/관리자 전용). 프론트 `api.js`에 래퍼가 없거나 제거됨.
- 완전히 제거된(더 이상 존재하지 않는) 엔드포인트는 하단 [제거된 엔드포인트](#제거된-엔드포인트-removed) 참고.

### System
| Method | Path | 설명 |
|--------|------|------|
| GET | `/` | API 정보 |
| GET | `/api/health` | 헬스체크(DB 연결 확인) |

### ETFs — `/api/etfs`
| Method | Path | 인증 | 설명 |
|--------|------|:---:|------|
| GET | `/api/etfs/` | | 전체 종목 목록 |
| GET | `/api/etfs/compare` | | 종목 비교 분석 |
| GET | `/api/etfs/{ticker}` | | 종목 상세 정보 |
| GET | `/api/etfs/{ticker}/prices` | | 가격 데이터(자동 수집) |
| POST | `/api/etfs/{ticker}/collect` | 🔒 † | 가격 데이터 수집 |
| GET | `/api/etfs/{ticker}/trading-flow` | | 투자자별 매매동향(자동 수집) |
| POST | `/api/etfs/{ticker}/collect-trading-flow` | 🔒 † | 매매동향 수집 |
| GET | `/api/etfs/{ticker}/metrics` | | 주요 지표(수익률·변동성) |
| GET | `/api/etfs/{ticker}/insights` | | 투자 인사이트 |
| POST | `/api/etfs/batch-summary` | | 다종목 요약 일괄 조회 |
| GET | `/api/etfs/{ticker}/intraday` | | 분봉(시간별 체결) 조회 |
| POST | `/api/etfs/{ticker}/collect-intraday` | 🔒 † | 분봉 수집 |
| GET | `/api/etfs/{ticker}/ai-prompt` | | 단일 종목 AI 프롬프트 생성 |
| POST | `/api/etfs/ai-prompt-multi` | | 복수 종목 통합 AI 프롬프트 생성 |
| GET | `/api/etfs/{ticker}/fundamentals` | | 펀더멘털 조회 |

### Data Collection — `/api/data`
| Method | Path | 인증 | Rate | 설명 |
|--------|------|:---:|------|------|
| GET | `/api/data/collect-progress` | | | 전체 수집 진행률 |
| POST | `/api/data/collect-all` | 🔒 | 10/min | 전체 종목 일괄 수집(+펀더멘털) |
| POST | `/api/data/backfill` | 🔒 † | 10/min | 히스토리 백필 |
| GET | `/api/data/status` | † | 200/min | 종목별 수집 현황 |
| GET | `/api/data/scheduler-status` | | 200/min | 스케줄러 상태 |
| GET | `/api/data/stats` | | 200/min | DB 통계 |
| GET | `/api/data/cache/stats` | † | 200/min | 캐시 통계 |
| DELETE | `/api/data/reset` | 🔒 | 5/min | DB 초기화(⚠️ 되돌릴 수 없음) |

### News — `/api/news`
| Method | Path | 인증 | 설명 |
|--------|------|:---:|------|
| GET | `/api/news/{ticker}` | | 종목별 뉴스 조회(분석 포함, 없으면 자동 수집) |
| POST | `/api/news/{ticker}/collect` | 🔒 | 뉴스 수집 |

### Settings — `/api/settings`
| Method | Path | 인증 | Rate | 설명 |
|--------|------|:---:|------|------|
| GET | `/api/settings/stocks` | | | 등록 종목 목록 |
| POST | `/api/settings/stocks` | 🔒 | 100/min | 종목 추가(201) |
| PUT | `/api/settings/stocks/{ticker}` | 🔒 | | 종목 수정(부분 업데이트) |
| DELETE | `/api/settings/stocks/{ticker}` | 🔒 | | 종목 삭제(관련 데이터 CASCADE) |
| GET | `/api/settings/stocks/{ticker}/validate` | | | 티커 검증(네이버 조회) |
| GET | `/api/settings/stocks/search` | | 30/min | 종목 검색(자동완성) |
| POST | `/api/settings/stocks/reorder` | 🔒 | 100/min | 종목 순서 변경 |
| GET | `/api/settings/ticker-catalog/collect-progress` | | | 카탈로그 수집 진행률 |
| POST | `/api/settings/ticker-catalog/collect` | 🔒 | 5/min | 전체 종목 카탈로그 수집 |
| GET | `/api/settings/api-keys` | (raw만 🔒) | | 저장된 API 키 조회 |
| PUT | `/api/settings/api-keys` | 🔒 | | API 키 저장 |

### Alerts — `/api/alerts`
| Method | Path | 인증 | 설명 |
|--------|------|:---:|------|
| POST | `/api/alerts/trigger` | 🔒 | 알림 트리거 기록 |
| GET | `/api/alerts/history/{ticker}` | † | 종목별 알림 이력 |
| POST | `/api/alerts/` | 🔒 | 알림 규칙 생성 |
| GET | `/api/alerts/{ticker}` | | 종목별 알림 규칙 목록 |
| PUT | `/api/alerts/{rule_id}` | 🔒 | 알림 규칙 수정 |
| DELETE | `/api/alerts/{rule_id}` | 🔒 | 알림 규칙 삭제 |

### Scanner — `/api/scanner`
| Method | Path | 인증 | Rate | 설명 |
|--------|------|:---:|------|------|
| GET | `/api/scanner` | | | 조건 기반 종목 검색 |
| GET | `/api/scanner/themes` | | | 섹터/테마별 그룹 |
| GET | `/api/scanner/recommendations` | | | 추천 프리셋 |
| GET | `/api/scanner/collect-progress` | | | 카탈로그 데이터 수집 진행률 |
| POST | `/api/scanner/collect-data` | 🔒 | 10/min | 카탈로그 데이터 수집 트리거 |
| POST | `/api/scanner/cancel-collect` | 🔒 | | 수집 중지 |

### Simulation — `/api/simulation`
| Method | Path | 설명 |
|--------|------|------|
| POST | `/api/simulation/lump-sum` | 일시 투자 시뮬레이션 |
| POST | `/api/simulation/dca` | 적립식(DCA) 시뮬레이션 |
| POST | `/api/simulation/portfolio` | 포트폴리오 시뮬레이션 |

### Market — `/api/market`
| Method | Path | 설명 |
|--------|------|------|
| GET | `/api/market/index/{code}/chart` | KOSPI/KOSDAQ 지수 차트 |
| GET | `/api/market/overview` | KOSPI/KOSDAQ 지수 현황 |

---

## 상세 명세 (Details)

### System

#### `GET /`
API 기본 정보 반환.
```json
{ "message": "ETF Weekly Report API", "docs": "/docs", "health": "/api/health" }
```

#### `GET /api/health`
헬스체크. DB 연결을 확인합니다.
```json
{ "status": "healthy", "message": "ETF Report API is running", "database": "connected" }
```
DB 오류 시 `status: "degraded"`, `database: "error: ..."`.

---

### ETFs

#### `GET /api/etfs/`
등록된 전체 종목(ETF + 주식) 목록.

**Response** `List[ETF]`
```json
[
  { "ticker": "487240", "name": "삼성 KODEX AI전력핵심설비 ETF", "type": "ETF",
    "theme": "AI/전력", "purchase_date": null, "purchase_price": null,
    "quantity": null, "search_keyword": null, "relevance_keywords": null }
]
```

#### `GET /api/etfs/compare`
여러 종목의 정규화 가격·통계·상관관계 비교. 데이터가 없으면 자동 수집 시도.

**Query**
| 이름 | 타입 | 필수 | 기본 | 설명 |
|------|------|:---:|------|------|
| `tickers` | string | ✓ | | 쉼표 구분 티커(2~20개) |
| `start_date` | date | | 30일 전 | 시작일 |
| `end_date` | date | | 오늘 | 종료일 |

**Response**: `normalized_prices`(시작일=100), 종목별 `statistics`(period_return, annualized_return, volatility, max_drawdown, sharpe_ratio, data_points), `correlation_matrix`.

#### `GET /api/etfs/{ticker}`
종목 상세. **Response** `ETF`. 없으면 `404`.

#### `GET /api/etfs/{ticker}/prices`
가격 데이터 조회(부족 시 자동 수집, 최대 30초).

**Query**: `start_date`(기본 7일 전), `end_date`(기본 오늘), `days`(범위 대신 최근 N일).

**Response** `List[PriceData]` — 날짜 내림차순.
```json
[{ "date": "2025-11-09", "open_price": 12400, "high_price": 12600,
   "low_price": 12300, "close_price": 12500, "volume": 1000000, "daily_change_pct": 2.5 }]
```

#### `POST /api/etfs/{ticker}/collect` 🔒 †
네이버 금융에서 가격 데이터 수집(프론트 미사용, 화면은 자동수집·`collect-all` 사용). **Query**: `days`(기본 10).
```json
{ "ticker": "487240", "collected": 10, "message": "Successfully collected 10 price records" }
```

#### `GET /api/etfs/{ticker}/trading-flow`
투자자별 매매동향(개인/기관/외국인 순매수). 부족 시 자동 수집.
**Query**: `start_date`(기본 7일 전), `end_date`(기본 오늘). **Response** `List[TradingFlow]`.

#### `POST /api/etfs/{ticker}/collect-trading-flow` 🔒 †
매매동향 수집(프론트 미사용). **Query**: `days`(1~90, 기본 10).

#### `GET /api/etfs/{ticker}/metrics`
주요 지표. **Response** `ETFMetrics`.
```json
{ "ticker": "487240", "aum": null,
  "returns": { "1w": 5.2, "1m": 12.5, "ytd": 18.3 },
  "volatility": 25.4, "max_drawdown": -8.2, "sharpe_ratio": 1.67 }
```

#### `GET /api/etfs/{ticker}/insights`
투자 전략·핵심포인트·리스크. **Query**: `period`(`1w`/`1m`/`3m`/`6m`/`1y`, 기본 `1m`). **Response** `ETFInsights`.

#### `POST /api/etfs/batch-summary`
대시보드용 다종목 요약 일괄 조회(N+1 최적화).

**Body** `BatchSummaryRequest`
```json
{ "tickers": ["487240", "466920"], "price_days": 5, "news_limit": 5 }
```
`tickers` 최대 50개, `price_days` 1~365(기본 5), `news_limit` 1~100(기본 5).

**Response** `BatchSummaryResponse` — `data: { ticker: ETFCardSummary }`. 각 항목에 `latest_price`, `prices`, `weekly_return`, `latest_trading_flow`, `latest_news` 포함.

#### `GET /api/etfs/{ticker}/intraday`
당일 분봉(시간별 체결). 데이터 없으면 백그라운드 수집 시작.

**Query**: `target_date`(기본 오늘), `auto_collect`(기본 true), `force_refresh`(기본 false).
```json
{ "ticker": "487240", "date": "2025-01-24",
  "data": [{ "datetime": "2025-01-24T09:00:00", "price": 12500, "change_amount": 100,
             "volume": 1500, "bid_volume": 800, "ask_volume": 700 }],
  "count": 390, "first_time": "09:00", "last_time": "15:30" }
```
수집 중이면 `background_collect_started: true` 및 안내 메시지 포함.

#### `POST /api/etfs/{ticker}/collect-intraday` 🔒 †
분봉 수집(프론트 미사용, 분봉 조회 시 자동 백그라운드 수집 사용). **Query**: `pages`(1~50, 기본 40).

#### `GET /api/etfs/{ticker}/ai-prompt`
단일 종목 AI 분석 프롬프트 생성(API 호출 없이 프롬프트만 반환). **Query**: `use_db_data`(기본 true, RAG).

#### `POST /api/etfs/ai-prompt-multi`
복수 종목 통합 비교 프롬프트. **Body**: `{ "stocks": [{ "ticker": "...", "name": "..." }, ...] }`(2개 이상). **Query**: `use_db_data`(기본 true).

#### `GET /api/etfs/{ticker}/fundamentals`
저장된 최신 펀더멘털 조회. STOCK=`data`(1건), ETF=`fundamentals`(최근 10건)+`holdings`(최신 1일).

---

### Data Collection

#### `GET /api/data/collect-progress`
전체 수집 진행 상태. `{"status": "idle" | "in_progress" | "completed", ...}`.

#### `POST /api/data/collect-all` 🔒 · 10/min
전체 종목 가격·매매동향·펀더멘털 일괄 수집. **Query**: `days`(1~365, 기본 1).
```json
{ "message": "Data collection completed for 6 tickers",
  "result": { "total_tickers": 6, "success_count": 6, "fail_count": 0,
              "total_price_records": 6, "total_trading_flow_records": 6,
              "fundamentals_success": 6, "fundamentals_failed": 0, "details": { ... } } }
```

#### `POST /api/data/backfill` 🔒 · 10/min †
전 종목 히스토리 백필(프론트 미사용). **Query**: `days`(1~365).

#### `GET /api/data/status` · 200/min †
종목별 최근 30일 데이터 개수/최신 날짜. (프론트 미사용)

#### `GET /api/data/scheduler-status` · 200/min
APScheduler 실행 상태 및 마지막 수집 시간.

#### `GET /api/data/stats` · 200/min
DB 통계.
```json
{ "etfs": 6, "prices": 1500, "news": 250, "trading_flow": 180,
  "stock_catalog": 2500, "last_collection": "2025-11-12T10:30:00", "database_size_mb": 2.5 }
```

#### `GET /api/data/cache/stats` · 200/min †
캐시 히트율/미스/크기 통계. (프론트 미사용)

#### `DELETE /api/data/reset` 🔒 · 5/min
⚠️ `prices`, `news`, `trading_flow`, `collection_status`, `intraday_prices` 전체 삭제(`etfs` 유지). 되돌릴 수 없음.
```json
{ "message": "Database reset successfully",
  "deleted": { "prices": 1500, "news": 250, "trading_flow": 180,
               "collection_status": 6, "intraday_prices": 5000 } }
```

---

### News

#### `GET /api/news/{ticker}`
종목별 뉴스(분석 포함). 캐시에 없으면 온디맨드 수집 후 반환.
**Query**: `start_date`(기본 7일 전), `end_date`(기본 오늘), `analyze`(기본 true).
**Response** `NewsListResponse` — `news`(항목별 sentiment/tags), `analysis`(sentiment/topics/summary).

#### `POST /api/news/{ticker}/collect` 🔒
뉴스 수집. **Query**: `days`(1~30, 기본 7). 네이버 검색 API 키 필요.

---

### Settings

#### `GET /api/settings/stocks`
`stocks.json` 기준 등록 종목 배열.

#### `POST /api/settings/stocks` 🔒 · 100/min
종목 추가(201). **Body** `StockCreate`(`ticker`, `name`, `type` 필수 + `theme`/`purchase_date`/`purchase_price`/`quantity`/`search_keyword`/`relevance_keywords` 선택). DB 자동 동기화.

#### `PUT /api/settings/stocks/{ticker}` 🔒
부분 업데이트. **Body** `StockUpdate`(모든 필드 선택). 전달된 필드만 갱신.

#### `DELETE /api/settings/stocks/{ticker}` 🔒
종목 및 관련 데이터(prices/news/trading_flow) CASCADE 삭제.
```json
{ "ticker": "487240", "deleted": { "prices": 150, "news": 20, "trading_flow": 30 } }
```

#### `GET /api/settings/stocks/{ticker}/validate`
네이버 금융에서 티커 검증 및 기본 정보 조회. 없으면 `404`.

#### `GET /api/settings/stocks/search` · 30/min
자동완성용 종목 검색. **Query**: `q`(2자 이상 필수), `type`(`STOCK`/`ETF`/`ALL`/null). 최대 20개.

#### `POST /api/settings/stocks/reorder` 🔒 · 100/min
종목 순서 변경. **Body**: 티커 배열 `["487240", "466920", ...]`.

#### `GET /api/settings/ticker-catalog/collect-progress`
카탈로그 수집 진행률.

#### `POST /api/settings/ticker-catalog/collect` 🔒 · 5/min
코스피/코스닥/ETF 전체 종목 목록을 `stock_catalog`에 수집(약 5~10분).

#### `GET /api/settings/api-keys`
저장된 API 키 조회. **Query**: `raw`(true면 원본, 🔒 인증 필요 / false면 마스킹, 기본).
```json
{ "keys": { "NAVER_CLIENT_ID": "abcd****", "NAVER_CLIENT_SECRET": "..." },
  "configured": { "naver": true } }
```

#### `PUT /api/settings/api-keys` 🔒
API 키 저장 및 즉시 적용. **Body**: `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET`, `PERPLEXITY_API_KEY`(모두 선택).

---

### Alerts

알림 유형: `buy`/`sell`(목표가), `price_change`(등락률 임계 %, 0~100), `trading_signal`(외국인·기관 동시 시그널). 방향: `above`/`below`/`both`.

#### `POST /api/alerts/trigger` 🔒
프론트에서 감지한 트리거를 이력에 기록. **Body**: `{ rule_id, ticker, alert_type, message }`.

#### `GET /api/alerts/history/{ticker}` †
종목별 알림 이력(프론트 미사용). **Query**: `limit`(1~100, 기본 20).

#### `POST /api/alerts/` 🔒
알림 규칙 생성. **Body** `AlertRuleCreate`(`ticker`, `alert_type`, `direction`, `target_price` + `memo` 선택). **Response** `AlertRuleResponse`.

#### `GET /api/alerts/{ticker}`
종목별 알림 규칙 목록. **Query**: `active_only`(기본 true).

#### `PUT /api/alerts/{rule_id}` 🔒
규칙 수정. **Body** `AlertRuleUpdate`(선택 필드; `is_active` 포함). 수정할 필드 없으면 `400`.

#### `DELETE /api/alerts/{rule_id}` 🔒
규칙 및 관련 이력 삭제. `{ "deleted": true, "id": <rule_id> }`.

---

### Scanner

`stock_catalog` 테이블 기반. `catalog_updated_at`이 있는(수집된) 종목만 대상.

#### `GET /api/scanner`
조건 기반 검색.

**Query**
| 이름 | 타입 | 기본 | 설명 |
|------|------|------|------|
| `q` | string | | 종목명/코드 검색 |
| `type` | string | `ETF` | `ETF`/`STOCK`/`ALL` |
| `market` | string | | `ETF`/`KOSPI`/`KOSDAQ`(지정 시 type 무시) |
| `sector` | string | | 섹터 필터 |
| `min_weekly_return`,`max_weekly_return` | float | | 주간수익률 범위 |
| `min_monthly_return`,`max_monthly_return` | float | | 월간수익률 범위 |
| `min_ytd_return`,`max_ytd_return` | float | | 연간(YTD) 범위 |
| `foreign_net_positive` | bool | | 외국인 순매수만 |
| `institutional_net_positive` | bool | | 기관 순매수만 |
| `sort_by` | string | `weekly_return` | 정렬 기준(화이트리스트) |
| `sort_dir` | string | `desc` | `asc`/`desc` |
| `page` | int | 1 | 페이지 |
| `page_size` | int | 20 | 1~50 |

**Response** `ScreeningResponse` — `items`(`ScreeningItem[]`), `total`, `page`, `page_size`.

#### `GET /api/scanner/themes`
섹터별 그룹(개수, 평균 주간수익률, 상위 3종목). **Response** `List[ThemeGroup]`.

#### `GET /api/scanner/recommendations`
추천 프리셋(주간 상위, 외국인·기관 순매수 상위, 거래량 상위, 주간 하락 상위). **Query**: `limit`(1~10, 기본 5). **Response** `List[RecommendationPreset]`.

#### `GET /api/scanner/collect-progress`
카탈로그 데이터 수집 진행률.

#### `POST /api/scanner/collect-data` 🔒 · 10/min
카탈로그(가격/수익률/매매동향) 데이터 수집 트리거. **Query**: `force`(기본 false). 최신이면 `{ "status": "fresh", "skipped": true }`, 진행 중이면 `already_running`.

#### `POST /api/scanner/cancel-collect` 🔒
진행 중 수집 중지 요청.

---

### Simulation

#### `POST /api/simulation/lump-sum`
일시 투자. **Body** `LumpSumRequest`: `{ ticker, buy_date, amount }`. **Response** `LumpSumResponse`(주수, 평가금액, 수익률, 최대손익, price_series 등).

#### `POST /api/simulation/dca`
적립식. **Body** `DCARequest`: `{ ticker, monthly_amount, start_date, end_date, buy_day(1~28) }`. 기간 최대 5년. **Response** `DCAResponse`(평균매수가, 총주수, monthly_data 등).

#### `POST /api/simulation/portfolio`
포트폴리오. **Body** `PortfolioSimulationRequest`: `{ holdings: [{ ticker, weight }], amount, start_date, end_date }`. 종목 1~20개, 중복 불가, 기간 최대 5년. **Response** `PortfolioSimulationResponse`.

---

### Market

#### `GET /api/market/index/{code}/chart`
지수 일별 차트. **Path**: `code`(`KOSPI`/`KOSDAQ`). **Query**: `period`(`1M`/`3M`/`6M`/`1Y`/`3Y`, 기본 `3M`).
```json
{ "code": "KOSPI", "name": "코스피", "period": "3M",
  "data": [{ "date": "...", "close": 2500.1, "open": ..., "high": ..., "low": ... }] }
```

#### `GET /api/market/overview`
KOSPI/KOSDAQ 현황. `{ "indices": [{ "code", "name", "close_price", "change", "change_ratio" }] }`.

---

## 데이터 모델 (Schemas)

`backend/app/models.py` 기준 주요 모델입니다.

### ETF
| 필드 | 타입 | 설명 |
|------|------|------|
| `ticker` | string | 종목 코드 |
| `name` | string | 종목명 |
| `type` | string | `ETF` / `STOCK` |
| `theme` | string? | 테마/섹터 |
| `purchase_date` | date? | 구매일 |
| `purchase_price` | float? | 매입 평균가 |
| `quantity` | int? | 보유 수량 |
| `search_keyword` | string? | 뉴스 검색어 |
| `relevance_keywords` | string[]? | 연관 키워드 |

### PriceData
`date`, `open_price?`, `high_price?`, `low_price?`, `close_price`, `volume`, `daily_change_pct?`

### TradingFlow
`date`, `individual_net`, `institutional_net`, `foreign_net`

### News / NewsWithAnalysis
`date`, `published_at?`, `title`, `url`, `source`, `relevance_score?` (+ `sentiment?`, `tags?`)

### ETFMetrics
`ticker`, `aum?`, `returns`(`{1w,1m,ytd}`), `volatility?`, `max_drawdown?`, `sharpe_ratio?`

### ETFInsights
`strategy`(`StrategyInsights`: short_term/medium_term/long_term/recommendation/comment), `key_points[]`, `risks[]`

### ScreeningItem
`ticker`, `name`, `type`, `market?`, `sector?`, `close_price?`, `daily_change_pct?`, `volume?`, `weekly_return?`, `monthly_return?`, `ytd_return?`, `ytd_base_date?`, `foreign_net?`, `institutional_net?`, `catalog_updated_at?`, `is_registered`

### AlertRuleResponse
`id`, `ticker`, `alert_type`, `direction`, `target_price`, `memo?`, `is_active`, `created_at?`, `last_triggered_at?`

---

## 제거된 엔드포인트 (Removed)

프론트엔드에서 전혀 사용하지 않고, 백엔드 스케줄러/서비스가 동일 기능을 직접 수행하고 있어 **삭제된** 엔드포인트입니다(2026-07-21). 펀더멘털은 `collect-all`·스케줄러가 자동 수집하고, 캐시 초기화는 요청 헤더 `X-No-Cache: true`로 대체됩니다.

| Method | Endpoint | 대체 |
|--------|----------|------|
| POST | ~~`/api/etfs/{ticker}/collect-fundamentals`~~ | `collect-all` / 스케줄러 자동 수집 |
| POST | ~~`/api/data/collect-fundamentals`~~ | `collect-all` / 스케줄러 자동 수집 |
| DELETE | ~~`/api/data/cache/clear`~~ | 요청 헤더 `X-No-Cache: true` |

> `sdk/openapi.json`은 백엔드 OpenAPI에서 자동 생성되므로, 재생성 시 위 항목이 자동으로 빠집니다.

### 프론트 래퍼 제거 (Frontend `api.js`)

위 3개 삭제와 함께, 백엔드에는 남아 있으나 프론트에서 호출하지 않던 래퍼(†)를 `api.js`에서 제거했습니다: `etfApi.collectPrices`, `etfApi.collectTradingFlow`, `etfApi.collectIntraday`, `dataApi.backfill`, `dataApi.getStatus`, `dataApi.getCacheStats`, `dataApi.fetchWithNoCache`, `alertApi.getHistory`, `newsApi.getAll`(존재하지 않는 `GET /api/news` 호출).

---

## 데이터 출처 (Data Sources)

- **가격/매매동향/분봉/펀더멘털**: 네이버 금융
- **KOSPI/KOSDAQ 지수**: 네이버 모바일 API
- **뉴스**: 네이버 검색 API (`NAVER_CLIENT_ID`/`NAVER_CLIENT_SECRET` 필요, 없으면 비활성화)
- **AI 분석 프롬프트**: Perplexity `sonar` (`PERPLEXITY_API_KEY` 필요)

외부 API 키는 Settings 화면(`PUT /api/settings/api-keys`)에서 `backend/config/api-keys.json`으로 관리됩니다.
