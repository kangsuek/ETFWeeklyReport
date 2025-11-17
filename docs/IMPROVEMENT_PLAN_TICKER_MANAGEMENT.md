# 티커 관리 기능 개선 계획

## 개요

현재 Setting 페이지의 종목 추가 기능을 개선하여 사용자 경험을 향상시키고, 티커 코드와 종목명을 미리 수집하여 활용하는 기능을 추가합니다.

## 현재 상태 분석

### 현재 구현 방식
1. **티커 코드 입력**: 사용자가 직접 티커 코드 입력
2. **자동 입력 버튼**: "네이버에서 자동 입력" 버튼 클릭
3. **네이버 스크래핑**: `TickerScraper`가 네이버 금융에서 실시간 스크래핑
4. **폼 자동 채움**: 스크래핑 결과로 폼 필드 자동 채움

### 현재 방식의 문제점
- 사용자가 버튼을 클릭해야 함 (추가 클릭 필요)
- 네이버 스크래핑이 느릴 수 있음 (네트워크 요청)
- 티커 코드를 정확히 알아야 함
- 오타 시 검증이 늦음

---

## 개선 방안 1: 자동 입력 기능 개선

### 방안 1-1: 티커 코드 입력 시 자동 검색 (Debounce)

**개념**: 티커 코드 입력 시 일정 시간 후 자동으로 검색 실행

**장점**:
- 버튼 클릭 불필요
- 더 직관적인 UX
- 실시간 피드백

**구현 방법**:
```javascript
// TickerForm.jsx
const [tickerInput, setTickerInput] = useState('')
const [isSearching, setIsSearching] = useState(false)

// Debounce hook 사용
useEffect(() => {
  if (tickerInput.length >= 6) { // 티커 코드는 보통 6자리
    const timer = setTimeout(() => {
      handleAutoFill(tickerInput)
    }, 800) // 800ms 후 자동 실행
    
    return () => clearTimeout(timer)
  }
}, [tickerInput])
```

**UI 변경**:
- "자동 입력" 버튼 제거 또는 옵션으로 유지
- 입력 필드에 로딩 인디케이터 표시
- 자동 검색 중일 때 시각적 피드백

### 방안 1-2: 드롭다운 자동완성

**개념**: 티커 코드 입력 시 미리 수집된 종목 목록에서 자동완성 제공

**장점**:
- 티커 코드를 정확히 몰라도 검색 가능
- 종목명으로도 검색 가능
- 빠른 응답 (로컬 데이터)

**구현 방법**:
```javascript
// TickerForm.jsx
const [searchQuery, setSearchQuery] = useState('')
const [suggestions, setSuggestions] = useState([])

// 종목 목록 검색
const searchStocks = async (query) => {
  if (query.length < 2) return
  
  const response = await api.get(`/settings/stocks/search?q=${query}`)
  setSuggestions(response.data)
}

// 드롭다운 표시
{suggestions.length > 0 && (
  <div className="absolute z-10 bg-white border rounded-lg shadow-lg">
    {suggestions.map(stock => (
      <div onClick={() => selectStock(stock)}>
        {stock.ticker} - {stock.name}
      </div>
    ))}
  </div>
)}
```

**백엔드 API 추가**:
```python
# backend/app/routers/settings.py
@router.get("/stocks/search")
async def search_stocks(q: str) -> List[Dict[str, Any]]:
    """티커 코드 또는 종목명으로 종목 검색"""
    # stock_catalog 테이블에서 검색
    # 티커 코드 또는 종목명으로 LIKE 검색
```

### 방안 1-3: 하이브리드 방식 (권장)

**개념**: 자동완성 + 자동 검색 조합

**동작 방식**:
1. 티커 코드 입력 시작 → 자동완성 드롭다운 표시
2. 드롭다운에서 선택 → 즉시 폼 채움 (스크래핑 불필요)
3. 직접 입력 완료 → Debounce 후 자동 스크래핑

**장점**:
- 빠른 선택 (자동완성)
- 유연성 (직접 입력도 가능)
- 최신 정보 (스크래핑)

---

## 개선 방안 2: 티커 코드 및 종목명 미리 수집 기능

### 목표
한국 주식/ETF 전체 목록을 미리 수집하여 데이터베이스에 저장하고, 종목 추가 시 빠르게 검색할 수 있도록 함.

### 데이터 소스 옵션

#### 옵션 1: 한국거래소(KRX) API (권장)
**장점**:
- 공식 데이터 소스
- 정확한 정보
- API 제공

