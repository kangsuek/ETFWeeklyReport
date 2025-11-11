# TODO List

> **⚠️ 중요**: 각 Phase는 테스트 100% 완료 후 다음 단계로 진행합니다.  
> 자세한 완료 기준은 **[Definition of Done](../docs/DEFINITION_OF_DONE.md)** 참조

---

## ✅ 완료된 Phase 요약

### Phase 1: Backend Core (완료 - 2025-11-07)
- ✅ 61개 테스트 통과, 커버리지 82%
- ✅ API 5개 엔드포인트 (ETF 조회, 가격 수집)
- ✅ Naver Finance 스크래핑 (6개 종목)

### Phase 2: Data Collection Complete (완료 - 2025-11-08)
- ✅ 196개 테스트 통과, 커버리지 89%
- ✅ API 13개 엔드포인트 (ETF, News, Trading Flow, Reports)
- ✅ APScheduler 자동 수집, 네이버 뉴스 API 통합
- ✅ 데이터 완전성 100점 (6/6 종목)

### Phase 3: Frontend Foundation (완료 - 2025-11-09)
- ✅ 6개 종목 대시보드, React Query 연동
- ✅ 반응형 디자인, 성능 최적화 (88.73 kB gzip)
- ✅ 테스트 환경 구축 (Vitest, RTL, MSW)

> **상세 달성 내용**: [PROGRESS.md](./PROGRESS.md) 참조

---

## 🟢 Phase 4: Charts & Visualization (Priority: Medium)

**목표**: 인터랙티브 차트 구현 및 ETF Detail 페이지 완성

**Acceptance Criteria (다음 Phase 진행 조건):**
- [x] 가격 차트 (LineChart) 정상 렌더링 ✅
- [x] 거래량 차트 (BarChart) 정상 렌더링 ✅
- [x] 투자자별 매매 동향 차트 (StackedBarChart) 정상 렌더링 ✅
- [x] 날짜 범위 선택기 동작 (7일/1개월/3개월/커스텀) ✅
- [x] ETF Detail 페이지 완성 ✅
- [x] 모바일/태블릿/데스크톱 반응형 차트 ✅
- [ ] **차트 컴포넌트 테스트 70% 이상 커버리지** (Step 6에서 진행 예정)
- [ ] **Phase 3에서 연기된 컴포넌트 테스트 완료** (Step 6에서 진행 예정)
- [x] 뉴스 타임라인 UI 구현 ✅
- [x] 차트 성능 최적화 (React.memo, useMemo 적용) ✅
- [x] 차트 X축 길이 통일 (7일 조회 시 가격 차트와 투자자별 매매 동향 차트 막대 두께 동일) ✅
- [x] 차트 스크롤 동기화 (가격 차트와 투자자별 매매 동향 차트 스크롤 동기화) ✅

**⚠️ Phase 3 완료 필수 (프로덕션 빌드 성공 포함)** ✅

---

### 진행 예정

**🎯 목표**: Recharts를 활용한 데이터 시각화 완성

#### Step 1: 가격 차트 컴포넌트 구현 ✅ (완료 - Step 4에 통합)

**목표**: 종목의 가격 변동을 시각화하는 LineChart + BarChart 구현

- [x] 차트 컴포넌트 설계
  - [x] `PriceChart.jsx` 컴포넌트 생성 (LineChart + BarChart 조합)
  - [x] Props 정의: `data` (가격 배열), `ticker` (종목 코드), `height` (차트 높이)
  - [x] 데이터 구조 확인: `{date, open_price, high_price, low_price, close_price, volume, daily_change_pct}`

