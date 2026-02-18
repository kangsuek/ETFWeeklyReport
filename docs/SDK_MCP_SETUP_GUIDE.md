# ETF Report API — 새 프로젝트에서 SDK/MCP 사용 환경 구축 가이드

새 프로젝트에서 ETF Report 백엔드를 실행하고, OpenAPI Python SDK 및 MCP 서버를 통해 모든 API 기능을 사용하는 환경을 구축하는 절차입니다.

---

## 전체 구조

```
[새 프로젝트 / AI 에이전트]
        │
        ├── OpenAPI Python SDK (etf_report_client)   ← HTTP 클라이언트
        └── MCP 서버 (etf-report-mcp)                ← AI 도구 인터페이스
                        │
                        ▼ HTTP (localhost:8000)
              [ETF Report Backend (FastAPI)]
                        │
                        ├── SQLite DB               ← 가격·수급·뉴스 데이터
                        ├── Naver API               ← 뉴스 수집 (선택)
                        └── config/stocks.json      ← 종목 설정
```

---

## 1단계: 저장소 클론

```bash
git clone <repository-url> ETFWeeklyReport
cd ETFWeeklyReport
```

---

## 2단계: 백엔드 설치 및 환경 설정

### 2-1. Python 의존성 설치

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -r requirements.txt
pip install -r requirements-dev.txt   # 개발 환경만
```

또는 `uv` 사용 시:

```bash
cd backend
uv venv && uv pip install -r requirements.txt
```

### 2-2. 환경 변수 설정

`backend/.env` 파일을 생성합니다.

```dotenv
# ── 필수 ────────────────────────────────────────────────
# 없으면 backend/data/etf_data.db 에 자동 생성됨 (기본값 사용 권장)
# DATABASE_URL=sqlite:///backend/data/etf_data.db

# ── 선택: API 인증 키 ─────────────────────────────────
# 설정 시 모든 요청에 X-API-Key 헤더 필요
# 설정 안 하면 인증 없이 접근 가능 (로컬 개발 환경)
# API_KEY=your-secret-key

# ── 선택: Naver 검색 API ─────────────────────────────
# get_etf_news 뉴스 수집 기능에만 필요
# https://developers.naver.com 에서 발급
# NAVER_CLIENT_ID=your-naver-client-id
# NAVER_CLIENT_SECRET=your-naver-client-secret

# ── 선택: CORS 허용 출처 ──────────────────────────────
# CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

> **Naver API 없이도** 뉴스 수집(`/api/news/{ticker}/collect`) 외 모든 기능은 정상 동작합니다.

### 2-3. 종목 설정 확인

`backend/config/stocks.json`에 분석할 종목이 등록되어 있는지 확인합니다.

```json
{
  "487240": {
    "name": "KODEX AI전력핵심설비 ETF",
    "type": "ETF",
    "theme": "AI/전력",
    "search_keyword": "AI 전력",
    "relevance_keywords": ["AI", "전력", "데이터센터"]
  }
}
```

### 2-4. 데이터베이스 초기화

```bash
cd backend
source .venv/bin/activate
python -m app.database
```

빈 SQLite DB(`backend/data/etf_data.db`)가 생성됩니다.

### 2-5. 백엔드 서버 실행

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

서버 기동 확인:

```bash
curl http://localhost:8000/api/health
# {"status": "ok"}
```

---

## 3단계: 초기 데이터 수집

서버 기동 직후에는 DB가 비어 있습니다. 가격·수급 데이터를 먼저 수집해야 API 응답이 채워집니다.

### 전체 종목 일괄 수집 (권장)

```bash
# 최근 30일치 데이터 수집
curl -X POST "http://localhost:8000/api/data/collect-all?days=30"
```

### 종목별 개별 수집

```bash
# 특정 종목 가격·수급 수집
curl -X POST "http://localhost:8000/api/etfs/487240/collect?days=30"

# 뉴스 수집 (Naver API 필요)
curl -X POST "http://localhost:8000/api/news/487240/collect?days=30"
```

### 수집 진행 상황 확인

```bash
curl http://localhost:8000/api/data/collect-progress
curl http://localhost:8000/api/data/stats
```

> 데이터 수집에는 종목 수·기간에 따라 수 분이 소요됩니다.

---

## 4단계: OpenAPI Python SDK 설치

### 4-1. openapi-python-client 설치

```bash
pip install openapi-python-client
```

### 4-2. SDK 생성 및 설치

```bash
# 프로젝트 루트에서 실행
bash sdk/generate.sh

# 생성된 클라이언트 설치
pip install -e sdk/python
```

### 4-3. SDK 사용 예시

```python
from etf_report_client import AuthenticatedClient, Client
from etf_report_client.api.etfs import get_api_etfs_ticker_prices

# 인증 없이 사용 (API_KEY 미설정 시)
client = Client(base_url="http://localhost:8000")

# 인증 키 사용 시
# client = AuthenticatedClient(base_url="http://localhost:8000", token="your-api-key")

# 가격 데이터 조회
with client as c:
    response = get_api_etfs_ticker_prices.sync(client=c, ticker="487240", days=30)
    print(response)
```

