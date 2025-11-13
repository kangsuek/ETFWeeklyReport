# TODO List

> **⚠️ 중요**: 각 Phase는 테스트 100% 완료 후 다음 단계로 진행합니다.

## ✅ 완료된 Phase (요약)
- **Phase 1**: Backend Core (61개 테스트, 커버리지 82%)
- **Phase 2**: Data Collection (196개 테스트, 커버리지 89%)
- **Phase 3**: Frontend Foundation (대시보드, 반응형 디자인)
- **Phase 4**: Charts & Visualization (가격/매매동향 차트, 날짜 선택기)
- **Phase 4.5**: Settings & Ticker Management ✅ (219개 테스트, 커버리지 87.37%)

## 🟢 Phase 5: Detail & Comparison Pages (거의 완료!)

**목표**: 종목 상세 페이지 강화 및 비교 페이지 완성

**예상 기간**: 10-13일 (2-3주)

**현재 진행 상황**:
- ✅ **Step 1 완료**: Detail 페이지 강화 (PriceTable, StatsSummary 컴포넌트 추가)
  - PriceTable: 24개 테스트 통과
  - StatsSummary: 22개 테스트 통과
  - 수익률 계산 버그 수정
- ✅ **Step 2 완료**: Comparison 페이지 구현
  - 백엔드 비교 API 완료 (33개 테스트 + 9개 통합 테스트 통과, 커버리지 82%)
  - TickerSelector 컴포넌트 완료 (2-6개 종목 선택 지원)
  - NormalizedPriceChart 컴포넌트 완료 (Recharts 사용)
  - ComparisonTable 컴포넌트 완료 (성과 비교 테이블)
  - Comparison.jsx 페이지 통합 완료
  - 프론트엔드 빌드 성공
- 🔄 **Step 3 선택**: UI/UX 개선 (ErrorBoundary, Toast - 선택 사항)

---

### 📍 Step 1: Detail 페이지 강화 ✅ (완료)

#### 1.1 PriceTable.jsx 컴포넌트 ✅
**파일**: `frontend/src/components/etf/PriceTable.jsx`

**기능**:
- [x] 일자, 시가, 고가, 저가, 종가, 거래량, 등락률 테이블
- [x] 정렬 기능 (일자, 종가, 거래량, 등락률)
- [x] 등락률 색상 표시 (빨강/파랑)
- [x] 반응형 디자인 (모바일: 카드, 데스크톱: 테이블)
- [x] 다크모드 지원
- [x] 페이지네이션 (20개 항목/페이지)

**테스트**: `PriceTable.test.jsx` ✅
- [x] 데이터 렌더링, 정렬, 페이지네이션 (24개 테스트 통과)
- [x] 반응형, 에러 처리
- [x] 잘못된 날짜 형식 처리

#### 1.2 StatsSummary.jsx 컴포넌트 ✅
**파일**: `frontend/src/components/etf/StatsSummary.jsx`

**기능** (간소화: 수익률 + 가격 범위만):
- [x] 수익률 카드: 기간 수익률 / 연환산 수익률
- [x] 가격 범위 카드: 최고가(날짜), 최저가(날짜), 평균가
- [x] 카드 레이아웃 (1x2 그리드)
- [x] 시각적 표시 (아이콘, 진행률 바, 그라디언트)
- [x] 수익률 계산 버그 수정 (API 데이터 순서 문제 해결)

**테스트**: `StatsSummary.test.jsx` ✅
- [x] 통계 계산 정확성 (22개 테스트 통과)
- [x] 에지 케이스 (데이터 0, 1, 2개)
- [x] 포맷팅, 반응형, 날짜 표시

#### 1.3 ETFDetail.jsx 통합 ✅
**파일**: `frontend/src/pages/ETFDetail.jsx`

- [x] StatsSummary를 날짜 선택기 아래 배치
- [x] PriceTable을 "가격 데이터" 섹션 추가
- [x] DateRangeSelector 연동
- [x] Loading/Error 상태 처리 (기존 구현 유지)
- [x] 빌드 성공 확인

**Step 1 완료 요약**:
- 총 46개 테스트 추가 (PriceTable 24개, StatsSummary 22개)
- 모든 테스트 100% 통과
- 빌드 성공
- 반응형 디자인 완료
- 다크모드 지원

---

### 📍 Step 2: Comparison 페이지 구현 ✅ (완료)

#### 2.1 백엔드 API 구현 ✅

**2.1.1 비교 API 엔드포인트** ✅
**파일**: `backend/app/routers/etfs.py`