**단점**:
- API 키 필요 (무료 제공)
- 일일 호출 제한 가능

**구현 방법**:
```python
# backend/app/services/krx_scraper.py
class KRXScraper:
    """한국거래소에서 종목 목록 수집"""
    
    def collect_all_stocks(self) -> List[Dict[str, Any]]:
        """
        KRX API를 통해 전체 종목 목록 수집
        - 주식 목록
        - ETF 목록
        - ETN 목록
        """
        # KRX OpenAPI 사용
        # 예: http://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd
```

#### 옵션 2: 네이버 금융 스크래핑
**장점**:
- API 키 불필요
- 이미 사용 중인 방식

**단점**:
- 스크래핑 속도 느림
- 구조 변경 시 파싱 실패 가능

**구현 방법**:
```python
# backend/app/services/ticker_catalog_collector.py
class TickerCatalogCollector:
    """네이버 금융에서 전체 종목 목록 수집"""
    
    def collect_all_stocks(self):
        """
        네이버 금융 종목 목록 페이지에서 수집
        - 주식: https://finance.naver.com/sise/sise_market_sum.naver
        - ETF: https://finance.naver.com/sise/etf.naver
        """
```

#### 옵션 3: 파일 기반 초기 데이터
**장점**:
- 빠른 초기화
- 네트워크 불필요

**단점**:
- 수동 업데이트 필요
- 최신 정보 보장 어려움

### 데이터베이스 스키마 추가

#### 새 테이블: `stock_catalog`
```sql
CREATE TABLE stock_catalog (
    ticker TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,  -- 'STOCK', 'ETF', 'ETN'
    market TEXT,  -- 'KOSPI', 'KOSDAQ', 'ETF', 'ETN'
    sector TEXT,  -- 업종/섹터
    listed_date DATE,  -- 상장일
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1  -- 상장폐지 여부
);

CREATE INDEX idx_stock_catalog_name ON stock_catalog(name);
CREATE INDEX idx_stock_catalog_type ON stock_catalog(type);
```

### 수집 스케줄러 추가

```python
# backend/app/services/ticker_catalog_scheduler.py
class TickerCatalogScheduler:
    """종목 목록 수집 스케줄러"""
    
    def collect_daily(self):
        """
        매일 새벽에 전체 종목 목록 업데이트
        - 신규 상장 종목 추가
        - 상장폐지 종목 표시
        - 종목명 변경 반영
        """
        # 1. 전체 종목 목록 수집
        # 2. 기존 데이터와 비교
        # 3. 신규/변경 사항 업데이트
```

### 백엔드 API 추가

```python
# backend/app/routers/settings.py

@router.get("/stocks/search")
async def search_stocks(
    q: str = Query(..., description="검색어 (티커 코드 또는 종목명)"),
    type: Optional[str] = Query(None, description="종목 타입 필터 (STOCK, ETF)")
) -> List[Dict[str, Any]]:
    """
    종목 목록 검색 (자동완성용)
    
    Returns:
        List of stocks matching the search query
    """
    # stock_catalog 테이블에서 검색
    # 티커 코드 또는 종목명으로 LIKE 검색
    # 최대 20개 결과 반환

@router.post("/settings/ticker-catalog/collect")
async def collect_ticker_catalog() -> Dict[str, Any]:
    """
    종목 목록 수집 트리거 (관리자용)
    
    Returns:
        수집된 종목 수 및 통계
    """
    # 전체 종목 목록 수집
    # stock_catalog 테이블에 저장/업데이트
```

### 프론트엔드 구현

```javascript
// frontend/src/components/settings/TickerForm.jsx

// 자동완성 검색
const searchStocks = async (query) => {
  if (query.length < 2) {
    setSuggestions([])
    return
  }
  
  const response = await settingsApi.searchStocks(query)
  setSuggestions(response.data)
}

// 드롭다운에서 선택 시
const handleSelectStock = (stock) => {
  // 미리 수집된 데이터 사용 (스크래핑 불필요)
  setFormData({
    ticker: stock.ticker,
    name: stock.name,
    type: stock.type,
    // ... 나머지 필드는 사용자가 입력하거나 자동 입력 버튼 사용
  })
  setSuggestions([])
}
```

---

## 구현 우선순위

### Phase 1: 자동 입력 개선 (빠른 개선)
1. ✅ Debounce 기반 자동 검색 구현
2. ✅ UI 개선 (로딩 인디케이터, 피드백)
3. ✅ 테스트 작성