> SDK 재생성 명령: `bash sdk/generate.sh` (백엔드 API 변경 후 실행)

---

## 5단계: MCP 서버 설정

### 5-1. MCP 서버 의존성 설치

```bash
# 프로젝트 루트에서 실행
uv sync --project mcp-server
```

또는 pip 사용 시:

```bash
cd mcp-server
pip install -e .
```

### 5-2. `.mcp.json` 설정

프로젝트 루트의 `.mcp.json`에 `etf-report` 항목이 이미 추가되어 있습니다.

```json
{
  "mcpServers": {
    "etf-report": {
      "command": "uv",
      "args": ["run", "--project", "mcp-server", "etf-report-mcp"],
      "env": {
        "ETF_REPORT_BASE_URL": "http://localhost:8000",
        "ETF_REPORT_API_KEY": ""
      }
    }
  }
}
```

**API_KEY를 설정한 경우** `ETF_REPORT_API_KEY`에 동일한 값을 입력합니다.

### 5-3. Claude Code에서 MCP 서버 확인

Claude Code를 재시작하면 `/mcp` 명령으로 `etf-report` 서버 인식을 확인할 수 있습니다.

---

## 6단계: 동작 검증

### 백엔드 API 직접 호출

```bash
# 종목 목록
curl http://localhost:8000/api/etfs/

# 가격 데이터
curl "http://localhost:8000/api/etfs/487240/prices?days=7"

# DB 통계
curl http://localhost:8000/api/data/stats
```

### MCP 도구 호출 (Claude Code 내)

```
list_stocks 도구를 써서 등록된 종목 목록을 보여줘
get_etf_prices 로 487240 최근 7일 가격을 조회해줘
simulate_lump_sum 으로 487240을 2024-01-01에 1,000,000원 투자했다면 현재 수익률은?
```

---

## 환경 변수 요약

| 변수 | 필수 | 기본값 | 설명 |
|------|------|--------|------|
| `DATABASE_URL` | 아니오 | `backend/data/etf_data.db` | SQLite 경로 또는 PostgreSQL URL |
| `API_KEY` | 아니오 | (없음, 인증 비활성화) | API 인증 키 |
| `NAVER_CLIENT_ID` | 아니오 | (없음) | 뉴스 수집용 Naver API ID |
| `NAVER_CLIENT_SECRET` | 아니오 | (없음) | 뉴스 수집용 Naver API Secret |
| `ETF_REPORT_BASE_URL` | 아니오 | `http://localhost:8000` | MCP 서버가 바라보는 백엔드 URL |
| `ETF_REPORT_API_KEY` | 아니오 | (없음) | MCP 서버 인증 키 (`API_KEY`와 동일) |

---

## 기능별 필요 조건 정리

| 기능 | SQLite DB | 데이터 수집 | Naver API |
|------|-----------|------------|-----------|
| 종목 목록 (`list_stocks`) | 필요 | 불필요 | 불필요 |
| 가격 데이터 (`get_etf_prices`) | 필요 | **필요** | 불필요 |
| 수급 데이터 (`get_trading_flow`) | 필요 | **필요** | 불필요 |
| 성과 지표 (`get_etf_metrics`) | 필요 | **필요** | 불필요 |
| 펀더멘털 (`get_etf_fundamentals`) | 필요 | **필요** | 불필요 |
| 뉴스 조회 (`get_etf_news`) | 필요 | **필요** | **필요** |
| 스캐너 (`scan_stocks`) | 필요 | **필요** | 불필요 |
| 투자 시뮬레이션 | 필요 | **필요** | 불필요 |
| AI 인사이트 (`get_etf_insights`) | 필요 | **필요** | 불필요 |

---

## 문제 해결

### 백엔드 기동 실패 — 모듈 없음
```bash
pip install -r backend/requirements.txt
```

### API 응답이 빈 배열 `[]`
데이터 수집이 안 된 상태입니다.
```bash
curl -X POST "http://localhost:8000/api/data/collect-all?days=30"
```

### MCP 서버가 인식 안 됨
Claude Code를 완전히 종료 후 재시작하거나 `.mcp.json` 경로가 프로젝트 루트인지 확인합니다.

### Naver API 오류 (뉴스 수집 시)
[Naver Developers](https://developers.naver.com/apps/#/register)에서 검색 API 애플리케이션 등록 후 발급받은 ID/Secret을 `backend/.env`에 설정합니다.

---

## 관련 문서

- [API_MANUAL.md](./API_MANUAL.md) — REST API 전체 엔드포인트 목록
- [API_SPECIFICATION.md](./API_SPECIFICATION.md) — API 상세 스펙
- [DATABASE_SCHEMA.md](./DATABASE_SCHEMA.md) — DB 스키마
- [RENDER_DEPLOYMENT.md](./RENDER_DEPLOYMENT.md) — 클라우드 배포 (백엔드를 원격 서버에 두고 싶을 때)
