# 기술 스택

## 백엔드

| 기술 | 버전 | 용도 |
|------|------|------|
| **Python** | 3.11.9 | 프로그래밍 언어 |
| **FastAPI** | 0.104.1 | 웹 프레임워크 |
| **Uvicorn** | 0.24.0 | ASGI 서버 |
| **Pydantic** | 2.5.0 | 데이터 검증 |
| **pandas** | 2.1.3 | 데이터 분석 |
| **requests** | 2.31.0 | HTTP 요청 |
| **BeautifulSoup4** | 4.12.2 | HTML 파싱 |
| **SQLite** | - | 개발 DB |
| **PostgreSQL** | - | 프로덕션 DB |

**주요 데이터 소스**: Naver Finance (네이버 증권) 웹 스크래핑

## 프론트엔드

| 기술 | 버전 | 용도 |
|------|------|------|
| **React** | 18.2.0 | UI 라이브러리 |
| **Vite** | 5.0.0 | 빌드 도구 |
| **React Router** | 6.20.0 | 라우팅 |
| **TanStack Query** | 5.8.4 | 서버 상태 관리 |
| **Axios** | 1.6.2 | HTTP 요청 |
| **TailwindCSS** | 3.3.5 | CSS 프레임워크 |
| **Recharts** | 2.10.3 | 차트 라이브러리 |
| **date-fns** | 2.30.0 | 날짜 포맷팅 |

## 개발 도구
- **테스트**: pytest, pytest-cov (백엔드)
- **포매팅**: black, isort (백엔드)
- **린팅**: flake8, pylint (백엔드), ESLint (프론트엔드)
- **타입 체킹**: mypy (백엔드)

## 배포
- **프론트엔드**: Vercel, Netlify
- **백엔드**: Render, Railway
- **데이터베이스**: Supabase, Neon (PostgreSQL)
