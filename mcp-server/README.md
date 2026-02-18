# ETF Report MCP Server

ETF Weekly Report 백엔드 API를 MCP(Model Context Protocol) 도구로 래핑하는 서버입니다.
Claude Desktop, Claude Code 등 MCP 호환 앱에서 ETF 데이터를 직접 조회할 수 있습니다.

## 설치

```bash
cd mcp-server
uv sync
```

## 사용법

### 환경 변수

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `ETF_REPORT_BASE_URL` | `http://localhost:8000` | 백엔드 API 서버 URL |
| `ETF_REPORT_API_KEY` | (빈 문자열) | API 인증 키 |

### 실행

```bash
ETF_REPORT_BASE_URL=http://localhost:8000 etf-report-mcp
```

### `.mcp.json` 설정 예시

```json
{
  "mcpServers": {
    "etf-report": {
      "command": "uv",
      "args": ["run", "--project", "mcp-server", "etf-report-mcp"],
      "env": {
        "ETF_REPORT_BASE_URL": "http://localhost:8000",
        "ETF_REPORT_API_KEY": "your-api-key"
      }
    }
  }
}
```

## 제공 도구 (16개)

| 도구 | 설명 |
|------|------|
| `list_stocks` | 등록된 전체 ETF·주식 목록 조회 |
| `get_etf_info` | 특정 종목 기본 정보 조회 |
| `get_etf_prices` | 가격 데이터 조회 (OHLCV) |
| `get_etf_metrics` | 수익률·변동성 등 성과 지표 조회 |
| `get_etf_fundamentals` | 펀더멘털 데이터 (PER, PBR 등) |
| `get_etf_news` | 관련 뉴스 조회 |
| `get_trading_flow` | 수급 데이터 (외국인·기관 순매수) |
| `get_etf_insights` | AI 인사이트 조회 |
| `compare_etfs` | 여러 종목 비교 분석 |
| `scan_stocks` | 조건 기반 종목 스캔 |
| `get_recommendations` | 추천 종목 조회 |
| `get_themes` | 투자 테마 목록 조회 |
| `simulate_lump_sum` | 일시 투자 시뮬레이션 |
| `simulate_dca` | 적립식 투자 시뮬레이션 |
| `simulate_portfolio` | 포트폴리오 시뮬레이션 |
| `get_db_stats` | 데이터베이스 통계 조회 |
