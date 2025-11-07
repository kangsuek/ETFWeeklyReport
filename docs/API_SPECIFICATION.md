# API 명세서

## Base URL

- 개발: `http://localhost:8000/api`
- 프로덕션: `https://your-domain.com/api`

## 공통 헤더

```
Content-Type: application/json
```

## 응답 형식

### 성공 응답

```json
{
  "data": { ... },
  "status": "success"
}
```

### 에러 응답

```json
{
  "detail": "Error message",
  "status_code": 400
}
```

---

## API 엔드포인트

### 1. Health Check

#### GET `/api/health`

서버 상태 확인

**응답 예시:**

```json
{
  "status": "healthy",
  "message": "ETF Report API is running"
}
```

---

### 2. 종목 목록 조회

#### GET `/api/etfs`

전체 종목 목록 조회 (ETF 4개 + 주식 2개)

**응답 예시:**

```json
[
  {
    "ticker": "487240",
    "name": "삼성 KODEX AI전력핵심설비 ETF",
    "type": "ETF",
    "theme": "AI/전력",
    "launch_date": "2024-03-15",
    "expense_ratio": 0.0045
  },
  {
    "ticker": "042660",
    "name": "한화오션",
    "type": "STOCK",
    "theme": "조선/방산",
    "launch_date": null,
    "expense_ratio": null
  }
]
```

---

### 3. 종목 기본 정보 조회

#### GET `/api/etfs/{ticker}`

특정 종목의 기본 정보 조회

**Path Parameters:**

- `ticker` (string, required): 종목 코드 (예: "487240", "042660")

**응답 예시:**

```json
{
  "ticker": "487240",
  "name": "삼성 KODEX AI전력핵심설비 ETF",
  "type": "ETF",
  "theme": "AI/전력",
  "launch_date": "2024-03-15",
  "expense_ratio": 0.0045
}
```

**에러:**

- `404`: 종목을 찾을 수 없음

---

### 4. 종목 가격 데이터 조회

#### GET `/api/etfs/{ticker}/prices`

특정 기간의 가격 데이터 조회

**Path Parameters:**

- `ticker` (string, required): 종목 코드 (ETF 또는 주식)

**Query Parameters:**

- `start_date` (date, optional): 시작 날짜 (YYYY-MM-DD), 기본값: 7일 전
- `end_date` (date, optional): 종료 날짜 (YYYY-MM-DD), 기본값: 오늘

**요청 예시:**

```
GET /api/etfs/487240/prices?start_date=2025-10-01&end_date=2025-11-01
GET /api/etfs/042660/prices?start_date=2025-10-01&end_date=2025-11-01
```

**응답 예시:**

```json
[
  {
    "date": "2025-11-01",
    "close_price": 12500.0,
    "volume": 1250000,
    "daily_change_pct": 2.5
  },
  {
    "date": "2025-10-31",
    "close_price": 12200.0,
    "volume": 980000,
    "daily_change_pct": -0.8
  }
]
```

---

### 5. 투자자별 매매 동향 조회

#### GET `/api/etfs/{ticker}/trading-flow`

투자자 유형별 순매수/순매도 데이터 조회

**Path Parameters:**

- `ticker` (string, required): ETF 티커 코드

**Query Parameters:**

- `start_date` (date, optional): 시작 날짜
- `end_date` (date, optional): 종료 날짜

**응답 예시:**

```json
[
  {
    "date": "2025-11-01",
    "individual_net": -15000000,
    "institutional_net": 8000000,
    "foreign_net": 7000000
  },
  {
    "date": "2025-10-31",
    "individual_net": 5000000,
    "institutional_net": -3000000,
    "foreign_net": -2000000
  }
]
```

**필드 설명:**

- `individual_net`: 개인 순매수 (양수: 순매수, 음수: 순매도)
- `institutional_net`: 기관 순매수
- `foreign_net`: 외국인 순매수

---

