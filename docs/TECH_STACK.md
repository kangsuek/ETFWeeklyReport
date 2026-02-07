# 기술 스택

## 백엔드

| 기술 | 버전 | 용도 |
|------|------|------|
| **Python** | 3.11+ | 프로그래밍 언어 |
| **FastAPI** | 0.104.1 | 웹 프레임워크 |
| **Uvicorn** | 0.24.0 | ASGI 서버 |
| **Pydantic** | 2.5.0 | 데이터 검증·설정 스키마 |
| **pydantic-settings** | 2.1.0 | 환경 변수 기반 설정 |
| **pandas** | 2.1.3 | 데이터 분석·가공 |
| **numpy** | 1.26.2 | 수치 연산 |
| **requests** | 2.31.0 | HTTP 요청 (동기) |
| **BeautifulSoup4** | 4.12.2 | HTML 파싱 |
| **lxml** | 4.9.3 | XML/HTML 파싱 가속 |
| **finance-datareader** | 0.9.96 | 금융 데이터 수집 보조 |
| **aiofiles** | 23.2.1 | 비동기 파일 I/O |
| **APScheduler** | 3.10.4 | 스케줄 작업 (일일 데이터 수집) |
| **slowapi** | 0.1.9 | Rate limiting |
| **limits** | 4.2 | Rate limit 백엔드 |
| **python-dotenv** | 1.0.0 | 루트 `.env` 로드 |
| **python-multipart** | 0.0.6 | multipart 폼 파싱 |
| **structlog** | 23.2.0 | 구조화 로깅 |
| **Selenium** | 4.15.2 | 브라우저 자동화 (분봉 등) |
| **webdriver-manager** | 4.0.1 | WebDriver 자동 관리 |
| **psycopg2-binary** | 2.9.9 | PostgreSQL 드라이버 (프로덕션) |
| **SQLite** | - | 개발·기본 DB |
| **PostgreSQL** | - | 프로덕션 DB (선택) |

**주요 데이터 소스**: 네이버 금융(가격·매매동향·분봉), 네이버 검색 API(뉴스)

## 프론트엔드

| 기술 | 버전 | 용도 |
|------|------|------|
| **React** | 18.2.0 | UI 라이브러리 |
| **Vite** | 5.0.0 | 빌드·개발 서버 |
| **React Router** | 6.20.0 | 라우팅 |
| **TanStack Query** | 5.8.4 | 서버 상태·캐시 |
| **Axios** | 1.6.2 | HTTP 클라이언트 |
| **TailwindCSS** | 3.3.5 | 유틸리티 CSS |
| **Recharts** | 2.10.3 | 차트 (가격·매매동향·비교·포트폴리오·히트맵 등) |
| **date-fns** | 2.30.0 | 날짜 포맷·계산 |
| **@dnd-kit/core** | 6.3.1 | 드래그 앤 드롭 (카드 순서 변경) |
| **@dnd-kit/sortable** | 10.0.0 | 정렬 가능 리스트 |
| **@dnd-kit/utilities** | 3.2.2 | dnd-kit 유틸리티 |
| **clsx** | 2.0.0 | 조건부 클래스명 |
| **prop-types** | 15.8.1 | 런타임 props 검증 |

## 개발 도구

| 구분 | 도구 | 용도 |
|------|------|------|
| **로컬 Python 환경** | uv | 패키지·가상환경 관리 (필수). `uv venv`, `uv pip install`, `uv run` |
| **백엔드 테스트** | pytest, pytest-asyncio, pytest-cov, pytest-mock, httpx | 단위·API 테스트, 커버리지 (requirements-dev.txt) |
| **백엔드 포맷** | black, isort | 코드 포맷팅 (line-length 100) |
| **백엔드 린트** | flake8, pylint | 스타일·정적 분석 |
| **백엔드 타입** | mypy | 정적 타입 검사 |
| **백엔드 기타** | pre-commit, coverage | 훅·커버리지 리포팅 |
| **프론트엔드 테스트** | Vitest, React Testing Library, @testing-library/user-event, MSW, jsdom | 단위·컴포넌트 테스트, API 목업 |
| **프론트엔드 린트** | ESLint (react, hooks, refresh) | 린트 |
| **프론트엔드 빌드** | PostCSS, autoprefixer | CSS 후처리 (Tailwind) |

## 배포

| 구분 | 옵션 |
|------|------|
| **프론트엔드** | Vite 빌드 → `dist/` 정적 호스팅 (Render Static Site, Vercel, Netlify 등) |
| **백엔드** | Uvicorn 기반 (Render Web Service, Railway, Fly.io 등). `render.yaml` Blueprint 지원. |
| **데이터베이스** | SQLite(로컬·기본) 또는 PostgreSQL (Render 등 프로덕션) |

버전 고정: 백엔드는 `requirements.txt` / `requirements-dev.txt`, 프론트엔드는 `package.json` (^ 범위) 참고.
