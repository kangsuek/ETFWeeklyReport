# Render.com 배포 가이드

이 문서는 ETF Weekly Report 애플리케이션을 Render.com에 무료로 배포하는 방법을 설명합니다.

## 📋 사전 요구사항

1. **Render.com 계정**: https://render.com 에서 무료 계정 생성
2. **GitHub 저장소**: 프로젝트가 GitHub에 푸시되어 있어야 함
3. **Naver API 키** (선택사항): 뉴스 수집 기능 사용 시 필요

## 🚀 배포 단계

### 방법 1: render.yaml 사용 (권장)

#### 1단계: GitHub에 코드 푸시

```bash
git add .
git commit -m "Add Render.com deployment configuration"
git push origin main
```

#### 2단계: Render.com에서 Blueprint 배포

1. Render.com 대시보드 접속
2. "New +" 버튼 클릭 → "Blueprint" 선택
3. GitHub 저장소 연결
4. `render.yaml` 파일이 자동으로 감지됨
5. "Apply" 클릭하여 배포 시작

#### 3단계: 환경 변수 설정

배포 후 Render 대시보드에서 각 서비스의 환경 변수를 설정하세요:

**Backend 서비스 (`etf-report-backend`):**
- `API_KEY`: 관리용 API 키 (수집·설정·DB 초기화 등, 프로덕션 권장)
- `CORS_ORIGINS`: 프론트엔드 URL (예: `https://etf-report-frontend.onrender.com`)
- `NAVER_CLIENT_ID`: Naver API Client ID (뉴스 수집 시 선택)
- `NAVER_CLIENT_SECRET`: Naver API Client Secret (뉴스 수집 시 선택)
- `SCRAPING_INTERVAL_MINUTES`: `60` (무료 플랜 권장)
- `CACHE_TTL_MINUTES`: `5` (기본값)

**Frontend 서비스 (`etf-report-frontend`):**
- `VITE_API_BASE_URL`: 백엔드 API URL (예: `https://etf-report-backend.onrender.com/api`)

**데이터베이스:**
- `DATABASE_URL`은 자동으로 설정됩니다 (수동 설정 불필요)

#### 환경 변수 상세 (참고)

| 서비스 | 변수 | 설명 | 비고 |
|--------|------|------|------|
| Backend | `DATABASE_URL` | PostgreSQL 연결 문자열 | render.yaml에서 자동 연결 |
| Backend | `API_KEY` | 관리용 API 키 (수집·설정·DB 초기화) | 프로덕션 권장 |
| Backend | `CORS_ORIGINS` | 프론트엔드 도메인 | 프론트 배포 후 설정 |
| Backend | `NAVER_CLIENT_ID` / `NAVER_CLIENT_SECRET` | 뉴스 수집 | 선택 |
| Backend | `SCRAPING_INTERVAL_MINUTES` | 수집 간격(분) | 무료 플랜 권장 60 |
| Backend | `CACHE_TTL_MINUTES` | 캐시(분) | 기본 5 |
| Backend | `DB_POOL_SIZE` | DB 연결 풀 | 무료 플랜 권장 5 |
| Frontend | `VITE_API_BASE_URL` | 백엔드 API URL (예: `https://xxx.onrender.com/api`) | 필수 |

`PYTHON_VERSION`, `API_HOST`, `API_PORT`는 render.yaml에서 자동 설정됩니다. URL 끝에 슬래시(`/`)를 붙이지 마세요.

### 방법 2: 수동 배포

#### 1단계: PostgreSQL 데이터베이스 생성

1. Render 대시보드에서 "New +" → "PostgreSQL" 선택
2. 설정:
   - **Name**: `etf-report-db`
   - **Database**: `etf_report`
   - **User**: `etf_report_user`
   - **Region**: `Singapore` (또는 가장 가까운 지역)
   - **Plan**: `Free`
3. "Create Database" 클릭
4. 생성 후 "Connections" 탭에서 `Internal Database URL` 복사

#### 2단계: Backend 서비스 배포

1. "New +" → "Web Service" 선택
2. GitHub 저장소 연결
3. 설정:
   - **Name**: `etf-report-backend`
   - **Region**: `Singapore`
   - **Branch**: `main`
   - **Root Directory**: (비워두기)
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r backend/requirements.txt`
   - **Start Command**: `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: `Free`
4. "Advanced" → "Add Environment Variable":
   - `DATABASE_URL`: 1단계에서 복사한 Internal Database URL
   - `API_KEY`: 관리용 API 키 (프로덕션 권장)
   - `CORS_ORIGINS`: `https://etf-report-frontend.onrender.com` (나중에 프론트엔드 URL로 변경)
   - `NAVER_CLIENT_ID`: (선택사항)
   - `NAVER_CLIENT_SECRET`: (선택사항)
   - `SCRAPING_INTERVAL_MINUTES`: `60`
   - `CACHE_TTL_MINUTES`: `5`
   - `DB_POOL_SIZE`: `5`
5. "Create Web Service" 클릭

#### 3단계: Frontend 서비스 배포

1. "New +" → "Static Site" 선택
2. GitHub 저장소 연결
3. 설정:
   - **Name**: `etf-report-frontend`
   - **Region**: `Singapore`
   - **Branch**: `main`
   - **Root Directory**: `frontend`
   - **Build Command**: `npm install && npm run build`
   - **Publish Directory**: `dist`
   - **Plan**: `Free`
4. "Advanced" → "Add Environment Variable":
   - `VITE_API_BASE_URL`: 백엔드 서비스 URL + `/api` (예: `https://etf-report-backend.onrender.com/api`)
5. "Create Static Site" 클릭

## 🔧 배포 후 설정

### 데이터베이스 초기화

Backend 서비스가 처음 시작될 때 자동으로 데이터베이스가 초기화됩니다. 
만약 수동으로 초기화해야 한다면:

1. Render 대시보드에서 Backend 서비스 선택
2. "Shell" 탭 클릭
3. 다음 명령 실행:
```bash
cd backend
python -m app.database
```

### CORS 설정 업데이트

Frontend URL이 생성된 후, Backend의 `CORS_ORIGINS` 환경 변수를 업데이트하세요:

1. Backend 서비스 → "Environment" 탭
2. `CORS_ORIGINS` 값을 프론트엔드 URL로 변경
3. "Save Changes" 클릭
4. 서비스 재시작 (자동)

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
1. 로그 확인: Render 대시보드 → 서비스 → "Logs" 탭
2. `requirements.txt`에 모든 의존성이 포함되어 있는지 확인
3. Python 버전 확인 (3.11.9 권장)

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
