# 성능 최적화 상세 계획

> **작성일**: 2025-11-18
> **목적**: ETF Weekly Report 애플리케이션의 성능 분석 결과 및 단계별 최적화 실행 계획

---

## 📊 성능 분석 결과 요약

### 현재 성능 지표

| 항목 | 현재 상태 | 목표 상태 | 우선순위 |
|------|----------|----------|---------|
| 초기 API 호출 수 | 22개 | ≤ 5개 | 🔴 Critical |
| 번들 크기 (gzip) | 167.12 kB | < 100 kB | 🔴 Critical |
| 캐시 Hit Rate | 32.88% | > 60% | 🟡 Medium |
| 메인 청크 크기 | 622.34 kB | < 300 kB | 🔴 Critical |
| DB 인덱스 | ✅ 완료 | ✅ 완료 | - |

### 데이터베이스 현황
- **Prices**: 862 레코드
- **Trading Flow**: 752 레코드
- **News**: 520 레코드
- **인덱스**: 적절히 설정됨 ✅

---

## 🎯 최적화 목표

### 단기 목표 (1-2주)
1. Dashboard 초기 로딩 시간 **50% 단축**
2. API 호출 수 **80% 감소** (22개 → 4개)
3. 번들 크기 **40% 감소** (167kB → 100kB)

### 중기 목표 (1개월)
1. 캐시 Hit Rate **60% 이상** 달성
2. 전체 페이지 로딩 시간 **3초 이내**
3. Lighthouse Performance 점수 **90점 이상**

---

## 📋 최적화 작업 상세 계획

### Phase 1: N+1 쿼리 문제 해결 (🔴 Critical)

#### 문제 상황
```
현재 Dashboard 로딩 시:
├── GET /api/etfs/ (1회)
└── 각 종목(7개)마다:
    ├── GET /api/etfs/{ticker}/prices?days=5
    ├── GET /api/etfs/{ticker}/trading-flow?days=1
    └── GET /api/news/{ticker}?limit=5

총 22개 API 호출 → 네트워크 병목 발생
```

#### 해결 방안: 배치 API 추가

##### 1.1 백엔드: 배치 API 엔드포인트 추가

**파일**: `backend/app/routers/etfs.py`

```python
from typing import Dict, Any

@router.post("/batch-summary", response_model=Dict[str, Any])
async def get_batch_summary(
    collector: ETFDataCollector = Depends(get_collector),
    tickers: List[str] = Body(..., description="조회할 종목 코드 리스트"),
    days: int = Body(5, description="가격 데이터 일수"),
    news_limit: int = Body(5, description="뉴스 개수")
):
    """
    여러 종목의 요약 데이터를 한 번에 조회

    Dashboard 초기 로딩 성능 최적화를 위한 배치 API

    **Request Body:**
    ```json
    {
      "tickers": ["487240", "466920", "0020H0", ...],
      "days": 5,
      "news_limit": 5
    }
    ```

    **Response:**
    ```json
    {
      "487240": {
        "prices": [...],
        "trading_flow": [...],
        "news": [...]
      },
      "466920": { ... },
      ...
    }
    ```
    """
    cache_key = make_cache_key(
        "batch_summary",
        tickers=",".join(sorted(tickers)),
        days=days,
        news_limit=news_limit
    )

    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result

    result = {}

    for ticker in tickers:
        try:
            # 가격 데이터
            prices = collector.get_prices(ticker, days=days)

            # 매매 동향
            trading_flow = collector.get_trading_flow(ticker, days=1)

            # 뉴스
            from app.services.news_scraper import NewsService
            news_service = NewsService()
            news = news_service.get_news_by_ticker(ticker, limit=news_limit)

            result[ticker] = {
                "prices": prices,
                "trading_flow": trading_flow,
                "news": news
            }
        except Exception as e:
            logger.error(f"Error fetching batch data for {ticker}: {e}")
            result[ticker] = {
                "prices": [],
                "trading_flow": [],
                "news": [],
                "error": str(e)
            }

    # 캐시 저장 (60초)
    cache.set(cache_key, result, ttl_seconds=60)

    return result
```

##### 1.2 프론트엔드: 배치 API 호출 로직

**파일**: `frontend/src/services/api.js`

```javascript
// 배치 API 추가
export const etfApi = {
  // ... 기존 메서드들

  /**
   * 여러 종목의 요약 데이터를 한 번에 조회
   */
  getBatchSummary: async (tickers, options = {}) => {
    const { days = 5, newsLimit = 5 } = options
    return await apiClient.post('/etfs/batch-summary', {
      tickers,
      days,
      news_limit: newsLimit
    }, {
      timeout: LONG_API_TIMEOUT // 60초
    })
  }
}
```

