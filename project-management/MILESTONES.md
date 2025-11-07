# 프로젝트 마일스톤

## 전체 일정

```
Phase 1: Backend Core             [=========>        ] 30%  (11/06 - 11/10)
Phase 2: Data Collection          [                  ] 0%   (11/11 - 11/15)
Phase 3: Frontend Foundation      [                  ] 0%   (11/16 - 11/20)
Phase 4: Charts & Visualization   [                  ] 0%   (11/21 - 11/25)
Phase 5: Detail & Comparison      [                  ] 0%   (11/26 - 11/30)
Phase 6: Report Generation        [                  ] 0%   (12/01 - 12/05)
Phase 7: Optimization & Deploy    [                  ] 0%   (12/06 - 12/10)
```

---

## Phase 1: Backend Core (Priority: High) 🔴

**기간**: 2025-11-06 ~ 2025-11-10 (5일)  
**상태**: ⏳ 진행 중 (30% 완료)  
**담당**: Backend

### 목표
백엔드 데이터 수집 및 기본 API 구축

### 체크리스트
- [x] FastAPI 프로젝트 초기화
- [x] 데이터베이스 스키마 생성
- [x] 기본 API 엔드포인트 구조
- [x] 종목코드 확정 (6개: ETF 4개 + 주식 2개)
- [x] 데이터 소스 확정 (Naver Finance 스크래핑)
- [ ] 1개 종목(487240) 데이터 수집 구현
- [ ] 가격 데이터 API 테스트
- [ ] 에러 핸들링 및 로깅

### 완료 조건 (Acceptance Criteria)
- ✅ API가 종목 가격 데이터를 성공적으로 반환
- ✅ 데이터가 데이터베이스에 저장됨
- ✅ Swagger 문서 (`/docs`)가 접근 가능
- ✅ 최소 1개 종목의 최근 30일 데이터 수집 완료 (Naver Finance 스크래핑)

### 진행 상황
- ✅ 프로젝트 구조 생성 (11/06)
- ✅ 문서 구조 재구성 (11/06)
- ⏳ 환경 설정 진행 중

---

## Phase 2: Data Collection Complete (Priority: High) 🟡

**기간**: 2025-11-11 ~ 2025-11-15 (5일)  
**상태**: ⏸️ 대기 중  
**담당**: Backend

### 목표
전체 6개 종목(ETF 4개 + 주식 2개)에 대한 완전한 데이터 수집 시스템 구축

### 체크리스트
- [ ] 나머지 5개 종목 데이터 수집 구현
  - [ ] 466920 (신한 SOL 조선TOP3플러스 ETF)
  - [ ] 0020H0 (KoAct 글로벌양자컴퓨팅액티브 ETF)
  - [ ] 442320 (KB RISE 글로벌원자력 iSelect ETF)
  - [ ] 042660 (한화오션)
  - [ ] 034020 (두산에너빌리티)
- [ ] 투자자별 매매 동향 데이터 수집
- [ ] 뉴스 스크래핑 구현
- [ ] 재시도 로직 (exponential backoff)
- [ ] Rate Limiting 구현 (Naver Finance 서버 부하 방지)
- [ ] 스케줄러 설정 (APScheduler)
- [ ] 히스토리 데이터 백필 (최근 1년)

### 완료 조건
- ✅ 6개 종목 모두 완전한 데이터 보유 (가격, 매매 동향, 뉴스)
- ✅ 스케줄러가 자동으로 일일 업데이트 수행
- ✅ 네트워크 실패 시 자동 재시도 작동

### 블로커
- Phase 1 완료 필요

---

## Phase 3: Frontend Foundation (Priority: High) 🟡

**기간**: 2025-11-16 ~ 2025-11-20 (5일)  
**상태**: ⏸️ 대기 중  
**담당**: Frontend

### 목표
React 앱 기본 UI 구축 및 백엔드 연동

### 체크리스트
- [ ] Vite + React 환경 설정
- [ ] TailwindCSS 및 라우팅 설정
- [ ] 레이아웃 컴포넌트 (Header, Footer)
- [ ] Dashboard 페이지 구현
- [ ] ETF 카드 컴포넌트 개선
- [ ] React Query로 백엔드 API 연결

### 완료 조건
- ✅ Dashboard에 6개 종목 카드 표시 (ETF 4개 + 주식 2개)
- ✅ 페이지 간 네비게이션 작동
- ✅ 백엔드에서 실제 데이터 로드

### 블로커
- Phase 2 완료 필요 (실제 데이터 필요)

---

## Phase 4: Charts & Visualization (Priority: Medium) 🟢

**기간**: 2025-11-21 ~ 2025-11-25 (5일)  
**상태**: ⏸️ 대기 중  
**담당**: Frontend

### 목표
인터랙티브 차트 및 시각화 구현

