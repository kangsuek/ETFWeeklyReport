# 개발 환경 설정 가이드

## 사전 요구사항
- Python 3.11.9, Node.js 18+, npm/yarn, Git

## 백엔드 설정

### 1. 가상환경 생성 및 활성화
```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate  # Windows
```

### 2. 의존성 설치
```bash
pip install --upgrade pip
pip install -r requirements-dev.txt  # 개발환경 (권장)
```

### 3. 환경 변수 설정
```bash
cp .env.example .env
# .env 파일 편집 (필요시)
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

## 프론트엔드 설정

### 1. 의존성 설치
```bash
cd frontend
npm install
```

### 2. 환경 변수 설정
```bash
cp .env.example .env
# .env 파일 편집
```

### 3. 개발 서버 실행
```bash
npm run dev
```

서버 확인: http://localhost:5173

## 설정 확인 체크리스트

### 백엔드
- [ ] Python 3.11.9 설치됨
- [ ] 가상환경 생성 및 활성화됨
- [ ] `requirements-dev.txt` 설치 완료
- [ ] `.env` 파일 생성 및 설정 완료
- [ ] 데이터베이스 초기화 완료
- [ ] 서버 실행 성공
- [ ] 테스트 실행 성공

### 프론트엔드
- [ ] Node.js 18+ 설치됨
- [ ] `npm install` 완료
- [ ] `.env` 파일 생성 및 설정 완료
- [ ] 개발 서버 실행 성공

## 일반적인 문제 해결

### 문제 1: `command not found: python`
```bash
python3 -m venv venv
```

### 문제 2: 포트 이미 사용 중
```bash
uvicorn app.main:app --reload --port 8001
npm run dev -- --port 5174
```

### 문제 3: 패키지 설치 오류
```bash
pip cache purge
pip install -r requirements-dev.txt --no-cache-dir
```
