# Render.com 배포 가이드

이 문서는 ETF Weekly Report 애플리케이션을 Render.com에 배포하는 방법을 설명합니다.

## 📋 사전 요구사항

1. **Render.com 계정**: [render.com](https://render.com)에서 무료 계정 생성
2. **GitHub 저장소**: 프로젝트가 GitHub에 푸시되어 있어야 함
3. **환경 변수**: Naver API 키 (선택사항)

## 🚀 배포 단계

### 1단계: GitHub에 코드 푸시

```bash
# 현재 변경사항 커밋
git add .
git commit -m "feat: Render.com 배포 준비 - PostgreSQL 지원 추가"

# GitHub에 푸시
git push origin main
```

### 2단계: Render.com에서 서비스 생성

#### 2-1. PostgreSQL 데이터베이스 생성

1. Render.com 대시보드에서 **"New +"** 클릭
2. **"PostgreSQL"** 선택
3. 설정:
   - **Name**: `etf-report-db`
   - **Database**: `etf_report`
   - **User**: `etf_report_user`
   - **Region**: 가장 가까운 지역 선택
   - **Plan**: **Free** 선택
4. **"Create Database"** 클릭
5. 데이터베이스가 생성되면 **"Connection String"** 복사 (나중에 사용)

#### 2-2. Backend 서비스 생성

1. Render.com 대시보드에서 **"New +"** 클릭
2. **"Web Service"** 선택
3. GitHub 저장소 연결
4. 설정:
   - **Name**: `etf-report-backend`
   - **Region**: 데이터베이스와 동일한 지역
   - **Branch**: `main`
   - **Root Directory**: `backend` (또는 비워두고 buildCommand에서 처리)
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r backend/requirements.txt`
   - **Start Command**: `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. **"Advanced"** 섹션에서 환경 변수 설정:
   - `DATABASE_URL`: PostgreSQL 연결 문자열 (자동 연결 가능)
   - `API_HOST`: `0.0.0.0`
   - `API_PORT`: `8000` (또는 `$PORT` 사용)
   - `CORS_ORIGINS`: 프론트엔드 URL (나중에 업데이트)
   - `SCRAPING_INTERVAL_MINUTES`: `3`
   - `CACHE_TTL_MINUTES`: `5`
   - `DB_POOL_SIZE`: `10`
   - `NAVER_CLIENT_ID`: (선택사항)
   - `NAVER_CLIENT_SECRET`: (선택사항)
   - `API_KEY`: (선택사항)
6. **"Create Web Service"** 클릭

#### 2-3. Frontend 서비스 생성

1. Render.com 대시보드에서 **"New +"** 클릭
2. **"Static Site"** 선택
3. GitHub 저장소 연결
4. 설정:
   - **Name**: `etf-report-frontend`
   - **Branch**: `main`
   - **Root Directory**: `frontend`
   - **Build Command**: `npm install && npm run build`
   - **Publish Directory**: `dist`
5. 환경 변수 설정:
   - `VITE_API_BASE_URL`: `https://etf-report-backend.onrender.com/api`
   - `VITE_APP_TITLE`: `ETF Weekly Report`
6. **"Create Static Site"** 클릭

### 3단계: 환경 변수 업데이트

#### Backend CORS 설정 업데이트

1. Backend 서비스 페이지로 이동
2. **"Environment"** 탭 클릭
3. `CORS_ORIGINS` 환경 변수 수정:
   ```
   https://etf-report-frontend.onrender.com,http://localhost:5173
   ```
4. **"Save Changes"** 클릭

### 4단계: 배포 확인

1. **Backend 확인**:
   - Backend 서비스 URL: `https://etf-report-backend.onrender.com`
   - Health Check: `https://etf-report-backend.onrender.com/api/health`
   - API 문서: `https://etf-report-backend.onrender.com/docs`

2. **Frontend 확인**:
   - Frontend URL: `https://etf-report-frontend.onrender.com`
   - 브라우저에서 접속하여 정상 작동 확인

## 🔧 환경 변수 설정

### Backend 환경 변수

| 변수명 | 설명 | 기본값 | 필수 |
|--------|------|--------|------|
| `DATABASE_URL` | PostgreSQL 연결 문자열 | - | ✅ |
| `API_HOST` | 서버 호스트 | `0.0.0.0` | ❌ |
| `API_PORT` | 서버 포트 | `8000` | ❌ |
| `CORS_ORIGINS` | CORS 허용 오리진 | - | ✅ |
| `SCRAPING_INTERVAL_MINUTES` | 데이터 수집 간격 (분) | `3` | ❌ |
| `CACHE_TTL_MINUTES` | 캐시 TTL (분) | `5` | ❌ |
| `DB_POOL_SIZE` | DB 연결 풀 크기 | `10` | ❌ |
| `NAVER_CLIENT_ID` | Naver API 클라이언트 ID | - | ❌ |
| `NAVER_CLIENT_SECRET` | Naver API 시크릿 | - | ❌ |
| `API_KEY` | API 인증 키 | - | ❌ |

### Frontend 환경 변수

| 변수명 | 설명 | 기본값 | 필수 |
|--------|------|------|------|
| `VITE_API_BASE_URL` | Backend API URL | `/api` | ❌ |
| `VITE_APP_TITLE` | 앱 제목 | `ETF Weekly Report` | ❌ |

## 📝 render.yaml 사용 (선택사항)

프로젝트 루트에 `render.yaml` 파일이 있으면 Render.com이 자동으로 서비스를 생성합니다.

1. Render.com 대시보드에서 **"New +"** 클릭
2. **"Blueprint"** 선택
3. GitHub 저장소 연결
4. **"Apply"** 클릭

`render.yaml` 파일이 있으면 위의 수동 설정 단계를 건너뛸 수 있습니다.

## ⚠️ 주의사항

### 무료 플랜 제한사항

1. **슬리프 모드**: 15분간 요청이 없으면 서비스가 슬리프 모드로 전환됩니다.
   - 첫 요청 시 약 30초 정도 지연될 수 있습니다.
   - 해결책: 유료 플랜 사용 또는 외부 모니터링 서비스 사용

2. **월 사용 시간**: 750시간/월 제한
   - 무료 플랜은 월 750시간까지 사용 가능
   - 24시간 운영 시 약 31일 사용 가능

3. **PostgreSQL 제한**:
   - 무료 플랜: 1GB 저장 공간
   - 90일간 비활성 시 삭제될 수 있음

### Selenium 관련

- Render.com 무료 플랜에서는 Selenium을 사용한 웹 스크래핑이 제한될 수 있습니다.
- 가능하면 API 기반 데이터 수집으로 전환하는 것을 권장합니다.

### 데이터베이스 마이그레이션

- SQLite에서 PostgreSQL로 자동 마이그레이션됩니다.
- `init_db()` 함수가 실행되면서 스키마가 자동 생성됩니다.

## 🔍 문제 해결

### Backend가 시작되지 않는 경우

1. **로그 확인**: Render.com 대시보드에서 로그 확인
2. **환경 변수 확인**: `DATABASE_URL`이 올바르게 설정되었는지 확인
3. **의존성 확인**: `requirements.txt`에 모든 패키지가 포함되어 있는지 확인

### Frontend가 API를 호출하지 못하는 경우

1. **CORS 설정 확인**: Backend의 `CORS_ORIGINS`에 Frontend URL이 포함되어 있는지 확인
2. **API URL 확인**: Frontend의 `VITE_API_BASE_URL`이 올바른지 확인
3. **브라우저 콘솔 확인**: 네트워크 에러 메시지 확인

### 데이터베이스 연결 오류

1. **연결 문자열 확인**: `DATABASE_URL` 형식이 올바른지 확인
2. **데이터베이스 상태 확인**: Render.com에서 데이터베이스가 실행 중인지 확인
3. **방화벽 확인**: 데이터베이스가 외부 접근을 허용하는지 확인

## 📚 추가 리소스

- [Render.com 문서](https://render.com/docs)
- [FastAPI 배포 가이드](https://fastapi.tiangolo.com/deployment/)
- [Vite 빌드 가이드](https://vitejs.dev/guide/build.html)

## 🎉 배포 완료

배포가 완료되면 다음 URL로 접속할 수 있습니다:

- **Frontend**: `https://etf-report-frontend.onrender.com`
- **Backend API**: `https://etf-report-backend.onrender.com`
- **API 문서**: `https://etf-report-backend.onrender.com/docs`

축하합니다! 🎊
