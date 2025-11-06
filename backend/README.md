# ETF Weekly Report - Backend

FastAPI 기반 ETF 분석 백엔드 API

## 🚀 빠른 시작

### 1. 가상환경 생성 및 활성화

```bash
# 가상환경 생성
python -m venv venv

# 활성화 (macOS/Linux)
source venv/bin/activate

# 활성화 (Windows)
venv\Scripts\activate
```

### 2. 의존성 설치

```bash
# 운영 환경
pip install -r requirements.txt

# 개발 환경 (테스트, 린터 포함)
pip install -r requirements-dev.txt
```

### 3. 환경 변수 설정

```bash
# .env.example을 .env로 복사 (이미 .env 파일이 있다면 건너뛰기)
cp .env.example .env

# .env 파일을 편집하여 필요한 설정 변경
```

### 4. 데이터베이스 초기화

```bash
python -m app.database
```

### 5. 서버 실행

```bash
# 개발 모드 (hot reload)
uvicorn app.main:app --reload

# 프로덕션 모드
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

서버 실행 후:
- API 문서: http://localhost:8000/docs
- Alternative API 문서: http://localhost:8000/redoc
- Health Check: http://localhost:8000/api/health

## 🧪 테스트

### 테스트 실행

```bash
# 모든 테스트 실행
pytest

# 특정 테스트 파일 실행
pytest tests/test_etfs.py

# 커버리지 리포트와 함께 실행
pytest --cov=app --cov-report=html

# 마커별 실행
pytest -m unit  # 단위 테스트만
pytest -m api   # API 테스트만
```

### 테스트 커버리지 확인

```bash
# 터미널에서 확인
pytest --cov=app --cov-report=term-missing

# HTML 리포트 생성 (htmlcov/index.html)
pytest --cov=app --cov-report=html
open htmlcov/index.html  # macOS
```

## 🔍 코드 품질

### Linting

```bash
# Black (코드 포매팅)
black app/ tests/

# isort (import 정렬)
isort app/ tests/

# Flake8 (스타일 검사)
flake8 app/ tests/

# Pylint (코드 분석)
pylint app/

# MyPy (타입 체킹)
mypy app/
```

### 모든 검사 한번에

```bash
# 포매팅
black app/ tests/ && isort app/ tests/

# 검사
flake8 app/ tests/ && pylint app/ && mypy app/
```

## 📁 프로젝트 구조

```
backend/
├── app/
│   ├── main.py              # FastAPI 애플리케이션 진입점
│   ├── config.py            # 설정 관리
│   ├── database.py          # 데이터베이스 연결
│   ├── models.py            # Pydantic 모델
│   ├── routers/             # API 라우터
│   │   ├── etfs.py
│   │   ├── reports.py
│   │   └── news.py
│   └── services/            # 비즈니스 로직
│       ├── data_collector.py
│       └── news_scraper.py
├── tests/                   # 테스트 파일
├── data/                    # 데이터베이스 파일
├── requirements.txt         # 운영 의존성
├── requirements-dev.txt     # 개발 의존성
├── pytest.ini              # Pytest 설정
├── pyproject.toml          # 프로젝트 메타데이터 및 도구 설정
├── .flake8                 # Flake8 설정
├── .env.example            # 환경변수 예시
└── .env                    # 실제 환경변수 (git 제외)
```

## 🛠️ 개발 워크플로우

1. **기능 개발**
   ```bash
   # 새 브랜치 생성
   git checkout -b feature/new-feature
   
   # 코드 작성
   # ...
   
   # 테스트 작성
   # tests/test_new_feature.py
   ```

2. **코드 품질 검사**
   ```bash
   # 포매팅
   black app/ tests/
   isort app/ tests/
   
   # 린팅
   flake8 app/ tests/
   pylint app/
   ```

3. **테스트 실행**
   ```bash
   # 테스트 실행 (100% 통과 필수!)
   pytest
   
   # 커버리지 확인
   pytest --cov=app --cov-report=term-missing
   ```

4. **커밋 및 푸시**
   ```bash
   git add .
   git commit -m "feat: 새 기능 추가"
   git push origin feature/new-feature
   ```

## 📚 주요 의존성

- **FastAPI**: 웹 프레임워크
- **Uvicorn**: ASGI 서버
- **Pydantic**: 데이터 검증
- **Pandas**: 데이터 처리
- **FinanceDataReader**: 금융 데이터 수집
- **BeautifulSoup4**: 웹 스크래핑

## 🧪 테스트 정책

⚠️ **중요**: 모든 기능은 테스트 100% 완료 후 다음 단계로 진행

- 단위 테스트 작성 필수
- API 엔드포인트 테스트 필수
- 커버리지 80% 이상 유지
- 모든 PR은 테스트 통과 필수

자세한 내용은 `../docs/DEFINITION_OF_DONE.md` 참조

## 🔐 환경 변수

`.env` 파일에 다음 변수들을 설정하세요:

- `API_HOST`: API 서버 호스트 (기본: 0.0.0.0)
- `API_PORT`: API 서버 포트 (기본: 8000)
- `DATABASE_URL`: 데이터베이스 URL
- `CACHE_TTL_MINUTES`: 캐시 TTL (분)
- `NEWS_MAX_RESULTS`: 뉴스 최대 결과 수

## 📖 API 문서

자세한 API 명세는 다음을 참조하세요:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- API 명세서: `../docs/API_SPECIFICATION.md`

## 🐳 Docker

```bash
# 이미지 빌드
docker build -t etf-backend .

# 컨테이너 실행
docker run -p 8000:8000 etf-backend

# docker-compose 사용 (권장)
cd ..
docker-compose up backend
```

