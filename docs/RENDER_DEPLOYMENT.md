# Render.com 배포 가이드

ETF Weekly Report를 Render.com에 배포하는 전체 절차입니다.
PostgreSQL(DB) + Web Service(백엔드) + Static Site(프론트엔드) 3개 서비스를 구성합니다.

---

## 배포 전 필수 확인 사항

배포 실패의 가장 흔한 원인 4가지를 먼저 이해하세요.

| # | 문제 | 증상 | 원인 |
|---|------|------|------|
| 1 | `API_KEY` 미설정 | 데이터 수집/설정 API → **503** | Render 환경(`RENDER` env 존재)에서 `API_KEY` 없으면 인증 미들웨어가 모든 protected 요청 거부 |
| 2 | `VITE_API_BASE_URL` 미설정 | API 호출 → **404** | 기본값 `/api`가 프론트 정적 사이트 자체로 요청됨 |
| 3 | `CORS_ORIGINS` 미설정 | 브라우저 → **CORS 에러** | 백엔드가 프론트 도메인을 허용하지 않음 |
| 4 | 초기 데이터 수집 누락 | 모든 API → **빈 배열** `[]` | DB 테이블은 생성됐지만 데이터 수집을 한 번도 실행하지 않은 상태 |

---

## 방법 A: render.yaml Blueprint (권장)

### 1단계 — render.yaml startCommand 수정

현재 `render.yaml`의 `startCommand`는 DB 초기화(`python -m app.database`)를 건너뜁니다.
`render-start.sh`를 사용하도록 수정합니다.

```yaml
# render.yaml 수정 전
startCommand: cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT

# render.yaml 수정 후 (render-start.sh 사용)
startCommand: cd backend && bash render-start.sh
```

`backend/render-start.sh`가 하는 일:
```bash
#!/bin/bash
python -m app.database   # DB 테이블 생성 (없으면 생성, 있으면 건너뜀)
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

### 2단계 — Blueprint 배포

1. [Render 대시보드](https://dashboard.render.com) → **New +** → **Blueprint**
2. GitHub 저장소 연결 → `render.yaml` 자동 감지 → **Apply**
3. PostgreSQL, Backend Web Service, Frontend Static Site 3개 서비스 자동 생성됨

### 3단계 — 환경 변수 설정 (필수)

Blueprint 배포 후 Render 대시보드에서 각 서비스에 아래 값을 입력합니다.

#### ① Backend 서비스 환경 변수

Render 대시보드 → `etf-report-backend` → **Environment** 탭

| 변수 | 설명 | 예시 |
|------|------|------|
| `DATABASE_URL` | PostgreSQL → **Connections** 탭 → **Internal Database URL** | `postgresql://user:pass@host/dbname` |
| `API_KEY` | 관리용 비밀키 (임의로 생성) | `openssl rand -hex 32` 출력값 |
| `CORS_ORIGINS` | 프론트엔드 URL (끝에 `/` 없이) | `https://etf-report-frontend.onrender.com` |
| `NAVER_CLIENT_ID` | Naver 검색 API ID (뉴스 수집 시 필요) | |
| `NAVER_CLIENT_SECRET` | Naver 검색 API Secret (뉴스 수집 시 필요) | |
| `SCRAPING_INTERVAL_MINUTES` | 수집 간격(분), 무료 플랜은 `60` 권장 | `60` |
| `CACHE_TTL_MINUTES` | 캐시 TTL(분) | `5` |
| `DB_POOL_SIZE` | DB 연결 풀 크기, 무료 플랜은 `5` 권장 | `5` |

> **`API_KEY`는 반드시 설정하세요.** Render 환경(`RENDER` 환경 변수 자동 주입)에서 `API_KEY`가 없으면 인증 미들웨어가 모든 쓰기 요청에 503을 반환합니다.

#### ② Frontend 서비스 환경 변수

Render 대시보드 → `etf-report-frontend` → **Environment** 탭