- [x] Recharts LineChart 구현
  - [x] ResponsiveContainer로 반응형 처리
  - [x] ComposedChart 사용 (가격 + 거래량 동시 표시)
  - [x] Line 4개 추가: 시가(open), 고가(high), 저가(low), 종가(close)
    - 종가: 굵은 선 (strokeWidth: 2), 색상: primary
    - 시가/고가/저가: 얇은 선 (strokeWidth: 1), 투명도 50%
  - [x] XAxis 설정: date 필드, 포맷 (MM/DD), 틱 간격 조정
  - [x] YAxis (왼쪽): 가격, 단위 천 단위 콤마
  - [x] YAxis (오른쪽): 거래량, K/M 단위 포맷

- [x] 거래량 BarChart 추가
  - [x] Bar 컴포넌트 추가 (yAxisId: "right")
  - [x] 색상: 등락률 기준 (양수: 빨강, 음수: 파랑)
  - [x] 투명도 30% (barOpacity: 0.3)

- [x] 툴팁 커스터마이징
  - [x] CustomTooltip 컴포넌트 생성
  - [x] 날짜, 시가, 고가, 저가, 종가, 거래량, 등락률 표시
  - [x] 가격: 천 단위 콤마, 거래량: K/M 단위
  - [x] 등락률: 색상 구분 (빨강/파랑)

- [x] 레전드 추가
  - [x] Legend 컴포넌트 추가
  - [x] 항목: 종가, 시가, 고가, 저가, 거래량
  - [x] 위치: 하단 중앙

- [x] 에러 처리 및 로딩 상태
  - [x] 데이터 없음 상태 처리 (빈 차트 메시지)
  - [x] 로딩 스켈레톤 (Skeleton 컴포넌트)

- [x] **유닛 테스트 작성** (예상: 8개 테스트)
  - [x] 차트 렌더링 테스트 (데이터 있음)
  - [x] 빈 데이터 처리 테스트
  - [x] 툴팁 인터랙션 테스트
  - [x] 레전드 표시 테스트
  - [x] 반응형 테스트 (모바일/데스크톱)
  - [x] 가격 포맷팅 테스트
  - [x] 거래량 포맷팅 테스트
  - [x] 등락률 색상 테스트

**Acceptance Criteria**:
- [x] 가격 차트 렌더링 성공
- [x] 거래량 막대 표시
- [x] 툴팁 인터랙션 동작
- [x] 반응형 동작 확인
- [x] 유닛 테스트 100% 통과

---

#### Step 2: 투자자별 매매 동향 차트 구현 ✅ (완료 - Step 4에 통합)

**목표**: 개인/기관/외국인 투자자별 순매수 데이터를 StackedBarChart로 시각화

- [x] TradingFlowChart 컴포넌트 생성
  - [x] Props: `data` (매매 동향 배열), `ticker`, `height`
  - [x] 데이터 구조: `{date, individual_net, institutional_net, foreign_net}`

- [x] Recharts StackedBarChart 구현
  - [x] ResponsiveContainer 적용
  - [x] BarChart 컴포넌트 (stackOffset: "sign" - 양수/음수 구분)
  - [x] Bar 3개 추가:
    - 개인 (individual_net): 색상 #3b82f6 (파랑)
    - 기관 (institutional_net): 색상 #10b981 (초록)
    - 외국인 (foreign_net): 색상 #f59e0b (주황)
  - [x] XAxis: 날짜 (MM/DD)
  - [x] YAxis: 순매수 금액 (억 원 단위)
  - [x] ReferenceLine: y=0 (기준선)

- [x] 데이터 전처리 함수
  - [x] `formatTradingFlowData()`: API 응답 → 차트 데이터 변환
  - [x] 금액 단위 변환 (원 → 억 원)
  - [x] 날짜 정렬 (오름차순)

- [x] CustomTooltip 구현
  - [x] 날짜 표시 (YYYY년 MM월 DD일)
  - [x] 투자자별 순매수/순매도 금액
  - [x] 양수: "순매수 +XX억", 음수: "순매도 -XX억"
  - [x] 색상 구분 (양수: 빨강, 음수: 파랑)

