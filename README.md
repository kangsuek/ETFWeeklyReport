# ETF Weekly Report Web Application

한국 고성장 섹터 **ETF·주식**에 대한 종합 분석 및 리포팅 웹 애플리케이션입니다.  
종목은 **설정**에서 자유롭게 추가·수정·삭제할 수 있으며, 포트폴리오(매입가·수량)를 입력하면 투자 현황과 기여도까지 한눈에 볼 수 있습니다.

---

## 주요 기능

| 기능 | 설명 |
|------|------|
| **대시보드** | 상단 **히트맵**(전체 현황·일간 변동률, 투자/관심 종목 구분) + 하단 **카드 그리드**(종가, 등락률, 미니 차트, 매매동향, 뉴스). 정렬(설정순·타입·이름·테마·커스텀), 드래그앤드롭 순서 변경, 자동/수동 갱신 |
| **종목 상세** | 투자 전략·핵심 포인트, 가격/통계, 가격·매매동향·RSI·MACD 차트, 분봉, 지지/저항선, 뉴스 타임라인 |
| **종목 비교** | 2~6종목 선택, 정규화 가격 차트(시작일=100), 수익률·변동성·MDD·샤프 비율 비교 테이블 |
| **포트폴리오** | 총 투자금·평가금·손익·수익률, 비중 파이차트, 일별 추이 차트, 종목별 기여도 테이블, 포트폴리오 분석 리포트 |
| **설정** | 다크 모드, 자동 갱신 간격, 기본 날짜 범위, **종목 추가/수정/삭제**, 데이터 수집·DB 초기화·캐시 관리 |

---

## 대상 종목 (예시)

종목은 **설정 > 종목 관리**에서 추가·삭제할 수 있습니다.  
초기 설치 시 `backend/config/stocks.json`에 등록된 종목이 사용되며, 예시는 다음과 같습니다.

- **ETF**: K-반도체, 글로벌반도체, KODEX 200미국채혼합, 로봇액티브, K방산, 조선TOP3, AI전력핵심설비, 양자컴퓨팅, 글로벌원자력, 금채굴기업, 자동차, 커버드콜 등
- **주식**: HD현대일렉트릭 등

매입가·수량을 입력한 종목은 **투자 종목**, 미입력 종목은 **관심 종목**으로 구분되어 대시보드 히트맵과 포트폴리오에 반영됩니다.

---

## 로컬 실행 가이드 (Quick Start)

### 사전 요구사항

| 요구사항 | 버전 | 확인 명령어 |
|---------|------|------------|
| Python | 3.11+ | `python3 --version` |
| Node.js | 18+ | `node --version` |
| npm | 9+ | `npm --version` |
| Git | 최신 | `git --version` |

### 한 번에 설정하기 (권장)

```bash
# 1. 프로젝트 클론
git clone https://github.com/your-repo/ETFWeeklyReport.git
cd ETFWeeklyReport

# 2. 백엔드 설정
cd backend
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements-dev.txt
cd .. && cp .env.example .env && cd backend   # 루트에 .env 생성 (백엔드/프론트 공용)
python -m app.database

# 3. 프론트엔드 설정 (새 터미널에서)
cd ../frontend
npm install

# 4. 서버 시작 (프로젝트 루트에서)
cd ..
./scripts/start-servers.sh
```

- **백엔드**: http://localhost:8000 (API 문서: `/docs`)
- **프론트엔드**: http://localhost:5173

---

