# TODO List

> **⚠️ 중요**: 각 Phase는 테스트 100% 완료 후 다음 단계로 진행합니다.

## ✅ 완료된 Phase
- **Phase 1**: Backend Core (61개 테스트, 커버리지 82%)
- **Phase 2**: Data Collection (196개 테스트, 커버리지 89%)
- **Phase 3**: Frontend Foundation (대시보드, 반응형 디자인)
- **Phase 4**: Charts & Visualization (가격/매매동향 차트, 날짜 선택기)
- **Phase 4.5**: Settings & Ticker Management (219개 테스트, 커버리지 87.37%)
- **Phase 5**: Detail & Comparison Pages + UI/UX 개선 (완료)
  - Detail 페이지 강화: PriceTable, StatsSummary (46개 테스트 통과)
  - Comparison 페이지: 백엔드 API + 프론트엔드 컴포넌트 (42개 테스트 통과, 커버리지 82%)
  - ErrorBoundary 구현 및 적용 (8개 테스트)
  - Toast 시스템 구현 (10개 테스트)
  - 접근성 개선 (ARIA 속성, 키보드 네비게이션, 포커스 관리)

## ✅ Phase 5: UI/UX 개선 완료

### Step 3: UI/UX 개선

#### 3.1 ErrorBoundary ✅
- [x] React Error Boundary 구현 및 적용
- [x] 에러 UI 및 로깅
- [x] 테스트 작성 (8개 테스트 통과)

#### 3.2 Toast 시스템 ✅
- [x] Toast 컴포넌트 및 Context 구현
- [x] 주요 기능에 토스트 연동 (DataManagementPanel)
- [x] 테스트 작성 (Toast, ToastContainer, ToastContext)

#### 3.3 접근성 개선 ✅
- [x] ARIA 속성 추가 (ETFCard, Header, Toast 등)
- [x] 키보드 네비게이션 최적화 (focus-visible 적용)
- [x] 포커스 관리 (ring 스타일 및 aria-label 추가)

---

## 🔴 Phase 6.1: 코드 품질 개선 - 버그 수정 (Priority: High)

> **참고**: 상세 계획은 [IMPROVEMENT_PLAN.md](./IMPROVEMENT_PLAN.md) 참조

### 6.1.1 에러 처리 버그 수정
- [x] `etfs.py:213-219` - ticker 변수 미정의 상태로 에러 로그 호출 수정
- [x] 테스트 작성 및 통과 확인

---

## 🟡 Phase 6.2: 코드 품질 개선 - 기능 완성도 (Priority: Medium)

> **참고**: 상세 계획은 [IMPROVEMENT_PLAN.md](./IMPROVEMENT_PLAN.md) 참조

### 6.2.1 불완전한 구현 완성
- [x] `data_collector.py:446` - TODO 주석 제거 및 주석 수정

### 6.2.2 하드코딩된 값 개선
- [x] `config.py:32-34` - SCRAPING_INTERVAL 상수화 (이미 환경변수로 관리됨)
- [x] `api.js:9` - 타임아웃 상수화
- [x] 컴포넌트 전반 - 색상 코드 상수화
- [x] Rate limiter interval (0.5초) 상수화

### 6.2.3 에러 메시지 일관성 개선 ✅
- [x] 백엔드 에러 메시지 표준화 (`backend/app/constants.py`에 상수 추가)
- [x] 백엔드 라우터들에서 표준 에러 메시지 사용 (`etfs.py`, `data.py`, `news.py`)
- [x] 프론트엔드 에러 메시지 표준화 (`frontend/src/constants.js`에 `ERROR_MESSAGES` 추가)
- [x] 프론트엔드 API 에러 처리 개선 (`api.js`에서 표준 메시지 사용)

### 6.2.4 API 타임아웃 처리 개선 ✅
- [x] 엔드포인트별 차등 타임아웃 적용
  - 빠른 조회: 10초 (`FAST_API_TIMEOUT`)
  - 일반 조회: 30초 (`NORMAL_API_TIMEOUT`)
  - 긴 작업: 60초 (`LONG_API_TIMEOUT`)
- [x] 타임아웃 에러 처리 개선 (타임아웃 감지 및 사용자 친화적 메시지)

### 6.2.5 날짜 범위 검증 통일 ✅
- [x] 프론트엔드 날짜 범위 검증 추가 (`frontend/src/utils/validation.js` 생성)
- [x] 백엔드와 동일한 검증 규칙 적용 (최대 365일, 시작일 <= 종료일, 미래 날짜 제한)
- [x] `DateRangeSelector`에 검증 로직 통합

---

## 🔵 Phase 6.3: 코드 품질 개선 - 유지보수성 (Priority: Low)

> **참고**: 상세 계획은 [IMPROVEMENT_PLAN.md](./IMPROVEMENT_PLAN.md) 참조

### 6.3.1 중복 코드 리팩토링 ✅
- [x] ETFDetail.jsx - ErrorFallback, NewsTimeline 컴포넌트 추출
- [x] 추출된 컴포넌트에 PropTypes 추가 및 테스트 작성
- [x] 기존 테스트 파일 업데이트 및 통과 확인
- [x] 백엔드 에러 핸들링 패턴 확인 (이미 통일되어 있음)

