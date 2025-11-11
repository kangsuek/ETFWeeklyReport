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

### Phase 4: Charts & Visualization (완료 - 2025-11-11)
- ✅ 186개 테스트 통과, 커버리지 82.52%
- ✅ 가격 차트 (LineChart + BarChart), 매매 동향 차트 (StackedBarChart)
- ✅ 날짜 범위 선택기, 뉴스 타임라인
- ✅ 차트 반응형 처리, 성능 최적화 (145.57 kB gzip)
- ✅ 차트 X축 길이 통일, 스크롤 동기화

> **상세 달성 내용**: [PROGRESS.md](./PROGRESS.md) 참조

---

## ✅ Phase 4: Charts & Visualization (완료 - 2025-11-11)

**목표**: 인터랙티브 차트 구현 및 ETF Detail 페이지 완성

**주요 달성 사항**:
- ✅ 가격 차트 (LineChart + BarChart), 매매 동향 차트 (StackedBarChart)
- ✅ 날짜 범위 선택기 (7일/1개월/3개월/커스텀)
- ✅ ETF Detail 페이지 완성 (차트 + 정보 + 뉴스)
- ✅ 차트 반응형 처리 및 성능 최적화
- ✅ 186개 테스트 통과, 커버리지 82.52%
- ✅ 프로덕션 빌드 성공 (145.57 kB gzip)

> **상세 작업 내역**: [PROGRESS.md](./PROGRESS.md) 참조

---

#### Step 6: Phase 3에서 연기된 컴포넌트 테스트 작성 ⏳ (Phase 5로 연기)

**목표**: Phase 3 Step 6에서 연기된 컴포넌트 테스트를 완료하여 전체 커버리지 70% 달성

**Note**: Phase 4에서 82.52% 커버리지를 달성했으나, 일부 컴포넌트(ETFCard 확장 테스트, Dashboard 확장 테스트 등)는 Phase 5에서 추가로 작성 예정

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

