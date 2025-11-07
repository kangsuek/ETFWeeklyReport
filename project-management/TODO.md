# TODO List

> **⚠️ 중요**: 각 Phase는 테스트 100% 완료 후 다음 단계로 진행합니다.  
> 자세한 완료 기준은 **[Definition of Done](../docs/DEFINITION_OF_DONE.md)** 참조

---

## ✅ Phase 1: Backend Core (Priority: High) - 완료

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

### ✅ 완료 - 데이터 수집 및 API 구현

**🎯 목표**: 1개 종목(487240)의 가격 데이터 수집 및 저장 완성 - **Naver Finance 스크래핑 사용** ✅

#### Step 1: 데이터 수집 기능 설계 ✅ (완료: 30분)
- [x] data_collector.py 현재 구조 리뷰 ✅
- [x] Naver Finance 스크래핑 방식 확정 ✅
  - URL: `https://finance.naver.com/item/sise_day.naver?code={종목코드}`
  - 6개 종목 코드: 487240, 466920, 0020H0, 442320, 042660, 034020
- [x] 수집할 데이터 필드 확정 ✅ (날짜, 시가, 고가, 저가, 종가, 거래량, 등락률)
- [x] 날짜 범위 처리 로직 설계 ✅ (기본 10일)

#### Step 2: 가격 데이터 수집 구현 ✅ (완료: 1.5시간)
- [x] Naver Finance 스크래핑 함수 구현
  - [x] requests + BeautifulSoup4로 HTML 파싱
  - [x] `table.type2`에서 데이터 행 추출
  - [x] 날짜/종가/시가/고가/저가/거래량/등락률 파싱
- [x] 파싱 데이터 → PriceData 모델 변환
- [x] 날짜 범위 파라미터 처리 (기본 10일치 데이터)
- [x] 기본 에러 처리 (네트워크 오류, HTML 구조 변경)
- [x] **유닛 테스트 작성** (test_data_collection) - 12개 테스트 모두 통과 ✅

#### Step 3: 데이터 검증 및 정제 ✅ (완료: 45분)
- [x] 데이터 유효성 검증 (가격 > 0, 거래량 >= 0) ✅
  - [x] 필수 필드 검증 (ticker, date, close_price)
  - [x] 날짜 타입 검증
  - [x] 가격/거래량 범위 검증
  - [x] 고가/저가/시가/종가 관계 검증
- [x] 결측치 처리 로직 (None 값 처리) ✅
  - [x] 누락된 가격 필드를 None으로 처리
  - [x] 누락된 거래량을 0으로 처리
- [x] 데이터 타입 변환 및 정규화 ✅
  - [x] 가격 필드 소수점 2자리 반올림
  - [x] 거래량 정수 변환
  - [x] 등락률 소수점 2자리 반올림
- [x] **유닛 테스트 작성** (19개 테스트 모두 통과 ✅)

#### Step 4: 데이터베이스 저장 로직 ✅ (이미 완료: Step 2에서 구현됨)
- [x] prices 테이블 INSERT 함수 구현 ✅ (save_price_data)
- [x] 중복 데이터 처리 (UPSERT: INSERT OR REPLACE) ✅
- [x] 트랜잭션 관리 및 롤백 처리 ✅
- [x] 저장 성공/실패 로깅 ✅
- [x] **유닛 테스트 작성** ✅ (test_save_price_data, test_save_price_data_with_invalid_data 등)

#### Step 5: API 엔드포인트 통합 ✅ (완료: 45분)
- [x] GET /api/etfs/{ticker}/prices 구현 ✅
  - [x] ETF/Stock 존재 확인
  - [x] 날짜 범위 파라미터 처리
  - [x] 404 에러 처리 (존재하지 않는 ticker)
- [x] POST /api/etfs/{ticker}/collect 구현 ✅ (새로운 엔드포인트)
  - [x] Naver Finance 데이터 수집 트리거
  - [x] 수집 결과 반환
- [x] data_collector와 라우터 연결 ✅
- [x] 에러 핸들링 (404, 500) 및 HTTP 상태 코드 ✅
  - [x] 404: ETF/Stock not found
  - [x] 500: Internal server error
  - [x] 422: Validation error
- [x] 로깅 추가 (수집 시작/완료/실패) ✅
- [x] **통합 테스트 작성** (18개 테스트 모두 통과 ✅)
  - [x] Health check 테스트 (2개)
  - [x] ETF 엔드포인트 테스트 (3개)
  - [x] Price 엔드포인트 테스트 (4개)
  - [x] Collect 엔드포인트 테스트 (4개)
  - [x] 에러 핸들링 테스트 (3개)
  - [x] End-to-End 통합 테스트 (2개)

#### Step 6: 종합 테스트 및 검증 ✅ (완료: 30분)
- [x] 전체 테스트 실행 (`pytest -v`) ✅
  - **61개 테스트 모두 통과** ✅
  - 43개 유닛 테스트
  - 18개 API 통합 테스트
- [x] 커버리지 확인 (`pytest --cov=app`) ✅
  - **전체 커버리지: 82%**
  - data_collector.py: 90%
  - database.py: 100%
  - models.py: 100%
- [x] **모든 테스트 100% 통과** ✅ ⚠️
- [x] API 문서 업데이트 (Swagger UI 자동 생성) ✅
- [x] 수동 테스트 (Swagger UI에서 확인) ✅
  - http://localhost:8000/docs
  - 6개 종목 데이터 수집 성공 확인

---

## 🟡 Phase 2: Data Collection Complete (Priority: High)

**목표**: 전체 6개 종목 데이터 수집 확장 (ETF 4개 + 주식 2개)

**Acceptance Criteria (다음 Phase 진행 조건):**
- ✅ 6개 종목 모두 데이터 수집 성공
- ✅ 스케줄러 정상 작동
- ✅ **각 데이터 수집 모듈 테스트 100% 통과**
- ✅ **재시도 로직 테스트 통과**
- ✅ 데이터 정합성 확인

**⚠️ Phase 1 완료 필수 (테스트 100% 통과 포함)**

- [ ] 나머지 5개 종목 데이터 수집 확장
  - [ ] 466920 (신한 SOL 조선TOP3플러스 ETF)
  - [ ] 0020H0 (KoAct 글로벌양자컴퓨팅액티브 ETF)
  - [ ] 442320 (KB RISE 글로벌원자력 iSelect ETF)
  - [ ] 042660 (한화오션)
  - [ ] 034020 (두산에너빌리티)
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
- ✅ Dashboard에 6개 종목 표시 (ETF 4개 + 주식 2개)
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
  - [ ] 종목 목록 조회 및 표시 (ETF/주식 구분)
  - [ ] 종목 카드 컴포넌트 개선
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

**Last Updated**: 2025-11-06