### 6.3.2 타입 안정성 개선 ✅
- [x] prop-types 패키지 설치
- [x] 주요 컴포넌트에 PropTypes 추가
  - PageHeader, LoadingIndicator, Spinner
  - DateRangeSelector, PriceChart, TradingFlowChart
  - ETFCard, ETFHeader, ETFCharts
  - DashboardFilters, ETFCardGrid

### 6.3.3 컴포넌트 크기 개선 ✅
- [x] ETFDetail.jsx 분리
  - Header 섹션 → ETFHeader.jsx
  - Charts 섹션 → ETFCharts.jsx
- [x] Dashboard.jsx 분리
  - 필터 섹션 → DashboardFilters.jsx
  - 카드 그리드 → ETFCardGrid.jsx
- [x] 분리된 컴포넌트에 PropTypes 추가 및 테스트 작성 (14개 테스트 통과)

### 6.3.4 매직 넘버 상수화 ✅
- [x] 차트 샘플링 최대 포인트 상수화 (`MAX_CHART_POINTS = 200`)
- [x] `PriceChart.jsx`, `TradingFlowChart.jsx`에서 상수 사용

### 6.3.5 코드 주석 품질 개선 ✅
- [x] 주석 언어 통일 (비즈니스 로직: 한글, 기술 용어: 영어) - 이미 완료
- [x] 복잡한 로직 주석 추가 - 주요 함수에 docstring 존재

### 6.3.6 로깅 개선 ✅
- [x] 로그 레벨 일관성 확보
- [x] 벌크 insert 로그에 "(bulk insert)" 표시 추가

### 6.3.7 성능 최적화 ✅
- [x] Dashboard 정렬 로직 메모이제이션 (`useMemo` 사용)
- [x] DB 벌크 insert 개선 (`executemany` 사용)
  - `save_price_data`, `save_trading_flow_data`, `save_news_data` 개선

---

## 🟣 Phase 6: Report Generation (Priority: Low)
- [ ] Markdown 리포트 생성기
- [ ] PDF 생성 (선택)
- [ ] 다운로드 UI

## 🔵 Phase 7: Performance Optimization (Priority: High)

> **📄 상세 계획**: [PERFORMANCE_OPTIMIZATION_PLAN.md](../PERFORMANCE_OPTIMIZATION_PLAN.md)

### 7.1 N+1 쿼리 문제 해결 (🔴 Critical) ✅
- [x] 백엔드: 배치 API 엔드포인트 추가 (`POST /api/etfs/batch-summary`)
- [x] 프론트엔드: 배치 API 호출 로직 구현
- [x] Dashboard 리팩토링 (18개 → 2개 API 호출로 감소)
- [x] 배치 API 단위 테스트 작성 (8개 테스트 통과)
- [x] 프론트엔드 빌드 성공 (gzip 167.36 kB)

### 7.2 프론트엔드 번들 크기 최적화 (🔴 Critical)
- [ ] Vite 설정: Code Splitting 적용 (manualChunks)
- [ ] Route-based Lazy Loading 구현
- [ ] 빌드 크기 검증 (목표: gzip 167kB → 100kB 이하)
- [ ] Lighthouse Performance 점수 측정

### 7.3 캐시 전략 최적화 (🟡 Medium)
- [ ] 백엔드: 엔드포인트별 차등 TTL 적용
- [ ] 캐시 무효화 로직 추가 (데이터 수집 후)
- [ ] 프론트엔드: TanStack Query 캐시 설정 최적화
- [ ] 캐시 Hit Rate 모니터링 (목표: 33% → 60% 이상)

### 7.4 데이터베이스 쿼리 최적화 (🟡 Medium)
- [ ] 배치 쿼리 구현 (IN 절 활용)
- [ ] 쿼리 결과 크기 제한 (limit 파라미터)
- [ ] Connection Pool 구현 (선택)
- [ ] 쿼리 성능 테스트

### 7.5 성능 모니터링 (🟢 Low)
- [ ] 백엔드: 성능 로깅 미들웨어 추가
- [ ] 프론트엔드: Web Vitals 측정
- [ ] 성능 대시보드 API 추가
- [ ] 주간 성능 리포트 자동화

## 🔵 Phase 8: Deployment & Production
- [ ] Docker 설정
- [ ] 배포 (Vercel/Render, PostgreSQL 마이그레이션)
- [ ] 프로덕션 모니터링 설정
- [ ] CI/CD 파이프라인 구축

---

## 📚 기술 참고

**주요 라이브러리**: Recharts, React Table, date-fns, Pandas, NumPy

**통계 계산 공식**:
- 기간 수익률 = (마지막 종가 - 첫 종가) / 첫 종가 × 100
- 연환산 수익률 = 기간 수익률 × (365 / 일수)
- 변동성 = 일일 수익률의 표준편차 × √252
- Max Drawdown = 최대 손실 구간의 낙폭 %
- 샤프비율 = (수익률 - 무위험 수익률) / 변동성