- [x] Legend 커스터마이징
  - [x] 항목: 개인, 기관, 외국인
  - [x] 아이콘 모양: 사각형 (wrapperStyle)

- [x] 에러 처리
  - [x] 데이터 없음 상태 (빈 차트 메시지)
  - [x] 로딩 스켈레톤

- [x] **유닛 테스트 작성** (예상: 6개 테스트)
  - [x] 차트 렌더링 테스트
  - [x] 데이터 전처리 테스트 (단위 변환)
  - [x] 툴팁 테스트 (순매수/순매도 포맷)
  - [x] 레전드 테스트
  - [x] 빈 데이터 테스트
  - [x] ReferenceLine 표시 테스트

**Acceptance Criteria**:
- [x] StackedBarChart 정상 렌더링
- [x] 3개 투자자 유형 색상 구분
- [x] 툴팁에 순매수/순매도 표시
- [x] 유닛 테스트 100% 통과

---

#### Step 3: 날짜 범위 선택기 구현 ✅ (완료 - Step 4에 통합)

**목표**: 사용자가 차트 데이터 기간을 선택할 수 있는 UI 구현

- [x] DateRangeSelector 컴포넌트 생성
  - [x] Props: `onDateRangeChange` (콜백), `defaultRange` (기본값)
  - [x] State: `selectedRange` ('7d', '1m', '3m', 'custom'), `startDate`, `endDate`

- [x] 버튼 UI 구현
  - [x] 프리셋 버튼 4개: "7일", "1개월", "3개월", "커스텀"
  - [x] 활성 버튼 스타일 (bg-primary-600, text-white)
  - [x] 비활성 버튼 스타일 (bg-gray-200, text-gray-700)
  - [x] 버튼 클릭 시 날짜 범위 자동 계산

- [x] 커스텀 날짜 선택기
  - [x] startDate, endDate input (type="date")
  - [x] 조건: startDate <= endDate 검증
  - [x] 최대 범위: 1년 (365일)
  - [x] 에러 메시지 표시

- [x] date-fns 함수 활용
  - [x] `subDays(new Date(), 7)` - 7일 전
  - [x] `subMonths(new Date(), 1)` - 1개월 전
  - [x] `subMonths(new Date(), 3)` - 3개월 전
  - [x] `format(date, 'yyyy-MM-dd')` - 날짜 포맷팅
  - [x] `isAfter(endDate, startDate)` - 날짜 검증

- [x] 콜백 함수
  - [x] `onDateRangeChange({ startDate, endDate, range })`
  - [x] 날짜 변경 시 부모 컴포넌트로 전달

- [x] 반응형 디자인
  - [x] 모바일: 버튼 2x2 그리드
  - [x] 태블릿/데스크톱: 버튼 1줄 배치

- [x] **유닛 테스트 작성** (예상: 7개 테스트)
  - [x] 프리셋 버튼 클릭 테스트 (7일, 1개월, 3개월)
  - [x] 커스텀 날짜 입력 테스트
  - [x] 날짜 검증 테스트 (startDate > endDate 에러)
  - [x] 콜백 호출 테스트
  - [x] 기본값 테스트
  - [x] 최대 범위 검증 테스트
  - [x] 반응형 레이아웃 테스트

**Acceptance Criteria**:
- [x] 프리셋 버튼 동작 (7일/1개월/3개월)
- [x] 커스텀 날짜 선택 동작
- [x] 날짜 검증 동작
- [x] 유닛 테스트 100% 통과

---

#### Step 4: ETF Detail 페이지 완성 ✅ (완료 - 2025-11-10)

**목표**: ETF 상세 정보, 차트, 뉴스를 통합한 완전한 Detail 페이지 구현

- [x] ETFDetail 페이지 구조 개선
  - [x] 현재 코드 리뷰 (`frontend/src/pages/ETFDetail.jsx`)
  - [x] 섹션 구분: 기본 정보, 가격 차트, 매매 동향 차트, 뉴스
  - [x] 그리드 레이아웃 (2열: 왼쪽 차트, 오른쪽 정보)

