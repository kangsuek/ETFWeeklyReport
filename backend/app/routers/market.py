"""
시장 개요 라우터

KOSPI / KOSDAQ 지수 현황을 실시간으로 제공합니다.
"""

from fastapi import APIRouter
from app.utils.cache import get_cache, make_cache_key
import requests
import logging
import os

router = APIRouter()
logger = logging.getLogger(__name__)

# 시장 지수 캐시 (30초 TTL - 빠른 갱신)
MARKET_CACHE_TTL = 30
cache = get_cache(ttl_seconds=MARKET_CACHE_TTL)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://m.stock.naver.com',
}

INDICES = {
    'KOSPI': '코스피',
    'KOSDAQ': '코스닥',
}


def _fetch_index(code: str) -> dict | None:
    """
    Naver 모바일 API에서 지수 현황을 가져옵니다.
    """
    try:
        url = f"https://m.stock.naver.com/api/index/{code}/basic"
        resp = requests.get(url, headers=HEADERS, timeout=5)
        resp.raise_for_status()
        data = resp.json()

        close_price = data.get('closePrice', '0').replace(',', '')
        change = data.get('compareToPreviousClosePrice', '0').replace(',', '')
        change_ratio = data.get('fluctuationsRatio', '0').replace('+', '')

        return {
            'code': code,
            'name': INDICES.get(code, code),
            'close_price': float(close_price) if close_price else 0,
            'change': float(change) if change else 0,
            'change_ratio': float(change_ratio) if change_ratio else 0,
        }
    except Exception as e:
        logger.warning(f"Failed to fetch index {code}: {e}")
        return None


PERIOD_COUNT = {
    "1M": 25,
    "3M": 70,
    "6M": 135,
    "1Y": 260,
    "3Y": 780,
}


def _fetch_index_chart(code: str, period: str = "3M") -> list[dict]:
    """
    Naver 모바일 API에서 지수 일별 차트 데이터를 가져옵니다.
    period: 1M | 3M | 6M | 1Y | 3Y
    """
    try:
        count = PERIOD_COUNT.get(period, 70)
        url = f"https://m.stock.naver.com/api/index/{code}/price?count={count}&requestType=1"
        resp = requests.get(url, headers=HEADERS, timeout=8)
        resp.raise_for_status()
        raw = resp.json()

        result = []
        for item in raw:
            date_str = item.get("localTradedAt", "")
            close = item.get("closePrice", "").replace(",", "")
            open_ = item.get("openPrice", "").replace(",", "")
            high = item.get("highPrice", "").replace(",", "")
            low = item.get("lowPrice", "").replace(",", "")
            if not date_str or not close:
                continue
            result.append({
                "date": date_str,
                "close": float(close) if close else None,
                "open": float(open_) if open_ else None,
                "high": float(high) if high else None,
                "low": float(low) if low else None,
            })
        # 오래된 순으로 정렬 (차트 표시용)
        result.sort(key=lambda x: x["date"])
        return result
    except Exception as e:
        logger.warning(f"Failed to fetch chart for {code} period={period}: {e}")
        return []


@router.get("/index/{code}/chart")
async def get_index_chart(code: str, period: str = "3M"):
    """
    KOSPI / KOSDAQ 지수 일별 차트 데이터 조회

    - code: KOSPI | KOSDAQ
    - period: 1M | 3M | 6M | 1Y | 3Y
    """
    if code not in INDICES:
        return {"code": code, "period": period, "data": []}

    cache_key = make_cache_key(f"market_chart_{code}_{period}")
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    data = _fetch_index_chart(code, period)
    response = {"code": code, "name": INDICES[code], "period": period, "data": data}
    cache.set(cache_key, response, ttl_seconds=300)  # 5분 캐시
    return response


@router.get("/overview")
async def get_market_overview():
    """
    KOSPI / KOSDAQ 지수 현황 조회

    Returns:
        각 지수의 현재가, 등락폭, 등락률
    """
    cache_key = make_cache_key("market_overview")
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    result = []
    for code in INDICES:
        index_data = _fetch_index(code)
        if index_data:
            result.append(index_data)

    response = {'indices': result}
    cache.set(cache_key, response, ttl_seconds=MARKET_CACHE_TTL)
    return response