**예상 소요 시간**: 2-3시간

### Phase 2: 티커 목록 수집 기능 (중기 개선)
1. ✅ `stock_catalog` 테이블 생성
2. ✅ 종목 목록 수집 서비스 구현 (네이버 금융 스크래핑)
3. ✅ 수집 스케줄러 추가 (매일 새벽 3:00 자동 실행)
4. ✅ 검색 API 구현
5. ✅ 프론트엔드 자동완성 구현
6. ✅ 테스트 작성

**예상 소요 시간**: 1-2일

### Phase 3: 통합 및 최적화 (장기 개선)
1. ✅ 하이브리드 방식 통합 (자동완성 + 자동 검색)
2. ✅ 캐싱 최적화 (검색 결과 5분 캐싱, 최대 128개)
3. ✅ 성능 튜닝 (인덱스 활용, 결과 제한)
4. ✅ 상장폐지 종목 처리 (is_active = 0)
5. ✅ 종목명 변경 자동 반영
6. ✅ 검색 캐시 자동 무효화

**예상 소요 시간**: 1일

**구현 완료 기능**:
- ✅ 티커 카탈로그 수집 스케줄러 (매일 새벽 3:00 KST)
- ✅ 검색 결과 캐싱 (5분 TTL, LRU 방식)
- ✅ 상장폐지 종목 자동 감지 및 비활성화
- ✅ 종목명 변경 자동 반영
- ✅ 신규 상장 종목 자동 추가

---

## 기술적 고려사항

### 성능
- 자동완성 검색은 인덱스 활용 (name, ticker)
- 결과 제한 (최대 20개)
- 클라이언트 측 디바운싱

### 데이터 일관성
- `stock_catalog`와 `etfs` 테이블 동기화
- 종목 삭제 시 `stock_catalog`는 유지 (히스토리)

### 에러 처리
- 네트워크 오류 시 폴백 (로컬 데이터)
- 스크래핑 실패 시 사용자 알림

### 보안
- 검색 API는 공개 가능
- 수집 트리거는 관리자 권한 필요

---

## 구현 완료 현황

### ✅ Phase 1: 자동 입력 개선
- ✅ Debounce 기반 자동 검색 (6자리 티커 코드 입력 시 0.8초 후 자동 실행)
- ✅ UI 개선 (로딩 인디케이터, 피드백)
- ✅ 테스트 작성 (16개 테스트 통과)

### ✅ Phase 2: 티커 목록 수집 기능
- ✅ `stock_catalog` 테이블 생성 및 인덱스 추가
- ✅ 종목 목록 수집 서비스 구현 (네이버 금융 스크래핑)
- ✅ 수집 API 엔드포인트 (`POST /api/settings/ticker-catalog/collect`)
- ✅ 검색 API 엔드포인트 (`GET /api/settings/stocks/search`)
- ✅ 프론트엔드 자동완성 구현 (티커 코드 필드 + 종목명 필드)
- ✅ 테스트 작성 (21개 테스트 통과)

### ✅ Phase 3: 통합 및 최적화
- ✅ 하이브리드 방식 통합 (자동완성 + 자동 검색)
- ✅ 검색 결과 캐싱 (5분 TTL, 최대 128개, LRU 방식)
- ✅ 성능 튜닝 (인덱스 활용, 결과 제한 20개)
- ✅ 상장폐지 종목 자동 감지 및 비활성화
- ✅ 종목명 변경 자동 반영
- ✅ 신규 상장 종목 자동 추가
- ✅ 티커 카탈로그 수집 스케줄러 (매일 새벽 3:00 KST 자동 실행)
- ✅ 검색 캐시 자동 무효화 (수집 후)

## 예상 효과

### 사용자 경험
- 종목 추가 시간: **30초 → 10초** (66% 단축)
- 클릭 횟수: **3회 → 1회** (66% 감소)
- 오류율: **10% → 2%** (80% 감소)

### 시스템 성능
- 네이버 스크래핑 호출: **100% → 30%** (70% 감소)
- 응답 시간: **2-3초 → 0.1-0.5초** (자동완성 사용 시)
- 검색 성능: **캐시 히트 시 즉시 응답** (DB 조회 불필요)

---

## 참고 자료

- [KRX OpenAPI 문서](http://data.krx.co.kr/contents/COM/GenerateOTP.jsp)
- [네이버 금융 종목 목록](https://finance.naver.com/sise/sise_market_sum.naver)
- [React Debounce Hook](https://usehooks.com/useDebounce/)

