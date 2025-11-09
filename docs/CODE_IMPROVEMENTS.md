# 코드 개선 필요 사항 분석

> 생성일: 2025-11-09  
> 분석 범위: 전체 소스코드 (백엔드 + 프론트엔드)

## 📋 목차

1. [보안 이슈](#1-보안-이슈)
2. [데이터베이스 연결 관리](#2-데이터베이스-연결-관리)
3. [에러 처리 개선](#3-에러-처리-개선)
4. [코드 중복](#4-코드-중복)
5. [환경 변수 미사용](#5-환경-변수-미사용)
6. [미구현 기능](#6-미구현-기능)
7. [성능 개선](#7-성능-개선)
8. [코드 품질](#8-코드-품질)
9. [테스트 커버리지](#9-테스트-커버리지)
10. [문서화](#10-문서화)
11. [우선순위별 개선 권장사항](#우선순위별-개선-권장사항)

---

## 1. 보안 이슈

### 1.1 API 키 노출 위험 ⚠️ **중요**

**문제:**
- `prototypes/news_scraper_poc/` 디렉토리에 하드코딩된 API 키 발견
- `NAVER_CLIENT_SECRET=GcptomaJI1`이 여러 파일에 하드코딩됨
- 영향: Git 히스토리에 민감 정보 노출 가능

**발견 위치:**
- `backend/prototypes/news_scraper_poc/QUICK_START.md`
- `backend/prototypes/news_scraper_poc/WORK_INSTRUCTION.md`
- `backend/prototypes/news_scraper_poc/새_세션_시작_방법.md`

**권장 조치:**
- 해당 파일들에서 하드코딩된 API 키 제거
- `.gitignore` 확인 및 `.env` 파일이 커밋되지 않았는지 확인
- Git 히스토리에서 민감 정보 제거 (필요시 `git filter-branch` 또는 `BFG Repo-Cleaner` 사용)

### 1.2 CORS 설정 하드코딩

**위치:** `backend/app/main.py:28`

**문제:**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # 하드코딩
    ...
)
```

**권장:**
- 환경 변수(`CORS_ORIGINS`)로 이동 (`.env.example`에 이미 정의됨)
- 프로덕션 환경에서는 보안을 위해 특정 도메인만 허용

---

## 2. 데이터베이스 연결 관리

### 2.1 연결 리소스 누수 위험 ⚠️ **중요**

**위치:** 
- `backend/app/services/data_collector.py`
- `backend/app/services/news_scraper.py`

**문제:**
- `get_db_connection()`이 매번 새 연결 생성
- 일부 메서드에서 `finally` 블록 없이 `conn.close()` 호출
- 예외 발생 시 연결이 닫히지 않을 수 있음

**예시:**
```python
# get_all_etfs() - 예외 발생 시 연결이 닫히지 않음
def get_all_etfs(self) -> List[ETF]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM etfs")
    rows = cursor.fetchall()
    conn.close()  # 예외 발생 시 실행 안됨
    return [ETF(**dict(row)) for row in rows]
```

**권장 해결책:**

**방법 1: Context Manager 사용**
```python
from contextlib import contextmanager

@contextmanager
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

# 사용 예시
def get_all_etfs(self) -> List[ETF]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM etfs")
        rows = cursor.fetchall()
        return [ETF(**dict(row)) for row in rows]
```

**방법 2: try-finally 보장**
```python
def get_all_etfs(self) -> List[ETF]:
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM etfs")
        rows = cursor.fetchall()
        return [ETF(**dict(row)) for row in rows]
    finally:
        conn.close()
```

**방법 3: Connection Pool 도입 (장기적)**
- SQLite는 단일 연결이지만, PostgreSQL로 전환 시 Connection Pool 고려

### 2.2 트랜잭션 관리 불일치

**위치:** `backend/app/services/data_collector.py:252-308`

**문제:**
- `save_price_data()`에서 `finally`에서 `conn.close()` 호출하지만, 예외 발생 시 `saved_count`가 초기화되지 않을 수 있음

**권장:**
- 트랜잭션 관리 일관성 확보
- 예외 발생 시 명확한 롤백 처리

---

## 3. 에러 처리 개선

### 3.1 과도하게 포괄적인 예외 처리

**위치:** 여러 라우터 파일

**문제:**
```python
# backend/app/routers/etfs.py:17-19
except Exception as e:
    logger.error(f"Error fetching ETFs: {e}")
    raise HTTPException(status_code=500, detail=str(e))
```

**권장:**
- 구체적인 예외 타입 처리
- 데이터베이스 오류, 네트워크 오류, 검증 오류 등 구분

**개선 예시:**
```python
except sqlite3.Error as e:
    logger.error(f"Database error fetching ETFs: {e}")
    raise HTTPException(status_code=500, detail="Database error occurred")
except ValueError as e:
    logger.error(f"Validation error: {e}")
    raise HTTPException(status_code=400, detail=str(e))
except Exception as e:
    logger.error(f"Unexpected error fetching ETFs: {e}", exc_info=True)
    raise HTTPException(status_code=500, detail="Internal server error")
```

### 3.2 에러 메시지에 민감 정보 노출 가능성

**위치:** `backend/app/routers/etfs.py:78`

**문제:**
```python
raise HTTPException(status_code=500, detail=f"Failed to fetch prices: {str(e)}")
```

**권장:**
- 프로덕션에서는 일반적인 메시지만 반환
- 상세 에러는 로그에만 기록

**개선 예시:**
```python
except Exception as e:
    logger.error(f"Error fetching prices for {ticker}: {e}", exc_info=True)
    # 프로덕션에서는 상세 정보 숨김
    raise HTTPException(
        status_code=500, 
        detail="Failed to fetch prices. Please try again later."
    )
```

---

## 4. 코드 중복

### 4.1 날짜 기본값 설정 중복

**위치:**
- `backend/app/routers/etfs.py:67-70`
- `backend/app/routers/news.py:35-38`

**문제:**
```python
# 중복된 코드
if not start_date:
    start_date = date.today() - timedelta(days=7)
if not end_date:
    end_date = date.today()
```

**권장:**
- 공통 유틸리티 함수로 추출

**개선 예시:**
```python
# backend/app/utils/date_utils.py
def get_default_date_range(days: int = 7) -> tuple[date, date]:
    """기본 날짜 범위 반환"""
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    return start_date, end_date

# 사용
start_date, end_date = get_default_date_range(7)
```

### 4.2 ETF 존재 확인 중복

**위치:** 여러 라우터에서 반복

**예시:**
- `backend/app/routers/etfs.py:61-64`
- `backend/app/routers/news.py:31-33`

**문제:**
```python
# 중복된 코드
etf = collector.get_etf_info(ticker)
if not etf:
    raise HTTPException(status_code=404, detail=f"ETF/Stock {ticker} not found")
```

**권장:**
- FastAPI 의존성 주입(Dependency Injection) 사용

**개선 예시:**
```python
# backend/app/dependencies.py
from fastapi import Depends, HTTPException
from app.services.data_collector import ETFDataCollector
from app.models import ETF

def get_etf_dependency(ticker: str, collector: ETFDataCollector = Depends()) -> ETF:
    """ETF 존재 확인 의존성"""
    etf = collector.get_etf_info(ticker)
    if not etf:
        raise HTTPException(status_code=404, detail=f"ETF/Stock {ticker} not found")
    return etf

# 사용
@router.get("/{ticker}/prices")
async def get_prices(
    etf: ETF = Depends(get_etf_dependency)
):
    # etf는 이미 검증됨
    ...
```

---

## 5. 환경 변수 미사용

### 5.1 DATABASE_URL 미사용

**위치:** `backend/app/database.py:8`

**문제:**
```python
DB_PATH = Path(__file__).parent.parent / "data" / "etf_data.db"  # 하드코딩
```

**권장:**
```python
from app.config import Config

DB_PATH = os.getenv("DATABASE_URL")
if not DB_PATH:
    # 기본값 (SQLite)
    DB_PATH = Path(__file__).parent.parent / "data" / "etf_data.db"
else:
    # PostgreSQL 등 다른 DB 사용 시
    DB_PATH = DB_PATH
```

### 5.2 CACHE_TTL_MINUTES 미구현

**문제:**
- `.env.example`에 정의되어 있지만 실제 사용되지 않음
- `backend/app/config.py`에 설정이 없음

**권장:**
- 캐싱 기능 구현 (Redis 또는 메모리 캐시)
- 또는 문서에서 "미구현" 명시

---

## 6. 미구현 기능

### 6.1 리포트 생성 미구현

**위치:** `backend/app/routers/reports.py:11`

**문제:**
```python
@router.post("/generate")
async def generate_report(tickers: List[str], format: str = "markdown"):
    """Generate report for selected ETFs"""
    # TODO: Implement report generation
    return {
        "message": "Report generation not yet implemented",
        ...
    }
```

**권장:**
- 구현 또는 API 문서에 "Coming Soon" 명시
- Swagger 문서에 `deprecated` 또는 `x-internal` 태그 추가

### 6.2 메트릭스 계산 미구현

**위치:** `backend/app/services/data_collector.py:395`

**문제:**
```python
# TODO: Implement metrics calculation
```

**권장:**
- 기본 메트릭스 구현 (수익률, 변동성 등)
- 또는 기본값 반환 및 로깅

---

## 7. 성능 개선

### 7.1 N+1 쿼리 가능성

**위치:** `frontend/src/pages/Dashboard.jsx`

**문제:**
- 각 `ETFCard`가 개별 API 호출 (`prices`, `trading-flow`, `news`)
- 6개 종목 × 3개 API = 18개 요청

**권장:**
- 배치 API 엔드포인트 추가
- 예: `GET /api/etfs/batch?tickers=487240,466920&include=prices,trading-flow,news`

**개선 예시:**
```python
# backend/app/routers/etfs.py
@router.post("/batch")
async def get_batch_data(
    tickers: List[str],
    include: List[str] = Query(default=["prices"])
):
    """여러 종목의 데이터를 한 번에 조회"""
    results = {}
    for ticker in tickers:
        results[ticker] = {}
        if "prices" in include:
            results[ticker]["prices"] = collector.get_price_data(...)
        if "trading-flow" in include:
            results[ticker]["trading_flow"] = collector.get_trading_flow_data(...)
    return results
```

### 7.2 데이터베이스 인덱스 부족

**위치:** `backend/app/database.py`

**문제:**
- `prices`, `trading_flow`, `news` 테이블에 날짜 기반 조회 인덱스 없음
- `UNIQUE(ticker, date)` 제약만 있음

**권장:**
```python
# 인덱스 추가
cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_prices_ticker_date 
    ON prices(ticker, date DESC)
""")

cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_trading_flow_ticker_date 
    ON trading_flow(ticker, date DESC)
""")

cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_news_ticker_date 
    ON news(ticker, date DESC)
""")
```

---

## 8. 코드 품질

### 8.1 타입 힌트 불완전

**위치:** 프론트엔드 (`frontend/src/`)

**문제:**
- JavaScript 사용, TypeScript 미도입
- 함수 파라미터와 반환값 타입 불명확

**권장:**
- TypeScript 도입 (장기적)
- 또는 PropTypes 추가 (단기적)

**예시:**
```javascript
import PropTypes from 'prop-types'

ETFCard.propTypes = {
  etf: PropTypes.shape({
    ticker: PropTypes.string.isRequired,
    name: PropTypes.string.isRequired,
    type: PropTypes.oneOf(['ETF', 'STOCK']).isRequired,
    theme: PropTypes.string,
  }).isRequired,
}
```

### 8.2 매직 넘버

**위치:** 여러 파일

**예시:**
- `frontend/src/pages/Dashboard.jsx:21` - `30000` (30초)
- `frontend/src/pages/Dashboard.jsx:43` - `300000` (5분)

**권장:**
```javascript
// constants.js
export const REFRESH_INTERVALS = {
  SCHEDULER_STATUS: 30000, // 30초
  DATA_CACHE: 300000, // 5분
  AUTO_REFRESH: 30000, // 30초
}
```

### 8.3 긴 함수

**위치:** `frontend/src/components/etf/ETFCard.jsx:105-231`

**문제:**
- `renderMiniChart()` 함수가 126줄로 과도하게 김
- 가독성 및 테스트 어려움

**권장:**
- 작은 함수로 분리
- 예: `calculateCandleData()`, `renderCandle()`, `renderTooltip()` 등

---

## 9. 테스트 커버리지

### 9.1 에러 케이스 테스트 부족

**문제:**
- 일부 엣지 케이스 테스트 부족
- 데이터베이스 연결 실패 시나리오 부족

**권장:**
- 더 많은 에러 시나리오 테스트 추가
- Mock을 사용한 데이터베이스 오류 테스트

**예시:**
```python
def test_get_all_etfs_database_error():
    """데이터베이스 오류 시 테스트"""
    with patch('app.services.data_collector.get_db_connection') as mock_conn:
        mock_conn.side_effect = sqlite3.Error("Database locked")
        response = client.get("/api/etfs/")
        assert response.status_code == 500
```

---

## 10. 문서화

### 10.1 API 문서 불완전

**문제:**
- 일부 엔드포인트에 상세 설명 부족
- 예시 요청/응답 부족

**권장:**
- Swagger/ReDoc 문서 보완
- 각 엔드포인트에 예시 추가

**예시:**
```python
@router.get("/{ticker}/prices", response_model=List[PriceData])
async def get_prices(
    ticker: str,
    start_date: Optional[date] = Query(default=None, description="조회 시작 날짜"),
    end_date: Optional[date] = Query(default=None, description="조회 종료 날짜"),
):
    """
    Get price data for ETF/Stock within date range
    
    **Example:**
    - GET /api/etfs/487240/prices?start_date=2025-11-01&end_date=2025-11-09
    - GET /api/etfs/487240/prices?days=7
    
    **Response:**
    ```json
    [
      {
        "date": "2025-11-09",
        "close_price": 12500.0,
        "volume": 1000000,
        "daily_change_pct": 2.5
      }
    ]
    ```
    """
```

---

## 우선순위별 개선 권장사항

### 🔴 높은 우선순위 (보안/안정성)

1. **데이터베이스 연결 리소스 관리 개선** (Context Manager)
   - 위치: `backend/app/services/data_collector.py`
   - 영향: 메모리 누수 방지, 안정성 향상
   - 예상 작업 시간: 2-3시간

2. **API 키 하드코딩 제거**
   - 위치: `backend/prototypes/news_scraper_poc/`
   - 영향: 보안 위험 제거
   - 예상 작업 시간: 1시간

3. **CORS 설정을 환경 변수로 이동**
   - 위치: `backend/app/main.py`
   - 영향: 설정 유연성 향상
   - 예상 작업 시간: 30분

4. **에러 메시지에서 민감 정보 제거**
   - 위치: 모든 라우터 파일
   - 영향: 보안 향상
   - 예상 작업 시간: 1-2시간

### 🟡 중간 우선순위 (코드 품질)

5. **코드 중복 제거** (날짜 기본값, ETF 존재 확인)
   - 위치: 라우터 파일들
   - 영향: 유지보수성 향상
   - 예상 작업 시간: 2-3시간

6. **환경 변수 활용** (DATABASE_URL)
   - 위치: `backend/app/database.py`
   - 영향: 설정 유연성 향상
   - 예상 작업 시간: 1시간

7. **데이터베이스 인덱스 추가**
   - 위치: `backend/app/database.py`
   - 영향: 쿼리 성능 향상
   - 예상 작업 시간: 30분

8. **과도한 예외 처리 구체화**
   - 위치: 모든 라우터 파일
   - 영향: 디버깅 용이성 향상
   - 예상 작업 시간: 2-3시간

### 🟢 낮은 우선순위 (기능/성능)

9. **N+1 쿼리 최적화**
   - 위치: `frontend/src/pages/Dashboard.jsx`
   - 영향: 성능 향상
   - 예상 작업 시간: 4-6시간

10. **미구현 기능 구현 또는 문서화**
    - 위치: `backend/app/routers/reports.py`
    - 영향: 기능 완성도 향상
    - 예상 작업 시간: 8-16시간 (구현 시)

11. **TypeScript 도입 검토**
    - 위치: 전체 프론트엔드
    - 영향: 타입 안정성 향상
    - 예상 작업 시간: 1-2주 (전환)

12. **긴 함수 리팩토링**
    - 위치: `frontend/src/components/etf/ETFCard.jsx`
    - 영향: 가독성 향상
    - 예상 작업 시간: 2-3시간

---

## 결론

전반적으로 코드 품질은 양호하지만, 위 항목들을 개선하면 **보안**, **안정성**, **유지보수성**이 크게 향상됩니다.

특히 **데이터베이스 연결 관리**와 **보안 이슈**는 우선적으로 해결하는 것을 권장합니다.

---

## 참고 자료

- [FastAPI Best Practices](https://fastapi.tiangolo.com/tutorial/)
- [Python Database Connection Management](https://docs.python.org/3/library/sqlite3.html)
- [React Query Best Practices](https://tanstack.com/query/latest/docs/react/guides/important-defaults)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)

