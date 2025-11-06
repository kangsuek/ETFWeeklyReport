# 개발 가이드

## 코드 품질 표준

### Python (백엔드)

#### 스타일 가이드

- **PEP 8** 준수
- 들여쓰기: 4 spaces
- 최대 줄 길이: 100자
- 타입 힌트 사용

#### 코드 예시

```python
from typing import Optional, List
from datetime import date
import logging

logger = logging.getLogger(__name__)

async def get_etf_prices(
    ticker: str,
    start_date: date,
    end_date: date
) -> Optional[List[dict]]:
    """
    특정 기간의 ETF 가격 데이터를 조회합니다.
    
    Args:
        ticker: ETF 티커 코드 (예: "480450")
        start_date: 조회 시작 날짜
        end_date: 조회 종료 날짜
        
    Returns:
        가격 데이터 리스트 또는 실패 시 None
        
    Raises:
        ValueError: 잘못된 날짜 범위
    """
    try:
        if start_date > end_date:
            raise ValueError("시작 날짜가 종료 날짜보다 늦을 수 없습니다")
        
        # 데이터 조회 로직
        data = await fetch_data(ticker, start_date, end_date)
        return data
        
    except Exception as e:
        logger.error(f"가격 데이터 조회 실패 ({ticker}): {e}")
        return None
```

#### 함수 작성 규칙

1. **단일 책임 원칙**: 한 함수는 하나의 작업만 수행
2. **Docstring 필수**: 모든 public 함수에 작성
3. **타입 힌트**: 파라미터 및 반환값에 타입 명시
4. **에러 처리**: try-except로 예외 처리, 로깅 포함
5. **비동기 I/O**: 네트워크/파일 작업은 async/await 사용

---

### JavaScript/React (프론트엔드)

#### 스타일 가이드

- **ESLint** 규칙 준수
- 들여쓰기: 2 spaces
- 함수형 컴포넌트 + Hooks 사용
- PropTypes 또는 TypeScript 사용 권장

#### 컴포넌트 예시

```javascript
import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { etfApi } from '@/services/api'
import Spinner from '@/components/common/Spinner'

/**
 * ETF 카드 컴포넌트
 * @param {Object} props
 * @param {string} props.ticker - ETF 티커 코드
 * @param {string} props.name - ETF 이름
 */
export default function ETFCard({ ticker, name }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['etf', ticker],
    queryFn: () => etfApi.getDetail(ticker),
    staleTime: 5 * 60 * 1000, // 5분
  })

  if (isLoading) return <Spinner />
  
  if (error) {
    return (
      <div className="text-red-600">
        데이터를 불러올 수 없습니다: {error.message}
      </div>
    )
  }

  return (
    <div className="card hover:shadow-lg transition-shadow">
      <h3 className="text-lg font-bold">{name}</h3>
      <p className="text-sm text-gray-600">{ticker}</p>
      {/* 추가 내용 */}
    </div>
  )
}
```

#### 컴포넌트 작성 규칙

1. **작고 집중된 컴포넌트**: 한 파일당 100줄 이하 권장
2. **Props 문서화**: JSDoc 주석 작성
3. **상태 관리**:
   - 서버 데이터: React Query
   - 로컬 UI 상태: useState
4. **로딩/에러 처리**: 항상 포함
5. **재사용성**: 공통 로직은 custom hooks로 추출

---

## 프로젝트 구조 규칙

### 백엔드 파일 구조

```
backend/app/
├── routers/              # API 엔드포인트 (라우팅)
│   └── etfs.py          # GET, POST 등 HTTP 메서드 정의
├── services/            # 비즈니스 로직 (순수 Python)
│   └── data_collector.py # 외부 API 호출, 데이터 가공
├── models.py            # Pydantic 모델 (데이터 검증)
├── database.py          # DB 연결 및 쿼리
└── main.py              # FastAPI 앱 초기화
```

