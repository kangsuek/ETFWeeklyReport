"""
네이버 증권 모바일 JSON API 공용 클라이언트

m.stock.naver.com / api.stock.naver.com 의 JSON 엔드포인트 접근을 한곳에 모은다.
구형 finance.naver.com HTML 파싱 대비 구조 변경에 강하고 필드가 풍부하다.

사용 모듈: etf_fundamentals_collector, data_collector(수급), catalog_data_collector(수급)
"""

import logging
from datetime import datetime, date
from typing import Optional, List, Dict, Any

import requests

logger = logging.getLogger(__name__)

MOBILE_API_BASE = "https://m.stock.naver.com/api"
CHART_API_BASE = "https://api.stock.naver.com"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
    ),
    "Referer": "https://m.stock.naver.com/",
}


def parse_number(v) -> Optional[float]:
    """'"-5,007,053"' / '"0.21%"' / '+55,458' 등 → float. 실패 시 None."""
    if v is None:
        return None
    try:
        return float(str(v).replace(',', '').replace('%', '').replace('+', '').strip())
    except (ValueError, TypeError):
        return None


def parse_int(v) -> Optional[int]:
    f = parse_number(v)
    return int(f) if f is not None else None


def parse_bizdate(v) -> Optional[date]:
    """'20260702' 또는 '2026-07-02' → date. 실패 시 None."""
    if not v:
        return None
    s = str(v).strip()
    for fmt in ('%Y%m%d', '%Y-%m-%d', '%Y.%m.%d'):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def get_json(url: str, params: Optional[dict] = None, timeout: int = 10):
    """JSON GET. 실패(HTTP 에러/파싱 실패) 시 None."""
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=timeout)
        if resp.status_code != 200:
            logger.warning(f"[NaverStockAPI] HTTP {resp.status_code}: {url}")
            return None
        return resp.json()
    except Exception as e:
        logger.error(f"[NaverStockAPI] fetch error {url}: {e}")
        return None


def fetch_price_page(ticker: str, page: int = 1, page_size: int = 10) -> List[Dict[str, Any]]:
    """
    일별 시세(/stock/{code}/price) 1페이지 조회 (최신순, pageSize 최대 60).

    각 행: localTradedAt('YYYY-MM-DD'), openPrice/highPrice/lowPrice/closePrice
    (쉼표 포함 문자열), fluctuationsRatio(등락률 %), accumulatedTradingVolume(정수).
    """
    url = f"{MOBILE_API_BASE}/stock/{ticker}/price"
    data = get_json(url, params={"pageSize": page_size, "page": page})
    return data if isinstance(data, list) else []


def fetch_trend_page(ticker: str, page: int = 1, page_size: int = 10) -> List[Dict[str, Any]]:
    """
    투자자별 매매동향(/stock/{code}/trend) 1페이지 조회.

    각 행: bizdate(YYYYMMDD), foreignerPureBuyQuant, organPureBuyQuant,
    individualPureBuyQuant(실측 개인 순매수, 주), foreignerHoldRatio('0.21%'),
    closePrice, accumulatedTradingVolume — 모두 쉼표 포함 문자열.
    """
    url = f"{MOBILE_API_BASE}/stock/{ticker}/trend"
    data = get_json(url, params={"pageSize": page_size, "page": page})
    return data if isinstance(data, list) else []