##### 1.3 프론트엔드: Dashboard 리팩토링

**파일**: `frontend/src/pages/Dashboard.jsx`

```javascript
export default function Dashboard() {
  // 배치 API로 모든 종목 데이터 한 번에 조회
  const { data: batchData, isLoading: batchLoading } = useQuery({
    queryKey: ['etfs-batch-summary'],
    queryFn: async () => {
      const etfsResponse = await etfApi.getAll()
      const tickers = etfsResponse.data.map(etf => etf.ticker)

      const batchResponse = await etfApi.getBatchSummary(tickers, {
        days: 5,
        newsLimit: 5
      })

      return {
        etfs: etfsResponse.data,
        summary: batchResponse.data
      }
    },
    retry: 2,
    staleTime: 60000, // 1분
  })

  // ... 나머지 로직
}
```

**파일**: `frontend/src/components/etf/ETFCard.jsx`

```javascript
// props로 데이터 전달받도록 수정
export default function ETFCard({ etf, summary }) {
  // API 호출 제거, props에서 데이터 사용
  const prices = summary?.prices || []
  const tradingFlow = summary?.trading_flow || []
  const news = summary?.news || []

  // ... 나머지 로직
}
```

#### 예상 효과
- API 호출: **22개 → 2개** (90% 감소)
- 초기 로딩 시간: **40-50% 단축**
- 서버 부하: 대폭 감소

---

### Phase 2: 프론트엔드 번들 크기 최적화 (🔴 Critical)

#### 2.1 Code Splitting 적용

**파일**: `frontend/vite.config.js`

```javascript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  build: {
    // 청크 크기 경고 제한 (기본 500kB)
    chunkSizeWarningLimit: 300,

    rollupOptions: {
      output: {
        // 수동 청크 분리
        manualChunks: {
          // React 관련 라이브러리
          'vendor-react': [
            'react',
            'react-dom',
            'react-router-dom'
          ],

          // TanStack Query
          'vendor-query': [
            '@tanstack/react-query'
          ],

          // 차트 라이브러리 (사용 중이라면)
          'vendor-charts': [
            'recharts'
          ],

          // 날짜 관련 유틸리티
          'vendor-date': [
            'date-fns'
          ]
        }
      }
    },

    // 소스맵 비활성화 (프로덕션)
    sourcemap: false,

    // 압축 옵션
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true, // console.log 제거
        drop_debugger: true
      }
    }
  }
})
```

#### 2.2 Route-based Code Splitting

**파일**: `frontend/src/App.jsx`

```javascript
import { lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/layout/Layout'
import LoadingIndicator from './components/common/LoadingIndicator'

// Lazy Loading으로 페이지 컴포넌트 로드
const Dashboard = lazy(() => import('./pages/Dashboard'))
const ETFDetail = lazy(() => import('./pages/ETFDetail'))
const Comparison = lazy(() => import('./pages/Comparison'))

function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Suspense fallback={<LoadingIndicator />}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/etf/:ticker" element={<ETFDetail />} />
            <Route path="/comparison" element={<Comparison />} />
          </Routes>
        </Suspense>
      </Layout>
    </BrowserRouter>
  )
}

export default App
```

#### 2.3 동적 Import 활용

```javascript
// 무거운 라이브러리는 필요할 때만 로드
// 예: PDF 생성 기능
const handleExportPDF = async () => {
  const jsPDF = await import('jspdf')
  // PDF 생성 로직
}
```

#### 예상 효과
- 메인 번들: **622kB → 150-200kB** (60-70% 감소)
- gzip 압축 후: **167kB → 80-100kB** (40-50% 감소)
- 초기 로딩 시간: **30-40% 단축**

---

### Phase 3: 캐시 전략 최적화 (🟡 Medium)

#### 3.1 차등 TTL 적용

**파일**: `backend/app/config.py`

```python
class Config:
    # ... 기존 설정

    # 캐시 TTL 설정 (초 단위)
    CACHE_TTL = {
        "etfs": 300,          # 5분 - 종목 목록은 거의 변하지 않음
        "prices": 60,         # 1분 - 가격 데이터
        "trading_flow": 60,   # 1분 - 매매 동향
        "news": 180,          # 3분 - 뉴스 데이터
        "batch_summary": 60,  # 1분 - 배치 요약
        "comparison": 120,    # 2분 - 비교 데이터
        "metrics": 300,       # 5분 - 통계 데이터
    }
```

**파일**: `backend/app/routers/etfs.py`

