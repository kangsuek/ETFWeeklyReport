# Render.com 환경 변수 설정 가이드

이 문서는 Render.com에 배포할 때 설정해야 하는 환경 변수 목록입니다.

## Backend 서비스 환경 변수

Render 대시보드에서 `etf-report-backend` 서비스의 "Environment" 탭에서 설정하세요.

### 필수 환경 변수

| 변수명 | 설명 | 예시 값 | 비고 |
|--------|------|---------|------|
| `DATABASE_URL` | PostgreSQL 연결 문자열 | 자동 설정됨 | `render.yaml`에서 자동 연결 |
| `CORS_ORIGINS` | 프론트엔드 도메인 | `https://etf-report-frontend.onrender.com` | 프론트엔드 배포 후 설정 |

### 선택적 환경 변수

| 변수명 | 설명 | 예시 값 | 기본값 |
|--------|------|---------|--------|
| `NAVER_CLIENT_ID` | Naver API Client ID | `your_client_id` | 뉴스 수집 기능 사용 시 필요 |
| `NAVER_CLIENT_SECRET` | Naver API Client Secret | `your_client_secret` | 뉴스 수집 기능 사용 시 필요 |
| `SCRAPING_INTERVAL_MINUTES` | 데이터 수집 간격 (분) | `60` | 무료 플랜 고려 |
| `CACHE_TTL_MINUTES` | 캐시 유지 시간 (분) | `5` | - |
| `DB_POOL_SIZE` | 데이터베이스 연결 풀 크기 | `5` | 무료 플랜 권장 |

### 자동 설정되는 변수

다음 변수들은 `render.yaml`에서 자동으로 설정되므로 수동 설정이 필요 없습니다:

- `PYTHON_VERSION`: `3.11.9`
- `API_HOST`: `0.0.0.0`
- `API_PORT`: Render가 자동으로 설정 (`$PORT`)

## Frontend 서비스 환경 변수

Render 대시보드에서 `etf-report-frontend` 서비스의 "Environment" 탭에서 설정하세요.

### 필수 환경 변수

| 변수명 | 설명 | 예시 값 |
|--------|------|---------|
| `VITE_API_BASE_URL` | 백엔드 API URL | `https://etf-report-backend.onrender.com/api` |

### 선택적 환경 변수

| 변수명 | 설명 | 예시 값 | 기본값 |
|--------|------|---------|--------|
| `VITE_APP_TITLE` | 애플리케이션 제목 | `ETF Weekly Report` | - |

## 설정 순서

1. **데이터베이스 생성**: `render.yaml`에서 자동 생성됨
2. **Backend 배포**: `DATABASE_URL`은 자동 연결됨
3. **Frontend 배포**: `VITE_API_BASE_URL`을 백엔드 URL로 설정
4. **CORS 설정**: Backend의 `CORS_ORIGINS`를 프론트엔드 URL로 업데이트

## 환경 변수 설정 방법

### Render 대시보드에서 설정

1. Render 대시보드 접속
2. 해당 서비스 선택
3. "Environment" 탭 클릭
4. "Add Environment Variable" 클릭
5. 변수명과 값 입력
6. "Save Changes" 클릭
7. 서비스가 자동으로 재시작됨

### 주의사항

- 환경 변수 변경 후 서비스가 자동으로 재시작됩니다
- `DATABASE_URL`은 수동으로 설정하지 마세요 (자동 연결됨)
- `CORS_ORIGINS`는 프론트엔드 URL이 생성된 후 설정하세요
- URL 끝에 슬래시(`/`)를 붙이지 마세요