| 변수 | 설명 | 예시 |
|------|------|------|
| `VITE_API_BASE_URL` | 백엔드 API Base URL (끝에 `/` 없이) | `https://etf-report-backend.onrender.com/api` |
| `VITE_API_KEY` | Backend의 `API_KEY`와 동일한 값 (데이터 수집/설정 기능) | |

> **`VITE_API_BASE_URL`은 반드시 설정하세요.** 미설정 시 기본값 `/api`(상대경로)가 사용되어 프론트엔드 정적 사이트 자체에 API를 요청해 404가 발생합니다.
> `VITE_` 접두사 변수는 **빌드 시점**에 코드에 삽입되므로, 값 변경 후에는 반드시 **재배포**해야 합니다.

### 4단계 — 프론트엔드 재배포

`VITE_API_BASE_URL`을 설정한 뒤, Frontend 서비스에서 **Manual Deploy → Deploy latest commit** 클릭.

---

## 방법 B: 수동 설정

### 1. PostgreSQL 생성

1. **New +** → **PostgreSQL**
2. Name: `etf-report-db`, Region: Singapore, Plan: Free
3. 생성 후 **Connections** 탭 → **Internal Database URL** 복사 (백엔드 설정에서 사용)

### 2. 백엔드 Web Service 생성

1. **New +** → **Web Service** → GitHub 저장소 연결 → Branch: `main`
2. 설정:

| 항목 | 값 |
|------|-----|
| **Root Directory** | (비움) |
| **Environment** | Python 3 |
| **Region** | Singapore |
| **Build Command** | `pip install -r backend/requirements.txt` |
| **Start Command** | `cd backend && bash render-start.sh` |
| **Plan** | Free |

