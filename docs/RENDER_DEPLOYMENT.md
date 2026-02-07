# Render.com 배포 가이드

ETF Weekly Report를 Render.com에 무료로 배포하는 방법입니다.  
프로젝트 루트의 **render.yaml**로 Blueprint 배포를 지원하며, 백엔드(FastAPI)·프론트엔드(Static Site)·PostgreSQL 구성을 정의합니다.

## 📋 사전 요구사항

1. **Render.com 계정**: https://render.com 에서 무료 계정 생성
2. **GitHub 저장소**: 프로젝트가 GitHub에 푸시되어 있어야 함
3. **Naver API 키** (선택): 뉴스 수집 기능 사용 시만 필요

## 🚀 배포 단계

### 방법 1: render.yaml Blueprint (권장)

#### 1단계: GitHub에 코드 푸시

```bash
git add .
git commit -m "Add Render deployment configuration"
git push origin main
```

#### 2단계: Render에서 Blueprint 배포

1. Render 대시보드 접속
2. **New +** → **Blueprint** 선택
3. GitHub 저장소 연결
4. 저장소 루트의 **render.yaml**이 자동으로 감지됨
5. **Apply** 클릭하여 배포 시작

**render.yaml 요약** (현재 소스 기준):

| 서비스 | 타입 | 빌드/시작 |
|--------|------|------------|
| **etf-report-backend** | Web (Python) | Build: `pip install -r backend/requirements.txt` / Start: `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| **etf-report-frontend** | Static | Build: `cd frontend && npm install && npm run build` / Publish: `frontend/dist` |
| **etf-report-db** | PostgreSQL | 자동 생성, Backend에 `DATABASE_URL` 연결 |

render.yaml에 `sync: false`로 되어 있는 변수는 **반드시 Render 대시보드에서 수동 설정**해야 합니다.

#### 3단계: 환경 변수 설정 (대시보드)

배포 후 각 서비스 → **Environment** 탭에서 아래 변수를 설정하세요.

**Backend (`etf-report-backend`)**  
(yaml에서 이미 설정된 것: `PYTHON_VERSION`, `API_HOST`, `DATABASE_URL`, `SCRAPING_INTERVAL_MINUTES`, `CACHE_TTL_MINUTES`, `DB_POOL_SIZE`)

- **`API_KEY`**: 관리용 API 키 (수집·설정·DB 초기화 등, 프로덕션 권장). render.yaml에 없으므로 대시보드에서 추가.
- **`CORS_ORIGINS`**: 프론트엔드 URL (예: `https://etf-report-frontend.onrender.com`). 프론트 배포 후 URL 확정되면 설정.
- **`NAVER_CLIENT_ID`** / **`NAVER_CLIENT_SECRET`**: 뉴스 수집 시 선택.

**Frontend (`etf-report-frontend`)**

- **`VITE_API_BASE_URL`**: 백엔드 API URL (예: `https://etf-report-backend.onrender.com/api`). 끝에 슬래시(`/`) 붙이지 마세요.

**데이터베이스**

- **`DATABASE_URL`**: render.yaml의 `fromDatabase`로 Backend에 자동 연결되므로 별도 설정 불필요.

#### 환경 변수 상세 (참고)

| 서비스 | 변수 | 설명 | 비고 |
|--------|------|------|------|
| Backend | `DATABASE_URL` | PostgreSQL 연결 문자열 | render.yaml에서 DB 자동 연결 |
| Backend | `API_KEY` | 관리용 API 키 | 대시보드에서 설정 (yaml 없음) |
| Backend | `CORS_ORIGINS` | 프론트엔드 도메인 | 대시보드에서 설정 (sync: false) |
| Backend | `NAVER_CLIENT_ID` / `NAVER_CLIENT_SECRET` | 뉴스 수집 | 선택, 대시보드에서 설정 |
| Backend | `SCRAPING_INTERVAL_MINUTES` | 수집 간격(분) | yaml 기본값 60 |
| Backend | `CACHE_TTL_MINUTES` | 캐시(분) | yaml 기본값 5 |
| Backend | `DB_POOL_SIZE` | DB 연결 풀 | yaml 기본값 5 |
| Frontend | `VITE_API_BASE_URL` | 백엔드 API URL | 필수, 대시보드에서 설정 |

