# 코드 품질 개선 계획

> **작성일**: 2025-01-XX  
> **목적**: 프로젝트의 코드 품질, 유지보수성, 안정성 향상을 위한 단계별 개선 계획

## 📋 개선사항 요약

### 🔴 HIGH Priority (버그 수정)
1. **에러 처리 버그** - `etfs.py:213-219` ticker 변수 미정의

### 🟡 MEDIUM Priority (기능 완성도)
2. **불완전한 구현** - `data_collector.py:446` TODO 주석 제거
3. **하드코딩된 값 개선** - 설정값 상수화
4. **에러 메시지 일관성 부족** - 표준화된 에러 메시지 체계
5. **API 타임아웃 처리 개선** - 엔드포인트별 차등 타임아웃
6. **날짜 범위 검증 불일치** - 프론트엔드/백엔드 검증 통일

### 🔵 LOW Priority (코드 품질/유지보수성)
7. **중복 코드 리팩토링** - 재사용 가능한 컴포넌트 추출
8. **타입 안정성 개선** - PropTypes 추가
9. **컴포넌트 크기 개선** - 대형 컴포넌트 분리
10. **매직 넘버 상수화** - 하드코딩 숫자 상수화
11. **코드 주석 품질** - 한글/영어 통일, 복잡한 로직 주석
12. **로깅 개선** - 구조화된 로깅 도입
13. **성능 최적화** - 메모이제이션, DB 벌크 insert

---

## 🔴 Phase 6.1: 버그 수정 (HIGH Priority)

### 목표
프로덕션에 영향을 주는 버그를 즉시 수정

### 작업 항목

#### 6.1.1 에러 처리 버그 수정 ✅
**파일**: `backend/app/routers/etfs.py:213-219`

**문제점**:
```python
except sqlite3.Error as e:
    logger.error(f"Database error fetching ETF {ticker}: {e}")  # ticker 변수 미정의
```

**해결 방안**:
- `etf` 객체에서 `ticker` 속성 사용
- 또는 예외 처리 블록에서 `etf.ticker` 사용

**작업 내용**:
- [x] `get_etf` 함수의 예외 처리 블록 수정
  - `ticker` → `etf.ticker`로 변경 (213-214줄)
  - 모든 예외 처리 블록에서 `etf.ticker` 사용 확인
- [x] 테스트 작성 (에러 케이스)
- [x] 린트 에러 확인

**예상 소요 시간**: 30분
**실제 소요 시간**: 완료

**테스트 계획**:
- 데이터베이스 에러 발생 시나리오 테스트
- ValidationException 발생 시나리오 테스트

---

## 🟡 Phase 6.2: 기능 완성도 개선 (MEDIUM Priority)

### 목표
불완전한 구현 완성 및 설정값 관리 개선

### 작업 항목

#### 6.2.1 TODO 주석 제거 및 구현 완성 ✅
**파일**: `backend/app/services/data_collector.py:446`

**문제점**:
```python
def get_price_data(self, ticker: str, start_date: date, end_date: date) -> List[PriceData]:
    """Get price data for date range"""
    # TODO: Implement actual data collection from Naver Finance
```

**해결 방안**:
- TODO 주석 제거 (이미 DB에서 조회하는 구현이 완료됨)
- 주석을 실제 동작에 맞게 수정

**작업 내용**:
- [x] TODO 주석 제거
- [x] 주석을 실제 동작 설명으로 수정
  - DB에서 가격 데이터를 조회하는 것으로 주석 수정
- [x] `get_trading_flow` 메서드도 동일하게 확인

**예상 소요 시간**: 15분
**실제 소요 시간**: 완료

#### 6.2.2 하드코딩된 값 상수화 ✅
**파일들**:
- `backend/app/config.py:32-34` - SCRAPING_INTERVAL (이미 환경변수로 관리됨)
- `frontend/src/services/api.js:9` - 타임아웃 60초
- 컴포넌트 전반 - 색상 코드

