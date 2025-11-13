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

## 🟣 Phase 6: Report Generation (Priority: Low)
- [ ] Markdown 리포트 생성기
- [ ] PDF 생성 (선택)
- [ ] 다운로드 UI

## 🔵 Phase 7: Optimization & Deployment
- [ ] 성능 최적화 (번들 크기, Code Splitting)
- [ ] Docker 설정
- [ ] 배포 (Vercel/Render, PostgreSQL 마이그레이션)
- [ ] 모니터링 설정

---

## 📚 기술 참고

**주요 라이브러리**: Recharts, React Table, date-fns, Pandas, NumPy

**통계 계산 공식**:
- 기간 수익률 = (마지막 종가 - 첫 종가) / 첫 종가 × 100
- 연환산 수익률 = 기간 수익률 × (365 / 일수)
- 변동성 = 일일 수익률의 표준편차 × √252
- Max Drawdown = 최대 손실 구간의 낙폭 %
- 샤프비율 = (수익률 - 무위험 수익률) / 변동성
