# Phase 2 최적화 상세 계획

## 문서별 최적화 내용 분석

### 1. ARCHITECTURE.md (현재: 272줄 → 목표: ~200줄, 26% 감소)

#### 최적화 가능한 내용

**1. 종목 목록 중복 제거** (135-140줄)
```markdown
현재:
- 487240: KODEX AI전력핵심설비
- 466920: SOL 조선TOP3플러스
- 0020H0: 글로벌양자컴퓨팅액티브
- 442320: RISE 글로벌원자력 iSelect
- 042660: 한화오션
- 034020: 두산에너빌리티

최적화 후:
- 대상: 6개 종목 (ETF 4개 + 주식 2개)
- 상세 목록: README.md 참조
```

**2. 구현된 기능 목록 축약** (159-166줄)
```markdown
현재:
- ✅ Naver Finance 스크래핑 (`fetch_naver_finance_prices`)
- ✅ 데이터 검증 (`validate_price_data`)
- ✅ 데이터 정제 (`clean_price_data`)
- ✅ 데이터베이스 저장 (`save_price_data`)
- ✅ 통합 수집 함수 (`collect_and_save_prices`)
- ✅ API 엔드포인트 (POST `/api/etfs/{ticker}/collect`)
- ✅ 61개 테스트 100% 통과

최적화 후:
- ✅ Phase 1 완료: Naver Finance 스크래핑, 데이터 검증/정제, API 엔드포인트
- 상세 내용: PROGRESS.md 참조
```

**3. 코드 예시 제거** (255-262줄)
```markdown
현재:
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

최적화 후:
- 로깅 설정: DEVELOPMENT_GUIDE.md 참조
```

**4. 디렉토리 구조 간소화** (31-53줄, 74-102줄)
- 주요 파일만 나열
- 상세 구조는 코드베이스 참조

**예상 절감**: 72줄 → **~200줄로 축소**

---

### 2. TECH_STACK.md (현재: 267줄 → 목표: ~200줄, 25% 감소)

#### 최적화 가능한 내용

**1. 환경 변수 예시 축약** (184-211줄)
```markdown
현재:
```bash
# API 설정
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# 데이터베이스
DATABASE_URL=sqlite:///./data/etf_data.db

# 데이터 수집
CACHE_TTL_MINUTES=10
NEWS_MAX_RESULTS=5

# 선택사항: 외부 API
NAVER_CLIENT_ID=your_client_id
NAVER_CLIENT_SECRET=your_client_secret
```

최적화 후:
- 주요 환경 변수: API_HOST, API_PORT, DATABASE_URL, NAVER_CLIENT_ID
- 상세 설정: SETUP_GUIDE.md 참조
```

**2. 의존성 설치 가이드 제거** (215-233줄)
```markdown
현재:
### 백엔드
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

최적화 후:
- 설치 방법: SETUP_GUIDE.md 참조
```

**3. 선택 기준 설명 축약** (140-181줄)
- 각 기술의 장점을 간단히만 나열
- 상세 비교는 제거

**4. 향후 고려 기술 축약** (245-262줄)
- 체크리스트만 유지
- 설명 제거

**예상 절감**: 67줄 → **~200줄로 축소**

---

### 3. DEVELOPMENT_GUIDE.md (현재: 476줄 → 목표: ~350줄, 26% 감소)

#### 최적화 가능한 내용

**1. 코드 예시 축약** (여러 곳)
- 현재: 완전한 코드 예시 (16-53줄, 76-113줄, 281-297줄 등)
- 최적화: 핵심 패턴만 보여주고, 상세 예시는 코드베이스 참조

**예시 1: Python 함수 예시** (16-53줄)
```markdown
현재: 38줄의 완전한 코드 예시
최적화 후: 핵심 패턴만 (타입 힌트, docstring, 에러 처리)
```

**예시 2: React 컴포넌트 예시** (76-113줄)
```markdown
현재: 38줄의 완전한 컴포넌트 예시
최적화 후: 핵심 패턴만 (useQuery, 로딩/에러 처리)
```

**예시 3: 테스트 코드 예시** (281-297줄, 302-317줄)
```markdown
현재: 완전한 테스트 코드
최적화 후: 테스트 구조만 (Given-When-Then 패턴)
```

**2. 성능 최적화 예시 축약** (372-419줄)
- 코드 예시 제거
- 원칙만 나열

**3. 한국어 처리 섹션 축약** (423-459줄)
- 핵심 포맷팅 함수만
- 상세 예시 제거

**예상 절감**: 126줄 → **~350줄로 축소**

---

### 4. DEFINITION_OF_DONE.md (현재: 410줄 → 목표: ~300줄, 26% 감소)

