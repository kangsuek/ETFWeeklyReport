# ETF Weekly Report Web Application

한국 고성장 섹터 6개 종목(ETF 4개 + 주식 2개)에 대한 종합 분석 및 리포팅 웹 애플리케이션

## 📊 대상 종목

### ETF 4개
1. **삼성 KODEX AI전력핵심설비 ETF** (487240) - AI & 전력 인프라
2. **신한 SOL 조선TOP3플러스 ETF** (466920) - 조선업
3. **KoAct 글로벌양자컴퓨팅액티브 ETF** (0020H0) - 양자컴퓨팅
4. **KB RISE 글로벌원자력 iSelect ETF** (442320) - 원자력

### 주식 2개
5. **한화오션** (042660) - 조선/방산
6. **두산에너빌리티** (034020) - 에너지/전력

---

## 🚀 로컬 실행 가이드 (Quick Start)

### 📋 사전 요구사항

| 요구사항 | 버전 | 확인 명령어 |
|---------|------|------------|
| Python | 3.11.9+ | `python3 --version` |
| Node.js | 18+ | `node --version` |
| npm | 9+ | `npm --version` |
| Git | 최신 | `git --version` |

### 🔧 한 번에 설정하기 (권장)

```bash
# 1. 프로젝트 클론
git clone https://github.com/your-repo/ETFWeeklyReport.git
cd ETFWeeklyReport

# 2. 백엔드 설정
cd backend
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env
python -m app.database

# 3. 프론트엔드 설정 (새 터미널에서)
cd ../frontend
npm install

# 4. 서버 시작 (프로젝트 루트에서)
cd ..
./scripts/start-servers.sh
```

---

## 📦 상세 설정 가이드

### Backend 설정

#### 1단계: 가상환경 생성 및 활성화

```bash
cd backend

# 가상환경 생성
python3 -m venv venv

# 가상환경 활성화
source venv/bin/activate      # macOS/Linux
# venv\Scripts\activate       # Windows
```

#### 2단계: 의존성 설치

```bash
# 개발 환경 (권장 - 테스트, 린터 포함)
pip install --upgrade pip
pip install -r requirements-dev.txt

# 운영 환경만
# pip install -r requirements.txt
```

#### 3단계: 환경 변수 설정

```bash
# .env 파일 생성
cp .env.example .env
```

`.env` 파일 내용 (필요시 수정):
```env
# 서버 설정
API_HOST=0.0.0.0
API_PORT=8000

# 데이터베이스
DATABASE_URL=sqlite:///./data/etf_data.db

# 캐시 설정
CACHE_TTL_MINUTES=5

# 뉴스 API (Naver Search API - 선택사항)
NAVER_CLIENT_ID=your_client_id
NAVER_CLIENT_SECRET=your_client_secret
```

#### 4단계: 데이터베이스 초기화

```bash
python -m app.database
```

이 명령은:
- SQLite 데이터베이스 생성 (`data/etf_data.db`)
- 6개 종목 초기 데이터 삽입

#### 5단계: 백엔드 서버 실행

```bash
# 개발 모드 (Hot Reload 활성화)
uvicorn app.main:app --reload

# 프로덕션 모드
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

#### 서버 확인
- **API 문서 (Swagger UI)**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/api/health

---

### Frontend 설정

#### 1단계: 의존성 설치

```bash
cd frontend
npm install
```

#### 2단계: 환경 변수 설정 (선택)

```bash
# .env 파일 생성 (기본값 사용 시 생략 가능)
cp .env.example .env
```

`.env` 파일 내용:
```env
VITE_API_BASE_URL=http://localhost:8000/api
VITE_APP_TITLE=ETF Weekly Report
```

#### 3단계: 개발 서버 실행

```bash
npm run dev
```

#### 서버 확인
- **웹 애플리케이션**: http://localhost:5173

---

## 🖥️ 스크립트로 한 번에 실행

### 모든 서버 시작

```bash
# 프로젝트 루트에서
./scripts/start-servers.sh
```

이 스크립트는:
- 백엔드 서버 시작 (포트 8000)
- 프론트엔드 서버 시작 (포트 5173)
- 로그 파일 생성 (`backend.log`, `frontend.log`)

### 모든 서버 종료

```bash
./scripts/stop-servers.sh
```

---

## 🧪 테스트 실행

### 백엔드 테스트

```bash
cd backend
source venv/bin/activate

# 모든 테스트 실행
pytest

# 상세 출력
pytest -v

# 커버리지 포함
pytest --cov=app --cov-report=term-missing

# HTML 커버리지 리포트
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

### 프론트엔드 테스트