**역할 분리:**
- `routers/`: HTTP 요청/응답 처리만
- `services/`: 실제 로직 구현
- `models.py`: 데이터 구조 정의
- `database.py`: DB 작업

### 프론트엔드 파일 구조

```
frontend/src/
├── pages/               # 라우트 레벨 컴포넌트
│   └── Dashboard.jsx    # /로 접근
├── components/          # 재사용 컴포넌트
│   ├── layout/         # 레이아웃 (Header, Footer)
│   ├── etf/            # ETF 관련 컴포넌트
│   └── common/         # 범용 컴포넌트 (Button, Spinner)
├── hooks/              # Custom Hooks
│   └── useETFData.js   # ETF 데이터 조회 훅
├── services/           # API 클라이언트
│   └── api.js          # Axios 인스턴스
└── utils/              # 유틸리티 함수
    └── formatters.js   # 날짜/금액 포맷팅
```

**컴포넌트 분류:**
- `pages/`: URL 라우트와 1:1 매칭
- `components/`: 페이지에서 사용되는 부품
- `hooks/`: 재사용 가능한 로직
- `services/`: 외부 통신

---

## 네이밍 규칙

### 백엔드 (Python)

```python
# 변수/함수: snake_case
user_data = get_user_data()

# 클래스: PascalCase
class ETFDataCollector:
    pass

# 상수: UPPER_CASE
MAX_RETRY_COUNT = 3

# Private: 언더스코어 prefix
def _internal_helper():
    pass
```

### 프론트엔드 (JavaScript/React)

```javascript
// 변수/함수: camelCase
const userData = getUserData()

// 컴포넌트: PascalCase
function ETFCard() {}

// 상수: UPPER_CASE
const API_BASE_URL = 'http://localhost:8000'

// 파일명:
// - 컴포넌트: PascalCase (ETFCard.jsx)
// - 유틸리티: camelCase (formatters.js)
```

---

## Git 워크플로우

### 브랜치 전략

```
main (프로덕션)
├── develop (개발)
│   ├── feature/dashboard
│   ├── feature/data-collection
│   └── fix/api-error
```

### 커밋 메시지 규칙

```
type(scope): subject

body (optional)

footer (optional)
```

**Type:**
- `feat`: 새로운 기능
- `fix`: 버그 수정
- `docs`: 문서 변경
- `style`: 코드 포맷팅
- `refactor`: 리팩토링
- `test`: 테스트 추가
- `chore`: 빌드/설정 변경

**예시:**

```
feat(backend): ETF 가격 데이터 수집 기능 추가

FinanceDataReader를 사용하여 네이버 증권에서
ETF 가격 데이터를 수집하는 기능을 구현했습니다.

Closes #15
```

---

## 테스트 전략

> **⚠️ 중요**: 모든 기능은 테스트 100% 완료 후 다음 단계로 진행합니다.  
> 자세한 내용은 **[Definition of Done](./DEFINITION_OF_DONE.md)** 참조

### 테스트 정책

1. **테스트 우선 개발 (Test-First)**
   - 기능 구현 전 또는 동시에 테스트 작성
   - 모든 테스트 통과 전까지 다음 기능 개발 금지

2. **커버리지 목표**
   - 백엔드: 최소 80%
   - 프론트엔드: 최소 70%
   - Critical Path: 100%

3. **테스트 종류**
   - 유닛 테스트: 개별 함수/메서드
   - 통합 테스트: API 엔드포인트
   - E2E 테스트: 전체 사용자 플로우

### 백엔드 테스트 (pytest)

```python
# tests/test_data_collector.py
import pytest
from app.services.data_collector import ETFDataCollector
from datetime import date

def test_get_etf_prices():
    collector = ETFDataCollector()
    prices = collector.get_price_data(
        ticker="480450",
        start_date=date(2025, 10, 1),
        end_date=date(2025, 10, 7)
    )
    
    assert prices is not None
    assert len(prices) > 0
    assert prices[0].ticker == "480450"
```