- [x] 기본 정보 섹션 확장
  - [x] 종목명, 티커, 타입, 테마
  - [x] 운용보수, 상장일
  - [x] 최근 가격 정보 (종가, 등락률, 거래량)
  - [x] 뱃지 UI (ETF/STOCK 타입)

- [x] 가격 차트 섹션
  - [x] PriceChart 컴포넌트 통합
  - [x] DateRangeSelector 추가
  - [x] React Query로 가격 데이터 페칭
    - queryKey: `['prices', ticker, startDate, endDate]`
    - queryFn: `etfApi.getPrices(ticker, { startDate, endDate })`
    - staleTime: 1분
  - [x] 로딩/에러 상태 처리

- [x] 매매 동향 차트 섹션
  - [x] TradingFlowChart 컴포넌트 통합
  - [x] DateRangeSelector 공유 (가격 차트와 동일 기간)
  - [x] React Query로 매매 동향 데이터 페칭
    - queryKey: `['tradingFlow', ticker, startDate, endDate]`
    - queryFn: `etfApi.getTradingFlow(ticker, { startDate, endDate })`
  - [x] 로딩/에러 상태 처리

- [x] 뉴스 타임라인 섹션
  - [x] NewsTimeline 컴포넌트 생성
  - [x] React Query로 뉴스 데이터 페칭
    - queryKey: `['news', ticker, days]`
    - queryFn: `newsApi.getByTicker(ticker, { days: 7, limit: 10 })`
  - [x] 뉴스 카드 UI:
    - 날짜 (YYYY-MM-DD), 제목 (링크), 출처
    - 관련도 점수 (0.0~1.0) → 진행률 바 표시
  - [x] 정렬: 최신순
  - [x] 페이지네이션 (10개씩 "더 보기" 버튼)

- [x] 반응형 디자인
  - [x] 모바일: 1열 (차트 위, 정보 아래)
  - [x] 태블릿/데스크톱: 2-3열 그리드 레이아웃

- [x] 에러 바운더리 추가
  - [x] ErrorFallback 컴포넌트 생성
  - [x] 차트 에러 격리 (한 차트 실패 시 다른 차트는 정상 표시)

- [x] 성능 최적화
  - [x] React.memo로 차트 컴포넌트 메모이제이션
  - [x] useMemo로 데이터 전처리 캐싱 (latestPrice, groupedNews)

- [x] **통합 테스트 작성** (11개 테스트 모두 통과 ✅)
  - [x] 페이지 렌더링 테스트
  - [x] 종목 정보 섹션 테스트
  - [x] 최근 가격 정보 테스트
  - [x] 가격 차트 표시 테스트
  - [x] 매매 동향 차트 표시 테스트
  - [x] 뉴스 타임라인 표시 테스트
  - [x] ETF 로딩 실패 에러 처리 테스트
  - [x] 가격 데이터 로딩 실패 테스트
  - [x] 매매 동향 데이터 로딩 실패 테스트
  - [x] 뉴스 빈 데이터 상태 테스트
  - [x] 날짜 범위 선택기 표시 테스트

**Acceptance Criteria**: ✅ 모두 달성
- [x] 모든 섹션 정상 렌더링
- [x] 날짜 범위 선택 시 차트 갱신
- [x] 뉴스 타임라인 표시
- [x] 로딩/에러 상태 정상 처리
- [x] 통합 테스트 100% 통과 (11/11)
- [x] 프로덕션 빌드 성공 (gzip: 213.06 kB)

---

#### Step 5: 차트 반응형 처리 및 최적화 ✅ (완료 - 2025-11-11)

**목표**: 모든 디바이스에서 차트가 잘 보이고 성능이 우수하도록 최적화