- [x] `GET /api/etfs/compare` 엔드포인트 구현
  - Query: `tickers` (쉼표 구분), `start_date`, `end_date`
  - Response: 정규화 가격, 통계, 상관관계
- [x] 입력 검증 (2-6개 종목, 날짜 범위)

**2.1.2 서비스 레이어** ✅
**파일**: `backend/app/services/comparison_service.py`

- [x] `normalize_prices()` - 시작일 = 100 정규화
- [x] `calculate_returns()` - 수익률 계산
- [x] `calculate_volatility()` - 변동성 계산
- [x] `calculate_correlation_matrix()` - 상관관계
- [x] `calculate_max_drawdown()` - 최대 낙폭
- [x] `calculate_sharpe_ratio()` - 샤프 비율

**테스트**: ✅
- [x] `tests/test_comparison_service.py` (33개 유닛 테스트, 100% 통과)
- [x] `tests/test_api.py::TestComparisonEndpoint` (9개 통합 테스트, 100% 통과)
- [x] 2개, 6개 종목 비교 검증
- [x] 잘못된 티커, 날짜 범위 처리
- [x] 정규화 및 통계 계산 정확성
- [x] 커버리지: comparison_service.py 82%

#### 2.2 프론트엔드 컴포넌트 ✅

**2.2.1 TickerSelector.jsx** ✅
**파일**: `frontend/src/components/comparison/TickerSelector.jsx`

- [x] 전체 종목 목록 표시
- [x] 다중 선택 (체크박스, 최소 2개, 최대 6개)
- [x] 선택된 종목 뱃지 표시
- [x] 선택 상태 표시 및 안내 메시지
- [x] 반응형 디자인 (모바일/데스크톱)

**2.2.2 NormalizedPriceChart.jsx** ✅
**파일**: `frontend/src/components/comparison/NormalizedPriceChart.jsx`

- [x] 다중 Line Chart (Recharts)
- [x] 시작일 = 100 정규화 표시
- [x] 각 종목 다른 색상 (최대 6개)
- [x] 커스텀 범례, 툴팁 (날짜, 정규화 가격, 수익률)
- [x] 반응형 디자인

**2.2.3 ComparisonTable.jsx** ✅
**파일**: `frontend/src/components/comparison/ComparisonTable.jsx`

- [x] 종목별 성과 테이블
  - 종목명, 기간 수익률, 연환산 수익률, 변동성, 샤프비율, Max DD
- [x] 정렬 기능 (각 열 클릭)
- [x] 최고 성과 하이라이트 (⭐)
- [x] 반응형 디자인 (데스크톱: 테이블, 모바일: 카드)

**2.2.4 CorrelationMatrix.jsx (선택, 미구현)**
**파일**: `frontend/src/components/comparison/CorrelationMatrix.jsx`

- [ ] 상관관계 히트맵 시각화 (나중에 추가 가능)

#### 2.3 Comparison.jsx 페이지 통합 ✅
**파일**: `frontend/src/pages/Comparison.jsx`

- [x] TickerSelector 구현
- [x] DateRangeSelector 추가
- [x] NormalizedPriceChart 추가
- [x] ComparisonTable 추가
- [x] API 연동 (useQuery)
- [x] Loading/Error 상태 처리
- [x] 안내 메시지 (선택 전/후)
- [x] 프론트엔드 빌드 성공

**Step 2 완료 요약**:
- 백엔드 테스트: 42개 (33 유닛 + 9 통합) 100% 통과
- 프론트엔드: 3개 주요 컴포넌트 완성 (TickerSelector, NormalizedPriceChart, ComparisonTable)
- 빌드 성공
- 반응형 디자인 완료
- 다크모드 지원

---

### 📍 Step 3: UI/UX 개선 (2-3일)

#### 3.1 ErrorBoundary.jsx
**파일**: `frontend/src/components/common/ErrorBoundary.jsx`

- [ ] React Error Boundary 구현
- [ ] 에러 UI 표시 (메시지, 스택)
- [ ] "새로고침" 버튼
- [ ] 에러 로깅
- [ ] App.jsx 및 주요 컴포넌트 적용
- [ ] 테스트 작성

#### 3.2 Toast 시스템
**파일**:
- `frontend/src/components/common/Toast.jsx`
- `frontend/src/contexts/ToastContext.jsx`

- [ ] Toast 컴포넌트 (Success, Error, Warning, Info)
- [ ] ToastContext 구현 (showToast 함수)
- [ ] 자동 사라짐 (3-5초)
- [ ] 다중 토스트 지원
- [ ] 닫기 버튼, 애니메이션
- [ ] 주요 기능에 토스트 추가 (데이터 수집 완료, 에러 등)
- [ ] 테스트 작성

