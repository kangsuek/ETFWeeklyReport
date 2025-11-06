# 기술 스택

## 백엔드

### 프레임워크 및 코어

| 기술 | 버전 | 용도 |
|------|------|------|
| **Python** | 3.10+ | 프로그래밍 언어 |
| **FastAPI** | 0.104.1 | 웹 프레임워크 |
| **Uvicorn** | 0.24.0 | ASGI 서버 |
| **Pydantic** | 2.5.0 | 데이터 검증 및 설정 관리 |

### 데이터 처리

| 기술 | 버전 | 용도 |
|------|------|------|
| **pandas** | 2.1.3 | 데이터 분석 및 가공 |
| **numpy** | 1.26.2 | 수치 연산 |
| **python-dateutil** | 2.8.2 | 날짜 처리 |

### 데이터 수집

| 기술 | 버전 | 용도 |
|------|------|------|
| **requests** | 2.31.0 | HTTP 요청 |
| **BeautifulSoup4** | 4.12.2 | HTML 파싱 (웹 스크래핑) |
| **lxml** | 4.9.3 | XML/HTML 파서 |
| **FinanceDataReader** | 0.9.50 | 한국 주식 데이터 수집 |

### 데이터베이스

| 기술 | 용도 |
|------|------|
| **SQLite** | 개발 환경 데이터베이스 |
| **PostgreSQL** | 프로덕션 데이터베이스 (권장) |

### 기타

| 기술 | 버전 | 용도 |
|------|------|------|
| **python-multipart** | 0.0.6 | 파일 업로드 지원 |
| **aiofiles** | 23.2.1 | 비동기 파일 I/O |

---

## 프론트엔드

### 프레임워크 및 빌드 도구

| 기술 | 버전 | 용도 |
|------|------|------|
| **React** | 18.2.0 | UI 라이브러리 |
| **Vite** | 5.0.0 | 빌드 도구 및 개발 서버 |
| **React Router** | 6.20.0 | 클라이언트 사이드 라우팅 |

### 상태 관리

| 기술 | 버전 | 용도 |
|------|------|------|
| **TanStack Query** (React Query) | 5.8.4 | 서버 상태 관리 및 캐싱 |

### HTTP 클라이언트

| 기술 | 버전 | 용도 |
|------|------|------|
| **Axios** | 1.6.2 | HTTP 요청 |

### UI 및 스타일링

| 기술 | 버전 | 용도 |
|------|------|------|
| **TailwindCSS** | 3.3.5 | 유틸리티 우선 CSS 프레임워크 |
| **PostCSS** | 8.4.31 | CSS 변환 도구 |
| **Autoprefixer** | 10.4.16 | CSS 벤더 접두사 자동 추가 |

### 차트 및 시각화

| 기술 | 버전 | 용도 |
|------|------|------|
| **Recharts** | 2.10.3 | React 차트 라이브러리 |

### 유틸리티

| 기술 | 버전 | 용도 |
|------|------|------|
| **date-fns** | 2.30.0 | 날짜 포맷팅 및 조작 |
| **clsx** | 2.0.0 | 조건부 className 관리 |

---

## 개발 도구

### 코드 품질

| 기술 | 용도 |
|------|------|
| **ESLint** | JavaScript/React 린터 |
| **eslint-plugin-react** | React 전용 린트 규칙 |
| **eslint-plugin-react-hooks** | React Hooks 린트 규칙 |

---

## 인프라 및 배포

### 컨테이너화

| 기술 | 버전 | 용도 |
|------|------|------|
| **Docker** | - | 컨테이너화 |
| **Docker Compose** | 3.8 | 멀티 컨테이너 오케스트레이션 |

### 배포 옵션 (권장)

#### 프론트엔드
- **Vercel** (무료 티어 가능)
- **Netlify** (무료 티어 가능)
- **Cloudflare Pages**

#### 백엔드
- **Render** (무료 티어 가능)
- **Railway** (무료 티어 가능)
- **Fly.io**
- **AWS EC2 / Google Cloud Run / Azure App Service**

#### 데이터베이스
- **Supabase** (무료 PostgreSQL)
- **Neon** (서버리스 PostgreSQL)
- **AWS RDS / Google Cloud SQL**

#### 캐싱 (선택사항)
- **Redis Cloud** (무료 티어)
- **Upstash** (서버리스 Redis)

---

## 선택 기준

### FastAPI 선택 이유

✅ **장점:**
- 자동 API 문서 생성 (Swagger UI)
- Pydantic을 통한 강력한 타입 검증
- 비동기 지원 (높은 성능)
- Python 생태계 활용 가능 (pandas, numpy 등)

### React + Vite 선택 이유

✅ **장점:**
- Vite의 빠른 개발 서버 및 빌드 속도
- React의 풍부한 생태계
- TailwindCSS로 빠른 UI 개발
- React Query로 서버 상태 관리 간소화

### TailwindCSS 선택 이유

✅ **장점:**
- 빠른 프로토타이핑
- 일관된 디자인 시스템
- 작은 번들 크기 (사용하지 않는 클래스 제거)
- 모바일 우선 반응형 디자인

### Recharts 선택 이유

✅ **장점:**
- React 네이티브 (React 컴포넌트 기반)
- 선언적 API
- 반응형 차트
- 커스터마이징 용이

### TanStack Query 선택 이유

✅ **장점:**
- 자동 캐싱 및 백그라운드 업데이트
- 로딩/에러 상태 관리 간소화
- 중복 요청 자동 제거
- 서버 상태와 클라이언트 상태 분리

---

## 환경 변수

### 백엔드 (.env)

```bash
# API 설정
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# 데이터베이스
DATABASE_URL=sqlite:///./data/etf_data.db

# 데이터 수집
CACHE_TTL_MINUTES=10
NEWS_MAX_RESULTS=5

# 선택사항: 외부 API
NAVER_CLIENT_ID=your_client_id
NAVER_CLIENT_SECRET=your_client_secret
```

### 프론트엔드 (.env)

```bash
VITE_API_BASE_URL=http://localhost:8000/api
VITE_APP_TITLE=ETF Weekly Report
```

---

## 의존성 설치

### 백엔드

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 프론트엔드

```bash
cd frontend
npm install
# 또는
yarn install
```

---

## 버전 관리 정책

- **Python**: 3.10 이상 (3.11 권장)
- **Node.js**: 18 LTS 이상 (20 LTS 권장)
- **패키지 업데이트**: 보안 패치는 즉시 적용, 메이저 버전 업그레이드는 테스트 후 적용

---

## 향후 추가 고려 기술

### 백엔드
- [ ] **APScheduler** - 주기적 데이터 수집 스케줄링
- [ ] **Redis** - 캐싱 및 세션 관리
- [ ] **Celery** - 백그라운드 작업 처리
- [ ] **Alembic** - 데이터베이스 마이그레이션

### 프론트엔드
- [ ] **TypeScript** - 타입 안정성 향상
- [ ] **React Testing Library** - 컴포넌트 테스트
- [ ] **Playwright** - E2E 테스트
- [ ] **TanStack Table** - 고급 테이블 기능

### 모니터링
- [ ] **Sentry** - 에러 추적
- [ ] **Google Analytics** - 사용자 분석
- [ ] **Prometheus + Grafana** - 성능 모니터링

---

**Last Updated**: 2025-11-06