로컬에서는 프로젝트 루트의 `.env`를 사용하지만, Render에는 `.env`가 없으므로 **모든 설정은 Render 환경 변수**에서 읽습니다. URL 끝에 슬래시(`/`)를 붙이지 마세요.

### 방법 2: 수동 배포

#### 1단계: PostgreSQL 데이터베이스 생성

1. Render 대시보드에서 **New +** → **PostgreSQL** 선택
2. 설정:
   - **Name**: `etf-report-db`
   - **Database**: `etf_report`
   - **User**: `etf_report_user`
   - **Region**: `Singapore` (또는 가까운 지역)
   - **Plan**: `Free`
3. **Create Database** 클릭
4. 생성 후 **Connections** 탭에서 **Internal Database URL** 복사

#### 2단계: Backend Web Service 배포

1. **New +** → **Web Service** 선택
2. GitHub 저장소 연결
3. 설정:
   - **Name**: `etf-report-backend`
   - **Region**: `Singapore`
   - **Branch**: `main`
   - **Root Directory**: (비움 — 저장소 루트 기준)
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r backend/requirements.txt`
   - **Start Command**: `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: `Free`
4. **Environment** (또는 Advanced → Add Environment Variable):
   - `DATABASE_URL`: 1단계에서 복사한 Internal Database URL
   - `API_KEY`: 관리용 API 키 (프로덕션 권장)
   - `CORS_ORIGINS`: `https://etf-report-frontend.onrender.com` (프론트 배포 후 실제 URL로 변경)
   - `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET`: (선택)
   - `SCRAPING_INTERVAL_MINUTES`: `60`
   - `CACHE_TTL_MINUTES`: `5`
   - `DB_POOL_SIZE`: `5`
5. **Create Web Service** 클릭

#### 3단계: Frontend Static Site 배포

1. **New +** → **Static Site** 선택
2. GitHub 저장소 연결
3. 설정:
   - **Name**: `etf-report-frontend`
   - **Region**: `Singapore`
   - **Branch**: `main`
   - **Root Directory**: `frontend`
   - **Build Command**: `npm install && npm run build`
   - **Publish Directory**: `dist`
   - **Plan**: `Free`
4. **Environment**에서:
   - `VITE_API_BASE_URL`: 백엔드 URL + `/api` (예: `https://etf-report-backend.onrender.com/api`). 끝에 `/` 제외.
5. **Create Static Site** 클릭

## 🔧 배포 후 설정

### 데이터베이스 초기화

Backend 서비스 시작 시 **앱 진입점(`app.main`)에서 `init_db()`가 자동 호출**되므로, 별도 DB 초기화는 필요하지 않습니다.  
테이블 생성·stocks 동기화는 모두 시작 시점에 수행됩니다.

수동으로 DB만 초기화해야 할 때 (예: 스키마 문제 복구):

1. Render 대시보드 → Backend 서비스 → **Shell** 탭
2. 다음 실행:
```bash
cd backend
python -m app.database
```

### CORS 설정 업데이트

Frontend 배포 후 생성된 URL로 Backend의 CORS를 맞춰주세요.

1. Backend 서비스 → **Environment** 탭
2. `CORS_ORIGINS`를 프론트엔드 URL로 설정 (예: `https://etf-report-frontend.onrender.com`)
3. **Save Changes** (재시작은 자동)

## 📝 무료 플랜 제한사항

### Render.com 무료 플랜 제한

1. **슬리프 모드**: 15분간 요청이 없으면 서비스가 슬리프 모드로 전환
   - 첫 요청 시 약 30초~1분 정도 지연될 수 있음
   - 해결: 무료 Keep-Alive 서비스 사용 (예: UptimeRobot)

