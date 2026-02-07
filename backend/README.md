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



### 3. 데이터베이스 초기화

```bash
python -m app.database
```

### 4. 서버 실행

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
# Black (코드 포매팅, max-line-length 100)
black app/ tests/

# isort (import 정렬, black 프로필)
isort app/ tests/

# Flake8 (스타일 검사, .flake8 기준)
flake8 app/

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
flake8 app/ && pylint app/ && mypy app/
```

## 📁 프로젝트 구조

```
backend/
├── app/
│   ├── main.py              # FastAPI 애플리케이션 진입점
│   ├── config.py            # 설정 (환경 변수, stocks.json)
│   ├── database.py          # DB 연결 (SQLite/PostgreSQL)
│   ├── models.py            # Pydantic 요청/응답 모델
│   ├── routers/             # API 라우터
│   │   ├── etfs.py          # 종목, 가격, 매매동향, 지표, 인사이트, 비교, 배치요약, 분봉
│   │   ├── news.py          # 뉴스 조회·수집
│   │   ├── data.py          # 일괄 수집, 백필, 상태, 캐시, DB 초기화
│   │   └── settings.py     # 종목 CRUD, 검색, 검증, 순서 변경, 종목 목록 수집
│   ├── services/            # 비즈니스 로직
│   │   ├── data_collector.py
│   │   ├── intraday_collector.py
│   │   ├── news_scraper.py
│   │   ├── news_analyzer.py
│   │   ├── insights_service.py
│   │   ├── comparison_service.py
│   │   ├── scheduler.py
│   │   ├── ticker_scraper.py
│   │   └── ticker_catalog_collector.py
│   ├── middleware/          # API Key, Rate Limit
│   └── utils/               # cache, stocks_manager 등
├── config/                  # stocks.json
├── tests/                   # pytest 테스트
├── data/                    # SQLite DB 파일 (gitignore)
├── requirements.txt
├── requirements-dev.txt
├── pytest.ini
└── .flake8
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

자세한 내용은 [DEVELOPMENT_GUIDE.md](../docs/DEVELOPMENT_GUIDE.md) 및 [AGENTS.md](../AGENTS.md) 참조

## 🔐 환경 변수

**프로젝트 루트**의 `.env` 파일만 사용합니다. (`backend/.env`는 사용하지 않음)

- `API_KEY`: 관리용 API 키 (수집·설정·DB 초기화 등, 미설정 시 개발 모드에서 모든 요청 허용)
- `API_HOST`: API 서버 호스트 (기본: 0.0.0.0)
- `API_PORT`: API 서버 포트 (기본: 8000)
- `DATABASE_URL`: 데이터베이스 URL (미설정 시 `backend/data/etf_data.db` 사용)
- `CACHE_TTL_MINUTES`: 캐시 TTL (분, 기본: 3)
- `SCRAPING_INTERVAL_MINUTES`: 스케줄러 주기 수집 간격 (분, 기본: 3)
- `NAVER_CLIENT_ID` / `NAVER_CLIENT_SECRET`: 뉴스 수집용 (선택)

## 📖 API 문서

자세한 API 명세는 다음을 참조하세요:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- API 명세서: `../docs/API_SPECIFICATION.md`

