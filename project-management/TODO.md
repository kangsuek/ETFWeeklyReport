# TODO List

> **⚠️ 중요**: 각 Phase는 테스트 100% 완료 후 다음 단계로 진행합니다.  
> 자세한 완료 기준은 **[Definition of Done](../docs/DEFINITION_OF_DONE.md)** 참조

---

## 🔴 Phase 1: Backend Core (Priority: High) - 진행 중

**목표**: 데이터 수집 및 기본 API 구축

**Acceptance Criteria (다음 Phase 진행 조건):**
- ✅ FastAPI 서버 정상 실행
- ✅ 최소 1개 ETF 데이터 수집 성공
- ✅ **유닛 테스트 100% 통과**
- ✅ **통합 테스트 100% 통과**
- ✅ API 문서 업데이트

### 완료
- [x] FastAPI 프로젝트 구조 생성
- [x] 데이터베이스 스키마 설계
- [x] 기본 API 엔드포인트 구조 생성
- [x] 라우터 및 서비스 레이어 분리

### 완료 (최근)
- [x] 백엔드 환경 설정 및 실행 확인
  - [x] Python 가상환경 생성
  - [x] 패키지 설치 (83개 패키지)
  - [x] 데이터베이스 초기화 (4개 ETF)
  - [x] FastAPI 서버 실행 테스트 ✅

### 진행 중
- [ ] ETF 데이터 수집 구현 (1개 ETF로 시작: 480450)
  - [ ] FinanceDataReader를 사용한 가격 데이터 수집
  - [ ] 네이버 증권 스크래핑 (필요 시)
  - [ ] 데이터베이스 저장 로직
  - [ ] API 엔드포인트 연결 및 테스트
  - [ ] **유닛 테스트 작성 (data_collector.py)**
  - [ ] **통합 테스트 작성 (API 엔드포인트)**
  - [ ] **모든 테스트 100% 통과 확인**
- [ ] 에러 핸들링 및 로깅 추가
  - [ ] **에러 핸들링 테스트 작성**
- [ ] 데이터 검증 로직 구현
  - [ ] **데이터 검증 테스트 작성**

---

## 🟡 Phase 2: Data Collection Complete (Priority: High)

**목표**: 전체 4개 ETF 데이터 수집 확장

**Acceptance Criteria (다음 Phase 진행 조건):**
- ✅ 4개 ETF 모두 데이터 수집 성공
- ✅ 스케줄러 정상 작동
- ✅ **각 데이터 수집 모듈 테스트 100% 통과**
- ✅ **재시도 로직 테스트 통과**
- ✅ 데이터 정합성 확인

**⚠️ Phase 1 완료 필수 (테스트 100% 통과 포함)**

- [ ] 나머지 3개 ETF 데이터 수집 확장
  - [ ] 456600 (SOL 조선TOP3플러스)
  - [ ] 497450 (KOACT 글로벌양자컴퓨팅액티브)
  - [ ] 481330 (KBSTAR 글로벌원자력 iSelect)
- [ ] 투자자별 매매 동향 데이터 수집
  - [ ] 개인/기관/외국인 순매수 데이터
  - [ ] 데이터베이스 저장
- [ ] 뉴스 스크래핑 구현
  - [ ] 네이버 뉴스 검색
  - [ ] 테마별 키워드 필터링
  - [ ] 관련도 점수 계산
- [ ] 재시도 로직 및 Rate Limiting
- [ ] 스케줄러 설정 (APScheduler)
  - [ ] 일일 데이터 업데이트 (장 마감 후)
  - [ ] 히스토리 데이터 백필

---

## 🟡 Phase 3: Frontend Foundation (Priority: High)

**목표**: React 앱 기본 UI 구축

**Acceptance Criteria (다음 Phase 진행 조건):**
- ✅ Dashboard에 4개 ETF 표시
- ✅ 백엔드 API 연동 성공
- ✅ **컴포넌트 테스트 100% 통과**
- ✅ **API 연동 테스트 통과**
- ✅ 크로스 브라우저 테스트 완료

**⚠️ Phase 2 완료 필수 (테스트 100% 통과 포함)**

- [ ] 프론트엔드 환경 설정
  - [ ] npm 패키지 설치
  - [ ] Vite 개발 서버 실행 테스트
  - [ ] 백엔드 API 연결 확인
- [ ] Dashboard 페이지 구현
  - [ ] ETF 목록 조회 및 표시
  - [ ] ETF 카드 컴포넌트 개선
  - [ ] 로딩 상태 처리
  - [ ] 에러 처리
- [ ] 레이아웃 개선
  - [ ] Header 네비게이션 개선
  - [ ] Footer 정보 추가
  - [ ] 반응형 디자인 적용

---

## 🟢 Phase 4: Charts & Visualization (Priority: Medium)

**목표**: 인터랙티브 차트 구현

- [ ] 가격 차트 컴포넌트
  - [ ] Recharts LineChart 구현
  - [ ] 거래량 BarChart 추가
  - [ ] 툴팁 및 레전드 커스터마이징
- [ ] 투자자별 매매 동향 차트
  - [ ] StackedBarChart 구현
  - [ ] 색상 구분 (개인/기관/외국인)
- [ ] 날짜 범위 선택기
  - [ ] 7일/1개월/3개월/커스텀
  - [ ] date-fns로 날짜 처리
- [ ] 차트 반응형 처리
- [ ] 성능 최적화 (대용량 데이터)

---

## 🟢 Phase 5: Detail & Comparison Pages (Priority: Medium)

**목표**: ETF 상세 페이지 및 비교 기능 완성

- [ ] ETF Detail 페이지
  - [ ] 가격 차트 통합
  - [ ] 주요 지표 패널
  - [ ] 일별 데이터 테이블 (정렬/필터링)
  - [ ] 뉴스 타임라인
- [ ] Comparison 페이지
  - [ ] 4개 ETF 성과 비교 테이블
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

**Last Updated**: 2025-11-06