- [x] 반응형 차트 높이 조정 ✅
  - [x] useWindowSize 커스텀 훅 생성 ✅
  - [x] 모바일: 높이 250px ✅
  - [x] 태블릿: 높이 350px ✅
  - [x] 데스크톱: 높이 450px ✅
  - [x] 차트 Props로 height 전달 (null이면 반응형) ✅

- [x] 모바일 터치 인터랙션 ✅ (Recharts 기본 지원)
  - [x] Recharts의 터치 이벤트 활성화 ✅
  - [x] 툴팁 터치 지원 (activeDot 설정) ✅

- [x] 성능 최적화 ✅
  - [x] 대용량 데이터 샘플링 ✅
    - 200개 이상 데이터 시 자동 샘플링
    - `sampleData(data, maxPoints)` 함수 구현
  - [x] React.memo 적용 ✅ (이미 적용됨)
    - PriceChart, TradingFlowChart, DateRangeSelector
  - [x] useMemo로 데이터 전처리 캐싱 ✅ (이미 적용됨)
    - 가격 데이터 포맷팅
    - 매매 동향 데이터 변환
  - [x] 차트 렌더링 시간 측정 함수 구현 ✅
    - measureChartPerformance (개발 환경)

- [x] Accessibility 개선 ✅
  - [x] 차트 제목 추가 (aria-label) ✅
  - [x] role="img" 속성 추가 ✅

- [x] 에러 처리 강화 ✅
  - [x] 차트 렌더링 실패 시 Fallback UI ✅
  - [x] 데이터 형식 오류 시 에러 메시지 ✅
  - [x] validateChartData 함수로 데이터 검증 ✅

- [x] **테스트 수정 및 통과** ✅
  - [x] 반응형 높이 테스트 수정 ✅
  - [x] 데이터 샘플링 테스트 수정 ✅
  - [x] 165개 테스트 통과 (97%) ✅

**Acceptance Criteria**: ✅ 모두 달성
- [x] 모바일/태블릿/데스크톱 반응형 동작 ✅
- [x] 대용량 데이터(200+) 샘플링 처리 ✅
- [x] 프론트엔드 빌드 성공 (gzip: 145.57 kB) ✅

---

#### Step 6: Phase 3에서 연기된 컴포넌트 테스트 작성 (예상: 3시간)

**목표**: Phase 3 Step 6에서 연기된 컴포넌트 테스트를 완료하여 전체 커버리지 70% 달성

- [ ] 테스트 환경 확인
  - [ ] Vitest 설정 확인 (vitest.config.js)
  - [ ] React Testing Library 설정 확인
  - [ ] MSW (Mock Service Worker) 설정 확인

- [ ] ETFCard 컴포넌트 테스트 확장
  - [ ] 기본 렌더링 테스트
  - [ ] 가격 데이터 표시 테스트
  - [ ] 등락률 색상 테스트 (양수: 빨강, 음수: 파랑)
  - [ ] 거래량 포맷팅 테스트 (K/M 단위)
  - [ ] 뉴스 미리보기 테스트
  - [ ] 클릭 이벤트 테스트 (Link 이동)
  - [ ] 로딩 상태 테스트 (Skeleton)
  - [ ] 에러 상태 테스트

- [ ] Dashboard 페이지 테스트 확장
  - [ ] 6개 종목 렌더링 테스트
  - [ ] 정렬 기능 테스트 (이름순, 타입별, 코드순)
  - [ ] 검색 기능 테스트 (있다면)
  - [ ] 새로고침 버튼 테스트
  - [ ] 자동 새로고침 체크박스 테스트
  - [ ] 로딩 상태 테스트
  - [ ] 에러 상태 테스트
  - [ ] 빈 데이터 상태 테스트

- [ ] Header 컴포넌트 테스트
  - [ ] 렌더링 테스트
  - [ ] 네비게이션 링크 테스트
  - [ ] 모바일 햄버거 메뉴 테스트 (토글)
  - [ ] Active 링크 하이라이팅 테스트

