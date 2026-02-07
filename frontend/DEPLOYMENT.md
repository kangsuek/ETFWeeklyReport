# Render.com 배포 가이드

ETF Weekly Report를 **Render.com**에서 프론트엔드(Static Site)와 백엔드(Web Service)로 배포하는 방법입니다.  
상세 단계·트러블슈팅은 **[docs/RENDER_DEPLOYMENT.md](../docs/RENDER_DEPLOYMENT.md)**를 참고하세요.

---

## 사전 요구사항

- **Render.com 계정**: https://render.com
- **GitHub 저장소**에 프로젝트 푸시 완료
- **Naver API 키** (선택): 뉴스 수집 시에만 필요

---

## 배포 구성

| 서비스 | 타입 | Root Directory | Build Command | Start / Publish |
|--------|------|----------------|---------------|-----------------|
| **Backend** | Web Service | (루트) | `pip install -r backend/requirements.txt` | `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| **Frontend** | Static Site | `frontend` | `npm install && npm run build` | Publish: `dist` |
| **DB** | PostgreSQL | - | - | Render에서 생성 후 `DATABASE_URL` 연결 |

---

## 프론트엔드 (Static Site) 배포

### 1. Render에서 Static Site 생성

1. Render 대시보드 → **New +** → **Static Site**
2. GitHub 저장소 연결, Branch: `main`
3. 설정:
   - **Name**: `etf-report-frontend` (원하는 이름)
   - **Root Directory**: `frontend`
   - **Build Command**: `npm install && npm run build`
   - **Publish Directory**: `dist`
   - **Plan**: Free

### 2. 환경 변수 (필수)

빌드 시점에 주입되므로 **반드시 설정**해야 합니다.

| 변수 | 설명 | 예시 |
|------|------|------|
| `VITE_API_BASE_URL` | 백엔드 API Base URL | `https://etf-report-backend.onrender.com/api` |

- URL 끝에 **슬래시(`/`) 붙이지 마세요.**
- 백엔드를 먼저 배포한 뒤 생성된 URL을 넣습니다. 나중에 변경 시 Frontend를 다시 배포해야 합니다.

### 3. 배포 후

- 생성된 URL (예: `https://etf-report-frontend.onrender.com`)을 백엔드 **CORS_ORIGINS**에 추가합니다.

---

## 백엔드 (Web Service) 배포

### 1. PostgreSQL 생성

1. **New +** → **PostgreSQL**
2. Name, Region 설정 후 생성
3. **Connections** 탭에서 **Internal Database URL** 복사

### 2. Web Service 생성

1. **New +** → **Web Service**
2. 저장소 연결, Branch: `main`
3. 설정:
   - **Root Directory**: (비움)
   - **Build Command**: `pip install -r backend/requirements.txt`
   - **Start Command**: `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: Free

### 3. 환경 변수

| 변수 | 설명 | 비고 |
|------|------|------|
| `DATABASE_URL` | PostgreSQL Internal Database URL | 필수 |
| `API_KEY` | 관리용 API 키 (수집·설정·DB 초기화) | 프로덕션 권장 |
| `CORS_ORIGINS` | 프론트엔드 URL | 프론트 배포 후 설정 |
| `NAVER_CLIENT_ID` / `NAVER_CLIENT_SECRET` | 뉴스 수집 | 선택 |
| `SCRAPING_INTERVAL_MINUTES` | 수집 간격(분) | 무료 플랜 권장 `60` |
| `CACHE_TTL_MINUTES` | 캐시(분) | 기본 `5` |
| `DB_POOL_SIZE` | DB 연결 풀 | 무료 플랜 권장 `5` |

---

## render.yaml 사용 (권장)

프로젝트 루트에 `render.yaml`이 있으면 **Blueprint**로 한 번에 배포할 수 있습니다.

1. Render → **New +** → **Blueprint**
2. GitHub 저장소 연결
3. `render.yaml` 자동 감지 후 **Apply**
4. 배포 완료 후 대시보드에서 **Frontend / Backend** 각각 환경 변수 설정 (위 표 참고)

---

## 로컬에서 프로덕션 빌드 확인

배포 전에 로컬에서 프로덕션 빌드를 테스트할 수 있습니다.

```bash
# 루트 .env 또는 frontend에서 빌드 시 사용할 값 설정
# VITE_API_BASE_URL=https://your-backend.onrender.com/api

cd frontend
npm run build
npm run preview
```

- http://localhost:4173 에서 `dist/` 내용 미리보기

---

## 무료 플랜 참고

- **슬리프 모드**: 15분 무요청 시 슬립 → 첫 요청 시 30초~1분 지연 가능. UptimeRobot 등 Keep-Alive 권장.
- **월 750시간**: Backend + Frontend 합산.
- **PostgreSQL**: 90일 비활성 시 삭제 가능, 1GB 제한.

---

## 트러블슈팅

| 증상 | 확인 사항 |
|------|-----------|
| CORS 에러 | Backend `CORS_ORIGINS`에 프론트 URL 포함, 끝에 `/` 없음, HTTPS |
| API 호출 실패 | `VITE_API_BASE_URL` 값, Backend 서비스 실행 여부, `/api/health` 확인 |
| 빌드 실패 | Render 로그 확인, Node 18+, `npm install && npm run build` 로컬 재현 |
| 첫 로딩 느림 | 슬리프 모드 — Keep-Alive 또는 유료 플랜 |

---

## 참고

- **상세 가이드**: [docs/RENDER_DEPLOYMENT.md](../docs/RENDER_DEPLOYMENT.md) (DB 초기화, CORS 업데이트, 트러블슈팅 상세)
- [Render 공식 문서](https://render.com/docs)
