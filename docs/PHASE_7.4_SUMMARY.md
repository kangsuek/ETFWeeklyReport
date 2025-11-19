# Phase 7.4: 데이터베이스 쿼리 최적화 완료 보고서

## 개요
Phase 7.4에서는 데이터베이스 쿼리 성능을 개선하기 위한 여러 최적화 작업을 수행했습니다.

## 완료된 작업

### 1. 배치 쿼리 구현 (IN 절 활용)

여러 종목의 데이터를 한 번의 쿼리로 조회하는 배치 메서드를 구현했습니다.

#### 새로운 메서드

**`get_price_data_batch(tickers, start_date, end_date, limit=None)`**
- 여러 종목의 가격 데이터를 단일 SQL 쿼리로 조회
- IN 절을 사용하여 N개 종목을 한 번에 조회
- 종목별로 결과를 그룹화하여 반환

**`get_trading_flow_batch(tickers, start_date, end_date, limit=None)`**
- 여러 종목의 매매동향 데이터를 단일 SQL 쿼리로 조회
- IN 절을 사용하여 효율적 조회
- 종목별로 결과를 그룹화하여 반환

**`get_latest_prices_batch(tickers)`**
- 여러 종목의 최신 가격을 서브쿼리로 효율적 조회
- MAX(date) 서브쿼리를 통해 최신 데이터만 조회
- 불필요한 데이터 스캔 최소화

#### 성능 개선 효과

**Before (Phase 7.4 이전):**
```python
# N개 종목에 대해 N번의 쿼리 실행
for ticker in tickers:
    prices = collector.get_price_data(ticker, start_date, end_date)
    # 총 N개의 SELECT 쿼리 실행
```

**After (Phase 7.4 적용 후):**
```python
# N개 종목에 대해 1번의 쿼리 실행
prices_batch = collector.get_price_data_batch(tickers, start_date, end_date)
# 단 1개의 SELECT 쿼리로 모든 종목 조회
```

- **쿼리 횟수 감소**: 6개 종목 기준 6개 쿼리 → 1개 쿼리 (83% 감소)
- **네트워크 오버헤드 감소**: DB 왕복 횟수 최소화
- **인덱스 활용 효율 향상**: 단일 쿼리에서 인덱스 스캔 최적화

### 2. 쿼리 결과 크기 제한 (LIMIT 파라미터)

모든 주요 조회 메서드에 `limit` 파라미터를 추가하여 불필요한 데이터 조회를 방지했습니다.

#### 업데이트된 메서드

- `get_price_data(ticker, start_date, end_date, limit=None)`
- `get_trading_flow(ticker, start_date, end_date, limit=None)`
- `get_trading_flow_data(ticker, start_date, end_date, limit=None)`

#### 예시

```python
# 최근 5일치만 조회
prices = collector.get_price_data(ticker, start_date, end_date, limit=5)

# 최근 3건의 매매동향만 조회
flows = collector.get_trading_flow(ticker, start_date, end_date, limit=3)
```

#### 효과
- 메모리 사용량 감소
- 데이터 전송량 감소
- 응답 시간 단축

### 3. Connection Pool 구현

SQLite 연결 관리를 위한 Connection Pool을 구현했습니다.

#### 구현 내용

**`ConnectionPool` 클래스**
- 최대 연결 수 제한 (기본값: 10, 환경변수 `DB_POOL_SIZE`로 설정 가능)
- 연결 재사용으로 생성/해제 오버헤드 감소
- Thread-safe 구현 (Lock 사용)
- 큐 기반 연결 관리

**`get_db_connection()` 개선**
```python
@contextmanager
def get_db_connection():
    """
    Connection pool을 사용하는 context manager
    """
    pool = get_connection_pool()
    conn = pool.get_connection()
    try:
        yield conn
    finally:
        pool.return_connection(conn)
```

#### 효과
- 동시 요청 처리 성능 향상
- 연결 생성/해제 오버헤드 감소
- PostgreSQL 마이그레이션 준비 (구조적 호환성 확보)

**Note**: SQLite는 파일 기반 DB로 connection pool의 이점이 제한적이지만, 향후 PostgreSQL 전환 시 큰 성능 향상 기대

### 4. 배치 엔드포인트 최적화

`POST /api/etfs/batch-summary` 엔드포인트를 배치 쿼리를 사용하도록 리팩토링했습니다.

#### Before
```python
for ticker in request.tickers:
    prices = collector.get_price_data(ticker, start_date, end_date)
    trading_flow = collector.get_trading_flow_data(ticker, start_date, end_date)
    # 6개 종목 × 2개 쿼리 = 12개 쿼리
```

#### After
```python
# 배치 쿼리로 한 번에 조회
prices_batch = collector.get_price_data_batch(request.tickers, start_date, end_date)
trading_flow_batch = collector.get_trading_flow_batch(request.tickers, start_date, end_date)
# 2개 쿼리로 모든 종목 처리
```

