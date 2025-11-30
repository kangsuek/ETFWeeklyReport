# 🚀 Replit 배포 가이드

ETF Weekly Report 애플리케이션을 Replit에 배포하는 방법입니다.

---

## 📋 목차

1. [Replit 프로젝트 생성](#1-replit-프로젝트-생성)
2. [프로젝트 가져오기](#2-프로젝트-가져오기)
3. [설정 파일 구성](#3-설정-파일-구성)
4. [환경 변수 설정](#4-환경-변수-설정)
5. [실행 및 배포](#5-실행-및-배포)
6. [배포 옵션](#6-배포-옵션)
7. [문제 해결](#7-문제-해결)

---

## 1. Replit 프로젝트 생성

### 방법 1: GitHub에서 Import (권장)

1. [Replit](https://replit.com) 로그인
2. **+ Create Repl** 클릭
3. **Import from GitHub** 선택
4. GitHub 저장소 URL 입력
5. **Import from GitHub** 클릭

### 방법 2: 새 Repl 생성 후 코드 업로드

1. **+ Create Repl** 클릭
2. Template: **Python** 또는 **Blank Repl** 선택
3. 이름 입력 (예: `etf-weekly-report`)
4. 프로젝트 파일 업로드

---

## 2. 프로젝트 가져오기

GitHub에서 Import한 경우, Replit이 자동으로 프로젝트를 감지합니다.  
수동으로 설정이 필요한 경우 아래 설정 파일들을 생성하세요.

---

## 3. 설정 파일 구성

### `.replit` 파일 (프로젝트 루트)

```toml
# Replit 설정 파일
run = "bash run.sh"

# 언어 설정
language = "python3"

# 포트 설정 (Replit은 자동으로 외부에 노출)
[[ports]]
localPort = 8000
externalPort = 80

[[ports]]
localPort = 5173
externalPort = 3000

# 숨김 파일
hidden = [".pythonlibs", "venv", "__pycache__", "node_modules"]

# 패키지 관리
[packager]
language = "python3"

[packager.features]
packageSearch = true
guessImports = true

# Nix 설정
[nix]
channel = "stable-23_11"

# 배포 설정
[deployment]
run = ["bash", "run.sh"]
deploymentTarget = "cloudrun"
```

### `replit.nix` 파일 (프로젝트 루트)

```nix
{ pkgs }: {
  deps = [
    # Python
    pkgs.python311
    pkgs.python311Packages.pip
    pkgs.python311Packages.virtualenv
    
    # Node.js
    pkgs.nodejs_20
    pkgs.nodePackages.npm
    
    # 빌드 도구
    pkgs.gcc
    pkgs.libffi
    pkgs.openssl
    
    # SQLite
    pkgs.sqlite
  ];
  
  env = {
    PYTHON_LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath [
      pkgs.stdenv.cc.cc.lib
      pkgs.libffi
      pkgs.openssl
    ];
  };
}
```

### `run.sh` 파일 (프로젝트 루트)

```bash
#!/bin/bash

echo "🚀 ETF Weekly Report 시작..."

# 백엔드 설정
echo "📦 백엔드 의존성 설치 중..."
cd backend
pip install -r requirements.txt --quiet

# 데이터베이스 초기화 (없는 경우)
if [ ! -f "data/etf_data.db" ]; then
    echo "🗃️ 데이터베이스 초기화 중..."
    python -m app.database
fi

# 백엔드 서버 시작 (백그라운드)
echo "🔧 백엔드 서버 시작 중 (포트 8000)..."
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

cd ..

# 프론트엔드 설정
echo "📦 프론트엔드 의존성 설치 중..."
cd frontend
npm install --silent

# 프론트엔드 빌드 및 서버 시작
echo "🎨 프론트엔드 빌드 중..."
npm run build

# 프론트엔드 서버 시작 (프로덕션 모드)
echo "🌐 프론트엔드 서버 시작 중 (포트 5173)..."
npm run preview -- --host 0.0.0.0 --port 5173 &
FRONTEND_PID=$!

cd ..

echo ""
echo "✅ 서버 시작 완료!"
echo "📊 백엔드 API: https://$REPL_SLUG.$REPL_OWNER.repl.co:8000"
echo "🌐 프론트엔드: https://$REPL_SLUG.$REPL_OWNER.repl.co"
echo ""

# 프로세스 대기
wait $BACKEND_PID $FRONTEND_PID
```

---

## 4. 환경 변수 설정

### Replit Secrets 설정

Replit 좌측 메뉴에서 **Secrets** (🔒 아이콘) 클릭 후 다음 환경 변수 추가:

| Key | Value | 설명 |
|-----|-------|------|
| `DATABASE_URL` | `sqlite:///./data/etf_data.db` | 데이터베이스 경로 |
| `API_HOST` | `0.0.0.0` | API 서버 호스트 |
| `API_PORT` | `8000` | API 서버 포트 |
| `NAVER_CLIENT_ID` | `your_client_id` | 네이버 API ID (선택) |
| `NAVER_CLIENT_SECRET` | `your_client_secret` | 네이버 API Secret (선택) |
| `CORS_ORIGINS` | `*` | CORS 허용 도메인 |

### 프론트엔드 환경 변수

`frontend/.env.production` 파일 수정:

```env
# Replit 배포 시 URL 형식
# https://your-repl-name.your-username.repl.co
VITE_API_BASE_URL=https://your-repl-name.your-username.repl.co/api
VITE_APP_TITLE=ETF Weekly Report
```

---

## 5. 실행 및 배포

### 개발 모드 실행

1. Replit 상단의 **Run** 버튼 클릭
2. 또는 Shell에서:
   ```bash
   bash run.sh
   ```

### 배포 (Deploy)

1. Replit 상단 메뉴에서 **Deploy** 클릭
2. **Reserved VM** 또는 **Autoscale** 선택
3. 설정 확인 후 **Deploy** 클릭

---

## 6. 배포 옵션

### 옵션 A: 백엔드만 배포

백엔드 API만 Replit에서 호스팅하려면:

**`.replit`** 파일:
```toml
run = "cd backend && pip install -r requirements.txt && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"

[[ports]]
localPort = 8000
externalPort = 80
```

### 옵션 B: 프론트엔드만 배포

프론트엔드만 Replit에서 호스팅하려면:

**`.replit`** 파일:
```toml
run = "cd frontend && npm install && npm run build && npm run preview -- --host 0.0.0.0 --port 3000"

[[ports]]
localPort = 3000
externalPort = 80
```

### 옵션 C: 풀스택 배포 (권장)

백엔드 + 프론트엔드 모두 배포:

위의 `run.sh` 스크립트 사용

---

## 7. 문제 해결

### 🔴 "Port already in use" 에러

```bash
# 기존 프로세스 종료
pkill -f uvicorn
pkill -f node

# 다시 실행
bash run.sh
```

### 🔴 Python 패키지 설치 실패

```bash
# pip 업그레이드
pip install --upgrade pip

# 캐시 없이 설치
pip install -r requirements.txt --no-cache-dir
```

### 🔴 Node.js 패키지 설치 실패

```bash
# node_modules 삭제 후 재설치
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### 🔴 데이터베이스 연결 오류

```bash
# 데이터베이스 재초기화
cd backend
rm -f data/etf_data.db
python -m app.database
```

### 🔴 CORS 에러

백엔드의 CORS 설정 확인:

```python
# backend/app/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replit에서는 "*" 사용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 🔴 메모리 부족

Replit 무료 플랜의 메모리 제한으로 인해 발생할 수 있습니다:

1. **Hacker Plan** 이상으로 업그레이드 권장
2. 또는 백엔드/프론트엔드 별도 Repl로 분리

---

## 📊 Replit 리소스 요구사항

| 구성 요소 | 최소 메모리 | 권장 메모리 |
|-----------|------------|------------|
| 백엔드 | 256MB | 512MB |
| 프론트엔드 | 256MB | 512MB |
| 풀스택 | 512MB | 1GB |

**권장 플랜**: Hacker ($7/월) 이상

---

## 📝 추가 설정 파일

### `pyproject.toml` 수정 (Replit 호환)

```toml
[tool.poetry]
name = "etf-weekly-report"
version = "1.0.0"
description = "ETF Weekly Report Backend"
authors = ["Your Name"]

[tool.poetry.dependencies]
python = "^3.11"

[build-system]
requires = ["poetry-core>=1.0.0"]
build-backend = "poetry.core.masonry.api"
```

---

## 🔗 유용한 링크

- [Replit 문서](https://docs.replit.com/)
- [Replit Python 가이드](https://docs.replit.com/programming-ide/getting-started/python)
- [Replit Node.js 가이드](https://docs.replit.com/programming-ide/getting-started/nodejs)
- [Replit 배포 가이드](https://docs.replit.com/hosting/deployments/about-deployments)

---

## ✅ 배포 체크리스트

- [ ] GitHub에서 프로젝트 Import
- [ ] `.replit` 파일 생성
- [ ] `replit.nix` 파일 생성
- [ ] `run.sh` 스크립트 생성
- [ ] Secrets에 환경 변수 설정
- [ ] 프론트엔드 `.env.production` 수정
- [ ] Run 버튼으로 테스트
- [ ] Deploy 버튼으로 배포

---

*마지막 업데이트: 2025년 11월*