## 상세 설정 가이드

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
# 환경 변수: 프로젝트 루트의 .env 만 사용 (루트에서 cp .env.example .env)
python -m app.database
uvicorn app.main:app --reload
```

- **API 문서 (Swagger)**: http://localhost:8000/docs
- **Health**: http://localhost:8000/api/health

환경 변수는 **프로젝트 루트**의 `.env` 한 파일만 사용합니다. 루트에서 `cp .env.example .env` 후 `API_KEY`(관리용, 선택), `DATABASE_URL`, `NAVER_CLIENT_ID`/`NAVER_CLIENT_SECRET`(뉴스 수집용, 선택) 등을 설정하세요.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

- **웹 앱**: http://localhost:5173

`.env`에 `VITE_API_BASE_URL`(기본: `/api`), `VITE_APP_TITLE` 등 설정 가능합니다.

---

## 스크립트

| 명령 | 설명 |
|------|------|
| `./scripts/start-servers.sh` | 백엔드(8000) + 프론트(5173) 동시 시작 |
| `./scripts/stop-servers.sh` | 실행 중인 서버 종료 |

---

## 테스트

```bash
# 백엔드
cd backend && source venv/bin/activate && pytest -v
pytest --cov=app --cov-report=html

# 프론트엔드
cd frontend && npm test
npm run test:coverage
```

---

## 주요 API (요약)

| 구분 | 엔드포인트 예시 |
|------|-----------------|
| 종목 | `GET /api/etfs`, `GET /api/etfs/{ticker}`, `GET /api/etfs/{ticker}/prices`, `GET /api/etfs/{ticker}/trading-flow`, `GET /api/etfs/{ticker}/metrics`, `GET /api/etfs/{ticker}/insights`, `GET /api/etfs/{ticker}/intraday` |
| 배치·비교 | `POST /api/etfs/batch-summary`, `GET /api/etfs/compare?tickers=...` |
| 뉴스 | `GET /api/news/{ticker}` |
| 데이터 | `POST /api/data/collect-all`, `GET /api/data/scheduler-status`, `GET /api/data/stats`, `DELETE /api/data/reset` |
| 설정 | `GET/POST /api/settings/stocks`, `PUT/DELETE /api/settings/stocks/{ticker}`, `GET /api/settings/stocks/search`, `POST /api/settings/stocks/reorder`, `POST /api/settings/ticker-catalog/collect` |

상세 스펙은 [docs/API_SPECIFICATION.md](./docs/API_SPECIFICATION.md) 및 [docs/FEATURES.md](./docs/FEATURES.md)를 참고하세요.

---

## 기술 스택

| 구분 | 기술 |
|------|------|
| **Backend** | FastAPI, Python 3.11, SQLite / PostgreSQL, APScheduler, Pandas |
| **Frontend** | React 18, Vite 5, Tailwind CSS, TanStack React Query, Recharts, React Router 6 |

---

## 문서

| 문서 | 설명 |
|------|------|
| [CLAUDE.md](./CLAUDE.md) | 문서 인덱스 |
| [docs/FEATURES.md](./docs/FEATURES.md) | 제공 기능 상세 |
| [docs/SETUP_GUIDE.md](./docs/SETUP_GUIDE.md) | 환경 설정·실행·Pre-commit |
| [docs/DEVELOPMENT_GUIDE.md](./docs/DEVELOPMENT_GUIDE.md) | 개발 가이드 |
| [docs/API_SPECIFICATION.md](./docs/API_SPECIFICATION.md) | REST API 명세 |
| [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) | 시스템 아키텍처 |
| [docs/PROJECT_STRUCTURE.md](./docs/PROJECT_STRUCTURE.md) | 파일 구조 (표준 정합성) |
| [docs/DATABASE_SCHEMA.md](./docs/DATABASE_SCHEMA.md) | DB 스키마 |
| [docs/INTRADAY.md](./docs/INTRADAY.md) | 분봉 차트 조회·수집 |
| [docs/TECH_STACK.md](./docs/TECH_STACK.md) | 기술 스택 |
| [docs/RENDER_DEPLOYMENT.md](./docs/RENDER_DEPLOYMENT.md) | Render.com 배포 |
| [docs/SECURITY_CHECKLIST.md](./docs/SECURITY_CHECKLIST.md) | 보안 체크리스트 |

---

## 데이터 소스

- **네이버 금융**: 가격, 투자자별 매매 동향, 분봉
- **네이버 검색 API**: 뉴스 (선택, API 키 필요)

---

## 라이센스

MIT License
