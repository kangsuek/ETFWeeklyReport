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
    "theme": "AI/전력"
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
  "theme": "AI/전력"
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
    "date": "2025-11-07",
    "close_price": 25695.0,
    "volume": 1705721,
    "daily_change_pct": -0.27
  }
]
```

**에러:**

- `404`: 종목을 찾을 수 없음
- `500`: 서버 내부 오류

---

### 5. 데이터 수집 트리거 ⭐ NEW (Phase 1 완료)

#### POST `/api/etfs/{ticker}/collect`

Naver Finance에서 특정 종목의 가격 데이터를 수집합니다.

**Path Parameters:**

- `ticker` (string, required): 종목 코드 (ETF 또는 주식)

**Query Parameters:**

- `days` (integer, optional): 수집할 일수 (기본값: 10)

**요청 예시:**

```
POST /api/etfs/487240/collect?days=10
POST /api/etfs/042660/collect?days=5
```

**응답 예시 (성공):**

```json
{
  "ticker": "487240",
  "collected": 10,
  "message": "Successfully collected 10 price records"
}
```

**응답 예시 (데이터 없음):**

```json
{
  "ticker": "487240",
  "collected": 0,
  "message": "No data collected. Check if the ticker is valid or data is available."
}
```

**에러:**

- `404`: 종목을 찾을 수 없음
- `500`: 데이터 수집 실패

---

### 6. 투자자별 매매 동향 조회 (Phase 2)

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
  }
]
```

**필드 설명:**

- `individual_net`: 개인 순매수 (양수: 순매수, 음수: 순매도)
- `institutional_net`: 기관 순매수
- `foreign_net`: 외국인 순매수

---

### 7. ETF 주요 지표 조회 (Phase 2)

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

### 8. ETF 관련 뉴스 조회 (Phase 2)

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
    "source": "매일경제",
    "relevance_score": 0.85
  }
]
```

#### POST `/api/news/{ticker}/collect`

ETF 테마 관련 뉴스 수집 트리거

**Path Parameters:**

- `ticker` (string, required): ETF 티커 코드

**Query Parameters:**

- `days` (int, optional): 수집할 일수 (기본: 7일, 최대: 30일)

**응답 예시:**

```json
{
  "ticker": "480450",
  "collected": 5,
  "keywords": ["AI", "데이터센터", "엔비디아"],
  "period": "7 days"
}
```


---

### 9. ETF 비교 (Phase 3)

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
  "comparison": [
    {
      "ticker": "480450",
      "name": "KODEX AI전력핵심설비",
      "return": 8.5,
      "volatility": 18.5
    }
  ]
}
```

---

### 10. 리포트 생성 (Phase 6)

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
| 404 | 리소스를 찾을 수 없음 (종목, 데이터 등) |
| 422 | 입력 값 검증 실패 (날짜 형식 오류 등) |
| 500 | 서버 내부 오류 |
| 503 | 외부 API 연결 실패 |

---

## API 구현 상태

### ✅ Phase 1 완료 (2025-11-07)
- ✅ **GET** `/api/health` - 헬스 체크
- ✅ **GET** `/api/etfs/` - 전체 종목 목록 (6개)
- ✅ **GET** `/api/etfs/{ticker}` - 종목 정보 조회
- ✅ **GET** `/api/etfs/{ticker}/prices` - 가격 데이터 조회
- ✅ **POST** `/api/etfs/{ticker}/collect` - 데이터 수집 트리거 ⭐

### 🔄 Phase 2 예정
- ⏳ **GET** `/api/etfs/{ticker}/trading-flow` - 투자자별 매매 동향
- ⏳ **GET** `/api/etfs/{ticker}/metrics` - ETF 주요 지표
- ⏳ **GET** `/api/news/{ticker}` - 뉴스 조회

### 🔄 Phase 3-6 예정
- ⏳ **GET** `/api/etfs/compare` - ETF 비교
- ⏳ **POST** `/api/reports/generate` - 리포트 생성

---

## Rate Limiting (추후 구현 예정)

- 일반 엔드포인트: 100 requests/minute
- 데이터 수집 엔드포인트: 10 requests/minute

---

## 참고 자료

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **실행 가이드**: [docs/RUNNING_GUIDE.md](./RUNNING_GUIDE.md)

---