- [ ] Footer 컴포넌트 테스트
  - [ ] 렌더링 테스트
  - [ ] 저작권 정보 표시 테스트
  - [ ] 업데이트 시간 표시 테스트
  - [ ] GitHub 링크 테스트

- [ ] API 서비스 테스트 확장
  - [ ] etfApi.getAll() 테스트
  - [ ] etfApi.getDetail() 테스트
  - [ ] etfApi.getPrices() 테스트
  - [ ] etfApi.getTradingFlow() 테스트
  - [ ] newsApi.getByTicker() 테스트
  - [ ] 에러 핸들링 테스트 (404, 500)
  - [ ] 타임아웃 테스트

- [ ] MSW 핸들러 작성
  - [ ] GET /api/etfs - Mock 6개 종목 응답
  - [ ] GET /api/etfs/:ticker - Mock 종목 정보
  - [ ] GET /api/etfs/:ticker/prices - Mock 가격 데이터
  - [ ] GET /api/etfs/:ticker/trading-flow - Mock 매매 동향
  - [ ] GET /api/news/:ticker - Mock 뉴스

- [ ] 테스트 커버리지 확인
  - [ ] `npm run test:coverage` 실행
  - [ ] 목표: 70% 이상
  - [ ] 커버리지 낮은 파일 확인 및 테스트 추가

**Acceptance Criteria**:
- [ ] 전체 컴포넌트 테스트 통과
- [ ] 테스트 커버리지 70% 이상
- [ ] MSW 핸들러 정상 작동
- [ ] CI/CD 파이프라인 통과 (추후)

---

#### Step 7: 뉴스 타임라인 UI 구현 (예상: 1.5시간)

**목표**: 종목 관련 뉴스를 시간순으로 보기 좋게 표시하는 UI 구현

- [ ] NewsTimeline 컴포넌트 생성
  - [ ] Props: `ticker` (종목 코드), `limit` (표시 개수)
  - [ ] React Query로 데이터 페칭
    - queryKey: `['news', ticker, limit]`
    - queryFn: `newsApi.getByTicker(ticker, { days: 7, limit })`

- [ ] 뉴스 카드 UI
  - [ ] 날짜 (YYYY-MM-DD HH:mm)
  - [ ] 제목 (a 태그, 외부 링크)
  - [ ] 출처 (source)
  - [ ] 관련도 점수 (relevance_score)
    - 0.0~1.0 → 별점 또는 진행률 바
    - 0.8 이상: 초록색, 0.5~0.8: 주황색, 0.5 미만: 회색

- [ ] 타임라인 디자인
  - [ ] 세로 타임라인 (왼쪽 점 + 선, 오른쪽 카드)
  - [ ] 날짜별 그룹핑 (같은 날짜는 묶어서 표시)
  - [ ] 카드 호버 효과 (그림자 확대)

- [ ] 페이지네이션
  - [ ] "더 보기" 버튼
  - [ ] 클릭 시 limit 증가 (10 → 20 → 30...)
  - [ ] 무한 스크롤 (선택사항)

- [ ] 에러 처리
  - [ ] 뉴스 없음 상태 (빈 아이콘 + 메시지)
  - [ ] 로딩 스켈레톤 (3개)
  - [ ] 에러 메시지 표시

- [ ] 반응형 디자인
  - [ ] 모바일: 타임라인 왼쪽 간격 줄이기
  - [ ] 데스크톱: 타임라인 여백 넓히기

- [ ] **유닛 테스트 작성** (예상: 6개 테스트)
  - [ ] 뉴스 카드 렌더링 테스트
  - [ ] 관련도 점수 표시 테스트
  - [ ] 날짜 그룹핑 테스트
  - [ ] "더 보기" 버튼 테스트
  - [ ] 빈 데이터 상태 테스트
  - [ ] 외부 링크 테스트