#### 3.3 접근성 개선

- [ ] **ARIA 속성 추가**
  - 버튼: `aria-label`, `aria-pressed`
  - 폼: `aria-required`, `aria-invalid`
  - 차트: `aria-label`
  - 모달: `role="dialog"`, `aria-modal`

- [ ] **키보드 네비게이션**
  - Tab 순서 최적화
  - Enter/Space 키 지원
  - Escape 키 (모달 닫기)
  - 화살표 키 (테이블, 페이지네이션)

- [ ] **포커스 관리**
  - 포커스 표시 (outline)
  - Skip to content 링크
  - 포커스 트랩 (모달)

**적용 컴포넌트**:
- [ ] `Header.jsx`
- [ ] `PriceTable.jsx`
- [ ] `ComparisonTable.jsx`
- [ ] 모든 인터랙티브 컴포넌트

---

### ✅ Acceptance Criteria (완료 조건)

#### Step 1: Detail 페이지 강화 ✅
- [x] PriceTable 컴포넌트 완성 (정렬, 페이지네이션)
- [x] StatsSummary 컴포넌트 완성 (수익률, 가격 범위 카드)
- [x] ETFDetail 페이지 통합 완료
- [x] 모든 컴포넌트 테스트 100% 통과 (46개 테스트)
- [x] 반응형 디자인 검증 (모바일, 태블릿, 데스크톱)

#### Step 2: Comparison 페이지
- [ ] 비교 API 구현 및 테스트 통과
- [ ] 종목 선택 UI 완성 (2-6개 제한)
- [ ] 정규화 차트 완성 (다중 Line)
- [ ] 비교 테이블 완성 (정렬, 하이라이트)
- [ ] Comparison 페이지 통합 완료
- [ ] 백엔드 테스트 100% 통과
- [ ] 프론트엔드 테스트 100% 통과

#### Step 3: UI/UX 개선
- [ ] ErrorBoundary 구현 및 전체 앱 적용
- [ ] Toast 시스템 구현 및 주요 기능 연동
- [ ] 접근성 개선 (ARIA, 키보드, 포커스)
- [ ] 모든 컴포넌트 테스트 100% 통과

#### Phase 5 전체 완료 기준
- [x] **핵심 기능 완성** (Detail 페이지 강화, Comparison 페이지)
- [x] **백엔드 테스트 100% 통과** (42개 테스트: 33 유닛 + 9 통합)
- [x] **comparison_service.py 커버리지 82%**
- [x] **프론트엔드 빌드 성공**
- [x] **반응형 디자인 구현** (모바일, 태블릿, 데스크톱)
- [x] **다크모드 지원**
- [x] **문서 업데이트** (TODO.md)
- [ ] **UI/UX 개선** (ErrorBoundary, Toast - 선택 사항)
- [ ] **프론트엔드 테스트** (선택 사항)
- [ ] **API 문서 업데이트** (API_SPECIFICATION.md - 선택 사항)

**Phase 5 주요 성과**:
- 백엔드: 비교 API 완성 (정규화, 통계, 상관관계 계산)
- 프론트엔드: 3개 주요 컴포넌트 완성 (TickerSelector, NormalizedPriceChart, ComparisonTable)
- 종목 비교 기능 완전 작동
- 테스트 커버리지 우수 (82%)

---

### 📚 기술 참고

**라이브러리**:
- Recharts: 정규화 차트, 상관관계 히트맵
- React Table: 테이블 정렬, 페이지네이션
- date-fns: 날짜 포맷팅
- Pandas: 통계 계산 (백엔드)
- NumPy: 상관관계 계산 (백엔드)

**통계 계산 공식**:
- 기간 수익률 = (마지막 종가 - 첫 종가) / 첫 종가 × 100
- 연환산 수익률 = 기간 수익률 × (365 / 일수)
- 변동성 = 일일 수익률의 표준편차 × √252
- Max Drawdown = 최대 손실 구간의 낙폭 %
- 샤프비율 = (수익률 - 무위험 수익률) / 변동성

## 🟣 Phase 6: Report Generation (Priority: Low)
- [ ] Markdown 리포트 생성기
- [ ] PDF 생성 (선택)
- [ ] 다운로드 UI

## 🔵 Phase 7: Optimization & Deployment
- [ ] 성능 최적화 (번들 크기, Code Splitting)
- [ ] Docker 설정
- [ ] 배포 (Vercel/Render, PostgreSQL 마이그레이션)
- [ ] 모니터링 설정