2. **월 750시간 제한**: 무료 플랜은 월 750시간만 사용 가능
   - 24시간 운영 시 약 31일 사용 가능
   - 2개 서비스(Backend + Frontend) = 월 375시간씩 사용

3. **PostgreSQL 제한**:
   - 90일간 비활성 시 삭제될 수 있음
   - 최대 1GB 저장 공간

### 권장 사항

1. **Keep-Alive 설정**: 
   - UptimeRobot (https://uptimerobot.com) 무료 계정 생성
   - 백엔드 서비스 URL을 5분마다 핑
   - 슬리프 모드 방지

2. **스케줄러 간격 조정**:
   - 무료 플랜에서는 `SCRAPING_INTERVAL_MINUTES=60` (1시간) 권장
   - 너무 자주 실행하면 리소스 제한에 걸릴 수 있음

3. **모니터링**:
   - Render 대시보드에서 로그 확인
   - 에러 발생 시 즉시 확인 가능

## 🔍 트러블슈팅

### 데이터베이스 연결 실패

**증상**: `psycopg2.OperationalError` 또는 연결 타임아웃

**해결책**:
1. `DATABASE_URL`이 올바른지 확인 (Internal Database URL 사용)
2. 데이터베이스가 같은 지역에 있는지 확인
3. Backend 서비스 재시작

### CORS 에러

**증상**: 브라우저 콘솔에 CORS 에러

**해결책**:
1. Backend의 `CORS_ORIGINS` 환경 변수에 프론트엔드 URL이 포함되어 있는지 확인
2. URL 끝에 슬래시(`/`)가 없는지 확인
3. HTTPS 프로토콜 사용 확인

### 빌드 실패

**증상**: 배포 시 빌드 에러

**해결책**:
1. 로그 확인: Render 대시보드 → 서비스 → **Logs** 탭
2. Backend: `backend/requirements.txt` 경로 및 의존성 확인. render.yaml 기준 Python 3.11.9 사용.
3. Frontend: Root Directory `frontend`일 때 `npm install && npm run build`가 정상 동작하는지 로컬에서 확인 (Node 18+).

### 프론트엔드 API 호출 실패

**증상**: 프론트엔드에서 API 호출이 실패

**해결책**:
1. `VITE_API_BASE_URL` 환경 변수가 올바른지 확인
2. 백엔드 서비스가 실행 중인지 확인
3. 브라우저 개발자 도구 → Network 탭에서 요청 확인

### 슬리프 모드 지연

**증상**: 첫 요청이 매우 느림 (30초~1분)

**해결책**:
1. UptimeRobot 등 Keep-Alive 서비스 설정
2. 또는 유료 플랜으로 업그레이드

## 📊 모니터링

### 로그 확인

1. Render 대시보드 → 서비스 선택
2. "Logs" 탭에서 실시간 로그 확인
3. 에러 발생 시 로그에서 원인 파악

### 메트릭 확인

1. "Metrics" 탭에서 CPU, 메모리 사용량 확인
2. 무료 플랜 제한 내에서 운영되는지 확인

## 🔄 업데이트 배포

코드 변경 후 자동 배포:

1. GitHub에 푸시
2. Render가 자동으로 감지하여 재배포
3. 배포 상태는 대시보드에서 확인 가능

수동 재배포:

1. 서비스 선택 → "Manual Deploy" → "Deploy latest commit"

## 📚 참고 자료

- [Render.com 공식 문서](https://render.com/docs)
- [FastAPI 배포 가이드](https://fastapi.tiangolo.com/deployment/)
- [React 배포 가이드](https://react.dev/learn/start-a-new-react-project#production-builds)

## 🆘 지원

문제가 발생하면:
1. Render 대시보드의 로그 확인
2. GitHub Issues에 문제 보고
3. Render.com 지원팀에 문의