```python
from app.config import Config

@router.get("/")
async def get_etfs(...):
    cache_key = make_cache_key("etfs")
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result

    result = collector.get_all_etfs()

    # 차등 TTL 적용
    cache.set(cache_key, result, ttl_seconds=Config.CACHE_TTL["etfs"])
    return result
```

#### 3.2 캐시 무효화 전략

**파일**: `backend/app/services/scheduler.py`

```python
class DataCollectionScheduler:
    def __init__(self):
        # ... 기존 코드
        self.cache = get_cache()

    async def _collect_data(self):
        """데이터 수집 후 관련 캐시 무효화"""

        # 데이터 수집
        for ticker in self.tickers:
            await self.collector.collect_etf_data(ticker)

            # 해당 종목 관련 캐시 무효화
            self.cache.invalidate_pattern(ticker)

        # 전체 배치 캐시 무효화
        self.cache.invalidate_pattern("batch_summary")

        logger.info("데이터 수집 완료, 캐시 무효화됨")
```

#### 3.3 프론트엔드 캐시 전략

**파일**: `frontend/src/services/api.js`

```javascript
// TanStack Query 캐시 설정
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // 차등 staleTime 적용
      staleTime: 60000, // 기본 1분
      cacheTime: 300000, // 5분간 메모리 유지
      refetchOnWindowFocus: false, // 포커스 시 자동 갱신 비활성화
      retry: 2,
    },
  },
})

// 엔드포인트별 커스텀 설정
export const CACHE_CONFIG = {
  etfs: {
    staleTime: 300000, // 5분
    cacheTime: 600000, // 10분
  },
  prices: {
    staleTime: 60000,  // 1분
    cacheTime: 180000, // 3분
  },
  news: {
    staleTime: 180000, // 3분
    cacheTime: 300000, // 5분
  },
}
```

#### 예상 효과
- 캐시 Hit Rate: **32.88% → 65-70%**
- API 응답 시간: **20-30% 단축**
- 서버 부하: **30-40% 감소**

---

### Phase 4: 데이터베이스 쿼리 최적화 (🟡 Medium)

#### 4.1 배치 쿼리 최적화

**파일**: `backend/app/services/data_collector.py`

```python
class ETFDataCollector:
    def get_batch_prices(self, tickers: List[str], days: int = 5) -> Dict[str, List[PriceData]]:
        """
        여러 종목의 가격 데이터를 한 번의 쿼리로 조회
        """
        conn = get_db_connection()
        cursor = conn.cursor()

        # IN 절을 사용한 배치 쿼리
        placeholders = ','.join('?' * len(tickers))

        query = f"""
            SELECT ticker, date, open_price, high_price, low_price,
                   close_price, volume, change_pct
            FROM prices
            WHERE ticker IN ({placeholders})
              AND date >= date('now', '-{days} days')
            ORDER BY ticker, date DESC
        """

        cursor.execute(query, tickers)
        rows = cursor.fetchall()

        # ticker별로 그룹화
        result = {}
        for row in rows:
            ticker = row[0]
            if ticker not in result:
                result[ticker] = []

            result[ticker].append(PriceData(
                ticker=row[0],
                date=row[1],
                open_price=row[2],
                # ... 나머지 필드
            ))

        conn.close()
        return result
```

#### 4.2 쿼리 결과 크기 제한

```python
@router.get("/{ticker}/prices")
async def get_prices(
    ticker: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    days: Optional[int] = None,
    limit: int = Query(1000, le=5000, description="최대 조회 개수")
):
    """
    limit 파라미터로 결과 크기 제한
    """
    # ... 쿼리 로직에 LIMIT 추가
```

#### 4.3 Connection Pool 설정

**파일**: `backend/app/database.py`

```python
import sqlite3
from contextlib import contextmanager
import threading

class DatabasePool:
    """SQLite Connection Pool"""

    def __init__(self, database_path: str, pool_size: int = 5):
        self.database_path = database_path
        self.pool_size = pool_size
        self._pool = []
        self._lock = threading.Lock()

        # 초기 커넥션 생성
        for _ in range(pool_size):
            conn = sqlite3.connect(database_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            self._pool.append(conn)

    @contextmanager
    def get_connection(self):
        """커넥션 풀에서 커넥션 가져오기"""
        with self._lock:
            if not self._pool:
                # 풀이 비었으면 새로 생성
                conn = sqlite3.connect(self.database_path)
                conn.row_factory = sqlite3.Row
            else:
                conn = self._pool.pop()

        try:
            yield conn
        finally:
            with self._lock:
                if len(self._pool) < self.pool_size:
                    self._pool.append(conn)
                else:
                    conn.close()

# 전역 풀 인스턴스
_db_pool = None

def get_db_pool() -> DatabasePool:
    global _db_pool
    if _db_pool is None:
        _db_pool = DatabasePool(Config.DATABASE_PATH, pool_size=5)
    return _db_pool
```