**작업 내용**:

**백엔드**:
- [x] `backend/app/constants.py`에 Rate Limiter interval 상수 추가
  - `DEFAULT_RATE_LIMITER_INTERVAL = 0.5` (기본 스크래핑)
  - `NEWS_RATE_LIMITER_INTERVAL = 0.1` (뉴스 API)
- [x] Rate limiter interval (0.5초) 상수화
  - `data_collector.py`: `0.5` → `DEFAULT_RATE_LIMITER_INTERVAL`
  - `ticker_scraper.py`: `0.5` → `DEFAULT_RATE_LIMITER_INTERVAL`
  - `news_scraper.py`: `0.1` → `NEWS_RATE_LIMITER_INTERVAL`

**프론트엔드**:
- [x] `frontend/src/constants.js` 생성
- [x] API 타임아웃 상수 정의
  - `DEFAULT_API_TIMEOUT = 60000` (60초)
  - `FAST_API_TIMEOUT = 10000` (10초)
  - `NORMAL_API_TIMEOUT = 30000` (30초)
  - `LONG_API_TIMEOUT = 60000` (60초)
- [x] 색상 코드를 `constants.js`로 이동
  - `COLORS` 객체 생성 (가격 변동, 순매수/순매도, 차트 색상 등)
  - `CHART_COLOR_PALETTE` 배열 생성
- [x] 하드코딩된 색상 코드 교체
  - `api.js`: 타임아웃 상수화
  - `format.js`: 색상 코드 → `COLORS` 상수
  - `PriceChart.jsx`: 모든 하드코딩 색상 → `COLORS` 상수
  - `TradingFlowChart.jsx`: 모든 하드코딩 색상 → `COLORS` 상수
  - `ETFCard.jsx`: 캔들스틱 색상 → `COLORS` 상수
  - `NormalizedPriceChart.jsx`: 색상 팔레트 → `CHART_COLOR_PALETTE`

**예상 소요 시간**: 2시간
**실제 소요 시간**: 완료

#### 6.2.3 에러 메시지 일관성 개선 ✅
**문제점**:
- 한글/영어 혼용
- 상세도 불일치
- 표준화된 에러 메시지 체계 부재

**작업 내용**:

**백엔드**:
- [x] `backend/app/constants.py`에 에러 메시지 상수 정의
- [x] 에러 메시지 템플릿 생성 (한글 표준)
- [x] 모든 라우터에서 표준 에러 메시지 사용 (`etfs.py`, `data.py`, `news.py`)
- [x] 에러 카테고리별 상수 정의 (데이터베이스, 검증, 리소스, 외부 서비스, 일반 서버 에러)

**프론트엔드**:
- [x] `frontend/src/constants.js`에 `ERROR_MESSAGES` 객체 추가
- [x] API 에러 응답을 사용자 친화적 메시지로 매핑 (`api.js` 인터셉터)
- [x] 타임아웃 에러 감지 및 처리 개선

**에러 메시지 카테고리**:
```python
# 백엔드 예시
ERROR_DATABASE = "데이터베이스 오류가 발생했습니다."
ERROR_VALIDATION_DATE_RANGE = "날짜 범위가 올바르지 않습니다."
ERROR_SCRAPER = "데이터 소스에 일시적으로 접근할 수 없습니다."
# ...
```

**예상 소요 시간**: 3시간
**실제 소요 시간**: 완료

#### 6.2.4 API 타임아웃 처리 개선 ✅
**파일**: `frontend/src/services/api.js`

**현재 상태**:
- 모든 API에 60초 동일 타임아웃 적용

**개선 방안**:
- 엔드포인트별 차등 타임아웃
- 자동 수집 API: 60초 (긴 작업)
- 일반 조회 API: 30초
- 빠른 조회 API: 10초

**작업 내용**:
- [x] 타임아웃 상수 정의 (`constants.js`)
  - `FAST_API_TIMEOUT = 10000` (10초)
  - `NORMAL_API_TIMEOUT = 30000` (30초)
  - `LONG_API_TIMEOUT = 60000` (60초)