### 프론트엔드 테스트 (React Testing Library)

```javascript
// components/etf/__tests__/ETFCard.test.jsx
import { render, screen } from '@testing-library/react'
import ETFCard from '../ETFCard'

test('renders ETF name', () => {
  const etf = {
    ticker: '480450',
    name: 'KODEX AI전력핵심설비'
  }
  
  render(<ETFCard etf={etf} />)
  
  expect(screen.getByText('KODEX AI전력핵심설비')).toBeInTheDocument()
})
```

---

## 데이터 수집 전략

### 수집 타이밍

1. **초기 로드**: 최근 1년 히스토리 데이터
2. **일일 업데이트**: 장 마감 후 15:30 KST
3. **실시간 업데이트**: 사용자 요청 시 (캐시 TTL: 10분)

### 에러 처리

```python
import time
from typing import Optional

def retry_with_backoff(func, max_retries=3):
    """지수 백오프를 사용한 재시도 데코레이터"""
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            wait_time = 2 ** attempt  # 1, 2, 4초
            logger.warning(f"재시도 {attempt + 1}/{max_retries}: {e}")
            time.sleep(wait_time)
```

### Rate Limiting 준수

```python
import time

class RateLimiter:
    def __init__(self, calls_per_minute=10):
        self.calls_per_minute = calls_per_minute
        self.last_call = 0
    
    def wait_if_needed(self):
        now = time.time()
        time_since_last = now - self.last_call
        min_interval = 60.0 / self.calls_per_minute
        
        if time_since_last < min_interval:
            time.sleep(min_interval - time_since_last)
        
        self.last_call = time.time()
```

---

## 성능 최적화

### 백엔드

1. **비동기 I/O 사용**
```python
async def fetch_multiple_etfs(tickers: List[str]):
    tasks = [fetch_etf_data(ticker) for ticker in tickers]
    return await asyncio.gather(*tasks)
```

2. **데이터베이스 인덱스**
```sql
CREATE INDEX idx_prices_ticker_date ON prices(ticker, date);
```

3. **쿼리 최적화**
```python
# Bad: N+1 쿼리
for ticker in tickers:
    get_latest_price(ticker)  # 4번 DB 호출

# Good: 단일 쿼리
get_latest_prices(tickers)  # 1번 DB 호출
```

### 프론트엔드

1. **React.memo로 불필요한 렌더링 방지**
```javascript
export default React.memo(ETFCard)
```

2. **Code Splitting**
```javascript
const Comparison = lazy(() => import('./pages/Comparison'))
```

3. **이미지 최적화**
```jsx
<img
  src="/logo.png"
  alt="Logo"
  loading="lazy"
  width={200}
  height={50}
/>
```

---

## 한국어 처리

### 인코딩

- 모든 파일: **UTF-8**
- HTTP 헤더: `Content-Type: application/json; charset=utf-8`

### 폰트

```css
/* TailwindCSS 설정 */
@layer base {
  body {
    font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, sans-serif;
  }
}
```

### 금액/날짜 포맷팅

```javascript
// utils/formatters.js
export const formatPrice = (price) => {
  return new Intl.NumberFormat('ko-KR', {
    style: 'currency',
    currency: 'KRW',
  }).format(price)
}

export const formatDate = (date) => {
  return new Intl.DateTimeFormat('ko-KR', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  }).format(new Date(date))
}
```

---

## 보안 체크리스트

- [ ] `.env` 파일을 `.gitignore`에 추가
- [ ] CORS 설정: 허용된 origin만 명시
- [ ] SQL Injection 방지: 파라미터화된 쿼리 사용
- [ ] XSS 방지: 사용자 입력 sanitize
- [ ] API Rate Limiting 구현
- [ ] HTTPS 사용 (프로덕션)
- [ ] 민감한 정보 로깅 금지

---

**Last Updated**: 2025-11-06

