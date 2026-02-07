# API 명세서

## Base URL
- 개발: `http://localhost:8000/api`
- 프로덕션: `https://your-domain.com/api`

## 인증 (선택)
- **X-API-Key** 헤더: 관리용 엔드포인트(수집, 설정 변경, DB 초기화 등)에서 사용. 미설정 시 개발 모드에서는 모든 요청 허용.

## 응답 형식
- **성공**: 각 엔드포인트별 JSON (일부는 `{ "data": ... }` 래핑)
- **에러**: `{ "detail": "메시지" }`, HTTP 상태 코드 4xx/5xx

---

## 1. Health
| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/health` | 서버 상태 확인 |

---

## 2. 종목/ETF (`/api/etfs`)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/etfs` | 전체 종목 목록 (설정된 모든 ETF·주식) |
| GET | `/api/etfs/{ticker}` | 종목 기본 정보 |
| GET | `/api/etfs/{ticker}/prices` | 가격 데이터. Query: `start_date`, `end_date`, `days` |
| GET | `/api/etfs/{ticker}/trading-flow` | 매매 동향. Query: `start_date`, `end_date` |
| GET | `/api/etfs/{ticker}/metrics` | 지표(수익률, 변동성, MDD, 샤프 비율 등) |
| GET | `/api/etfs/{ticker}/insights` | 인사이트. Query: `period` (1w, 1m, 3m, 6m, 1y) |
| GET | `/api/etfs/{ticker}/intraday` | 분봉 데이터. Query: `target_date`, `auto_collect`, `force_refresh` |
| GET | `/api/etfs/compare` | 종목 비교. Query: `tickers`(쉼표 구분, 2~6개), `start_date`, `end_date` |
| POST | `/api/etfs/{ticker}/collect` | 가격·매매동향 수집. Query: `days`. API Key 권장 |
| POST | `/api/etfs/{ticker}/collect-trading-flow` | 매매동향 수집. Query: `days`. API Key 권장 |
| POST | `/api/etfs/{ticker}/collect-intraday` | 분봉 수집. Query: `pages`. API Key 권장 |
| POST | `/api/etfs/batch-summary` | 배치 요약(대시보드용). Body: `tickers`, `price_days`, `news_limit` |

---

## 3. 뉴스 (`/api/news`)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/news/{ticker}` | 종목별 뉴스. Query: `start_date`, `end_date` |
| POST | `/api/news/{ticker}/collect` | 뉴스 수집. Query: `days` (1~30). API Key 권장 |

---

## 4. 데이터 수집·상태 (`/api/data`)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/api/data/collect-all` | 전체 종목 일괄 수집. Query: `days` (1~365). API Key 필요 |
| POST | `/api/data/backfill` | 히스토리 백필. Query: `days`. API Key 필요 |
| GET | `/api/data/status` | 종목별 수집 상태 |
| GET | `/api/data/scheduler-status` | 스케줄러 상태(마지막 수집 시각 등) |
| GET | `/api/data/stats` | DB 통계(테이블별 건수, DB 크기 등) |
| GET | `/api/data/cache/stats` | 캐시 통계 |
| DELETE | `/api/data/cache/clear` | 캐시 전체 삭제. API Key 필요 |
| DELETE | `/api/data/reset` | DB 초기화(가격·뉴스·매매동향·분봉 삭제). API Key 필요 |

---

## 5. 설정·종목 관리 (`/api/settings`)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/settings/stocks` | 종목 목록(stocks.json 기반) |
| POST | `/api/settings/stocks` | 종목 추가. Body: ticker, name, type, theme, purchase_date, purchase_price, quantity, search_keyword, relevance_keywords. API Key 필요 |
| PUT | `/api/settings/stocks/{ticker}` | 종목 수정. API Key 필요 |
| DELETE | `/api/settings/stocks/{ticker}` | 종목 삭제. API Key 필요 |
| GET | `/api/settings/stocks/{ticker}/validate` | 티커 검증(네이버 금융 스크래핑) |
| GET | `/api/settings/stocks/search` | 종목 검색(자동완성). Query: `q`, `type` (STOCK/ETF/ALL) |
| POST | `/api/settings/stocks/reorder` | 종목 순서 변경. Body: `tickers` 배열. API Key 필요 |
| POST | `/api/settings/ticker-catalog/collect` | 종목 목록(코스피/코스닥/ETF) 수집. API Key 필요 |

---

## 에러 코드
| 코드 | 설명 |
|-----|------|
| 200 | 성공 |
| 201 | 생성됨 |
| 400 | 잘못된 요청 |
| 401 | 인증 필요 |
| 404 | 리소스를 찾을 수 없음 |
| 422 | 입력 값 검증 실패 |
| 429 | Rate Limit 초과 |
| 500 | 서버 내부 오류 |

---

## 참고
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- 상세 요청/응답 스키마는 Swagger에서 확인.
