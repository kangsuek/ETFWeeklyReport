# TODO List

> **⚠️ 중요**: 각 Phase는 테스트 100% 완료 후 다음 단계로 진행합니다.
> 자세한 완료 기준은 [Definition of Done](../docs/DEFINITION_OF_DONE.md) 참조

## ✅ 완료된 Phase (요약)

- **Phase 1**: Backend Core (61개 테스트, 커버리지 82%)
- **Phase 2**: Data Collection (196개 테스트, 커버리지 89%)
- **Phase 3**: Frontend Foundation (대시보드, 반응형 디자인)
- **Phase 4**: Charts & Visualization (가격/매매동향 차트, 날짜 선택기)
- **Phase 4.5**: Settings & Ticker Management ✅ (완료 - 2025-11-13)
  - 네이버 금융 자동 스크래핑 (ticker_scraper.py)
  - stocks.json 기반 종목 CRUD API
  - Settings 페이지 (종목/일반/데이터 관리)
  - 뉴스 키워드 최적화 (평균 200배 개선)
  - LocalStorage 기반 설정 관리
  - 다크 모드 테마
  - 현재: 219개 테스트, 커버리지 87.37%

> 상세 내역: [PROGRESS.md](./PROGRESS.md)

---

## 🟢 Phase 5: Detail & Comparison Pages (진행 중)

**목표**: 종목 상세 페이지 강화 및 비교 페이지 완성

**예상 소요 시간**: 약 8-10시간

### 현재 상태 (Phase 4 완료)
- ✅ ETF Detail 페이지 기본 구조
- ✅ 가격/매매 동향 차트, 날짜 선택기, 뉴스 타임라인

### Step 1: Detail 페이지 강화 (3-4시간)

#### Task 1.1: 일별 데이터 테이블 (1.5시간)
- [ ] `PriceTable.jsx` 컴포넌트 생성
  - [ ] 일별 가격 데이터 테이블 (날짜, 시가, 고가, 저가, 종가, 거래량, 등락률)
  - [ ] 정렬 기능, 페이지네이션 (10/25/50/100 rows)
  - [ ] 반응형 (모바일: 카드 형태)
- [ ] ETFDetail 페이지에 통합

#### Task 1.2: 통계 요약 패널 (1시간)
- [ ] `StatsSummary.jsx` 컴포넌트 생성
  - [ ] 기간 내 통계 (최고가, 최저가, 평균 거래량)
  - [ ] 수익률 (7일, 1개월, 3개월)
  - [ ] 변동성 (표준편차)
- [ ] `utils/statistics.js` 유틸리티 함수
  - [ ] `calculateReturns()`, `calculateVolatility()`

#### Task 1.3: 테스트 (0.5-1시간)
- [ ] `PriceTable.test.jsx` - 테이블 렌더링, 정렬, 페이지네이션
- [ ] `StatsSummary.test.jsx` - 통계 계산 및 표시
- [ ] `utils/statistics.test.js` - 유틸리티 함수 테스트

**Acceptance Criteria**:
- [ ] 일별 데이터 테이블 정상 표시
- [ ] 정렬/페이지네이션 정상 작동
- [ ] 통계 요약 정확 계산
- [ ] 모든 테스트 통과 (커버리지 70% 이상)

---

### Step 2: Comparison 페이지 구현 (4-5시간)

#### Task 2.1: 백엔드 API (0.5시간)
- [ ] `GET /api/etfs/compare` 엔드포인트 확인/구현
- [ ] 프론트엔드 API 서비스 함수 추가

#### Task 2.2: 정규화된 가격 차트 (1.5시간)
- [ ] `NormalizedPriceChart.jsx` 생성
  - [ ] 6개 종목 가격을 100 기준으로 정규화
  - [ ] 다중 라인 차트 (Recharts)
  - [ ] 범례, 툴팁, 날짜 범위 선택기
- [ ] `utils/normalize.js` - 가격 정규화 함수

#### Task 2.3: 비교 테이블 (1.5시간)
- [ ] `ComparisonTable.jsx` 생성
  - [ ] 6개 종목 성과 비교 (현재가, 수익률, 변동성)
  - [ ] 정렬 기능, 등락률 색상
  - [ ] 행 클릭 시 Detail 페이지 이동

#### Task 2.4: 상관관계 매트릭스 (선택, 1시간)
- [ ] `CorrelationMatrix.jsx` - 6x6 히트맵
- [ ] `utils/correlation.js` - 피어슨 상관계수 계산

#### Task 2.5: 페이지 통합 (0.5시간)
- [ ] `Comparison.jsx`에 컴포넌트 통합
- [ ] 로딩/에러 상태 처리

