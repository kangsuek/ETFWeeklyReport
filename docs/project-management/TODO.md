# TODO List

> **⚠️ 중요**: 각 Phase는 테스트 100% 완료 후 다음 단계로 진행합니다.

## ✅ 완료된 Phase (요약)
- **Phase 1**: Backend Core (61개 테스트, 커버리지 82%)
- **Phase 2**: Data Collection (196개 테스트, 커버리지 89%)
- **Phase 3**: Frontend Foundation (대시보드, 반응형 디자인)
- **Phase 4**: Charts & Visualization (가격/매매동향 차트, 날짜 선택기)
- **Phase 4.5**: Settings & Ticker Management ✅ (219개 테스트, 커버리지 87.37%)

## 🟢 Phase 5: Detail & Comparison Pages (진행 중)

**목표**: 종목 상세 페이지 강화 및 비교 페이지 완성

**예상 기간**: 10-13일 (2-3주)

---

### 📍 Step 1: Detail 페이지 강화 (3-4일)

#### 1.1 PriceTable.jsx 컴포넌트
**파일**: `frontend/src/components/etf/PriceTable.jsx`

**기능**:
- [ ] 일자, 시가, 고가, 저가, 종가, 거래량, 등락률 테이블
- [ ] 정렬 기능 (일자, 종가, 거래량, 등락률)
- [ ] 등락률 색상 표시 (빨강/파랑)
- [ ] 반응형 디자인 (모바일: 카드)
- [ ] 다크모드 지원

**테스트**: `PriceTable.test.jsx`
- [ ] 데이터 렌더링, 정렬, 페이지네이션
- [ ] 반응형, 에러 처리

#### 1.2 StatsSummary.jsx 컴포넌트
**파일**: `frontend/src/components/etf/StatsSummary.jsx`

**기능**:
- [ ] 기간 수익률 / 연환산 수익률
- [ ] 변동성 (표준편차) / Max Drawdown
- [ ] 가격 범위 (최고가, 최저가, 평균가)
- [ ] 거래량 통계 (평균, 최대)
- [ ] 카드 레이아웃 (2x2 그리드)
- [ ] 시각적 표시 (아이콘, 진행률 바)

**테스트**: `StatsSummary.test.jsx`
- [ ] 통계 계산 정확성
- [ ] 에지 케이스 (데이터 0, 1, 2개)
- [ ] 포맷팅, 반응형

#### 1.3 ETFDetail.jsx 통합
**파일**: `frontend/src/pages/ETFDetail.jsx`

- [ ] StatsSummary를 페이지 상단 배치
- [ ] PriceTable을 "가격 데이터" 섹션 추가
- [ ] DateRangeSelector 연동
- [ ] Loading/Error 상태 처리
- [ ] 테스트 업데이트

---

### 📍 Step 2: Comparison 페이지 구현 (5-6일)

#### 2.1 백엔드 API 구현

**2.1.1 비교 API 엔드포인트**
**파일**: `backend/app/routers/etfs.py`

- [ ] `GET /api/etfs/compare` 엔드포인트 구현
  - Query: `tickers` (쉼표 구분), `start_date`, `end_date`
  - Response: 정규화 가격, 통계, 상관관계
- [ ] 입력 검증 (2-6개 종목, 날짜 범위)

**2.1.2 서비스 레이어**
**파일**: `backend/app/services/comparison_service.py`

- [ ] `normalize_prices()` - 시작일 = 100 정규화
- [ ] `calculate_returns()` - 수익률 계산
- [ ] `calculate_volatility()` - 변동성 계산
- [ ] `calculate_correlation_matrix()` - 상관관계

**테스트**:
- [ ] `test_routers/test_etfs_comparison.py` (API 테스트)
- [ ] `test_services/test_comparison_service.py` (서비스 테스트)
- [ ] 2개, 6개 종목 비교 검증
- [ ] 잘못된 티커, 날짜 범위 처리
- [ ] 정규화 및 통계 계산 정확성

#### 2.2 프론트엔드 컴포넌트

**2.2.1 TickerSelector.jsx**
**파일**: `frontend/src/components/comparison/TickerSelector.jsx`

- [ ] 전체 종목 목록 표시
- [ ] 다중 선택 (체크박스, 최소 2개, 최대 6개)
- [ ] 선택된 종목 뱃지 표시
- [ ] "비교하기" 버튼
- [ ] 테스트 작성

**2.2.2 NormalizedPriceChart.jsx**
**파일**: `frontend/src/components/comparison/NormalizedPriceChart.jsx`

- [ ] 다중 Line Chart (Recharts)
- [ ] 시작일 = 100 정규화 표시
- [ ] 각 종목 다른 색상
- [ ] 범례, 툴팁 (날짜, 정규화 가격, 수익률)
- [ ] 확대/축소, 반응형
- [ ] 테스트 작성

**2.2.3 ComparisonTable.jsx**
**파일**: `frontend/src/components/comparison/ComparisonTable.jsx`

- [ ] 종목별 성과 테이블
  - 종목명, 수익률, 변동성, 샤프비율, Max DD
- [ ] 정렬 기능 (각 열)
- [ ] 최고 성과 하이라이트
- [ ] 반응형 디자인
- [ ] 테스트 작성

**2.2.4 CorrelationMatrix.jsx (선택, Priority: Low)**
**파일**: `frontend/src/components/comparison/CorrelationMatrix.jsx`

- [ ] 상관관계 히트맵 시각화
- [ ] 색상 코딩 (-1: 빨강, 0: 흰색, 1: 파랑)
- [ ] 호버 시 상관계수 표시
- [ ] 테스트 작성

#### 2.3 Comparison.jsx 페이지 통합
**파일**: `frontend/src/pages/Comparison.jsx`

- [ ] TickerSelector 구현
- [ ] DateRangeSelector 추가
- [ ] NormalizedPriceChart 추가
- [ ] ComparisonTable 추가
- [ ] CorrelationMatrix 추가 (선택)
- [ ] API 연동 (useQuery)
- [ ] Loading/Error 상태 처리
- [ ] 페이지 테스트 작성

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

#### Step 1: Detail 페이지 강화
- [ ] PriceTable 컴포넌트 완성 (정렬, 페이지네이션)
- [ ] StatsSummary 컴포넌트 완성 (4가지 통계 카테고리)
- [ ] ETFDetail 페이지 통합 완료
- [ ] 모든 컴포넌트 테스트 100% 통과
- [ ] 반응형 디자인 검증 (모바일, 태블릿, 데스크톱)

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
- [ ] **전체 테스트 커버리지 70% 이상**
- [ ] **모든 테스트 100% 통과** (백엔드 + 프론트엔드)
- [ ] **린트 에러 없음**
- [ ] **브라우저 검증 완료** (Chrome, Firefox, Safari)
- [ ] **반응형 디자인 검증** (모바일, 태블릿, 데스크톱)
- [ ] **다크모드 정상 작동**
- [ ] **문서 업데이트** (API_SPECIFICATION.md)

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
