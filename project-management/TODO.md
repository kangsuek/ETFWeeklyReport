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

### Step 1: Detail 페이지 강화
- [ ] `PriceTable.jsx` - 일별 가격 데이터 테이블 (정렬, 페이지네이션)
- [ ] `StatsSummary.jsx` - 통계 요약 패널 (수익률, 변동성)
- [ ] 테스트 작성

### Step 2: Comparison 페이지 구현
- [ ] `NormalizedPriceChart.jsx` - 정규화된 가격 차트
- [ ] `ComparisonTable.jsx` - 성과 비교 테이블
- [ ] `CorrelationMatrix.jsx` - 상관관계 매트릭스 (선택)
- [ ] 테스트 작성

### Step 3: UI/UX 개선
- [ ] `ErrorBoundary.jsx` - 에러 바운더리
- [ ] `Toast.jsx` - 토스트 알림
- [ ] 접근성 개선 (ARIA, 키보드 네비게이션)

**Acceptance Criteria**:
- [ ] Detail 페이지 강화 완료
- [ ] Comparison 페이지 완성
- [ ] 모든 테스트 100% 통과
- [ ] 테스트 커버리지 70% 이상 유지

## 🟣 Phase 6: Report Generation (Priority: Low)
- [ ] Markdown 리포트 생성기
- [ ] PDF 생성 (선택)
- [ ] 다운로드 UI

## 🔵 Phase 7: Optimization & Deployment
- [ ] 성능 최적화 (번들 크기, Code Splitting)
- [ ] Docker 설정
- [ ] 배포 (Vercel/Render, PostgreSQL 마이그레이션)
- [ ] 모니터링 설정
