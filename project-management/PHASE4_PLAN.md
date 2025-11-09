# Phase 4 상세 구현 계획

**작성일**: 2025-11-10
**Phase**: 4 - Charts & Visualization
**우선순위**: Medium
**예상 소요 시간**: 16.5시간

---

## 📋 목차

1. [개요](#개요)
2. [목표 및 Acceptance Criteria](#목표-및-acceptance-criteria)
3. [8단계 구현 계획](#8단계-구현-계획)
4. [기술 스택 및 아키텍처](#기술-스택-및-아키텍처)
5. [테스트 전략](#테스트-전략)
6. [성능 최적화 전략](#성능-최적화-전략)
7. [리스크 및 대응 방안](#리스크-및-대응-방안)

---

## 개요

### Phase 4의 목적

Phase 4는 **데이터 시각화**를 중심으로, Recharts 라이브러리를 사용하여 인터랙티브 차트를 구현하고 ETF Detail 페이지를 완성하는 단계입니다.

### 주요 달성 목표

1. **가격 차트**: 시가/고가/저가/종가 LineChart + 거래량 BarChart
2. **매매 동향 차트**: 투자자별 순매수 StackedBarChart
3. **날짜 범위 선택기**: 7일/1개월/3개월/커스텀 기간 선택
4. **ETF Detail 페이지**: 차트, 정보, 뉴스 통합
5. **뉴스 타임라인**: 시간순 뉴스 표시 UI
6. **반응형 차트**: 모바일/태블릿/데스크톱 지원
7. **성능 최적화**: 1000+ 데이터 포인트 < 500ms
8. **테스트 완료**: Phase 3 연기된 테스트 + Phase 4 테스트 (커버리지 70%)

### Phase 3과의 차이점

| 구분 | Phase 3 | Phase 4 |
|------|---------|---------|
| 목적 | 기본 UI 및 API 연동 | 데이터 시각화 및 상세 페이지 |
| 주요 컴포넌트 | Dashboard, ETFCard, Header, Footer | PriceChart, TradingFlowChart, DateRangeSelector, NewsTimeline |
| 차트 | 없음 | 가격 차트, 매매 동향 차트 |
| ETF Detail | 기본 정보만 | 차트 + 정보 + 뉴스 통합 |
| 테스트 | 환경 설정만 | 전체 테스트 작성 (70% 커버리지) |

---

## 목표 및 Acceptance Criteria

### Phase 4 완료 조건 (다음 Phase 진행 필수)

- [ ] 가격 차트 (LineChart) 정상 렌더링
- [ ] 거래량 차트 (BarChart) 정상 렌더링
- [ ] 투자자별 매매 동향 차트 (StackedBarChart) 정상 렌더링
- [ ] 날짜 범위 선택기 동작 (7일/1개월/3개월/커스텀)
- [ ] ETF Detail 페이지 완성 (차트 + 정보 + 뉴스)
- [ ] 모바일/태블릿/데스크톱 반응형 차트
- [ ] **차트 컴포넌트 테스트 70% 이상 커버리지**
- [ ] **Phase 3에서 연기된 컴포넌트 테스트 완료**
- [ ] 뉴스 타임라인 UI 구현
- [ ] 차트 성능 최적화 (1000+ 데이터 포인트 < 500ms)

### 성공 지표 (KPI)

1. **기능**: 모든 차트가 정상 렌더링되고 인터랙션 동작
2. **성능**: 차트 렌더링 시간 < 500ms (1000+ 데이터)
3. **테스트**: 테스트 커버리지 70% 이상, 모든 테스트 100% 통과
4. **반응형**: 모바일/태블릿/데스크톱 모두 정상 동작
5. **사용성**: 날짜 범위 선택, 툴팁, 레전드 모두 직관적

---

## 8단계 구현 계획

### Step 1: 가격 차트 컴포넌트 구현 (2.5시간)

**목표**: 종목의 가격 변동을 시각화하는 LineChart + BarChart 구현

#### 주요 작업

1. **PriceChart.jsx 컴포넌트 생성**
   - Props: `data`, `ticker`, `height`
   - 데이터 구조: `{date, open_price, high_price, low_price, close_price, volume, daily_change_pct}`

2. **Recharts ComposedChart 구현**
   - ResponsiveContainer (반응형)
   - Line 4개: 시가, 고가, 저가, 종가
   - Bar 1개: 거래량 (등락률 기준 색상)

3. **CustomTooltip 구현**
   - 날짜, 시가, 고가, 저가, 종가, 거래량, 등락률
   - 가격: 천 단위 콤마
   - 거래량: K/M 단위
   - 등락률: 색상 구분 (빨강/파랑)

4. **Legend 추가**
   - 항목: 종가, 시가, 고가, 저가, 거래량
   - 위치: 하단 중앙

5. **유닛 테스트 작성** (8개)
   - 차트 렌더링, 빈 데이터 처리, 툴팁, 레전드, 반응형, 포맷팅, 색상

#### Acceptance Criteria

- [ ] 가격 차트 렌더링 성공
- [ ] 거래량 막대 표시
- [ ] 툴팁 인터랙션 동작
- [ ] 반응형 동작 확인
- [ ] 유닛 테스트 100% 통과

---

### Step 2: 투자자별 매매 동향 차트 구현 (2시간)

**목표**: 개인/기관/외국인 투자자별 순매수 데이터를 StackedBarChart로 시각화

#### 주요 작업

1. **TradingFlowChart.jsx 컴포넌트 생성**
   - Props: `data`, `ticker`, `height`
   - 데이터 구조: `{date, individual_net, institutional_net, foreign_net}`

2. **StackedBarChart 구현**
   - Bar 3개: 개인(파랑), 기관(초록), 외국인(주황)
   - stackOffset: "sign" (양수/음수 구분)
   - ReferenceLine: y=0 (기준선)

3. **데이터 전처리**
   - `formatTradingFlowData()`: 원 → 억 원 변환
   - 날짜 정렬 (오름차순)

4. **CustomTooltip 구현**
   - 투자자별 순매수/순매도 표시
   - 양수: "순매수 +XX억", 음수: "순매도 -XX억"
   - 색상 구분

5. **유닛 테스트 작성** (6개)
   - 차트 렌더링, 데이터 전처리, 툴팁, 레전드, 빈 데이터, ReferenceLine

#### Acceptance Criteria

- [ ] StackedBarChart 정상 렌더링
- [ ] 3개 투자자 유형 색상 구분
- [ ] 툴팁에 순매수/순매도 표시
- [ ] 유닛 테스트 100% 통과

---

### Step 3: 날짜 범위 선택기 구현 (1.5시간)

**목표**: 사용자가 차트 데이터 기간을 선택할 수 있는 UI 구현

#### 주요 작업

1. **DateRangeSelector.jsx 컴포넌트 생성**
   - Props: `onDateRangeChange`, `defaultRange`
   - State: `selectedRange`, `startDate`, `endDate`

2. **프리셋 버튼 UI**
   - 버튼 4개: "7일", "1개월", "3개월", "커스텀"
   - 활성 버튼 스타일 (bg-primary-600)
   - 버튼 클릭 시 날짜 범위 자동 계산

3. **커스텀 날짜 선택기**
   - startDate, endDate input (type="date")
   - 검증: startDate <= endDate
   - 최대 범위: 1년

4. **date-fns 활용**
   - `subDays()`, `subMonths()`, `format()`, `isAfter()`

5. **유닛 테스트 작성** (7개)
   - 프리셋 버튼 클릭, 커스텀 날짜 입력, 검증, 콜백, 기본값, 최대 범위, 반응형

#### Acceptance Criteria

- [ ] 프리셋 버튼 동작 (7일/1개월/3개월)
- [ ] 커스텀 날짜 선택 동작
- [ ] 날짜 검증 동작
- [ ] 유닛 테스트 100% 통과

---

### Step 4: ETF Detail 페이지 완성 (3시간)

**목표**: ETF 상세 정보, 차트, 뉴스를 통합한 완전한 Detail 페이지 구현

#### 주요 작업

1. **ETFDetail.jsx 구조 개선**
   - 섹션: 기본 정보, 가격 차트, 매매 동향 차트, 뉴스
   - 그리드 레이아웃 (2열)

2. **기본 정보 섹션 확장**
   - 종목명, 티커, 타입, 테마, 운용보수, 상장일
   - 최근 가격 정보 (종가, 등락률, 거래량)
   - 뱃지 UI (ETF/STOCK)

3. **가격 차트 섹션**
   - PriceChart 통합
   - DateRangeSelector 추가
   - React Query 데이터 페칭

4. **매매 동향 차트 섹션**
   - TradingFlowChart 통합
   - DateRangeSelector 공유

5. **뉴스 타임라인 섹션**
   - NewsTimeline 컴포넌트
   - React Query 뉴스 데이터 페칭

6. **ErrorBoundary 추가**
   - 차트 에러 격리

7. **성능 최적화**
   - React.memo, useMemo
   - 차트 데이터 샘플링

8. **통합 테스트 작성** (8개)
   - 페이지 렌더링, 차트 표시, 뉴스 표시, 날짜 변경, 로딩, 에러, 반응형

#### Acceptance Criteria

- [ ] 모든 섹션 정상 렌더링
- [ ] 날짜 범위 선택 시 차트 갱신
- [ ] 뉴스 타임라인 표시
- [ ] 로딩/에러 상태 정상 처리
- [ ] 통합 테스트 100% 통과

---

### Step 5: 차트 반응형 처리 및 최적화 (1.5시간)

**목표**: 모든 디바이스에서 차트가 잘 보이고 성능이 우수하도록 최적화

#### 주요 작업

1. **반응형 차트 높이**
   - useWindowSize 커스텀 훅
   - 모바일: 250px, 태블릿: 350px, 데스크톱: 450px

2. **모바일 터치 인터랙션**
   - Recharts 터치 이벤트 활성화
   - 툴팁 터치 지원

3. **성능 최적화**
   - 대용량 데이터 샘플링 (1000+ → 매 5번째)
   - React.memo, useMemo
   - 차트 렌더링 시간 측정 (< 500ms)

4. **Accessibility 개선**
   - 차트 제목 (aria-label)
   - 툴팁 색상 대비 비율 (WCAG AA)
   - 키보드 네비게이션

5. **성능 테스트 작성** (5개)
   - 1000개 데이터 렌더링, 샘플링, React.memo, 렌더링 시간, 메모리 누수

#### Acceptance Criteria

- [ ] 모바일/태블릿/데스크톱 반응형 동작
- [ ] 차트 렌더링 시간 < 500ms
- [ ] 1000+ 데이터 정상 표시
- [ ] 성능 테스트 통과

---

### Step 6: Phase 3에서 연기된 컴포넌트 테스트 작성 (3시간)

**목표**: Phase 3 Step 6에서 연기된 컴포넌트 테스트를 완료하여 전체 커버리지 70% 달성

#### 주요 작업

1. **ETFCard 컴포넌트 테스트 확장**
   - 렌더링, 가격 표시, 등락률 색상, 거래량 포맷, 뉴스, 클릭, 로딩, 에러

2. **Dashboard 페이지 테스트 확장**
   - 종목 렌더링, 정렬, 새로고침, 자동 새로고침, 로딩, 에러, 빈 데이터

3. **Header 컴포넌트 테스트**
   - 렌더링, 네비게이션, 햄버거 메뉴, Active 링크

4. **Footer 컴포넌트 테스트**
   - 렌더링, 저작권, 업데이트 시간, GitHub 링크

5. **API 서비스 테스트 확장**
   - etfApi, newsApi 메서드 테스트
   - 에러 핸들링, 타임아웃

6. **MSW 핸들러 작성**
   - 모든 API 엔드포인트 Mock

7. **테스트 커버리지 확인**
   - `npm run test:coverage` (목표: 70%)

#### Acceptance Criteria

- [ ] 전체 컴포넌트 테스트 통과
- [ ] 테스트 커버리지 70% 이상
- [ ] MSW 핸들러 정상 작동

---

### Step 7: 뉴스 타임라인 UI 구현 (1.5시간)

**목표**: 종목 관련 뉴스를 시간순으로 보기 좋게 표시하는 UI 구현

#### 주요 작업

1. **NewsTimeline.jsx 컴포넌트 생성**
   - Props: `ticker`, `limit`
   - React Query 데이터 페칭

2. **뉴스 카드 UI**
   - 날짜, 제목 (링크), 출처, 관련도 점수
   - 관련도: 별점 또는 진행률 바

3. **타임라인 디자인**
   - 세로 타임라인 (점 + 선)
   - 날짜별 그룹핑

4. **페이지네이션**
   - "더 보기" 버튼
   - limit 증가 (10 → 20 → 30...)

5. **유닛 테스트 작성** (6개)
   - 뉴스 카드 렌더링, 관련도 점수, 날짜 그룹핑, 더 보기, 빈 데이터, 외부 링크

#### Acceptance Criteria

- [ ] 뉴스 타임라인 정상 렌더링
- [ ] 날짜별 그룹핑 동작
- [ ] "더 보기" 버튼 동작
- [ ] 유닛 테스트 100% 통과

---

### Step 8: 종합 테스트 및 문서화 (1.5시간)

**목표**: Phase 4 전체 기능 검증 및 문서 업데이트

#### 주요 작업

1. **전체 테스트 실행**
   - `npm test`, `npm run test:coverage`
   - 실패한 테스트 수정

2. **수동 테스트 체크리스트**
   - ETF Detail 페이지 접속 (6개 종목)
   - 차트 렌더링, 날짜 범위 선택, 뉴스 타임라인
   - 모바일 반응형, 차트 인터랙션

3. **성능 테스트**
   - 차트 렌더링 시간 (< 500ms)
   - 1000개 데이터 렌더링
   - 메모리 사용량

4. **크로스 브라우저 테스트**
   - Chrome, Firefox, Safari, Edge

5. **문서 업데이트**
   - `frontend/README.md`: 차트 컴포넌트 사용법
   - `PROGRESS.md`: Phase 4 완료 기록
   - `TODO.md`: Phase 4 체크

6. **코드 정리**
   - console.log 제거
   - 불필요한 주석 제거
   - TODO 주석 정리
   - ESLint 경고 수정

#### Acceptance Criteria

- [ ] 모든 테스트 100% 통과
- [ ] 테스트 커버리지 70% 이상
- [ ] 크로스 브라우저 동작 확인
- [ ] 문서 업데이트 완료
- [ ] 코드 정리 완료

---

## 기술 스택 및 아키텍처

### 차트 라이브러리

**Recharts 2.10.3** (이미 설치됨)

- **ResponsiveContainer**: 반응형 차트 처리
- **ComposedChart**: LineChart + BarChart 조합 (가격 + 거래량)
- **BarChart**: StackedBarChart (투자자별 매매 동향)
- **Line**: 시가, 고가, 저가, 종가 표시
- **Bar**: 거래량, 투자자별 순매수 표시
- **XAxis / YAxis**: 날짜, 가격, 거래량 축
- **Tooltip**: 커스텀 툴팁
- **Legend**: 범례
- **ReferenceLine**: 기준선 (y=0)

### 상태 관리

**React Query (TanStack Query) 5.8.4**

- **useQuery**: 데이터 페칭 (가격, 매매 동향, 뉴스)
- **queryKey**: `['prices', ticker, startDate, endDate]`
- **staleTime**: 가격 1분, 뉴스 5분
- **refetchOnWindowFocus**: true (Dashboard에서 활성화)

### 날짜 처리

**date-fns 2.30.0**

- `subDays()`, `subMonths()`: 날짜 범위 계산
- `format()`: 날짜 포맷팅 (YYYY-MM-DD, MM/DD)
- `isAfter()`, `isBefore()`: 날짜 검증

### 컴포넌트 구조

```
frontend/src/
├── components/
│   ├── charts/
│   │   ├── PriceChart.jsx          # 가격 차트 (ComposedChart)
│   │   ├── TradingFlowChart.jsx    # 매매 동향 차트 (StackedBarChart)
│   │   ├── DateRangeSelector.jsx   # 날짜 범위 선택기
│   │   └── NewsTimeline.jsx        # 뉴스 타임라인
│   ├── common/
│   │   ├── ErrorBoundary.jsx       # 에러 바운더리
│   │   └── Spinner.jsx             # 로딩 스피너
│   └── etf/
│       └── ETFCard.jsx             # ETF 카드 (이미 존재)
├── pages/
│   ├── Dashboard.jsx               # 대시보드 (이미 존재)
│   └── ETFDetail.jsx               # ETF 상세 페이지 (확장)
├── hooks/
│   └── useWindowSize.js            # 윈도우 사이즈 훅
├── utils/
│   └── chartHelpers.js             # 차트 헬퍼 함수
└── services/
    └── api.js                      # API 서비스 (이미 존재)
```

---

## 테스트 전략

### 테스트 도구

- **Vitest 4.0.8**: 테스트 프레임워크
- **React Testing Library 16.3.0**: 컴포넌트 테스트
- **MSW (Mock Service Worker) 2.12.1**: API Mock
- **@vitest/coverage-v8**: 커버리지 측정

### 테스트 유형

#### 1. 유닛 테스트

**대상**: 개별 컴포넌트 (PriceChart, TradingFlowChart, DateRangeSelector, NewsTimeline)

**예시**:
```javascript
// PriceChart.test.jsx
describe('PriceChart', () => {
  it('should render chart with data', () => {
    // 차트 렌더링 테스트
  })

  it('should show tooltip on hover', () => {
    // 툴팁 인터랙션 테스트
  })

  it('should handle empty data', () => {
    // 빈 데이터 처리 테스트
  })
})
```

#### 2. 통합 테스트

**대상**: ETFDetail 페이지 전체 플로우

**예시**:
```javascript
// ETFDetail.test.jsx
describe('ETFDetail', () => {
  it('should render all sections', () => {
    // 모든 섹션 렌더링 테스트
  })

  it('should update charts when date range changes', () => {
    // 날짜 범위 변경 시 차트 갱신 테스트
  })
})
```

#### 3. 성능 테스트

**대상**: 차트 렌더링 시간, 메모리 사용량

**예시**:
```javascript
// performanceTest.js
it('should render 1000 data points in < 500ms', () => {
  const startTime = performance.now()
  // 차트 렌더링
  const endTime = performance.now()
  expect(endTime - startTime).toBeLessThan(500)
})
```

### 테스트 커버리지 목표

- **전체 커버리지**: 70% 이상
- **차트 컴포넌트**: 80% 이상
- **페이지 컴포넌트**: 70% 이상
- **API 서비스**: 90% 이상

### MSW 핸들러 예시

```javascript
// mocks/handlers.js
export const handlers = [
  http.get('/api/etfs/:ticker/prices', () => {
    return HttpResponse.json([
      { date: '2025-11-01', close_price: 25000, volume: 1000000, daily_change_pct: 2.5 },
      // ...
    ])
  }),

  http.get('/api/etfs/:ticker/trading-flow', () => {
    return HttpResponse.json([
      { date: '2025-11-01', individual_net: 5000000, institutional_net: -3000000, foreign_net: -2000000 },
      // ...
    ])
  }),
]
```

---

## 성능 최적화 전략

### 1. 차트 렌더링 최적화

**문제**: 1000+ 데이터 포인트 렌더링 시 느려짐

**해결책**:
- **데이터 샘플링**: 1000개 이상 시 매 5번째 포인트만 표시
- **React.memo**: 차트 컴포넌트 메모이제이션
- **useMemo**: 데이터 전처리 캐싱

```javascript
// 데이터 샘플링 함수
function sampleData(data, maxPoints = 200) {
  if (data.length <= maxPoints) return data
  const step = Math.ceil(data.length / maxPoints)
  return data.filter((_, index) => index % step === 0)
}

// useMemo 사용 예시
const chartData = useMemo(() => {
  return sampleData(rawData, 200)
}, [rawData])
```

### 2. React.memo 적용

```javascript
// PriceChart.jsx
const PriceChart = React.memo(({ data, ticker, height }) => {
  // 차트 렌더링
})
```

### 3. 차트 렌더링 시간 측정

```javascript
// 개발 환경에서만
if (process.env.NODE_ENV === 'development') {
  console.time('PriceChart render')
  // 차트 렌더링
  console.timeEnd('PriceChart render')
}
```

### 4. 반응형 차트 높이

```javascript
// useWindowSize.js
function useWindowSize() {
  const [windowSize, setWindowSize] = useState({
    width: window.innerWidth,
    height: window.innerHeight,
  })

  useEffect(() => {
    function handleResize() {
      setWindowSize({
        width: window.innerWidth,
        height: window.innerHeight,
      })
    }

    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  return windowSize
}
```

---

## 리스크 및 대응 방안

### 리스크 1: 차트 렌더링 성능 이슈

**가능성**: 중
**영향도**: 높음

**대응 방안**:
- 데이터 샘플링 적용 (1000+ → 200개)
- React.memo, useMemo 적용
- Recharts의 `isAnimationActive={false}` 옵션 고려

### 리스크 2: 테스트 커버리지 70% 미달

**가능성**: 중
**영향도**: 중

**대응 방안**:
- Step 6에 충분한 시간 할애 (3시간)
- 커버리지 낮은 파일 우선 테스트 작성
- 필요 시 Step 8에서 추가 시간 투입

### 리스크 3: 크로스 브라우저 호환성 문제

**가능성**: 낮음
**영향도**: 중

**대응 방안**:
- Vite의 자동 폴리필 활용
- Recharts는 모든 모던 브라우저 지원
- Safari에서 수동 테스트 필수

### 리스크 4: API 응답 시간 지연

**가능성**: 중
**영향도**: 낮음

**대응 방안**:
- React Query 캐싱 활용 (staleTime: 1분)
- 로딩 스켈레톤 UI 표시
- 에러 재시도 로직 (retry: 2)

---

## 참고 자료

### Recharts 공식 문서
- https://recharts.org/en-US/
- ComposedChart: https://recharts.org/en-US/api/ComposedChart
- BarChart: https://recharts.org/en-US/api/BarChart
- CustomTooltip: https://recharts.org/en-US/guide/customize

### React Testing Library
- https://testing-library.com/docs/react-testing-library/intro/

### Vitest
- https://vitest.dev/

### MSW (Mock Service Worker)
- https://mswjs.io/

---

## 체크리스트

### 시작 전 확인

- [ ] Phase 3 완료 확인 (TODO.md)
- [ ] Recharts 설치 확인 (package.json)
- [ ] 테스트 환경 설정 확인 (vitest.config.js)
- [ ] 백엔드 API 정상 작동 확인 (http://localhost:8000)

### Step별 체크리스트

- [ ] Step 1: PriceChart 완료
- [ ] Step 2: TradingFlowChart 완료
- [ ] Step 3: DateRangeSelector 완료
- [ ] Step 4: ETFDetail 페이지 완료
- [ ] Step 5: 차트 최적화 완료
- [ ] Step 6: 컴포넌트 테스트 완료
- [ ] Step 7: NewsTimeline 완료
- [ ] Step 8: 종합 테스트 및 문서화 완료

### 최종 확인

- [ ] 모든 테스트 100% 통과
- [ ] 테스트 커버리지 70% 이상
- [ ] 프로덕션 빌드 성공 (`npm run build`)
- [ ] 크로스 브라우저 테스트 완료
- [ ] 문서 업데이트 완료 (README, PROGRESS, TODO)
- [ ] Git 커밋 완료

---

**문서 버전**: 1.0
**마지막 업데이트**: 2025-11-10