### 6. ETF 주요 지표 조회

#### GET `/api/etfs/{ticker}/metrics`

ETF의 주요 성과 지표 조회

**Path Parameters:**

- `ticker` (string, required): ETF 티커 코드

**응답 예시:**

```json
{
  "ticker": "480450",
  "aum": 150.5,
  "returns": {
    "1w": 2.3,
    "1m": 8.5,
    "ytd": 15.3,
    "1y": 25.8
  },
  "volatility": 18.5
}
```

**필드 설명:**

- `aum`: 순자산총액 (단위: 십억 원)
- `returns`: 수익률 (%, 기간별)
- `volatility`: 변동성 (연환산 표준편차, %)

---

### 7. ETF 관련 뉴스 조회

#### GET `/api/news/{ticker}`

ETF 테마 관련 뉴스 조회

**Path Parameters:**

- `ticker` (string, required): ETF 티커 코드

**Query Parameters:**

- `start_date` (date, optional): 시작 날짜
- `end_date` (date, optional): 종료 날짜

**응답 예시:**

```json
[
  {
    "date": "2025-11-01",
    "title": "AI 데이터센터 투자 급증... 전력주 주목",
    "url": "https://news.naver.com/...",
    "source": "매일경제",
    "relevance_score": 0.85
  },
  {
    "date": "2025-10-31",
    "title": "엔비디아, 차세대 AI 칩 발표",
    "url": "https://news.naver.com/...",
    "source": "한국경제",
    "relevance_score": 0.72
  }
]
```

---

### 8. ETF 비교

#### GET `/api/etfs/compare`

여러 ETF의 성과 비교

**Query Parameters:**

- `tickers` (string, required): 쉼표로 구분된 티커 목록 (예: "480450,456600,497450,481330")
- `start_date` (date, optional): 비교 시작 날짜
- `end_date` (date, optional): 비교 종료 날짜

**요청 예시:**

```
GET /api/etfs/compare?tickers=480450,456600&start_date=2025-10-01
```

**응답 예시:**

```json
{
  "tickers": ["480450", "456600"],
  "period": {
    "start": "2025-10-01",
    "end": "2025-11-01"
  },
  "comparison": [
    {
      "ticker": "480450",
      "name": "KODEX AI전력핵심설비",
      "return": 8.5,
      "volatility": 18.5,
      "sharpe_ratio": 1.2
    },
    {
      "ticker": "456600",
      "name": "SOL 조선TOP3플러스",
      "return": 12.3,
      "volatility": 22.1,
      "sharpe_ratio": 1.4
    }
  ]
}
```

---

### 9. 리포트 생성

#### POST `/api/reports/generate`

선택된 ETF에 대한 리포트 생성

**요청 Body:**

```json
{
  "tickers": ["480450", "456600"],
  "format": "markdown",
  "start_date": "2025-10-01",
  "end_date": "2025-11-01"
}
```

**필드 설명:**

- `tickers` (array, required): 리포트에 포함할 ETF 티커 목록
- `format` (string, required): "markdown" 또는 "pdf"
- `start_date` (date, optional): 분석 시작 날짜
- `end_date` (date, optional): 분석 종료 날짜

**응답 예시:**

```json
{
  "report_id": "rpt_20251101_123456",
  "download_url": "/api/reports/download/rpt_20251101_123456",
  "format": "markdown",
  "created_at": "2025-11-01T14:30:00Z"
}
```

---

## 에러 코드

| 코드 | 설명 |
|-----|------|
| 200 | 성공 |
| 400 | 잘못된 요청 (파라미터 오류) |
| 404 | 리소스를 찾을 수 없음 |
| 500 | 서버 내부 오류 |
| 503 | 외부 API 연결 실패 |

---

## Rate Limiting (추후 구현 예정)

- 일반 엔드포인트: 100 requests/minute
- 데이터 수집 엔드포인트: 10 requests/minute

---

**Last Updated**: 2025-11-06