---

### Phase 5: 성능 모니터링 (🟢 Low)

#### 5.1 백엔드 성능 로깅

**파일**: `backend/app/middleware/performance.py`

```python
import time
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

class PerformanceMiddleware(BaseHTTPMiddleware):
    """API 응답 시간 측정 미들웨어"""

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        response = await call_next(request)

        process_time = time.time() - start_time

        # 느린 API 로깅 (500ms 이상)
        if process_time > 0.5:
            logger.warning(
                f"Slow API: {request.method} {request.url.path} "
                f"took {process_time:.2f}s"
            )

        # 응답 헤더에 처리 시간 추가
        response.headers["X-Process-Time"] = str(process_time)

        return response
```

**파일**: `backend/app/main.py`

```python
from app.middleware.performance import PerformanceMiddleware

app = FastAPI()
app.add_middleware(PerformanceMiddleware)
```

#### 5.2 프론트엔드 성능 측정

**파일**: `frontend/src/utils/performance.js`

```javascript
/**
 * Web Vitals 측정
 */
export const measureWebVitals = () => {
  if ('PerformanceObserver' in window) {
    // Largest Contentful Paint
    const lcpObserver = new PerformanceObserver((list) => {
      const entries = list.getEntries()
      const lastEntry = entries[entries.length - 1]
      console.log('LCP:', lastEntry.renderTime || lastEntry.loadTime)
    })
    lcpObserver.observe({ entryTypes: ['largest-contentful-paint'] })

    // First Input Delay
    const fidObserver = new PerformanceObserver((list) => {
      const entries = list.getEntries()
      entries.forEach((entry) => {
        console.log('FID:', entry.processingStart - entry.startTime)
      })
    })
    fidObserver.observe({ entryTypes: ['first-input'] })
  }
}

/**
 * API 호출 시간 측정
 */
export const measureApiCall = async (name, apiCall) => {
  const start = performance.now()
  try {
    const result = await apiCall()
    const duration = performance.now() - start
    console.log(`API ${name}: ${duration.toFixed(2)}ms`)
    return result
  } catch (error) {
    const duration = performance.now() - start
    console.error(`API ${name} failed after ${duration.toFixed(2)}ms`)
    throw error
  }
}
```

#### 5.3 성능 대시보드

**파일**: `backend/app/routers/monitoring.py`

```python
from fastapi import APIRouter
from typing import Dict, Any
from app.utils.cache import get_cache

router = APIRouter(prefix="/monitoring", tags=["monitoring"])

@router.get("/performance")
async def get_performance_metrics() -> Dict[str, Any]:
    """
    성능 메트릭 조회
    """
    cache = get_cache()
    cache_stats = cache.get_stats()

    return {
        "cache": cache_stats,
        "database": {
            "total_queries": "TODO",
            "slow_queries": "TODO",
        },
        "api": {
            "avg_response_time": "TODO",
            "p95_response_time": "TODO",
        }
    }
```

---

## 📅 실행 일정

### Week 1-2: Critical Issues
- [ ] **Day 1-3**: Phase 1 - 배치 API 구현 및 테스트
  - 백엔드 API 개발
  - 프론트엔드 통합
  - 단위 테스트 작성

- [ ] **Day 4-5**: Phase 2 - Code Splitting 적용
  - Vite 설정 변경
  - Route-based splitting
  - 빌드 크기 검증

- [ ] **Day 6-7**: 통합 테스트 및 성능 측정
  - E2E 테스트
  - Lighthouse 점수 측정
  - 배포 전 최종 검증

### Week 3-4: Medium Priority
- [ ] **Week 3**: Phase 3 - 캐시 최적화
  - 차등 TTL 적용
  - 캐시 무효화 로직
  - Hit Rate 모니터링

- [ ] **Week 4**: Phase 4 - DB 쿼리 최적화
  - 배치 쿼리 구현
  - Connection Pool
  - 성능 테스트

### Week 5+: Low Priority
- [ ] Phase 5 - 모니터링 시스템
- [ ] 추가 최적화 및 Fine-tuning

---

## ✅ 검증 기준

### 성능 목표 달성 여부