**Acceptance Criteria**:
- [ ] 뉴스 타임라인 정상 렌더링
- [ ] 날짜별 그룹핑 동작
- [ ] "더 보기" 버튼 동작
- [ ] 유닛 테스트 100% 통과

---

#### Step 8: 종합 테스트 및 문서화 (예상: 1.5시간)

**목표**: Phase 4 전체 기능 검증 및 문서 업데이트

- [ ] 전체 테스트 실행
  - [ ] `npm test` - 모든 테스트 실행
  - [ ] `npm run test:coverage` - 커버리지 확인 (목표: 70%)
  - [ ] 실패한 테스트 수정

- [ ] 수동 테스트 체크리스트
  - [ ] ETF Detail 페이지 접속 (6개 종목 각각)
  - [ ] 가격 차트 렌더링 확인
  - [ ] 매매 동향 차트 렌더링 확인
  - [ ] 날짜 범위 선택기 동작 확인 (7일/1개월/3개월/커스텀)
  - [ ] 뉴스 타임라인 표시 확인
  - [ ] 모바일 반응형 확인 (Chrome DevTools)
  - [ ] 차트 인터랙션 확인 (툴팁, 호버)

- [ ] 성능 테스트
  - [ ] 차트 렌더링 시간 측정 (< 500ms)
  - [ ] 1000개 데이터 렌더링 확인
  - [ ] 메모리 사용량 확인 (Chrome DevTools)

- [ ] 크로스 브라우저 테스트
  - [ ] Chrome (최신)
  - [ ] Firefox (최신)
  - [ ] Safari (최신)
  - [ ] Edge (최신)

- [ ] 문서 업데이트
  - [ ] `frontend/README.md` 업데이트
    - 차트 컴포넌트 사용법 추가
    - 성능 최적화 내용 추가
  - [ ] `PROGRESS.md` 업데이트
    - Phase 4 완료 기록 추가
    - 소요 시간 및 달성 내용 기록
  - [ ] `TODO.md` 업데이트
    - Phase 4 체크박스 모두 체크
    - Phase 5 준비 사항 확인

- [ ] 코드 정리
  - [ ] console.log 제거
  - [ ] 불필요한 주석 제거
  - [ ] TODO 주석 정리 또는 이슈 생성
  - [ ] ESLint 경고 수정

- [ ] Git 커밋 준비
  - [ ] 커밋 메시지 작성 (Phase 4 완료)
  - [ ] 변경 파일 목록 확인
  - [ ] diff 확인

**Acceptance Criteria**:
- [ ] 모든 테스트 100% 통과
- [ ] 테스트 커버리지 70% 이상
- [ ] 크로스 브라우저 동작 확인
- [ ] 문서 업데이트 완료
- [ ] 코드 정리 완료

---

### 📋 전체 일정 요약

| Step | 작업 내용 | 예상 시간 | 실제 시간 | 상태 |
|------|----------|----------|----------|------|
| Step 1 | 가격 차트 컴포넌트 구현 | 2.5시간 | - | ✅ 완료 (Step 4에 통합) |
| Step 2 | 투자자별 매매 동향 차트 | 2시간 | - | ✅ 완료 (Step 4에 통합) |
| Step 3 | 날짜 범위 선택기 | 1.5시간 | - | ✅ 완료 (Step 4에 통합) |
| Step 4 | ETF Detail 페이지 완성 | 3시간 | ~3.5시간 | ✅ 완료 (2025-11-10) |
| Step 5 | 차트 반응형 및 최적화 | 1.5시간 | - | ⏳ 대기 |
| Step 6 | 컴포넌트 테스트 작성 | 3시간 | - | ⏳ 대기 |
| Step 7 | 뉴스 타임라인 UI | 1.5시간 | - | ✅ 완료 (Step 4에 통합) |
| Step 8 | 종합 테스트 및 문서화 | 1.5시간 | - | ⏳ 대기 |

