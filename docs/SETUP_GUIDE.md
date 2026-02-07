# 개발 환경 설정 및 실행 가이드

## 사전 요구사항

| 항목 | 버전 | 확인 명령어 |
|------|------|-------------|
| Python | 3.11+ | `python3 --version` |
| Node.js | 18+ | `node --version` |
| npm | 9+ | `npm --version` |
| Git | 최신 | `git --version` |

---

## 한 번에 설정·실행 (권장)

```bash
# 1. 백엔드
cd backend
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements-dev.txt
cd .. && cp .env.example .env && cd backend
python -m app.database

# 2. 프론트엔드 (새 터미널)
cd frontend && npm install

# 3. 서버 시작 (프로젝트 루트에서)
./scripts/start-servers.sh
```

- **백엔드**: http://localhost:8000/docs  
- **프론트엔드**: http://localhost:5173  
- **종료**: `./scripts/stop-servers.sh`

---

## 백엔드 설정

### 1. 가상환경 생성 및 활성화
```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows
```

### 2. 의존성 설치
```bash
pip install --upgrade pip
pip install -r requirements-dev.txt  # 개발환경 (권장)
```

### 3. 환경 변수 설정
백엔드·프론트엔드 모두 **프로젝트 루트**의 `.env` 한 파일만 사용합니다 (`backend/.env`, `frontend/.env` 미사용).
```bash
cd ..   # 프로젝트 루트로 이동
cp .env.example .env
# .env 편집 (필요 시): API_KEY(선택), DATABASE_URL, NAVER_CLIENT_ID/SECRET(뉴스용 선택), VITE_API_BASE_URL 등
cd backend
```

### 4. 데이터베이스 초기화
```bash
python -m app.database
```

### 5. 개발 서버 실행
```bash
uvicorn app.main:app --reload
```
서버 확인: http://localhost:8000/docs

### 6. 테스트 실행
```bash
pytest
pytest -v --cov=app --cov-report=term-missing
```

---

## 프론트엔드 설정

### 1. 의존성 설치
```bash
cd frontend
npm install
```

### 2. 환경 변수 설정
프론트엔드도 **프로젝트 루트**의 `.env`를 사용합니다 (Vite `envDir: '..'`). 로컬 개발 시 프록시(`/api` → 백엔드)가 설정되어 있어 `VITE_API_BASE_URL` 없이도 동작합니다. 프로덕션 빌드 시에만 필요.

### 3. 개발 서버 실행
```bash
npm run dev
```
서버 확인: http://localhost:5173

---

## Pre-commit 설정 (선택)

커밋 전 자동으로 코드 품질 검사·포매팅을 적용하려면 **프로젝트 루트**에서:

```bash
# 백엔드 가상환경이 있으면 스크립트가 자동으로 사용 (없으면 시스템 Python)
./scripts/setup-pre-commit.sh
```

- **설정 파일**: `.pre-commit-config.yaml` (프로젝트 루트)
- **백엔드**: Black, isort, Flake8 (`backend/` 대상)
- **프론트엔드**: ESLint (`frontend/` 내 .js, .jsx)
- **공통**: trailing-whitespace, end-of-file-fixer, check-yaml, check-json 등
- **수동 실행**: `pre-commit run --all-files`
- **건너뛰기(비상시)**: `git commit --no-verify`

---

## 설정 확인 체크리스트

### 백엔드
- [ ] Python 3.11+ 설치됨
- [ ] 가상환경 생성 및 활성화됨
- [ ] `requirements-dev.txt` 설치 완료
- [ ] **프로젝트 루트** `.env` 파일 생성 및 설정 완료
- [ ] 데이터베이스 초기화 완료
- [ ] 서버 실행 성공
- [ ] 테스트 실행 성공

### 프론트엔드
- [ ] Node.js 18+ 설치됨
- [ ] `npm install` 완료
- [ ] (선택) 루트 `.env`에 `VITE_*` 변수 필요 시 설정
- [ ] 개발 서버 실행 성공

---

## 서버 실행

### 백엔드
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
- Health: http://localhost:8000/api/health
- Swagger: http://localhost:8000/docs

### 프론트엔드
```bash
cd frontend
npm run dev
```
- 앱: http://localhost:5173

---

## 일반적인 문제 해결

| 문제 | 해결 |
|------|------|
| `command not found: python` | `python3` 사용 |
| 포트 이미 사용 중 | `uvicorn ... --port 8001`, `npm run dev -- --port 5174` |
| 패키지 설치 오류 | `pip cache purge` 후 `pip install -r requirements-dev.txt --no-cache-dir` |
| 서버 미시작 | 가상환경 활성화 확인, 다른 포트 시도 |
| 데이터 수집 실패 | `curl https://finance.naver.com/` 연결 확인, 종목 DB 등록 여부 확인 |

---

## 주요 테스트 시나리오

```bash
# 전체 종목 목록
curl http://localhost:8000/api/etfs/ | python3 -m json.tool

# 데이터 수집
curl -X POST "http://localhost:8000/api/etfs/487240/collect?days=10"

# 가격 데이터 (날짜는 실제 기준으로 변경)
curl "http://localhost:8000/api/etfs/487240/prices?days=7"
```

---

## 데이터베이스 확인

기본 DB 경로: `backend/data/etf_data.db` (`.env`의 `DATABASE_URL` 미설정 시).

```bash
cd backend
sqlite3 data/etf_data.db
```
```sql
SELECT * FROM etfs;
SELECT * FROM prices WHERE ticker = '487240' ORDER BY date DESC LIMIT 10;
```

---

## 참고

- **문서 인덱스**: [CLAUDE.md](../CLAUDE.md)
- **상세 실행·스크립트**: [README.md](../README.md)
- **배포**: [RENDER_DEPLOYMENT.md](./RENDER_DEPLOYMENT.md), [frontend/DEPLOYMENT.md](../frontend/DEPLOYMENT.md)