```bash
cd frontend

# 테스트 실행
npm test

# 테스트 UI
npm run test:ui

# 커버리지
npm run test:coverage
```

---

## 📡 주요 API 엔드포인트

### 종목 관리
| 메서드 | 엔드포인트 | 설명 |
|--------|-----------|------|
| GET | `/api/etfs` | 전체 종목 조회 |
| GET | `/api/etfs/{ticker}` | 개별 종목 정보 |
| GET | `/api/etfs/{ticker}/prices` | 가격 데이터 |
| GET | `/api/etfs/{ticker}/trading-flow` | 매매 동향 |

### 데이터 수집
| 메서드 | 엔드포인트 | 설명 |
|--------|-----------|------|
| POST | `/api/data/collect-all` | 전체 데이터 수집 |
| POST | `/api/data/backfill` | 히스토리 백필 |
| GET | `/api/data/status` | 수집 상태 조회 |

### 뉴스
| 메서드 | 엔드포인트 | 설명 |
|--------|-----------|------|
| GET | `/api/news/{ticker}` | 종목별 뉴스 |

### cURL 예시

```bash
# 전체 종목 조회
curl http://localhost:8000/api/etfs | python3 -m json.tool

# 특정 종목 가격 데이터 조회
curl "http://localhost:8000/api/etfs/487240/prices?start_date=2025-11-01&end_date=2025-11-30"

# 데이터 수집 트리거
curl -X POST "http://localhost:8000/api/data/collect-all"
```

---

## 🛠️ 문제 해결

### 자주 발생하는 문제

#### 1. `command not found: python`
```bash
# python3 사용
python3 -m venv venv
```

#### 2. 포트가 이미 사용 중
```bash
# 백엔드 다른 포트 사용
uvicorn app.main:app --reload --port 8001

# 프론트엔드 다른 포트 사용
npm run dev -- --port 5174
```

#### 3. 패키지 설치 오류
```bash
# pip 캐시 삭제 후 재설치
pip cache purge
pip install -r requirements-dev.txt --no-cache-dir
```

#### 4. 프론트엔드 CORS 에러
백엔드가 실행 중인지 확인하세요. 백엔드는 `localhost:5173`에서의 요청을 허용하도록 설정되어 있습니다.

#### 5. 데이터베이스 초기화 실패
```bash
# 기존 DB 삭제 후 재생성
rm -f data/etf_data.db
python -m app.database
```

---

## 📚 문서

| 문서 | 설명 |
|------|------|
| [CLAUDE.md](./CLAUDE.md) | 문서 인덱스 |
| [FEATURES.md](./docs/FEATURES.md) | 제공 기능 상세 |
| [SETUP_GUIDE.md](./docs/SETUP_GUIDE.md) | 개발 환경 설정 |
| [RUNNING_GUIDE.md](./docs/RUNNING_GUIDE.md) | 실행 가이드 |
| [API_SPECIFICATION.md](./docs/API_SPECIFICATION.md) | REST API 명세 |
| [ARCHITECTURE.md](./docs/ARCHITECTURE.md) | 시스템 아키텍처 |
| [DATABASE_SCHEMA.md](./docs/DATABASE_SCHEMA.md) | DB 스키마 |
| [DEFINITION_OF_DONE.md](./docs/DEFINITION_OF_DONE.md) | 완료 기준 |
| [TODO.md](./docs/project-management/TODO.md) | 할 일 목록 |

---

## 🔧 기술 스택

### Backend
- **Framework**: FastAPI 0.104.1
- **Runtime**: Python 3.11.9
- **Database**: SQLite (개발) / PostgreSQL (프로덕션)
- **Scheduler**: APScheduler
- **Data**: Pandas, FinanceDataReader

### Frontend
- **Framework**: React 18.2.0
- **Build**: Vite 5.0.0
- **Styling**: Tailwind CSS 3.3.5
- **State**: TanStack React Query 5.8.4
- **Charts**: Recharts 2.10.3
- **Routing**: React Router DOM 6.20.0

---

## 📊 프로젝트 현황

| Phase | 상태 | 테스트 | 커버리지 |
|-------|------|--------|----------|
| Phase 1: Backend Core | ✅ 완료 | 61개 | 82% |
| Phase 2: Data Collection | ✅ 완료 | 196개 | 89% |
| Phase 3: Frontend Foundation | ✅ 완료 | - | - |
| Phase 4: Charts & Visualization | 🟢 진행 중 | - | - |

---

## 📖 데이터 소스

- **Naver Finance**: 가격 데이터, 투자자별 매매 동향
- **Naver Search API**: 뉴스 데이터

---

## 📄 라이센스

MIT License