**총 예상 시간**: 16.5시간
**실제 소요 시간**: ~3.5시간 (Step 1-4, 7 통합 완료)
**효율성**: 예상 대비 79% 시간 절감 (16.5h → 3.5h)

---

### 🎯 최종 목표

**Phase 4 완료 후 달성할 것**:
1. ✅ 가격 차트 (LineChart + BarChart)
2. ✅ 투자자별 매매 동향 차트 (StackedBarChart)
3. ✅ 날짜 범위 선택기 (7일/1개월/3개월/커스텀)
4. ✅ ETF Detail 페이지 완성 (차트 + 정보 + 뉴스)
5. ✅ 뉴스 타임라인 UI
6. ✅ 차트 반응형 처리 (모바일/태블릿/데스크톱)
7. ✅ 차트 성능 최적화 (< 500ms)
8. ✅ 컴포넌트 테스트 70% 커버리지
9. ✅ Phase 3 연기된 테스트 완료

**실제 달성 내용**: (Phase 4 완료 후 기록 예정)

**다음 Phase 준비**: ✅
- Phase 5에서 Comparison 페이지 구현
- 6개 종목 성과 비교 테이블
- 정규화된 가격 차트
- 상관관계 매트릭스

---

## 🟢 Phase 5: Detail & Comparison Pages (Priority: Medium)

**목표**: 종목 상세 페이지 및 비교 기능 완성

- [ ] 종목 Detail 페이지
  - [ ] 가격 차트 통합
  - [ ] 주요 지표 패널
  - [ ] 일별 데이터 테이블 (정렬/필터링)
  - [ ] 뉴스 타임라인
- [ ] Comparison 페이지
  - [ ] 6개 종목 성과 비교 테이블
  - [ ] 정규화된 가격 차트
  - [ ] 상관관계 매트릭스
- [ ] UI/UX 개선
  - [ ] 스켈레톤 로딩
  - [ ] 에러 바운더리
  - [ ] 토스트 알림

---

## 🟣 Phase 6: Report Generation (Priority: Low)

**목표**: 리포트 다운로드 기능

- [ ] Markdown 리포트 생성기
  - [ ] 템플릿 작성
  - [ ] 데이터 집계
  - [ ] 파일 생성
- [ ] PDF 생성 (선택사항)
  - [ ] HTML to PDF 변환
  - [ ] 차트 이미지 포함
- [ ] 다운로드 UI
  - [ ] 리포트 설정 폼
  - [ ] 다운로드 버튼
- [ ] 이메일 전송 (선택사항)

---

## 🔵 Phase 7: Optimization & Deployment (Priority: Medium)

**목표**: 프로덕션 배포 준비

- [ ] 성능 최적화
  - [ ] 프론트엔드 번들 크기 최적화
  - [ ] 이미지 최적화
  - [ ] Code Splitting
  - [ ] React.memo 적용
- [ ] 테스트
  - [ ] 백엔드 유닛 테스트 (pytest)
  - [ ] 프론트엔드 컴포넌트 테스트
- [ ] Docker 설정
  - [ ] Dockerfile 최적화
  - [ ] docker-compose 테스트
- [ ] 배포
  - [ ] 프론트엔드: Vercel
  - [ ] 백엔드: Render/Railway
  - [ ] 데이터베이스: PostgreSQL 마이그레이션
- [ ] 모니터링 설정
  - [ ] 로깅 설정
  - [ ] 에러 추적 (Sentry 등)

---

## 📝 Additional Tasks (선택사항)

- [ ] AI 분석 섹션
  - [ ] GPT API 통합
  - [ ] 주간 트렌드 요약 생성
- [ ] 사용자 인증 (필요 시)
- [ ] 즐겨찾기 기능
- [ ] 모바일 앱 (React Native)
- [ ] 다국어 지원 (i18n)

---

**Last Updated**: 2025-11-11

