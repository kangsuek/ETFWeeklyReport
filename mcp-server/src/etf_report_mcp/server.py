import asyncio
import json
import os

import httpx
import mcp.server.stdio
from mcp.server import Server
from mcp.types import CallToolResult, TextContent, Tool

BASE_URL = os.getenv("ETF_REPORT_BASE_URL", "http://localhost:8000")
API_KEY = os.getenv("ETF_REPORT_API_KEY", "")

server = Server("etf-report")


def _headers() -> dict:
    return {"X-API-Key": API_KEY} if API_KEY else {}


def _ok(data) -> list[TextContent]:
    return [TextContent(type="text", text=json.dumps(data, ensure_ascii=False, indent=2))]


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="list_stocks",
            description="등록된 전체 ETF·주식 목록 조회",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="get_etf_info",
            description="특정 ETF·주식의 기본 정보 조회",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "종목 코드 (예: 487240)"},
                },
                "required": ["ticker"],
            },
        ),
        Tool(
            name="get_etf_prices",
            description="ETF·주식의 가격 데이터 조회 (OHLCV)",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "종목 코드"},
                    "start_date": {"type": "string", "description": "시작일 (YYYY-MM-DD)"},
                    "end_date": {"type": "string", "description": "종료일 (YYYY-MM-DD)"},
                    "days": {"type": "integer", "description": "조회 기간(일), 기본값 30"},
                },
                "required": ["ticker"],
            },
        ),
        Tool(
            name="get_etf_metrics",
            description="ETF·주식의 수익률, 변동성 등 성과 지표 조회",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "종목 코드"},
                },
                "required": ["ticker"],
            },
        ),
        Tool(
            name="get_etf_fundamentals",
            description="ETF·주식의 펀더멘털 데이터 조회 (PER, PBR, 배당수익률 등)",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "종목 코드"},
                },
                "required": ["ticker"],
            },
        ),
        Tool(
            name="get_etf_news",
            description="ETF·주식 관련 뉴스 조회",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "종목 코드"},
                    "start_date": {"type": "string", "description": "시작일 (YYYY-MM-DD)"},
                    "end_date": {"type": "string", "description": "종료일 (YYYY-MM-DD)"},
                    "analyze": {"type": "boolean", "description": "AI 감성 분석 포함 여부"},
                },
                "required": ["ticker"],
            },
        ),
        Tool(
            name="get_trading_flow",
            description="ETF·주식의 수급 데이터 조회 (외국인·기관 순매수)",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "종목 코드"},
                    "start_date": {"type": "string", "description": "시작일 (YYYY-MM-DD)"},
                    "end_date": {"type": "string", "description": "종료일 (YYYY-MM-DD)"},
                },
                "required": ["ticker"],
            },
        ),
        Tool(
            name="get_etf_insights",
            description="ETF·주식의 AI 인사이트 및 분석 조회",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "종목 코드"},
                    "period": {"type": "string", "description": "분석 기간"},
                },
                "required": ["ticker"],
            },
        ),
        Tool(
            name="compare_etfs",
            description="여러 ETF·주식을 비교 분석",
            inputSchema={
                "type": "object",
                "properties": {
                    "tickers": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "비교할 종목 코드 목록 (예: [\"487240\", \"448540\"])",
                    },
                    "start_date": {"type": "string", "description": "시작일 (YYYY-MM-DD)"},
                    "end_date": {"type": "string", "description": "종료일 (YYYY-MM-DD)"},
                },
                "required": ["tickers"],
            },
        ),
        Tool(
            name="scan_stocks",
            description="조건에 따라 ETF·주식 스캔 및 필터링",
            inputSchema={
                "type": "object",
                "properties": {
                    "q": {"type": "string", "description": "검색어"},
                    "type": {"type": "string", "description": "종목 유형 (ETF/STOCK)"},
                    "sector": {"type": "string", "description": "섹터"},
                    "min_weekly_return": {"type": "number", "description": "최소 주간 수익률"},
                    "max_weekly_return": {"type": "number", "description": "최대 주간 수익률"},
                    "foreign_net_positive": {"type": "boolean", "description": "외국인 순매수 여부"},
                    "institutional_net_positive": {"type": "boolean", "description": "기관 순매수 여부"},
                    "sort_by": {"type": "string", "description": "정렬 기준"},
                    "sort_dir": {"type": "string", "description": "정렬 방향 (asc/desc)"},
                    "page": {"type": "integer", "description": "페이지 번호"},
                    "page_size": {"type": "integer", "description": "페이지 크기"},
                },
            },
        ),
        Tool(
            name="get_recommendations",
            description="스캐너 기반 추천 종목 조회",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "최대 결과 수"},
                },
            },
        ),
        Tool(
            name="get_themes",
            description="투자 테마 목록 및 관련 종목 조회",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="simulate_lump_sum",
            description="일시 투자 시뮬레이션 (특정 날짜에 일괄 매수 시 현재 수익률 계산)",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "종목 코드"},
                    "buy_date": {"type": "string", "description": "매수일 (YYYY-MM-DD)"},
                    "amount": {"type": "number", "description": "투자 금액 (원)"},
                },
                "required": ["ticker", "buy_date", "amount"],
            },
        ),
        Tool(
            name="simulate_dca",
            description="적립식 투자 시뮬레이션 (매월 일정 금액 매수 시 수익률 계산)",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "종목 코드"},
                    "monthly_amount": {"type": "number", "description": "월 투자 금액 (원)"},
                    "start_date": {"type": "string", "description": "시작일 (YYYY-MM-DD)"},
                    "end_date": {"type": "string", "description": "종료일 (YYYY-MM-DD)"},
                    "buy_day": {"type": "integer", "description": "매월 매수일 (기본값 1)"},
                },
                "required": ["ticker", "monthly_amount", "start_date", "end_date"],
            },
        ),
        Tool(
            name="simulate_portfolio",
            description="포트폴리오 시뮬레이션 (여러 종목 비중 설정 후 수익률 계산)",
            inputSchema={
                "type": "object",
                "properties": {
                    "holdings": {
                        "type": "array",
                        "description": "보유 종목 목록 (예: [{\"ticker\": \"487240\", \"weight\": 0.5}])",
                        "items": {
                            "type": "object",
                            "properties": {
                                "ticker": {"type": "string"},
                                "weight": {"type": "number"},
                            },
                        },
                    },
                    "amount": {"type": "number", "description": "총 투자 금액 (원)"},
                    "start_date": {"type": "string", "description": "시작일 (YYYY-MM-DD)"},
                    "end_date": {"type": "string", "description": "종료일 (YYYY-MM-DD)"},
                },
                "required": ["holdings", "amount", "start_date", "end_date"],
            },
        ),
        Tool(
            name="get_db_stats",
            description="데이터베이스 통계 조회 (수집된 데이터 현황)",
            inputSchema={"type": "object", "properties": {}},
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    headers = _headers()
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        match name:
            case "list_stocks":
                r = await client.get("/api/etfs/", headers=headers)

            case "get_etf_info":
                ticker = arguments["ticker"]
                r = await client.get(f"/api/etfs/{ticker}", headers=headers)

            case "get_etf_prices":
                ticker = arguments["ticker"]
                params = {k: v for k, v in arguments.items() if k != "ticker" and v is not None}
                r = await client.get(f"/api/etfs/{ticker}/prices", params=params, headers=headers)

            case "get_etf_metrics":
                ticker = arguments["ticker"]
                r = await client.get(f"/api/etfs/{ticker}/metrics", headers=headers)

            case "get_etf_fundamentals":
                ticker = arguments["ticker"]
                r = await client.get(f"/api/etfs/{ticker}/fundamentals", headers=headers)

            case "get_etf_news":
                ticker = arguments["ticker"]
                params = {k: v for k, v in arguments.items() if k != "ticker" and v is not None}
                r = await client.get(f"/api/news/{ticker}", params=params, headers=headers)

            case "get_trading_flow":
                ticker = arguments["ticker"]
                params = {k: v for k, v in arguments.items() if k != "ticker" and v is not None}
                r = await client.get(f"/api/etfs/{ticker}/trading-flow", params=params, headers=headers)

            case "get_etf_insights":
                ticker = arguments["ticker"]
                params = {k: v for k, v in arguments.items() if k != "ticker" and v is not None}
                r = await client.get(f"/api/etfs/{ticker}/insights", params=params, headers=headers)

            case "compare_etfs":
                tickers = arguments["tickers"]
                params: dict = {"tickers": tickers}
                if "start_date" in arguments:
                    params["start_date"] = arguments["start_date"]
                if "end_date" in arguments:
                    params["end_date"] = arguments["end_date"]
                r = await client.get("/api/etfs/compare", params=params, headers=headers)

            case "scan_stocks":
                params = {k: v for k, v in arguments.items() if v is not None}
                r = await client.get("/api/scanner", params=params, headers=headers)

            case "get_recommendations":
                params = {k: v for k, v in arguments.items() if v is not None}
                r = await client.get("/api/scanner/recommendations", params=params, headers=headers)

            case "get_themes":
                r = await client.get("/api/scanner/themes", headers=headers)

            case "simulate_lump_sum":
                r = await client.post("/api/simulation/lump-sum", json=arguments, headers=headers)

            case "simulate_dca":
                r = await client.post("/api/simulation/dca", json=arguments, headers=headers)

            case "simulate_portfolio":
                r = await client.post("/api/simulation/portfolio", json=arguments, headers=headers)

            case "get_db_stats":
                r = await client.get("/api/data/stats", headers=headers)

            case _:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]

        r.raise_for_status()
        return _ok(r.json())


def main():
    asyncio.run(mcp.server.stdio.run(server))


if __name__ == "__main__":
    main()