#### 성능 개선
- **쿼리 횟수**: 12개 → 2개 (83% 감소)
- **Dashboard 로딩 시간 단축** (Phase 7.1과 시너지)

## 테스트 결과

### 새로운 테스트 파일
`backend/tests/test_batch_queries.py` (12개 테스트)

#### 테스트 커버리지

**배치 쿼리 테스트 (7개)**
- ✅ `test_get_price_data_batch_basic`: 기본 기능
- ✅ `test_get_price_data_batch_with_limit`: Limit 파라미터
- ✅ `test_get_price_data_batch_empty_tickers`: 빈 입력 처리
- ✅ `test_get_trading_flow_batch_basic`: 매매동향 배치
- ✅ `test_get_trading_flow_batch_with_limit`: Limit 파라미터
- ✅ `test_get_latest_prices_batch_basic`: 최신 가격 배치
- ✅ `test_batch_vs_single_query_consistency`: 결과 일관성

**Limit 파라미터 테스트 (2개)**
- ✅ `test_get_price_data_with_limit`
- ✅ `test_get_trading_flow_with_limit`

**Connection Pool 테스트 (3개)**
- ✅ `test_connection_pool_basic`
- ✅ `test_connection_pool_multiple_connections`
- ✅ `test_get_db_connection_context_manager`

### 테스트 실행 결과
```bash
======================== 12 passed, 1 warning in 1.39s =========================
```

모든 테스트 통과 ✅

## 기술적 세부사항

### SQL 쿼리 예시

#### 배치 가격 조회
```sql
SELECT ticker, date, open_price, high_price, low_price, close_price, volume, daily_change_pct
FROM prices
WHERE ticker IN (?, ?, ?, ?, ?, ?)  -- 6개 종목
  AND date BETWEEN ? AND ?
ORDER BY ticker, date DESC
```

#### 최신 가격 배치 조회 (서브쿼리 활용)
```sql
SELECT p.ticker, p.date, p.open_price, p.high_price, p.low_price,
       p.close_price, p.volume, p.daily_change_pct
FROM prices p
INNER JOIN (
    SELECT ticker, MAX(date) as max_date
    FROM prices
    WHERE ticker IN (?, ?, ?, ?, ?, ?)
    GROUP BY ticker
) latest ON p.ticker = latest.ticker AND p.date = latest.max_date
```

### 파일 변경 사항

1. **`backend/app/services/data_collector.py`**
   - `get_price_data_batch()` 추가 (59줄)
   - `get_trading_flow_batch()` 추가 (58줄)
   - `get_latest_prices_batch()` 추가 (48줄)
   - `get_price_data()`, `get_trading_flow()`, `get_trading_flow_data()`에 limit 파라미터 추가

2. **`backend/app/database.py`**
   - `ConnectionPool` 클래스 추가 (62줄)
   - `get_connection_pool()` 함수 추가
   - `get_db_connection()` 리팩토링 (Connection Pool 적용)

3. **`backend/app/routers/etfs.py`**
   - `get_batch_summary()` 엔드포인트 리팩토링 (배치 쿼리 사용)

4. **`backend/tests/test_batch_queries.py`**
   - 새로운 테스트 파일 생성 (12개 테스트)

## 향후 개선 사항

### PostgreSQL 마이그레이션 시
1. **Connection Pool 최적화**
   - `psycopg2.pool.ThreadedConnectionPool` 사용
   - 연결 재사용으로 대폭적인 성능 향상 기대

2. **배치 쿼리 확장**
   - 뉴스 데이터도 배치 쿼리 적용 검토
   - JOIN을 활용한 더 복잡한 배치 쿼리 구현

3. **쿼리 튜닝**
   - EXPLAIN ANALYZE로 쿼리 플랜 분석
   - 복합 인덱스 최적화
   - Prepared Statements 활용

### 성능 모니터링 (Phase 7.5)
- 쿼리 실행 시간 로깅
- 슬로우 쿼리 감지 및 알림
- Connection Pool 사용률 모니터링

## 결론

Phase 7.4를 통해 데이터베이스 쿼리 성능을 크게 개선했습니다:

✅ **배치 쿼리**: N개 쿼리 → 1개 쿼리 (83% 감소)
✅ **Limit 파라미터**: 불필요한 데이터 조회 방지
✅ **Connection Pool**: 연결 재사용으로 오버헤드 감소
✅ **테스트 검증**: 12개 테스트 모두 통과

이러한 최적화는 Phase 7.1 (N+1 쿼리 해결), 7.2 (번들 크기), 7.3 (캐시 전략)과 결합되어
전체적인 애플리케이션 성능 향상에 기여합니다.

---

**작성일**: 2025-11-19
**Phase**: 7.4 - 데이터베이스 쿼리 최적화
**상태**: ✅ 완료