- [x] 엔드포인트별 타임아웃 설정
  - 빠른 조회: `/etfs/`, `/etfs/{ticker}`, `/data/status`, `/health`
  - 일반 조회: 가격/매매동향/뉴스 조회, 종목 비교
  - 긴 작업: 데이터 수집, 백필, 초기화
- [x] 타임아웃 에러 처리 개선 (타임아웃 감지 및 사용자 친화적 메시지)
- [x] 사용자에게 적절한 피드백 제공

**예상 소요 시간**: 1시간
**실제 소요 시간**: 완료

#### 6.2.5 날짜 범위 검증 통일 ✅
**문제점**:
- 백엔드: 최대 365일 검증
- 프론트엔드: 검증 없음

**작업 내용**:
- [x] 프론트엔드에 날짜 범위 검증 추가
- [x] `frontend/src/utils/validation.js` 생성
  - `validateDateRange()` 함수 구현
  - `isValidDateFormat()` 함수 구현
- [x] DateRangeSelector에 검증 로직 추가
  - 기존 하드코딩된 검증 로직을 `validateDateRange()`로 교체
- [x] 백엔드와 동일한 검증 규칙 적용
  - `MAX_DATE_RANGE_DAYS = 365` 상수 사용
- [x] 사용자에게 명확한 에러 메시지 표시

**검증 규칙**:
- 최대 조회 기간: 365일
- 시작일 <= 종료일
- 과거 날짜만 허용 (미래 날짜 제한)

**예상 소요 시간**: 1.5시간
**실제 소요 시간**: 완료

---

## 🔵 Phase 6.3: 코드 품질 개선 (LOW Priority)

### 목표
코드 유지보수성 및 가독성 향상

### 작업 항목

#### 6.3.1 중복 코드 리팩토링 ✅
**대상 파일들**:
- `frontend/src/pages/ETFDetail.jsx` - ErrorFallback, NewsTimeline

**작업 내용**:
- [x] `ErrorFallback` 컴포넌트를 `components/common/ErrorFallback.jsx`로 추출
- [x] `NewsTimeline` 컴포넌트를 `components/news/NewsTimeline.jsx`로 추출
- [x] 추출된 컴포넌트에 PropTypes 추가
- [x] 추출된 컴포넌트에 대한 테스트 작성 (ErrorFallback: 5개, NewsTimeline: 7개)
- [x] ETFDetail.jsx에서 추출된 컴포넌트 import 및 사용
- [x] 기존 테스트 파일 업데이트 및 통과 확인
- [x] 백엔드 에러 핸들링 패턴 확인 (이미 통일되어 있음 - 6.2.3에서 완료)

**예상 소요 시간**: 2시간
**실제 소요 시간**: 완료

#### 6.3.2 타입 안정성 개선 ✅
**단기 계획 (PropTypes)**:
- [x] prop-types 패키지 설치
- [x] 주요 컴포넌트에 PropTypes 추가
  - PageHeader, LoadingIndicator, Spinner
  - DateRangeSelector, PriceChart, TradingFlowChart
  - ETFCard, ETFHeader, ETFCharts
  - DashboardFilters, ETFCardGrid
- [x] 필수 prop 검증
- [x] 기본값 설정

**장기 계획 (TypeScript)**:
- Phase 7에서 TypeScript 마이그레이션 검토

**예상 소요 시간**: 4시간 (PropTypes)
**실제 소요 시간**: 완료

#### 6.3.3 컴포넌트 크기 개선 ✅
**대상 파일들**:
- `ETFDetail.jsx` - 517줄 → 약 320줄로 감소
- `Dashboard.jsx` - 384줄 → 약 305줄로 감소

