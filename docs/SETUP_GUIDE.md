# 🚀 개발 환경 설정 가이드

ETF Weekly Report 프로젝트의 표준 개발 환경 설정 방법입니다.

## 📋 사전 요구사항

- Python 3.9 이상
- Node.js 18 이상
- npm 또는 yarn
- Git

## 🐍 백엔드 설정 (Python/FastAPI)

### 1️⃣ 가상환경 생성

```bash
cd backend

# venv 생성
python3 -m venv venv

# 또는 특정 Python 버전 사용
python3.11 -m venv venv
```

### 2️⃣ 가상환경 활성화

```bash
# macOS / Linux
source venv/bin/activate

# Windows (PowerShell)
venv\Scripts\Activate.ps1

# Windows (CMD)
venv\Scripts\activate.bat
```

가상환경이 활성화되면 터미널 프롬프트에 `(venv)` 표시가 나타납니다.

### 3️⃣ Python 버전 확인

```bash
python --version
# Python 3.9.6 이상이어야 함
```

### 4️⃣ pip 업그레이드

```bash
pip install --upgrade pip
```

### 5️⃣ 의존성 설치

```bash
# 운영 환경 (최소 의존성)
pip install -r requirements.txt

# 개발 환경 (테스트, 린터, 디버거 포함) ⭐ 권장
pip install -r requirements-dev.txt
```

설치되는 패키지:
- **운영용**: FastAPI, Uvicorn, Pydantic, Pandas, FinanceDataReader 등
- **개발용**: pytest, black, flake8, pylint, coverage 등

### 6️⃣ 환경 변수 설정

```bash
# .env.example을 .env로 복사
cp .env.example .env

# .env 파일 편집 (필요시)
nano .env
# 또는
code .env  # VS Code
```

`.env` 파일 내용 확인:
```bash
API_HOST=0.0.0.0
API_PORT=8000
DATABASE_URL=sqlite:///./data/etf_data.db
CACHE_TTL_MINUTES=10
NEWS_MAX_RESULTS=5
```

### 7️⃣ 데이터베이스 초기화

```bash
python -m app.database
```

출력 예시:
```
INFO - Database initialized successfully
```

### 8️⃣ 개발 서버 실행

```bash
# Hot reload 모드 (개발용)
uvicorn app.main:app --reload

# 다른 포트 사용
uvicorn app.main:app --reload --port 8080

# 모든 인터페이스에서 접속 허용
uvicorn app.main:app --reload --host 0.0.0.0
```

서버 실행 확인:
- 🔗 API 문서: http://localhost:8000/docs
- 🔗 Alternative 문서: http://localhost:8000/redoc
- 🔗 Health Check: http://localhost:8000/api/health

### 9️⃣ 테스트 실행 ⚠️ 필수

```bash
# 모든 테스트 실행
pytest

# 상세 출력과 커버리지
pytest -v --cov=app --cov-report=term-missing

# HTML 커버리지 리포트 생성
pytest --cov=app --cov-report=html
open htmlcov/index.html  # macOS
```

## ⚛️ 프론트엔드 설정 (React/Vite)

### 1️⃣ 프론트엔드 디렉토리로 이동

```bash
# 새 터미널 열기 (백엔드 서버는 계속 실행)
cd frontend
```

### 2️⃣ Node.js 버전 확인

```bash
node --version
# v18.0.0 이상이어야 함

npm --version
# 9.0.0 이상 권장
```

### 3️⃣ 의존성 설치

```bash
# npm 사용
npm install

# 또는 yarn 사용
yarn install

# 또는 pnpm 사용 (빠름)
pnpm install
```

설치되는 패키지:
- React, React Router
- TanStack Query (React Query)
- Axios
- Recharts
- TailwindCSS
- Vite

### 4️⃣ 환경 변수 설정

```bash
# .env.example을 .env로 복사
cp .env.example .env

# .env 파일 편집 (필요시)
nano .env
```

`.env` 파일 내용:
```bash
VITE_API_BASE_URL=http://localhost:8000/api
VITE_APP_TITLE=ETF Weekly Report
```

### 5️⃣ 개발 서버 실행

```bash
npm run dev

# 또는 특정 포트 사용
npm run dev -- --port 3000
```

서버 실행 확인:
- 🔗 프론트엔드: http://localhost:5173

### 6️⃣ 빌드 (프로덕션)

```bash
# 프로덕션 빌드
npm run build

# 빌드 미리보기
npm run preview
```

## 🐳 Docker로 실행 (대안)

프로젝트 루트에서:

```bash
# 모든 서비스 시작
docker-compose up --build

# 백그라운드 실행
docker-compose up -d

# 특정 서비스만 실행
docker-compose up backend
docker-compose up frontend

# 중지
docker-compose down
```

## ✅ 설정 확인 체크리스트

### 백엔드
- [ ] Python 3.9+ 설치됨
- [ ] 가상환경(venv) 생성 및 활성화됨
- [ ] `requirements-dev.txt` 설치 완료
- [ ] `.env` 파일 생성 및 설정 완료
- [ ] 데이터베이스 초기화 완료
- [ ] 서버 실행 성공 (http://localhost:8000/docs 접속 가능)
- [ ] 테스트 실행 성공 (`pytest` 통과)

### 프론트엔드
- [ ] Node.js 18+ 설치됨
- [ ] `npm install` 완료
- [ ] `.env` 파일 생성 및 설정 완료
- [ ] 개발 서버 실행 성공 (http://localhost:5173 접속 가능)
- [ ] 백엔드 API 연동 확인 (Dashboard 데이터 로딩 성공)

## 🔧 일반적인 문제 해결

### 문제 1: `command not found: python`
```bash
# 해결: python3 사용
python3 -m venv venv
```

### 문제 2: `permission denied` (macOS/Linux)
```bash
# 해결: 스크립트 실행 권한 추가
chmod +x venv/bin/activate
source venv/bin/activate
```

### 문제 3: 포트 이미 사용 중
```bash
# 해결: 다른 포트 사용
uvicorn app.main:app --reload --port 8001
npm run dev -- --port 5174
```

### 문제 4: 가상환경 비활성화
```bash
# 가상환경 나가기
deactivate
```

### 문제 5: 패키지 설치 오류
```bash
# 캐시 삭제 후 재설치
pip cache purge
pip install -r requirements-dev.txt --no-cache-dir
```

### 문제 6: SQLite 데이터베이스 권한 오류
```bash
# data 디렉토리 권한 확인
chmod 755 backend/data
```

## 📚 다음 단계

설정이 완료되면:

1. 📖 [개발 가이드](./DEVELOPMENT_GUIDE.md) 읽기
2. 📋 [TODO 목록](../project-management/TODO.md) 확인
3. 🧪 [Definition of Done](./DEFINITION_OF_DONE.md) 숙지
4. 💻 개발 시작!

## 🆘 도움이 필요하신가요?

- API 문서: http://localhost:8000/docs
- 프로젝트 구조: [ARCHITECTURE.md](./ARCHITECTURE.md)
- 개발 가이드: [DEVELOPMENT_GUIDE.md](./DEVELOPMENT_GUIDE.md)
- API 명세: [API_SPECIFICATION.md](./API_SPECIFICATION.md)

---

**⚠️ 중요**: 모든 기능 개발 전에 테스트를 100% 통과해야 합니다!