#### 최적화 가능한 내용

**1. 완료된 Phase 1 상세 체크리스트 축약** (67-113줄)
```markdown
현재:
#### 기능 요구사항
- [x] FastAPI 서버가 정상적으로 실행됨 ✅
- [x] 데이터베이스 연결 및 초기 데이터 로드 완료 ✅ (6개 종목)
- [x] 최소 1개 종목(487240)의 가격 데이터 수집 성공 ✅ (모든 6개 종목 확인)
- [x] GET /api/etfs 엔드포인트 정상 응답 ✅
- [x] POST /api/etfs/{ticker}/collect 엔드포인트 구현 ✅ (NEW)

#### 테스트 요구사항 (필수)
- [x] **data_collector.py 유닛 테스트** (43개 테스트) ✅
  - [x] `fetch_naver_finance_prices()` 테스트 ✅
  - [x] `validate_price_data()` 테스트 (12개) ✅
  - [x] `clean_price_data()` 테스트 (5개) ✅
  - [x] `save_price_data()` 테스트 ✅
  - [x] 에러 핸들링 테스트 (11개) ✅
- [x] **API 엔드포인트 통합 테스트** (18개 테스트) ✅
  - [x] GET /api/health 테스트 ✅
  - [x] GET /api/etfs 테스트 ✅
  - [x] GET /api/etfs/{ticker} 테스트 ✅
  - [x] GET /api/etfs/{ticker}/prices 테스트 ✅
  - [x] POST /api/etfs/{ticker}/collect 테스트 ✅
- [x] **모든 테스트 통과율 100%** ✅ (61개 테스트)

최적화 후:
### ✅ Phase 1: Backend Core - 완료 (2025-11-07)
- ✅ FastAPI 서버, 데이터베이스 연결, API 엔드포인트 5개
- ✅ 61개 테스트 100% 통과, 커버리지 82%
- 상세 내용: PROGRESS.md 참조
```

**2. Phase 2-7 체크리스트 간소화** (116-278줄)
- 현재 Phase만 상세히
- 나머지 Phase는 핵심 요구사항만

**3. 테스트 정책 섹션 축약** (282-313줄)
- 핵심 원칙만 유지
- 코드 예시 제거

**4. 체크리스트 사용 방법 간소화** (378-395줄)
- 핵심 단계만

**예상 절감**: 110줄 → **~300줄로 축소**

---

## 최적화 원칙

### 제거할 내용
1. ✅ **중복 정보**: 종목 목록, 환경 변수 상세 예시
2. ✅ **완료된 Phase 상세 내용**: 요약만 유지
3. ✅ **과도한 코드 예시**: 핵심 패턴만
4. ✅ **설치 가이드**: SETUP_GUIDE.md 참조
5. ✅ **상세 설명**: 원칙만 유지

### 유지할 내용
1. ✅ **핵심 아키텍처 다이어그램**
2. ✅ **기술 스택 목록 및 버전**
3. ✅ **코딩 규칙 및 원칙**
4. ✅ **현재/다음 Phase 체크리스트**
5. ✅ **테스트 정책 핵심 원칙**

---

## 예상 효과

### 줄 수 절감
| 문서 | 최적화 전 | 최적화 후 | 감소율 |
|------|----------|----------|--------|
| **ARCHITECTURE.md** | 272줄 | 200줄 | **26% 감소** |
| **TECH_STACK.md** | 267줄 | 200줄 | **25% 감소** |
| **DEVELOPMENT_GUIDE.md** | 476줄 | 350줄 | **26% 감소** |
| **DEFINITION_OF_DONE.md** | 410줄 | 300줄 | **26% 감소** |
| **합계** | 1,425줄 | 1,050줄 | **26% 감소** |

### 토큰 수 절감
- **최적화 전**: 약 1,425줄 × 4 토큰/줄 = **약 5,700 토큰**
- **최적화 후**: 약 1,050줄 × 4 토큰/줄 = **약 4,200 토큰**
- **절감**: 약 **1,500 토큰 (26% 감소)**

---

## Phase 1 + Phase 2 총 효과

### 전체 문서 최적화 효과
- **Phase 1**: 1,175줄 → 980줄 (17% 감소)
- **Phase 2**: 1,425줄 → 1,050줄 (26% 감소)
- **총합**: 2,600줄 → 2,030줄 (**22% 감소**)

### 토큰 수 총 절감
- **최적화 전**: 약 10,400 토큰
- **최적화 후**: 약 8,120 토큰
- **절감**: 약 **2,280 토큰 (22% 감소)**

---

**작성일**: 2025-11-09

