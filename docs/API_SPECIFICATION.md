# API 명세서

## Base URL
- 개발: `http://localhost:8000/api`
- 프로덕션: `https://your-domain.com/api`

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

## 주요 API 엔드포인트

### 1. Health Check
**GET** `/api/health`
- 서버 상태 확인

### 2. 종목 목록 조회
**GET** `/api/etfs`
- 전체 종목 목록 조회 (ETF 4개 + 주식 2개)

### 3. 종목 기본 정보 조회
**GET** `/api/etfs/{ticker}`
- 특정 종목의 기본 정보 조회

### 4. 종목 가격 데이터 조회
**GET** `/api/etfs/{ticker}/prices`
- Query: `start_date`, `end_date` (YYYY-MM-DD)

### 5. 데이터 수집 트리거
**POST** `/api/etfs/{ticker}/collect`
- Query: `days` (기본값: 10)

### 6. 투자자별 매매 동향 조회
**GET** `/api/etfs/{ticker}/trading-flow`
- Query: `start_date`, `end_date`

### 7. ETF 관련 뉴스 조회
**GET** `/api/news/{ticker}`
- Query: `start_date`, `end_date`

**POST** `/api/news/{ticker}/collect`
- Query: `days` (기본: 7일, 최대: 30일)

### 8. ETF 비교
**GET** `/api/etfs/compare`
- Query: `tickers` (쉼표로 구분), `start_date`, `end_date`

### 8.5. 종목 인사이트 조회
**GET** `/api/etfs/{ticker}/insights`
- Query: `period` (기본값: "1m", 선택: "1w", "1m", "3m", "6m", "1y")
- 종목의 투자 전략, 핵심 포인트, 리스크 분석 제공
- 응답: `strategy` (단기/중기/장기 전략, 종합 추천, 코멘트), `key_points` (최대 3개), `risks` (최대 3개)
- 캐시: 1분

### 8.6. 종목 지표 조회 (확장)
**GET** `/api/etfs/{ticker}/metrics`
- 수익률 (1주, 1개월, YTD)
- 연환산 변동성
- 최대 낙폭 (MDD) - **신규 추가**
- 샤프 비율 - **신규 추가**
- 캐시: 1분

### 9. 리포트 생성
**POST** `/api/reports/generate`
- Body: `tickers`, `format` (markdown/pdf), `start_date`, `end_date`

### 10. 종목 목록 수집 (관리자용)
**POST** `/api/settings/ticker-catalog/collect`
- 네이버 금융에서 전체 종목 목록(코스피, 코스닥, ETF) 수집
- `stock_catalog` 테이블에 저장
- 응답: 수집 통계 (total_collected, kospi_count, kosdaq_count, etf_count, saved_count)

### 11. 종목 검색 (자동완성용)
**GET** `/api/settings/stocks/search`
- Query: `q` (검색어, 최소 2자), `type` (선택, STOCK/ETF)
- `stock_catalog` 테이블에서 티커 코드 또는 종목명으로 검색
- 최대 20개 결과 반환

## 에러 코드
| 코드 | 설명 |
|-----|------|
| 200 | 성공 |
| 400 | 잘못된 요청 |
| 404 | 리소스를 찾을 수 없음 |
| 422 | 입력 값 검증 실패 |
| 500 | 서버 내부 오류 |

## API 구현 상태
- ✅ Phase 1: Health, 종목 목록, 가격 데이터, 데이터 수집
- ✅ Phase 2: 투자자별 매매 동향, 뉴스
- ✅ Phase 2.5: 티커 카탈로그 수집 및 검색 (종목 목록 수집, 자동완성 검색)
- ✅ Phase 4: 종목 인사이트 조회 (`/api/etfs/{ticker}/insights`)
- ⏳ Phase 3-6: 비교, 리포트 생성

## 참고
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
