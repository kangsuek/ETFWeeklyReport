# 개발 환경 설정 및 실행 가이드

## 사전 요구사항
- Python 3.11+, Node.js 18+, npm/yarn, Git

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
백엔드·프론트엔드 모두 **프로젝트 루트**의 `.env`만 사용합니다.
```bash
cd ..   # 프로젝트 루트로 이동
cp .env.example .env
# .env 파일 편집 (필요시)
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
프론트엔드도 **프로젝트 루트**의 `.env`를 사용합니다 (Vite `envDir: '..'`). 루트에 `.env`가 있으면 추가 설정 불필요.

### 3. 개발 서버 실행
```bash
npm run dev
```
서버 확인: http://localhost:5173

---

## Pre-commit 설정 (선택)

커밋 전 자동으로 코드 품질 검사·포매팅을 하려면 프로젝트 루트에서:

```bash
# 백엔드 가상환경 생성 후 (아직 없다면)
cd backend && python3 -m venv venv && source venv/bin/activate && pip install -r requirements-dev.txt && cd ..

# 통합 Pre-commit 설치 (백엔드+프론트 모두 적용)
./scripts/setup-pre-commit.sh
```

- **설정 파일**: `.pre-commit-config.yaml` (프로젝트 루트)
- **백엔드**: Black, isort, Flake8
- **프론트엔드**: ESLint
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

```bash
cd backend
sqlite3 data/etf_data.db
```
```sql
SELECT * FROM etfs;
SELECT * FROM prices WHERE ticker = '487240' ORDER BY date DESC LIMIT 10;
```