### 체크리스트
- [ ] 가격 차트 컴포넌트 (Recharts)
- [ ] 투자자별 매매 동향 차트
- [ ] 날짜 범위 선택기
- [ ] 반응형 차트 디자인
- [ ] 대용량 데이터 성능 테스트

### 완료 조건
- ✅ 차트가 실제 데이터로 매끄럽게 렌더링
- ✅ 인터랙티브 기능 작동 (툴팁, 줌 등)
- ✅ 모바일에서도 차트 표시

### 블로커
- Phase 3 완료 필요

---

## Phase 5: Detail & Comparison Pages (Priority: Medium) 🟢

**기간**: 2025-11-26 ~ 2025-11-30 (5일)  
**상태**: ⏸️ 대기 중  
**담당**: Full-stack

### 목표
종목 상세 페이지 및 비교 기능 완성

### 체크리스트
- [ ] 종목 Detail 페이지 구현
- [ ] 뉴스 타임라인 구현
- [ ] Comparison 페이지 구현 (6개 종목 비교)
- [ ] 정렬 가능한 데이터 테이블
- [ ] 주요 지표 패널
- [ ] ETF/주식 구분 표시

### 완료 조건
- ✅ 모든 페이지가 기능적으로 완성
- ✅ 실시간 데이터 업데이트 작동
- ✅ UI가 세련되고 사용자 친화적

### 블로커
- Phase 4 완료 필요

---

## Phase 6: Report Generation (Priority: Low) 🟣

**기간**: 2025-12-01 ~ 2025-12-05 (5일)  
**상태**: ⏸️ 대기 중  
**담당**: Backend

### 목표
리포트 다운로드 기능 추가

### 체크리스트
- [ ] Markdown 리포트 생성기
- [ ] PDF 생성 (선택사항)
- [ ] 다운로드 UI
- [ ] 리포트 생성 테스트

### 완료 조건
- ✅ 리포트 다운로드 가능
- ✅ 리포트에 모든 관련 데이터 포함
- ✅ 리포트가 잘 포맷팅됨

### 블로커
- Phase 5 완료 필요

---

## Phase 7: Optimization & Deployment (Priority: Medium) 🔵

**기간**: 2025-12-06 ~ 2025-12-10 (5일)  
**상태**: ⏸️ 대기 중  
**담당**: DevOps

### 목표
프로덕션 배포 준비 및 최적화

### 체크리스트
- [ ] 프론트엔드 번들 크기 최적화
- [ ] 로딩 상태 및 에러 바운더리 추가
- [ ] 백엔드 Dockerfile 작성
- [ ] docker-compose 설정
- [ ] 스테이징 환경 배포 테스트
- [ ] 프로덕션 배포

### 완료 조건
- ✅ Docker 컨테이너에서 앱 실행
- ✅ 성능 최적화 완료
- ✅ 프로덕션 배포 준비 완료

### 배포 플랫폼 (예정)
- Frontend: Vercel
- Backend: Render / Railway
- Database: PostgreSQL (Supabase / Neon)

---

## 전체 프로젝트 타임라인

```
Week 1 (11/06 - 11/10): Backend Core
Week 2 (11/11 - 11/17): Data Collection + Frontend Start
Week 3 (11/18 - 11/24): Charts & Visualization
Week 4 (11/25 - 12/01): Detail Pages
Week 5 (12/02 - 12/08): Reports & Optimization
Week 6 (12/09 - 12/10): Deployment
```

**예상 완료일**: 2025년 12월 10일

---

## 리스크 및 대응 계획

### 리스크 1: 데이터 수집 실패
**확률**: Low (Naver Finance 스크래핑 확정)  
**영향도**: High  
**대응**:
- ✅ Naver Finance 스크래핑으로 6개 종목 모두 수집 가능 확인
- 재시도 로직 및 에러 핸들링 철저히 구현
- HTML 구조 변경 대비 유연한 파싱 로직
- Mock 데이터로 프론트엔드 개발 병행 가능

### 리스크 2: 성능 이슈
**확률**: Medium  
**영향도**: Medium  
**대응**:
- 초기부터 캐싱 전략 수립
- 데이터베이스 인덱스 최적화
- 차트 라이브러리 성능 테스트 선행

### 리스크 3: 일정 지연
**확률**: High  
**영향도**: Medium  
**대응**:
- Phase 6 (Report)는 선택사항으로 우선순위 낮춤
- Core 기능 (Phase 1-3)에 집중
- 반복 개발로 점진적 개선

---

## 주간 회고 (Weekly Review)

### Week 1 회고 (11/06)
- **잘된 점**: 문서 구조 재구성으로 효율성 향상
- **개선할 점**: 개발 환경 설정 빠르게 진행 필요
- **다음 주 목표**: Phase 1 완료 및 Phase 2 시작

---

**Last Updated**: 2025-11-06

