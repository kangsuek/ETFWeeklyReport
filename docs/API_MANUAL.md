# Backend API 매뉴얼

한국 고성장 섹터 ETF·주식 분석 웹앱의 백엔드 REST API 사용 설명서입니다.

---

## 목차

1. [개요](#1-개요)
2. [Health](#2-health)
3. [종목/ETF (`/api/etfs`)](#3-종목etf-apietfs)
4. [뉴스 (`/api/news`)](#4-뉴스-apinews)
5. [데이터 수집·상태 (`/api/data`)](#5-데이터-수집상태-apidata)
6. [설정·종목 관리 (`/api/settings`)](#6-설정종목-관리-apisettings)
7. [알림 (`/api/alerts`)](#7-알림-apialerts)
8. [스캐너 (`/api/scanner`)](#8-스캐너-apiscanner)
9. [시뮬레이션 (`/api/simulation`)](#9-시뮬레이션-apisimulation)
10. [에러 코드](#10-에러-코드)
11. [참고](#11-참고)

---

## 1. 개요

### Base URL

| 환경 | Base URL |
|------|----------|
| 개발 | `http://localhost:8000` |
| 프로덕션 | `https://your-domain.com` |

API 경로는 모두 `/api` 접두사를 사용합니다 (예: `/api/health`, `/api/etfs`).

### 인증

- **X-API-Key** 헤더: 관리용 엔드포인트(수집, 설정 변경, DB 초기화, 캐시 삭제 등)에서 사용합니다.
- 미설정 시 개발 모드에서는 모든 요청이 허용될 수 있습니다.
- API 키는 설정 화면에서 관리하며 `api-keys.json`에 저장됩니다.

### 공통 응답 형식

- **성공**: 엔드포인트별 JSON (일부는 `{ "data": ... }` 래핑).
- **에러**: `{ "detail": "메시지" }`, HTTP 상태 코드 4xx/5xx.

### 캐시 무효화

- 요청 헤더 **X-No-Cache: true** 를 보내면 해당 요청 처리 시 서버 메모리 캐시가 비워집니다 (프론트엔드 새로고침 용도).

---

## 2. Health

서버 및 DB 상태 확인용 엔드포인트입니다.

### GET /api/health

서버 상태와 DB 연결 여부를 반환합니다.

**요청**

- 메서드: `GET`
- 경로: `/api/health`
- Query/Body: 없음

**요청 예시**

```http
GET /api/health HTTP/1.1
Host: localhost:8000
```

**응답 예시**

```json
{
  "status": "healthy",
  "message": "ETF Report API is running",
  "database": "connected"
}
```

DB 연결 실패 시 `status`는 `"degraded"`, `database`에는 오류 메시지가 포함됩니다.

**상태 코드**

| 코드 | 설명 |
|------|------|
| 200 | 성공 (healthy 또는 degraded) |

---

## 3. 종목/ETF (`/api/etfs`)

등록된 ETF·주식 종목의 조회, 가격·매매동향·분봉 수집, 비교·지표·인사이트·AI 프롬프트·펀더멘털 조회를 제공합니다.

### GET /api/etfs

전체 종목 목록을 반환합니다 (stocks.json + DB 동기화된 etfs 테이블 기준).

**요청**

- 메서드: `GET`
- 경로: `/api/etfs` 또는 `/api/etfs/`
- Query: 없음

**요청 예시**

```http
GET /api/etfs HTTP/1.1
Host: localhost:8000
```

**응답**

- `ETF[]`: `ticker`, `name`, `type`(ETF/STOCK), `theme`, `launch_date`, `expense_ratio` 등

**응답 예시**

```json
[
  {
    "ticker": "487240",
    "name": "삼성 KODEX AI전력핵심설비 ETF",
    "type": "ETF",
    "theme": "AI/전력",
    "purchase_date": null,
    "purchase_price": null,
    "quantity": null,
    "search_keyword": null,
    "relevance_keywords": null
  },
  {
    "ticker": "042660",
    "name": "한화오션",
    "type": "STOCK",
    "theme": "조선/방산",
    "purchase_date": null,
    "purchase_price": null,
    "quantity": null,
    "search_keyword": null,
    "relevance_keywords": null
  }
]
```

**상태 코드**: 200 성공, 500 서버 오류

---

### GET /api/etfs/{ticker}

단일 종목 기본 정보를 반환합니다.

**요청**

- Path: `ticker` — 종목 코드 (예: `487240`, `042660`)

**요청 예시**

```http
GET /api/etfs/487240 HTTP/1.1
Host: localhost:8000
```

**응답**

- `ETF` 객체

**응답 예시**

```json
{
  "ticker": "487240",
  "name": "삼성 KODEX AI전력핵심설비 ETF",
  "type": "ETF",
  "theme": "AI/전력",
  "purchase_date": null,
  "purchase_price": null,
  "quantity": null,
  "search_keyword": null,
  "relevance_keywords": null
}
```

**상태 코드**: 200 성공, 404 종목 없음, 500 서버 오류

---

### GET /api/etfs/{ticker}/prices

종목의 일봉 가격 데이터를 반환합니다.

**Query**

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| start_date | date | N | 조회 시작일 (기본: 30일 전) |
| end_date | date | N | 조회 종료일 (기본: 오늘) |
| days | int | N | 최근 N일 (start_date/end_date 대신 사용 가능) |

**요청 예시**

```http
GET /api/etfs/487240/prices?start_date=2025-01-01&end_date=2025-02-18 HTTP/1.1
Host: localhost:8000
```

```http
GET /api/etfs/487240/prices?days=30 HTTP/1.1
Host: localhost:8000
```

**응답**

- `PriceData[]`: `date`, `open_price`, `high_price`, `low_price`, `close_price`, `volume`, `daily_change_pct`

**응답 예시**

```json
[
  {
    "date": "2025-02-14",
    "open_price": 12450.0,
    "high_price": 12600.0,
    "low_price": 12380.0,
    "close_price": 12520.0,
    "volume": 125000,
    "daily_change_pct": 0.56
  },
  {
    "date": "2025-02-13",
    "open_price": 12380.0,
    "high_price": 12500.0,
    "low_price": 12300.0,
    "close_price": 12450.0,
    "volume": 98000,
    "daily_change_pct": -0.24
  }
]
```

**상태 코드**: 200, 404, 400(검증 실패), 500

---

### GET /api/etfs/{ticker}/trading-flow

종목의 매매 동향(개인/기관/외국인 순매수)을 반환합니다.

**Query**

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| start_date | date | N | 조회 시작일 |
| end_date | date | N | 조회 종료일 |

**요청 예시**

```http
GET /api/etfs/487240/trading-flow?start_date=2025-02-01&end_date=2025-02-18 HTTP/1.1
Host: localhost:8000
```

**응답**

- `TradingFlow[]`: `date`, `individual_net`, `institutional_net`, `foreign_net`

**응답 예시**

```json
[
  {
    "date": "2025-02-14",
    "individual_net": -12500,
    "institutional_net": 8200,
    "foreign_net": 4300
  },
  {
    "date": "2025-02-13",
    "individual_net": 3100,
    "institutional_net": -2100,
    "foreign_net": -1000
  }
]
```

**상태 코드**: 200, 404, 400, 500

---

### GET /api/etfs/{ticker}/metrics

종목의 지표(수익률, 변동성, MDD, 샤프 비율 등)를 반환합니다.

**요청**

- Path: `ticker`

**요청 예시**

```http
GET /api/etfs/487240/metrics HTTP/1.1
Host: localhost:8000
```

**응답**

- `ETFMetrics`: `ticker`, `aum`, `returns`(1w/1m/ytd 등), `volatility`, `max_drawdown`, `sharpe_ratio`

**응답 예시**

```json
{
  "ticker": "487240",
  "aum": 125.5,
  "returns": {
    "1w": 0.023,
    "1m": 0.085,
    "3m": 0.12,
    "6m": 0.18,
    "ytd": 0.153
  },
  "volatility": 18.5,
  "max_drawdown": -8.2,
  "sharpe_ratio": 1.25
}
```

**상태 코드**: 200, 404, 500

---

### GET /api/etfs/{ticker}/insights

종목 인사이트(요약, 강점/약점 등)를 반환합니다.

**Query**

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| period | str | N | 1w, 1m, 3m, 6m, 1y (기본: 1m) |

**요청 예시**

```http
GET /api/etfs/487240/insights?period=1m HTTP/1.1
Host: localhost:8000
```

**응답**

- `ETFInsights`: 기간별 수익률, 인사이트 텍스트 등

**응답 예시**

```json
{
  "strategy": {
    "short_term": "보유",
    "medium_term": "비중확대",
    "long_term": "장기 보유",
    "recommendation": "중기적으로 비중 확대 검토",
    "comment": "AI·전력 테마 성장 기대"
  },
  "key_points": [
    "주간 수익률 상위권 유지",
    "외국인·기관 순매수 지속",
    "거래량 확대"
  ],
  "risks": [
    "단기 변동성 확대 가능",
    "섹터 집중 리스크"
  ]
}
```

**상태 코드**: 200, 404, 500

---

### GET /api/etfs/{ticker}/intraday

분봉 데이터를 반환합니다.

**Query**

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| target_date | date | N | 조회 대상일 (기본: 오늘) |
| auto_collect | bool | N | 데이터 없을 때 자동 수집 여부 (기본: true) |
| force_refresh | bool | N | 캐시 무시 강제 수집 (기본: false) |

**요청 예시**

```http
GET /api/etfs/487240/intraday?target_date=2025-02-18 HTTP/1.1
Host: localhost:8000
```

```http
GET /api/etfs/487240/intraday?force_refresh=true HTTP/1.1
Host: localhost:8000
```

**응답**

- 분봉 시계열 (시간, 시가/고가/저가/종가, 거래량 등)

**응답 예시**

```json
{
  "ticker": "487240",
  "date": "2025-02-18",
  "data": [
    {
      "datetime": "2025-02-18T09:00:00",
      "price": 12500.0,
      "change_amount": 100.0,
      "volume": 1500,
      "bid_volume": 800,
      "ask_volume": 700
    }
  ],
  "count": 390,
  "first_time": "09:00",
  "last_time": "15:30"
}
```

**상태 코드**: 200, 404, 503(수집 실패), 500

---

### GET /api/etfs/compare

여러 종목의 가격·통계를 비교합니다.

**Query**

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| tickers | string | Y | 쉼표 구분 종목 코드 (2~20개) |
| start_date | date | N | 시작일 (기본: 30일 전) |
| end_date | date | N | 종료일 (기본: 오늘) |

**요청 예시**

```http
GET /api/etfs/compare?tickers=487240,466920,042660&start_date=2025-01-20&end_date=2025-02-18 HTTP/1.1
Host: localhost:8000
```

**응답**

- `normalized_prices`: 날짜별 정규화 가격
- `statistics`: 종목별 기간 수익률 등 통계

**응답 예시**

```json
{
  "normalized_prices": {
    "dates": ["2025-01-20", "2025-01-21", "2025-01-22"],
    "data": {
      "487240": [100, 102.5, 98.3],
      "466920": [100, 101.2, 99.8],
      "042660": [100, 103.1, 105.2]
    }
  },
  "statistics": {
    "487240": {
      "period_return": 12.5,
      "volatility": 18.2
    },
    "466920": {
      "period_return": 8.3,
      "volatility": 15.1
    },
    "042660": {
      "period_return": 15.2,
      "volatility": 22.0
    }
  }
}
```

**상태 코드**: 200, 400(파라미터 오류), 500

---

### GET /api/etfs/{ticker}/ai-prompt

단일 종목용 AI 분석 프롬프트를 생성합니다 (RAG: DB 데이터 포함 가능).

**Query**

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| use_db_data | bool | N | DB 데이터를 프롬프트에 포함 여부 (기본: true) |

**요청 예시**

```http
GET /api/etfs/487240/ai-prompt?use_db_data=true HTTP/1.1
Host: localhost:8000
```

**응답**

```json
{
  "ticker": "487240",
  "name": "삼성 KODEX AI전력핵심설비 ETF",
  "prompt": "...",
  "use_db_data": true
}
```

**상태 코드**: 200, 404, 500

---

### POST /api/etfs/ai-prompt-multi

복수 종목 통합 비교 분석용 AI 프롬프트를 생성합니다.

**Body**

- `stocks`: 배열 (최소 2개) — 각 항목 `ticker`, `name`

**Query**

- `use_db_data`: bool (기본 true)

**요청 예시**

```http
POST /api/etfs/ai-prompt-multi?use_db_data=true HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
  "stocks": [
    { "ticker": "487240", "name": "삼성 KODEX AI전력핵심설비 ETF" },
    { "ticker": "466920", "name": "KODEX 2차전지산업 ETF" }
  ]
}
```

**응답**

- `stocks`, `prompt`, `use_db_data`

**상태 코드**: 200, 400(2개 미만 종목), 500

---

### GET /api/etfs/{ticker}/fundamentals

DB에 저장된 해당 종목의 최근 펀더멘털 데이터를 반환합니다.

- **STOCK**: `stock_fundamentals` 최근 1건 (PER, PBR, ROE, EPS 등)
- **ETF**: `etf_fundamentals` 최근 10건, `etf_holdings` 최근 1일

**요청 예시**

```http
GET /api/etfs/487240/fundamentals HTTP/1.1
Host: localhost:8000
```

**응답**

- `ticker`, `type`(STOCK/ETF), `data` (또는 ETF의 경우 fundamentals/holdings 구조)

**응답 예시 (STOCK)**

```json
{
  "ticker": "042660",
  "type": "STOCK",
  "data": {
    "ticker": "042660",
    "date": "2025-02-17",
    "per": 12.5,
    "pbr": 1.2,
    "roe": 9.8,
    "eps": 1250,
    "bps": 12500
  }
}
```

**응답 예시 (ETF)**

```json
{
  "ticker": "487240",
  "type": "ETF",
  "fundamentals": [
    {
      "date": "2025-02-17",
      "nav": 12500.0,
      "expense_ratio": 0.0045
    }
  ],
  "holdings": [
    {
      "ticker": "005930",
      "name": "삼성전자",
      "weight": 0.15,
      "date": "2025-02-17"
    }
  ]
}
```

**상태 코드**: 200, 404, 500

---

### POST /api/etfs/{ticker}/collect

해당 종목의 가격·매매동향을 수집합니다. (API Key 권장)

**Query**

- `days`: int (수집 일수, 기본값 사용 시 1일)

**요청 예시**

```http
POST /api/etfs/487240/collect?days=5 HTTP/1.1
Host: localhost:8000
X-API-Key: your-api-key
```

**응답**

- 수집 결과 메시지 및 요약

**응답 예시**

```json
{
  "ticker": "487240",
  "collected": 5,
  "message": "Successfully collected 5 price records"
}
```

**상태 코드**: 200, 404, 400, 503, 500

---

### POST /api/etfs/{ticker}/collect-trading-flow

해당 종목의 매매동향만 수집합니다. (API Key 권장)

**Query**

- `days`: int

**요청 예시**

```http
POST /api/etfs/487240/collect-trading-flow?days=10 HTTP/1.1
Host: localhost:8000
X-API-Key: your-api-key
```

**응답 예시**

```json
{
  "ticker": "487240",
  "name": "삼성 KODEX AI전력핵심설비 ETF",
  "collected": 10,
  "days": 10,
  "message": "Successfully collected 10 trading flow records"
}
```

**상태 코드**: 200, 404, 503, 500

---

### POST /api/etfs/{ticker}/collect-intraday

해당 종목의 분봉 데이터를 수집합니다. (API Key 권장)

**Query**

- `pages`: int (수집할 페이지 수, 선택)

**요청 예시**

```http
POST /api/etfs/487240/collect-intraday HTTP/1.1
Host: localhost:8000
X-API-Key: your-api-key
```

**응답 예시**

```json
{
  "ticker": "487240",
  "name": "삼성 KODEX AI전력핵심설비 ETF",
  "collected": 390,
  "days": 1,
  "message": "Successfully collected 390 intraday records"
}
```

**상태 코드**: 200, 404, 503, 500

---

### POST /api/etfs/{ticker}/collect-fundamentals

해당 종목의 펀더멘털 데이터를 수집하여 DB에 저장합니다.

- **STOCK**: 네이버 기업실적분석 → `stock_fundamentals`
- **ETF**: 네이버 NAV 추이, 펀드보수, 구성종목 → `etf_fundamentals`, `etf_holdings`

**요청 예시**

```http
POST /api/etfs/487240/collect-fundamentals HTTP/1.1
Host: localhost:8000
```

**응답**

- `ticker`, `type`, 수집 결과 객체

**상태 코드**: 200, 404, 500

---

### POST /api/etfs/batch-summary

대시보드용 배치 요약(종목별 요약 정보)을 반환합니다.

**Body**

- `tickers`: string[] (필수, 최대 50개)
- `price_days`: int (기본 5, 1~365)
- `news_limit`: int (기본 5, 1~100)

**요청 예시**

```http
POST /api/etfs/batch-summary HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
  "tickers": ["487240", "466920"],
  "price_days": 30,
  "news_limit": 5
}
```

**응답**

- `BatchSummaryResponse`: 종목별 카드 요약, 가격, 뉴스 등

**응답 예시**

```json
{
  "data": {
    "487240": {
      "ticker": "487240",
      "latest_price": {
        "date": "2025-02-18",
        "close_price": 12520.0,
        "volume": 125000,
        "daily_change_pct": 0.56
      },
      "prices": [],
      "weekly_return": 2.3,
      "latest_trading_flow": {
        "date": "2025-02-18",
        "individual_net": -12500,
        "institutional_net": 8200,
        "foreign_net": 4300
      },
      "latest_news": [
        {
          "date": "2025-02-18",
          "title": "AI 전력 ETF 거래량 확대",
          "url": "https://...",
          "source": "한국경제",
          "relevance_score": 0.9
        }
      ]
    }
  }
}
```

**상태 코드**: 200, 400, 500

---

## 4. 뉴스 (`/api/news`)

종목별 뉴스 조회 및 수집을 제공합니다.

### GET /api/news/{ticker}

종목별 뉴스 목록을 반환합니다 (분석: 센티먼트, 태그, 요약 포함 옵션).

**Query**

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| start_date | date | N | 조회 시작일 (기본: 7일 전) |
| end_date | date | N | 조회 종료일 (기본: 오늘) |
| analyze | bool | N | 뉴스 분석 포함 여부 (기본: true) |

**요청 예시**

```http
GET /api/news/487240?start_date=2025-02-01&end_date=2025-02-18&analyze=true HTTP/1.1
Host: localhost:8000
```

**응답**

- `NewsListResponse`: `news` (제목, URL, 날짜, 센티먼트, 태그 등), `analysis` (전체 요약 등)

**응답 예시**

```json
{
  "news": [
    {
      "date": "2025-02-18",
      "title": "AI 전력 ETF, 거래량 2배 급증",
      "url": "https://...",
      "source": "한국경제",
      "relevance_score": 0.92,
      "sentiment": "positive",
      "tags": ["AI", "전력", "ETF"]
    }
  ],
  "analysis": {
    "overall_sentiment": "positive",
    "topics": ["AI 인프라", "전력 수요"],
    "summary": "AI·전력 테마 관련 뉴스가 긍정적 흐름."
  }
}
```

**상태 코드**: 200, 404, 500

---

### POST /api/news/{ticker}/collect

해당 종목의 뉴스를 수집하여 DB에 저장합니다. (API Key 권장)

**Query**

- `days`: int (1~30, 수집할 기간 일수)

**요청 예시**

```http
POST /api/news/487240/collect?days=7 HTTP/1.1
Host: localhost:8000
X-API-Key: your-api-key
```

**응답**

- 수집된 건수 등 결과

**응답 예시**

```json
{
  "ticker": "487240",
  "collected": 15,
  "days": 7,
  "message": "Successfully collected 15 news articles"
}
```

**상태 코드**: 200, 404, 400, 503, 500

---

## 5. 데이터 수집·상태 (`/api/data`)

전체 수집, 백필, 수집 진행률, 스케줄러 상태, DB/캐시 통계, 펀더멘털 일괄 수집, 캐시 삭제, DB 초기화를 제공합니다.

### GET /api/data/collect-progress

전체 데이터 수집(`collect-all`) 진행률을 반환합니다.

**요청 예시**

```http
GET /api/data/collect-progress HTTP/1.1
Host: localhost:8000
```

**응답**

- `status`: `idle` | `in_progress` | `completed` (및 진행률 등)

**응답 예시**

```json
{
  "status": "idle"
}
```

```json
{
  "status": "in_progress",
  "current": 3,
  "total": 6,
  "message": "Collecting data for 487240..."
}
```

**상태 코드**: 200

---

### POST /api/data/collect-all

등록된 전체 종목에 대해 가격·매매동향·뉴스·**펀더멘털**을 일괄 수집합니다. (API Key 필요)

**Query**

- `days`: int (1~365, 기본값: 상수 기준)

**요청 예시**

```http
POST /api/data/collect-all?days=10 HTTP/1.1
Host: localhost:8000
X-API-Key: your-api-key
```

**응답**

- `message`, `result`: `total_tickers`, `success_count`, `fail_count`, `fundamentals_success`, `fundamentals_failed`, `details` (종목별 상세)

**응답 예시**

```json
{
  "message": "Data collection completed for 6 tickers",
  "result": {
    "total_tickers": 6,
    "success_count": 6,
    "fail_count": 0,
    "total_price_records": 6,
    "total_trading_flow_records": 6,
    "total_news_records": 12,
    "fundamentals_success": 6,
    "fundamentals_failed": 0,
    "details": {
      "487240": {
        "name": "삼성 KODEX AI전력핵심설비 ETF",
        "success": true,
        "price_records": 1,
        "trading_flow_records": 1,
        "news_records": 2
      }
    }
  }
}
```

**상태 코드**: 200, 400, 401, 503, 500

---

### POST /api/data/backfill

과거 데이터 백필 수집을 실행합니다. (API Key 필요)

**Query**

- `days`: int

**요청 예시**

```http
POST /api/data/backfill?days=90 HTTP/1.1
Host: localhost:8000
X-API-Key: your-api-key
```

**상태 코드**: 200, 400, 401, 503, 500

---

### GET /api/data/status

종목별 수집 상태(마지막 수집 일시 등)를 반환합니다.

**요청 예시**

```http
GET /api/data/status HTTP/1.1
Host: localhost:8000
```

**응답**

- 종목 티커별 상태 객체

**응답 예시**

```json
{
  "total_tickers": 6,
  "status": [
    {
      "ticker": "487240",
      "name": "삼성 KODEX AI전력핵심설비 ETF",
      "type": "ETF",
      "recent_data_count": 30,
      "latest_date": "2025-02-18"
    }
  ]
}
```

**상태 코드**: 200, 500

---

### GET /api/data/scheduler-status

스케줄러 상태(마지막 수집 시각, 다음 예정 등)를 반환합니다.
스케줄: **평일(월~금) 09:00** 가격·매매동향·뉴스, **평일 16:30** 펀더멘털 자동 수집.

**요청 예시**

```http
GET /api/data/scheduler-status HTTP/1.1
Host: localhost:8000
```

**응답**

- 스케줄러 설정 및 마지막 실행 정보 (가격/뉴스 + 펀더멘털 수집 시각 포함)

**응답 예시**

```json
{
  "running": true,
  "last_collection_time": "2026-02-18T09:00:00",
  "next_collection_time": "2026-02-19T09:00:00",
  "last_fundamentals_collection_time": "2026-02-18T16:30:00",
  "next_fundamentals_collection_time": "2026-02-19T16:30:00",
  "is_collecting": false,
  "is_collecting_fundamentals": false,
  "jobs": [
    {
      "id": "daily_collection",
      "name": "Daily Data Collection",
      "next_run": "2026-02-19T09:00:00+09:00"
    },
    {
      "id": "fundamentals_collection",
      "name": "Fundamentals Collection",
      "next_run": "2026-02-19T16:30:00+09:00"
    }
  ]
}
```

**상태 코드**: 200, 500

---

### GET /api/data/stats

DB 통계(테이블별 건수, DB 크기 등)를 반환합니다.

**요청 예시**

```http
GET /api/data/stats HTTP/1.1
Host: localhost:8000
```

**응답**

- 테이블별 row 수, DB 파일 크기 등

**응답 예시**

```json
{
  "etfs": 6,
  "prices": 1500,
  "news": 250,
  "trading_flow": 180,
  "stock_catalog": 2500,
  "last_collection": "2025-02-18T09:00:00",
  "database_size_mb": 2.5
}
```

**상태 코드**: 200, 500

---

### GET /api/data/cache/stats

캐시 통계를 반환합니다.

**요청 예시**

```http
GET /api/data/cache/stats HTTP/1.1
Host: localhost:8000
```

**응답**

- 캐시 키 수, 메모리 사용량 등

**응답 예시**

```json
{
  "hits": 150,
  "misses": 50,
  "hit_rate_pct": 75.0,
  "total_requests": 200,
  "evictions": 5,
  "sets": 55,
  "current_size": 50,
  "max_size": 1000,
  "default_ttl_seconds": 30
}
```

**상태 코드**: 200, 500

---

### POST /api/data/collect-fundamentals

전체 종목(etfs 테이블 기준)에 대해 펀더멘털을 일괄 수집합니다. (API Key 필요)

**요청 예시**

```http
POST /api/data/collect-fundamentals HTTP/1.1
Host: localhost:8000
X-API-Key: your-api-key
```

**응답**

- `total`, `success`, `failed`, `results` (종목별 성공/실패)

**응답 예시**

```json
{
  "total": 6,
  "success": 5,
  "failed": 1,
  "results": [
    {
      "ticker": "487240",
      "type": "ETF",
      "success": true,
      "result": {}
    },
    {
      "ticker": "042660",
      "type": "STOCK",
      "success": false,
      "error": "Scraper timeout"
    }
  ]
}
```

**상태 코드**: 200, 401, 500

---

### DELETE /api/data/cache/clear

메모리 캐시를 전체 삭제합니다. (API Key 필요)

**요청 예시**

```http
DELETE /api/data/cache/clear HTTP/1.1
Host: localhost:8000
X-API-Key: your-api-key
```

**응답**

- `message`: "Cache cleared successfully"

**응답 예시**

```json
{
  "message": "Cache cleared successfully"
}
```

**상태 코드**: 200, 401, 500

---

### DELETE /api/data/reset

DB 초기화: 가격·뉴스·매매동향·분봉·수집 상태 등 테이블 데이터 삭제 (etfs는 유지). (API Key 필요)

**⚠️ 되돌릴 수 없는 작업입니다.**

**요청 예시**

```http
DELETE /api/data/reset HTTP/1.1
Host: localhost:8000
X-API-Key: your-api-key
```

**응답**

- `message`, `deleted`: 테이블별 삭제 건수

**응답 예시**

```json
{
  "message": "Database reset successfully",
  "deleted": {
    "prices": 1500,
    "news": 250,
    "trading_flow": 180,
    "collection_status": 6,
    "intraday_prices": 2340
  }
}
```

**상태 코드**: 200, 401, 500

---

## 6. 설정·종목 관리 (`/api/settings`)

종목(stocks.json) CRUD, 티커 검증, 종목 검색, 순서 변경, 티커 카탈로그 수집, API 키 조회/수정을 제공합니다.

### GET /api/settings/stocks

현재 설정된 종목 목록을 반환합니다 (stocks.json 기반).

**요청 예시**

```http
GET /api/settings/stocks HTTP/1.1
Host: localhost:8000
```

**응답**

- `Array<{ ticker, name, type, theme, purchase_date, ... }>`

**응답 예시**

```json
[
  {
    "ticker": "005930",
    "name": "삼성전자",
    "type": "STOCK",
    "theme": "반도체/전자",
    "purchase_date": "2024-01-15",
    "purchase_price": 72000,
    "quantity": 10,
    "search_keyword": "삼성전자",
    "relevance_keywords": ["삼성전자", "반도체"]
  }
]
```

**상태 코드**: 200, 500

---

### POST /api/settings/stocks

종목을 추가합니다. (API Key 필요)

**Body**

- `ticker`: string (필수)
- `name`: string (필수)
- `type`: "ETF" | "STOCK" (필수)
- `theme`: string (선택)
- `purchase_date`: string YYYY-MM-DD (선택)
- `purchase_price`, `quantity`, `search_keyword`, `relevance_keywords`: 선택

**요청 예시**

```http
POST /api/settings/stocks HTTP/1.1
Host: localhost:8000
Content-Type: application/json
X-API-Key: your-api-key

{
  "ticker": "005930",
  "name": "삼성전자",
  "type": "STOCK",
  "theme": "반도체/전자",
  "purchase_date": "2024-01-15",
  "search_keyword": "삼성전자",
  "relevance_keywords": ["삼성전자", "반도체"]
}
```

**응답**

- 생성된 종목 객체 + `message`

**응답 예시**

```json
{
  "ticker": "005930",
  "name": "삼성전자",
  "type": "STOCK",
  "theme": "반도체/전자",
  "purchase_date": "2024-01-15",
  "search_keyword": "삼성전자",
  "relevance_keywords": ["삼성전자", "반도체"],
  "message": "Stock created successfully"
}
```

**상태 코드**: 201, 400, 401, 500

---

### PUT /api/settings/stocks/{ticker}

기존 종목을 수정합니다 (부분 업데이트). (API Key 필요)

**Body**

- `name`, `type`, `theme`, `purchase_date`, `purchase_price`, `quantity`, `search_keyword`, `relevance_keywords` (모두 선택)

**요청 예시**

```http
PUT /api/settings/stocks/005930 HTTP/1.1
Host: localhost:8000
Content-Type: application/json
X-API-Key: your-api-key

{
  "theme": "반도체/전자/메모리",
  "relevance_keywords": ["삼성전자", "반도체", "HBM"]
}
```

**상태 코드**: 200, 400, 401, 404, 500

---

### DELETE /api/settings/stocks/{ticker}

종목을 삭제합니다. (API Key 필요)

**요청 예시**

```http
DELETE /api/settings/stocks/005930 HTTP/1.1
Host: localhost:8000
X-API-Key: your-api-key
```

**응답**

- `StockDeleteResponse`: 삭제 결과 메시지

**응답 예시**

```json
{
  "ticker": "005930",
  "deleted": {
    "prices": 150,
    "news": 20,
    "trading_flow": 30
  }
}
```

**상태 코드**: 200, 401, 404, 500

---

### GET /api/settings/stocks/{ticker}/validate

티커가 네이버 금융에서 유효한지 검증합니다 (스크래핑 기반).

**요청 예시**

```http
GET /api/settings/stocks/005930/validate HTTP/1.1
Host: localhost:8000
```

**응답**

- 유효 여부, 종목명 등

**응답 예시**

```json
{
  "valid": true,
  "ticker": "005930",
  "name": "삼성전자",
  "type": "STOCK"
}
```

**상태 코드**: 200, 404, 503, 500

---

### GET /api/settings/stocks/search

종목 검색(자동완성)을 수행합니다.

**Query**

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| q | string | Y | 검색어 |
| type | string | N | STOCK / ETF / ALL (기본: ALL) |

**요청 예시**

```http
GET /api/settings/stocks/search?q=삼성&type=STOCK HTTP/1.1
Host: localhost:8000
```

**응답**

- 검색된 종목 목록 (ticker, name, type 등)

**응답 예시**

```json
[
  {
    "ticker": "005930",
    "name": "삼성전자",
    "type": "STOCK"
  },
  {
    "ticker": "005935",
    "name": "삼성전자우",
    "type": "STOCK"
  }
]
```

**상태 코드**: 200, 500

---

### POST /api/settings/stocks/reorder

종목 표시 순서를 변경합니다. (API Key 필요)

**Body**

- `tickers`: string[] — 원하는 순서의 티커 배열

**요청 예시**

```http
POST /api/settings/stocks/reorder HTTP/1.1
Host: localhost:8000
Content-Type: application/json
X-API-Key: your-api-key

["487240", "466920", "042660"]
```

**응답 예시**

```json
{
  "message": "Successfully reordered stocks",
  "count": 3,
  "order": ["487240", "466920", "042660"]
}
```

**상태 코드**: 200, 400, 401, 500

---

### GET /api/settings/ticker-catalog/collect-progress

티커 카탈로그(코스피/코스닥/ETF 목록) 수집 진행률을 반환합니다.

**요청 예시**

```http
GET /api/settings/ticker-catalog/collect-progress HTTP/1.1
Host: localhost:8000
```

**응답**

- `status`: idle / in_progress / completed / error 등

**응답 예시**

```json
{
  "status": "idle"
}
```

```json
{
  "status": "in_progress",
  "phase": "ETF",
  "current": 50,
  "total": 200
}
```

**상태 코드**: 200

---

### POST /api/settings/ticker-catalog/collect

티커 카탈로그 수집을 시작합니다 (백그라운드). (API Key 필요)

**요청 예시**

```http
POST /api/settings/ticker-catalog/collect HTTP/1.1
Host: localhost:8000
X-API-Key: your-api-key
```

**응답 예시**

```json
{
  "message": "Ticker catalog collection started",
  "status": "started"
}
```

**상태 코드**: 200, 401, 500

---

### GET /api/settings/api-keys

저장된 API 키 목록(키 이름만, 값은 마스킹)을 반환합니다.

**요청 예시**

```http
GET /api/settings/api-keys HTTP/1.1
Host: localhost:8000
```

**응답**

- 키 이름 목록 또는 마스킹된 객체

**응답 예시**

```json
{
  "keys": ["NAVER_CLIENT_ID", "NAVER_CLIENT_SECRET", "PERPLEXITY_API_KEY"]
}
```

**상태 코드**: 200, 500

---

### PUT /api/settings/api-keys

API 키를 저장/수정합니다. (기존 api-keys.json 갱신)

**Body**

- 키 이름과 값 객체 (예: `NAVER_CLIENT_ID`, `PERPLEXITY_API_KEY` 등)

**요청 예시**

```http
PUT /api/settings/api-keys HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
  "NAVER_CLIENT_ID": "your_naver_client_id",
  "NAVER_CLIENT_SECRET": "your_naver_client_secret",
  "PERPLEXITY_API_KEY": "your_perplexity_api_key"
}
```

**응답 예시**

```json
{
  "message": "API 키가 저장되었습니다",
  "updated": ["NAVER_CLIENT_ID", "PERPLEXITY_API_KEY"]
}
```

**상태 코드**: 200, 400, 500

---

## 7. 알림 (`/api/alerts`)

알림 규칙 CRUD, 트리거 기록, 종목별 이력 조회를 제공합니다.

### GET /api/alerts/{ticker}

종목별 알림 규칙 목록을 반환합니다.

**Query**

- `active_only`: bool (기본 true) — 활성 규칙만 반환할지 여부

**요청 예시**

```http
GET /api/alerts/487240?active_only=true HTTP/1.1
Host: localhost:8000
```

**응답**

- `AlertRuleResponse[]`: id, ticker, alert_type, direction, target_price, memo, is_active 등

**응답 예시**

```json
[
  {
    "id": 1,
    "ticker": "487240",
    "alert_type": "buy",
    "direction": "above",
    "target_price": 13000,
    "memo": "목표가 도달 시 알림",
    "is_active": 1,
    "created_at": "2025-02-01T10:00:00",
    "last_triggered_at": null
  }
]
```

**상태 코드**: 200, 500

---

### POST /api/alerts/

알림 규칙을 생성합니다.

**Body**

- `ticker`: string (필수)
- `alert_type`: "buy" | "sell" | "price_change" | "trading_signal"
- `direction`: "above" | "below" | "both"
- `target_price`: number (목표가 또는 등락률 임계값)
- `memo`: string (선택)

**요청 예시**

```http
POST /api/alerts/ HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
  "ticker": "487240",
  "alert_type": "buy",
  "direction": "above",
  "target_price": 13000,
  "memo": "목표가 도달 시 알림"
}
```

**응답**

- `AlertRuleResponse`

**응답 예시**

```json
{
  "id": 1,
  "ticker": "487240",
  "alert_type": "buy",
  "direction": "above",
  "target_price": 13000,
  "memo": "목표가 도달 시 알림",
  "is_active": 1,
  "created_at": "2025-02-01T10:00:00",
  "last_triggered_at": null
}
```

**상태 코드**: 200, 400, 500

---

### PUT /api/alerts/{rule_id}

알림 규칙을 수정합니다.

**Body**

- `alert_type`, `direction`, `target_price`, `memo`, `is_active` (모두 선택)

**요청 예시**

```http
PUT /api/alerts/1 HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
  "target_price": 13500,
  "memo": "목표가 상향 조정",
  "is_active": 1
}
```

**상태 코드**: 200, 400, 404, 500

---

### DELETE /api/alerts/{rule_id}

알림 규칙을 삭제합니다 (관련 히스토리 포함 삭제).

**요청 예시**

```http
DELETE /api/alerts/1 HTTP/1.1
Host: localhost:8000
```

**상태 코드**: 200, 404, 500

---

### POST /api/alerts/trigger

프론트엔드에서 감지한 알림 트리거를 히스토리에 기록합니다.

**Body**

- `rule_id`: int
- `ticker`: string
- `alert_type`: string
- `message`: string

**요청 예시**

```http
POST /api/alerts/trigger HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
  "rule_id": 1,
  "ticker": "487240",
  "alert_type": "buy",
  "message": "목표가 13000원 도달"
}
```

**응답**

- `recorded`: true

**응답 예시**

```json
{
  "recorded": true
}
```

**상태 코드**: 200, 500

---

### GET /api/alerts/history/{ticker}

종목별 알림 발동 이력을 반환합니다.

**Query**

- `limit`: int (1~100, 기본 20)

**요청 예시**

```http
GET /api/alerts/history/487240?limit=20 HTTP/1.1
Host: localhost:8000
```

**응답**

- `alert_history[]`: rule_id, ticker, alert_type, message, triggered_at 등

**응답 예시**

```json
[
  {
    "id": 1,
    "rule_id": 1,
    "ticker": "487240",
    "alert_type": "buy",
    "message": "목표가 13000원 도달",
    "triggered_at": "2025-02-18T14:30:00"
  }
]
```

**상태 코드**: 200, 500

---

## 8. 종목 발굴 (`/api/scanner`)

조건 기반 종목 검색, 테마별 그룹, 추천 프리셋, 종목 발굴 수집 진행/취소를 제공합니다.

### GET /api/scanner

조건 기반 종목 검색 결과를 반환합니다.

**Query**

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| q | string | N | 종목명/코드 검색어 |
| type | string | N | ETF / STOCK / ALL (기본: ETF) |
| sector | string | N | 섹터 필터 |
| min_weekly_return | float | N | 최소 주간수익률 |
| max_weekly_return | float | N | 최대 주간수익률 |
| foreign_net_positive | bool | N | 외국인 순매수만 |
| institutional_net_positive | bool | N | 기관 순매수만 |
| sort_by | string | N | weekly_return, daily_change_pct, volume, close_price, foreign_net, institutional_net, name |
| sort_dir | string | N | asc / desc (기본: desc) |
| page | int | N | 페이지 (기본: 1) |
| page_size | int | N | 페이지 크기 (1~50, 기본: 20) |

**요청 예시**

```http
GET /api/scanner?q=AI&type=ETF&sort_by=weekly_return&sort_dir=desc&page=1&page_size=20 HTTP/1.1
Host: localhost:8000
```

**응답**

- `ScreeningResponse`: `items`, `total`, `page`, `page_size`

**응답 예시**

```json
{
  "items": [
    {
      "ticker": "487240",
      "name": "삼성 KODEX AI전력핵심설비 ETF",
      "type": "ETF",
      "market": "KRX",
      "sector": "AI/전력",
      "close_price": 12520.0,
      "daily_change_pct": 0.56,
      "volume": 125000,
      "weekly_return": 2.3,
      "foreign_net": 4300,
      "institutional_net": 8200,
      "catalog_updated_at": "2025-02-18T09:00:00",
      "is_registered": true
    }
  ],
  "total": 150,
  "page": 1,
  "page_size": 20
}
```

**상태 코드**: 200, 500

---

### GET /api/scanner/themes

섹터/테마별 그룹(평균 수익률, 상위 종목 등)을 반환합니다.

**요청 예시**

```http
GET /api/scanner/themes HTTP/1.1
Host: localhost:8000
```

**응답**

- `ThemeGroup[]`: sector, 평균 수익률, top 종목 등

**응답 예시**

```json
[
  {
    "sector": "AI/전력",
    "count": 12,
    "avg_weekly_return": 2.5,
    "top_performers": [
      {
        "ticker": "487240",
        "name": "삼성 KODEX AI전력핵심설비 ETF",
        "type": "ETF",
        "weekly_return": 3.2,
        "close_price": 12520.0
      }
    ]
  }
]
```

**상태 코드**: 200, 500

---

### GET /api/scanner/recommendations

추천 프리셋(주간 상위, 외국인 매수 등)을 반환합니다.

**Query**

- `limit`: int (1~10, 기본 5)

**요청 예시**

```http
GET /api/scanner/recommendations?limit=5 HTTP/1.1
Host: localhost:8000
```

**응답**

- `RecommendationPreset[]`

**응답 예시**

```json
[
  {
    "preset_id": "weekly_top",
    "title": "주간 수익률 상위",
    "description": "최근 1주일 수익률 상위 종목",
    "items": [
      {
        "ticker": "487240",
        "name": "삼성 KODEX AI전력핵심설비 ETF",
        "type": "ETF",
        "weekly_return": 3.2
      }
    ]
  }
]
```

**상태 코드**: 200, 500

---

### GET /api/scanner/collect-progress

종목 발굴용 카탈로그 데이터 수집 진행률을 반환합니다.

**요청 예시**

```http
GET /api/scanner/collect-progress HTTP/1.1
Host: localhost:8000
```

**응답**

- `status`: idle / in_progress / completed / cancelled / error

**응답 예시**

```json
{
  "status": "idle"
}
```

**상태 코드**: 200

---

### POST /api/scanner/collect-data

종목 발굴 카탈로그 데이터 수집을 백그라운드로 시작합니다.

**요청 예시**

```http
POST /api/scanner/collect-data HTTP/1.1
Host: localhost:8000
```

**응답 예시**

```json
{
  "message": "카탈로그 데이터 수집이 시작되었습니다",
  "status": "started"
}
```

**상태 코드**: 200, 500

---

### POST /api/scanner/cancel-collect

진행 중인 수집을 중지 요청합니다.

**요청 예시**

```http
POST /api/scanner/cancel-collect HTTP/1.1
Host: localhost:8000
```

**응답 예시**

```json
{
  "message": "수집 중지 요청됨",
  "status": "cancelling"
}
```

**상태 코드**: 200, 500

---

## 9. 시뮬레이션 (`/api/simulation`)

일시 투자, 적립식(DCA), 포트폴리오 시뮬레이션을 제공합니다.

### POST /api/simulation/lump-sum

일시 투자 시뮬레이션을 실행합니다.

**Body**

- `ticker`: string (필수)
- `buy_date`: date YYYY-MM-DD (필수)
- `amount`: number (투자 금액, 필수)

**요청 예시**

```http
POST /api/simulation/lump-sum HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
  "ticker": "487240",
  "buy_date": "2024-06-01",
  "amount": 100000
}
```

**응답**

- 매수 주수, 현재 평가액, 수익률, 최대 수익/손실, 가격 시리즈 등 (`LumpSumResponse`)

**응답 예시**

```json
{
  "ticker": "487240",
  "name": "삼성 KODEX AI전력핵심설비 ETF",
  "buy_date": "2024-06-01",
  "buy_price": 10500.0,
  "current_date": "2025-02-18",
  "current_price": 12520.0,
  "shares": 9,
  "remainder": 5500.0,
  "total_invested": 100000.0,
  "total_valuation": 112680.0,
  "total_return_pct": 12.68,
  "max_gain": { "date": "2025-02-10", "price": 12800.0, "return_pct": 21.9 },
  "max_loss": { "date": "2024-08-15", "price": 9800.0, "return_pct": -6.67 },
  "price_series": [
    { "date": "2024-06-01", "close_price": 10500.0, "valuation": 94500.0, "return_pct": -5.5 }
  ]
}
```

**상태 코드**: 200, 400, 503, 500

---

### POST /api/simulation/dca

적립식(DCA) 투자 시뮬레이션을 실행합니다.

**Body**

- `ticker`: string (필수)
- `monthly_amount`: number (월 투자액, 필수)
- `start_date`: date (필수)
- `end_date`: date (필수, 시작일보다 이후)
- `buy_day`: int (1~28, 매수일, 필수)

**제한**

- 시뮬레이션 기간 최대 5년

**요청 예시**

```http
POST /api/simulation/dca HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
  "ticker": "487240",
  "monthly_amount": 100000,
  "start_date": "2024-06-01",
  "end_date": "2025-02-18",
  "buy_day": 1
}
```

**응답**

- 총 투자금, 평가액, 평균 매수가, 월별 상세 등 (`DCAResponse`)

**응답 예시**

```json
{
  "ticker": "487240",
  "name": "삼성 KODEX AI전력핵심설비 ETF",
  "total_invested": 600000.0,
  "total_valuation": 672000.0,
  "total_return_pct": 12.0,
  "avg_buy_price": 11200.0,
  "total_shares": 60,
  "monthly_data": [
    {
      "date": "2024-06-01",
      "buy_price": 10500.0,
      "shares_bought": 9,
      "cumulative_shares": 9,
      "cumulative_invested": 100000.0,
      "cumulative_valuation": 94500.0,
      "return_pct": -5.5
    }
  ]
}
```

**상태 코드**: 200, 400, 503, 500

---

### POST /api/simulation/portfolio

포트폴리오 시뮬레이션을 실행합니다.

**Body**

- `holdings`: Array<{ ticker, weight }> (비중 합계 1.0, 최대 20종목, 중복 불가)
- `amount`: number (총 투자금)
- `start_date`: date
- `end_date`: date

**제한**

- 기간 최대 5년

**요청 예시**

```http
POST /api/simulation/portfolio HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
  "holdings": [
    { "ticker": "487240", "weight": 0.5 },
    { "ticker": "466920", "weight": 0.5 }
  ],
  "amount": 1000000,
  "start_date": "2024-06-01",
  "end_date": "2025-02-18"
}
```

**응답**

- 종목별 결과, 일별 포트폴리오 가치 시리즈 (`PortfolioSimulationResponse`)

**응답 예시**

```json
{
  "total_invested": 1000000.0,
  "total_valuation": 1120000.0,
  "total_return_pct": 12.0,
  "holdings_result": [
    {
      "ticker": "487240",
      "weight": 0.5,
      "invested": 500000.0,
      "valuation": 560000.0,
      "return_pct": 12.0
    },
    {
      "ticker": "466920",
      "weight": 0.5,
      "invested": 500000.0,
      "valuation": 560000.0,
      "return_pct": 12.0
    }
  ],
  "daily_series": [
    { "date": "2024-06-01", "valuation": 1000000.0, "return_pct": 0.0 },
    { "date": "2025-02-18", "valuation": 1120000.0, "return_pct": 12.0 }
  ]
}
```

**상태 코드**: 200, 400, 503, 500

---

## 10. 에러 코드

### HTTP 상태 코드

| HTTP 코드 | 설명 |
|-----------|------|
| 200 | 성공 |
| 201 | 생성됨 (POST로 리소스 생성 시) |
| 400 | 잘못된 요청 (파라미터/바디 검증 실패) |
| 401 | 인증 필요 (API Key 누락/오류) |
| 404 | 리소스를 찾을 수 없음 (종목, 규칙 등) |
| 422 | Unprocessable Entity (입력 값 검증 실패) |
| 429 | Rate Limit 초과 |
| 500 | 서버 내부 오류 |
| 503 | 서비스 일시 불가 (외부 데이터 수집 실패 등) |

### 에러 응답 예시

요청 실패 시 응답 본문은 다음 형식입니다.

```json
{
  "detail": "오류 메시지 (문자열)"
}
```

복수 필드 검증 실패(422) 시:

```json
{
  "detail": [
    {
      "loc": ["body", "ticker"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

**상태 코드**: 요청에 따라 400, 401, 404, 422, 429, 500, 503

---

## 11. 참고

- **Swagger UI**: `http://localhost:8000/docs` — 대화형 API 문서 및 요청/응답 스키마 확인
- **ReDoc**: `http://localhost:8000/redoc` — 읽기용 API 문서
- **상세 스키마**: 요청/응답 모델은 Swagger 또는 `backend/app/models.py` 참고
- **명세 요약**: [API_SPECIFICATION.md](./API_SPECIFICATION.md)
- **DB 스키마**: [DATABASE_SCHEMA.md](./DATABASE_SCHEMA.md)