#### Task 2.6: 테스트 (1시간)
- [ ] 각 컴포넌트 및 유틸리티 함수 테스트

**Acceptance Criteria**:
- [ ] 비교 차트/테이블 정상 표시
- [ ] 모든 테스트 통과

---

### Step 3: UI/UX 개선 (1.5-2시간)

#### Task 3.1: 에러 바운더리 (0.5시간)
- [ ] `ErrorBoundary.jsx` 컴포넌트 생성
- [ ] App.jsx에 적용

#### Task 3.2: 토스트 알림 (0.5-1시간)
- [ ] `Toast.jsx` 컴포넌트
- [ ] `useToast.js` 커스텀 훅
- [ ] 주요 액션에 적용

#### Task 3.3: 접근성 개선 (0.5시간)
- [ ] ARIA 라벨, 키보드 네비게이션
- [ ] 색상 대비 확인 (WCAG AA)

#### Task 3.4: 테스트 (0.5시간)
- [ ] ErrorBoundary, Toast 테스트

---

### Step 4: E2E 테스트 (선택, 1-2시간)

#### Task 4.1: Playwright 설정 (0.5시간)
- [ ] Playwright 설치 및 설정

#### Task 4.2: E2E 테스트 시나리오 (1-1.5시간)
- [ ] `e2e/dashboard.spec.js` - 대시보드 플로우
- [ ] `e2e/etf-detail.spec.js` - Detail 페이지
- [ ] `e2e/comparison.spec.js` - Comparison 페이지

---

## Phase 5 완료 기준

### 기능 요구사항
- [ ] Detail 페이지 강화 (일별 데이터 테이블, 통계)
- [ ] Comparison 페이지 완성 (비교 차트, 테이블)
- [ ] UI/UX 개선 (에러 바운더리, 토스트)

### 테스트 요구사항
- [ ] 페이지별 통합 테스트
- [ ] 데이터 테이블 정렬/필터링 테스트
- [ ] 비교 로직 테스트
- [ ] E2E 테스트 (선택)
- [ ] 모든 테스트 100% 통과
- [ ] 테스트 커버리지 70% 이상 유지 (현재 87.37%)

### 문서화
- [ ] 새 컴포넌트 JSDoc 주석
- [ ] API 변경사항 반영
- [ ] PROGRESS.md 업데이트

### 검증
- [ ] 전체 사용자 플로우 수동 테스트
- [ ] 크로스 브라우저 테스트
- [ ] 모바일 반응형 확인
- [ ] 성능 테스트 (Lighthouse > 90)
- [ ] 프로덕션 빌드 성공

### 성능 목표
- [ ] 번들 크기 < 200 kB (gzip)
- [ ] 페이지 로딩 < 3초
- [ ] API 응답 < 1초

---

## 작업 우선순위

1. **High Priority** (필수)
   - Detail 페이지 강화 (일별 데이터 테이블)
   - Comparison 페이지 기본 구현
   - 테스트 작성

2. **Medium Priority** (권장)
   - 상관관계 매트릭스
   - E2E 테스트
   - 접근성 개선

3. **Low Priority** (선택)
   - 샤프 비율 계산
   - CI/CD 파이프라인 (Phase 7)

---

## 리스크 및 대응

### 리스크 1: 백엔드 API 부족
- **대응**: 프론트엔드에서 개별 API 호출 후 클라이언트 계산

### 리스크 2: 성능 저하
- **대응**: 데이터 샘플링, React.memo 적용

### 리스크 3: 시간 초과
- **대응**: 상관관계, E2E 테스트를 Phase 7로 연기

**예상 총 소요 시간**: 8-10시간

---

## 🟣 Phase 6: Report Generation (Priority: Low)

**목표**: 리포트 다운로드 기능

- [ ] Markdown 리포트 생성기
- [ ] PDF 생성 (선택)
- [ ] 다운로드 UI
- [ ] 이메일 전송 (선택)

---

## 🔵 Phase 7: Optimization & Deployment (Priority: Medium)

**목표**: 프로덕션 배포 준비

- [ ] 성능 최적화 (번들 크기, Code Splitting)
- [ ] 연기된 테스트 완료 (Settings 신규 기능)
- [ ] Docker 설정
- [ ] 배포 (Vercel/Render, PostgreSQL 마이그레이션)
- [ ] 모니터링 설정
- [ ] 문서화 완료 (API 명세, 아키텍처)

---

## 📝 Additional Tasks (선택)

- [ ] AI 분석 섹션 (GPT API 통합)
- [ ] 사용자 인증
- [ ] 즐겨찾기 기능
- [ ] 모바일 앱 (React Native)
- [ ] 다국어 지원 (i18n)