| 메트릭 | 현재 | 목표 | 측정 방법 |
|--------|------|------|----------|
| 초기 로딩 시간 | ~3s | < 1.5s | Chrome DevTools Network |
| API 호출 수 | 22개 | ≤ 5개 | Network 탭 카운트 |
| 번들 크기 (gzip) | 167kB | < 100kB | `npm run build` 출력 |
| 캐시 Hit Rate | 33% | > 60% | `/api/data/cache/stats` |
| Lighthouse Score | - | > 90 | Chrome Lighthouse |
| First Contentful Paint | - | < 1s | Web Vitals |
| Time to Interactive | - | < 2s | Web Vitals |

### 테스트 체크리스트

#### 기능 테스트
- [ ] Dashboard 정상 로딩
- [ ] 모든 ETF 카드 데이터 표시
- [ ] Detail 페이지 정상 작동
- [ ] Comparison 페이지 정상 작동
- [ ] 캐시 적중 시 빠른 응답
- [ ] 에러 처리 정상 작동

#### 성능 테스트
- [ ] 초기 로딩 1.5초 이내
- [ ] API 호출 5개 이하
- [ ] 번들 크기 100kB 이하
- [ ] 캐시 Hit Rate 60% 이상
- [ ] 모바일 환경 테스트

#### 부하 테스트
- [ ] 동시 사용자 50명 처리
- [ ] API 응답 시간 < 200ms
- [ ] 메모리 누수 없음

---

## 🚨 위험 요소 및 대응

### 잠재적 문제

1. **배치 API 응답 시간 증가**
   - 위험: 7개 종목 데이터를 한 번에 조회하면 응답 시간이 길어질 수 있음
   - 대응:
     - 병렬 처리 (`asyncio.gather`)
     - 타임아웃 설정 (60초)
     - 부분 실패 허용 (일부 종목만 성공해도 응답)

2. **캐시 메모리 사용량 증가**
   - 위험: 배치 데이터가 크면 메모리 부담
   - 대응:
     - 캐시 최대 크기 제한 (1000개 → 500개로 조정)
     - LRU eviction 정책 활용

3. **Code Splitting으로 인한 추가 HTTP 요청**
   - 위험: 청크 파일이 많아지면 HTTP 요청 증가
   - 대응:
     - HTTP/2 사용 (병렬 다운로드)
     - 적절한 청크 크기 유지 (너무 잘게 나누지 않기)

4. **프론트엔드 캐시와 백엔드 캐시 불일치**
   - 위험: 데이터 갱신 시 동기화 문제
   - 대응:
     - 캐시 무효화 로직 추가
     - 버전 기반 캐시 키 사용

---

## 📈 예상 효과

### 정량적 효과

```
초기 로딩 시간
Before: ~3.0s
After:  ~1.2s (60% 개선)

네트워크 요청
Before: 22개 API 호출
After:  2-4개 API 호출 (80% 감소)

번들 크기
Before: 622kB (167kB gzip)
After:  ~200kB (~90kB gzip) (70% 감소)

캐시 효율
Before: 33% Hit Rate
After:  65-70% Hit Rate (2배 향상)

서버 부하
Before: 100% (기준)
After:  ~40% (60% 감소)
```

### 정성적 효과

- ✅ **사용자 경험 대폭 개선**: 페이지 로딩이 즉각적으로 느껴짐
- ✅ **모바일 환경 최적화**: 번들 크기 감소로 모바일에서도 빠른 로딩
- ✅ **서버 비용 절감**: API 호출 감소로 인프라 비용 감소
- ✅ **확장성 향상**: 사용자 증가에도 안정적 서비스 가능
- ✅ **SEO 개선**: Lighthouse 점수 향상으로 검색 순위 상승 가능

---

## 📚 참고 자료

### 성능 최적화 가이드
- [Web.dev - Performance](https://web.dev/performance/)
- [React Performance Optimization](https://react.dev/learn/render-and-commit)
- [Vite - Build Optimizations](https://vitejs.dev/guide/build.html)
- [TanStack Query - Performance](https://tanstack.com/query/latest/docs/react/guides/performance)

### 도구
- [Lighthouse](https://developers.google.com/web/tools/lighthouse)
- [Chrome DevTools](https://developer.chrome.com/docs/devtools/)
- [Bundle Analyzer](https://www.npmjs.com/package/rollup-plugin-visualizer)
- [Web Vitals](https://web.dev/vitals/)

---

## 🎯 다음 단계

1. ✅ 이 문서를 팀과 공유 및 검토
2. [ ] Phase 1 백엔드 API 개발 시작
3. [ ] 성능 베이스라인 측정 (Before 데이터 수집)
4. [ ] 각 Phase별 브랜치 생성 및 작업 시작
5. [ ] 주간 성능 리포트 작성 및 공유

---

**작성자**: Claude Code
**최종 수정**: 2025-11-18
