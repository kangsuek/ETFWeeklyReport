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