3. **Environment Variables**에서 위 [Backend 환경 변수 표](#-backend-서비스-환경-변수) 참고하여 입력
4. **Create Web Service** 클릭

### 3. 프론트엔드 Static Site 생성

1. **New +** → **Static Site** → GitHub 저장소 연결 → Branch: `main`
2. 설정:

| 항목 | 값 |
|------|-----|
| **Root Directory** | `frontend` |
| **Build Command** | `npm install && npm run build` |
| **Publish Directory** | `dist` |
| **Plan** | Free |

3. **Environment Variables**에서 `VITE_API_BASE_URL`, `VITE_API_KEY` 설정
4. **Create Static Site** 클릭

### 4. CORS 업데이트

프론트엔드 배포 후 생성된 URL을 백엔드 `CORS_ORIGINS`에 설정하고 백엔드를 재배포합니다.

---

## 배포 후 초기 데이터 수집

DB 테이블은 `render-start.sh` 실행 시 자동 생성되지만, 가격·수급 데이터는 직접 수집해야 합니다.

### 헬스 체크

```bash
curl https://etf-report-backend.onrender.com/api/health
# {"status": "ok"} 확인
```

### curl로 수집 트리거

```bash
export BACKEND_URL="https://etf-report-backend.onrender.com"
export API_KEY="your-api-key-here"

# 전체 종목 30일치 가격·수급 수집
curl -X POST "$BACKEND_URL/api/data/collect-all?days=30" \
  -H "X-API-Key: $API_KEY"

# 수집 진행 상황 확인
curl "$BACKEND_URL/api/data/collect-progress"

# DB 통계 확인 (prices count가 0보다 커야 정상)
curl "$BACKEND_URL/api/data/stats"
```

### 앱 설정 화면에서 수집

1. 프론트엔드 URL 접속 → **설정** 메뉴
2. **API 키** 입력 (백엔드 `API_KEY`와 동일)
3. **데이터 관리** → **전체 수집** 버튼 클릭
4. 진행률 바 확인

---

## DB 관리

### 테이블 생성 (자동)

배포/재시작 시 `render-start.sh`가 `python -m app.database`를 실행하여 테이블을 자동 생성합니다.
`CREATE TABLE IF NOT EXISTS`를 사용하므로 이미 있는 테이블은 영향 없습니다.

### 데이터만 초기화 (API)

가격·뉴스·수급 데이터만 삭제하고 종목 목록은 유지:

```bash
curl -X DELETE "https://etf-report-backend.onrender.com/api/data/reset" \
  -H "X-API-Key: YOUR_API_KEY"
```

> **되돌릴 수 없습니다.** 실행 전 확인하세요.

### 스키마 완전 초기화 (PostgreSQL DROP)

테이블까지 모두 삭제 후 재생성하려면:

1. Render 대시보드 → PostgreSQL 서비스 → **Connect** → PSQL 또는 External URL로 접속
2. 아래 SQL 실행:

```sql
DROP TABLE IF EXISTS
  alert_history, alert_rules, intraday_prices, collection_status,
  news, trading_flow, prices, etf_holdings, etf_fundamentals,
  etf_rebalancing, etf_distributions, stock_fundamentals,
  stock_distributions, stock_catalog, etfs CASCADE;
```

3. 백엔드 서비스 **Manual Deploy** 또는 **Restart** → `init_db()` 재실행으로 테이블 재생성

---

## 트러블슈팅

### 데이터 수집/설정 API → 503 오류

**원인**: Render 환경에서 `API_KEY`가 미설정됨.
```
# 확인: 백엔드 로그에 아래 메시지가 있으면 이 문제
[인증] 프로덕션 환경에서 API_KEY가 설정되지 않았습니다! 요청을 거부합니다.
```
**해결**: Backend 환경 변수에 `API_KEY` 설정 후 재배포.

---

### API 요청이 404 (정적 사이트 자체로 요청)

**원인**: `VITE_API_BASE_URL` 미설정으로 `/api` 상대경로 사용.
```
# Network 탭에서 확인: 요청 URL이 아래처럼 보이면 이 문제
GET https://etf-report-frontend.onrender.com/api/etfs
```
**해결**: Frontend 환경 변수 `VITE_API_BASE_URL=https://etf-report-backend.onrender.com/api` 설정 후 **재배포**.

---

### 브라우저 콘솔에 CORS 에러

**원인**: `CORS_ORIGINS`에 프론트엔드 도메인이 없음.
```
Access to XMLHttpRequest at 'https://...backend...' from origin 'https://...frontend...'
has been blocked by CORS policy
```
**해결**: Backend 환경 변수 `CORS_ORIGINS=https://etf-report-frontend.onrender.com` (끝에 `/` 없이) 설정 후 백엔드 재배포.

---

### 모든 API 응답이 빈 배열 `[]`

**원인**: 데이터 수집을 한 번도 실행하지 않음.
**해결**: [초기 데이터 수집](#배포-후-초기-데이터-수집) 섹션 참고.

---

### DB 테이블 없음 에러

**원인**: `startCommand`가 `uvicorn`만 실행하고 `python -m app.database` 미실행.
**해결**: Start Command를 `cd backend && bash render-start.sh`로 변경 후 재배포.

---

### 첫 요청이 30초 이상 느림

**원인**: 무료 플랜 슬립 모드 (15분 무요청 시 슬립).
**해결**: [UptimeRobot](https://uptimerobot.com) 등에서 5분마다 `https://...backend.../api/health` 모니터링 설정.

---

## 배포 완료 체크리스트

```
□ Backend: /api/health → {"status": "ok"}
□ Frontend: 페이지 로딩 정상
□ Network 탭: API 요청이 backend URL(etf-report-backend.onrender.com)로 전송됨
□ 브라우저 콘솔: CORS 에러 없음
□ 설정 화면: API 키 입력 후 수집 버튼 작동
□ 대시보드: 종목 카드 표시됨
```

---

## 참고

- [render.yaml](../render.yaml) — Render Blueprint 설정 파일
- [frontend/DEPLOYMENT.md](../frontend/DEPLOYMENT.md) — 프론트엔드 배포 간략 가이드
- [Render 공식 문서](https://render.com/docs)
- [Naver Developers](https://developers.naver.com/apps/#/register) — API 키 발급