**작업 내용**:
- [x] `ETFDetail.jsx` 분리 완료
  - Header 섹션 → `components/etf/ETFHeader.jsx` (PropTypes 포함)
  - Charts 섹션 → `components/etf/ETFCharts.jsx` (PropTypes 포함)
  - Stats 섹션은 이미 `StatsSummary` 컴포넌트로 분리되어 있음
- [x] `Dashboard.jsx` 분리 완료
  - 필터 섹션 → `components/dashboard/DashboardFilters.jsx` (PropTypes 포함)
  - 카드 그리드 → `components/dashboard/ETFCardGrid.jsx` (PropTypes 포함)
- [x] 분리된 컴포넌트에 PropTypes 추가
- [x] 테스트 작성 및 통과 확인 (14개 테스트 통과)

**예상 소요 시간**: 4시간
**실제 소요 시간**: 완료

#### 6.3.4 매직 넘버 상수화
**대상**:
- Rate limiter interval (0.5초)
- 차트 샘플링 최대 포인트 (200개)
- 페이지네이션 기본값
- 기타 하드코딩 숫자

**작업 내용**:
- [ ] `backend/app/constants.py`에 상수 추가
- [ ] `frontend/src/constants.js`에 상수 추가
- [ ] 모든 매직 넘버를 상수로 교체

**예상 소요 시간**: 1.5시간

#### 6.3.5 코드 주석 품질 개선
**문제점**:
- 한글/영어 혼용
- 복잡한 로직에 주석 부족

**작업 내용**:
- [ ] 주석 언어 통일 (비즈니스 로직: 한글, 기술 용어: 영어)
- [ ] 복잡한 알고리즘에 상세 주석 추가
- [ ] 함수/클래스 docstring 표준화
- [ ] TODO/FIXME 주석 정리

**예상 소요 시간**: 3시간

#### 6.3.6 로깅 개선
**작업 내용**:
- [ ] 구조화된 로깅 도입 (JSON 포맷)
- [ ] 로그 레벨 일관성 확보
- [ ] 로그 컨텍스트 추가 (request_id, user_id 등)
- [ ] 프로덕션/개발 환경별 로그 레벨 설정

**예상 소요 시간**: 2시간

#### 6.3.7 성능 최적화
**작업 내용**:
- [ ] Dashboard 정렬 로직 메모이제이션
- [ ] DB 벌크 insert 개선 (현재 개별 insert)
- [ ] React 컴포넌트 메모이제이션 검토
- [ ] 불필요한 리렌더링 방지

**예상 소요 시간**: 3시간

---

## 📅 실행 계획

### Phase 6.1: 버그 수정 (1주차)
- **목표**: 프로덕션 버그 즉시 수정
- **예상 소요**: 1일
- **우선순위**: 🔴 HIGH

### Phase 6.2: 기능 완성도 개선 (1-2주차)
- **목표**: 불완전한 구현 완성 및 설정값 관리
- **예상 소요**: 1-2주
- **우선순위**: 🟡 MEDIUM

### Phase 6.3: 코드 품질 개선 (2-4주차)
- **목표**: 유지보수성 및 가독성 향상
- **예상 소요**: 2-3주
- **우선순위**: 🔵 LOW

---

## ✅ Definition of Done

각 작업 항목은 다음을 만족해야 합니다:

1. **코드 작성 및 동작 확인**
2. **테스트 작성 및 100% 통과** (버그 수정, 기능 추가 시)
3. **린트 에러 없음**
4. **문서 업데이트** (API 변경, 상수 추가 시)
5. **코드 리뷰** (선택적)

---

## 📊 진행 상황 추적

각 Phase별로 TODO.md에 작업 항목을 추가하고, 완료 시 체크박스를 업데이트합니다.

---

## 🔗 관련 문서

- [TODO.md](./TODO.md) - 전체 작업 목록
- [DEFINITION_OF_DONE.md](../DEFINITION_OF_DONE.md) - 완료 기준
- [DEVELOPMENT_GUIDE.md](../DEVELOPMENT_GUIDE.md) - 개발 가이드

