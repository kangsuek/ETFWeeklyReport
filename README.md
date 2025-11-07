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

## 🚀 빠른 시작

### 사전 요구사항

- Python 3.10+
- Node.js 18+
- npm 또는 yarn

### 백엔드 설정

```bash
cd backend

# 1. 가상환경 생성
python -m venv venv

# 2. 가상환경 활성화
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 의존성 설치
pip install -r requirements-dev.txt  # 개발환경 (테스트, 린터 포함)
# 또는
pip install -r requirements.txt      # 운영환경만

# 4. 환경변수 설정
cp .env.example .env  # .env 파일을 편집하여 설정 변경

# 5. 데이터베이스 초기화
python -m app.database

# 6. 개발 서버 실행
uvicorn app.main:app --reload
```

백엔드 실행: http://localhost:8000  
API 문서 (Swagger): http://localhost:8000/docs  
API 문서 (ReDoc): http://localhost:8000/redoc

### 프론트엔드 설정

```bash
cd frontend
npm install
npm run dev
```

프론트엔드 실행: http://localhost:5173

### Docker로 실행

```bash
docker-compose up --build
```

## 📚 문서

### 시작하기
- **[CLAUDE.md](./CLAUDE.md)** - 프로젝트 문서 인덱스 (여기서 시작하세요)
- **[개발 환경 설정 가이드](./docs/SETUP_GUIDE.md)** - 상세한 환경 설정 방법 ⭐

### 개발 문서
- [시스템 아키텍처](./docs/ARCHITECTURE.md)
- [API 명세서](./docs/API_SPECIFICATION.md)
- [데이터베이스 스키마](./docs/DATABASE_SCHEMA.md)
- [기술 스택](./docs/TECH_STACK.md)
- [개발 가이드](./docs/DEVELOPMENT_GUIDE.md)

### 품질 기준 ⭐
- **[Definition of Done](./docs/DEFINITION_OF_DONE.md)** - 완료 기준 및 테스트 정책

### 프로젝트 관리
- [할 일 목록](./project-management/TODO.md)
- [진행 상황](./project-management/PROGRESS.md)
- [마일스톤](./project-management/MILESTONES.md)

## 📝 개발 워크플로우

1. [TODO.md](./project-management/TODO.md)에서 현재 작업 확인
2. 기능 구현 + 테스트 작성
3. **코드 품질 검사 실행** (black, flake8, pylint)
4. [Definition of Done](./docs/DEFINITION_OF_DONE.md) 체크리스트 확인
5. **모든 테스트 100% 통과 확인** ⚠️
6. 문서 업데이트
7. TODO.md 체크박스 체크

자세한 개발 가이드는 [SETUP_GUIDE.md](./docs/SETUP_GUIDE.md)를 참조하세요.

자세한 진행 상황은 [PROGRESS.md](./project-management/PROGRESS.md)를 참조하세요.

## ✨ 주요 기능

- **실시간 종목 추적** - 6개 종목(ETF 4개 + 주식 2개)의 가격, 거래량 모니터링
- **투자자 매매 동향** - 개인/기관/외국인 순매수 분석
- **뉴스 집계** - 테마별 뉴스 자동 수집
- **비교 분석** - 종목 간 성과 비교 및 상관관계 분석
- **리포트 생성** - PDF/Markdown 리포트 다운로드

## 🔧 기술 스택

- **Backend**: FastAPI, Python 3.10+
- **Frontend**: React 18, Vite, TailwindCSS
- **Database**: SQLite (개발) / PostgreSQL (프로덕션)
- **Charts**: Recharts
- **State Management**: TanStack Query
- **Deployment**: Docker, docker-compose

## 📦 프로젝트 구조

```
ETFWeeklyReport/
├── backend/              # FastAPI 백엔드
│   ├── app/             # 애플리케이션 코드
│   ├── tests/           # 테스트 코드
│   ├── venv/            # Python 가상환경
│   ├── requirements.txt # 운영 의존성
│   ├── requirements-dev.txt  # 개발/테스트 의존성
│   ├── pytest.ini       # 테스트 설정
│   ├── pyproject.toml   # 프로젝트 메타데이터 및 도구 설정
│   ├── .flake8          # 린터 설정
│   ├── .env             # 환경변수 (git 제외)
│   └── README.md        # 백엔드 가이드
├── frontend/            # React 프론트엔드
│   ├── src/            # 소스 코드
│   ├── public/         # 정적 파일
│   └── package.json    # Node.js 의존성
├── docs/                # 프로젝트 문서
│   ├── SETUP_GUIDE.md  # 개발 환경 설정 가이드
│   ├── ARCHITECTURE.md
│   ├── API_SPECIFICATION.md
│   └── ...
├── project-management/  # 진행 상황 추적
├── docker-compose.yml   # Docker 설정
├── .cursorrules         # Cursor AI 규칙
├── .gitignore          # Git 제외 파일
└── CLAUDE.md           # AI 컨텍스트 및 문서 인덱스
```

## 🧪 테스트

### 백엔드 테스트

```bash
cd backend
source venv/bin/activate

# 모든 테스트 실행
pytest

# 상세 출력 + 커버리지
pytest -v --cov=app --cov-report=term-missing

# HTML 커버리지 리포트 생성
pytest --cov=app --cov-report=html
open htmlcov/index.html  # macOS
```

### 백엔드 코드 품질 검사

```bash
# 코드 포매팅
black app/ tests/
isort app/ tests/

# 린팅
flake8 app/ tests/
pylint app/

# 타입 체킹
mypy app/
```

### 프론트엔드 테스트

```bash
cd frontend
npm test -- --coverage
```

## 🛠️ 개발 환경

### 백엔드 필수 파일
- `venv/` - Python 가상환경 (83개 패키지)
- `requirements.txt` - 운영 의존성 (FastAPI, Pandas 등)
- `requirements-dev.txt` - 개발 의존성 (pytest, black, flake8 등)
- `.env` - 환경변수 (`.env.example`에서 복사)
- `pytest.ini` - 테스트 설정
- `pyproject.toml` - 프로젝트 및 도구 설정

### 개발 도구
- **테스트**: pytest, pytest-cov, pytest-asyncio
- **포매팅**: black, isort
- **린팅**: flake8, pylint
- **타입 체킹**: mypy
- **디버깅**: ipython, ipdb

## 📖 데이터 소스

- **Naver Finance (네이버 증권)** - 주요 데이터 소스 (스크래핑)
  - 일별 가격 데이터 (시가/고가/저가/종가/거래량)
  - 투자자별 매매 동향 (개인/기관/외국인)
- **KRX (한국거래소)** - 보조 데이터 소스
- **ETF 운용사** - 삼성/신한/KoAct/KB 자산운용
- **뉴스** - 네이버 뉴스
