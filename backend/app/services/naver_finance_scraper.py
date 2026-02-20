"""
네이버 금융 메인 페이지 공통 스크래퍼

finance.naver.com/item/main.naver?code={ticker} 페이지를 수집하여
BeautifulSoup 파싱 결과를 반환합니다.

주식·ETF 파서가 동일 URL을 사용하므로 한 번만 요청하고 각 수집기에서 필요한 섹션만 파싱합니다.
"""

import logging
import requests
from bs4 import BeautifulSoup
from typing import Optional

from app.utils.retry import retry_with_backoff
from app.utils.rate_limiter import RateLimiter
from app.constants import DEFAULT_RATE_LIMITER_INTERVAL

logger = logging.getLogger(__name__)

NAVER_MAIN_URL = "https://finance.naver.com/item/main.naver?code={ticker}"

_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

# 모듈 단위 RateLimiter (모든 호출자 공유)
_rate_limiter = RateLimiter(min_interval=DEFAULT_RATE_LIMITER_INTERVAL)


@retry_with_backoff(
    max_retries=3,
    base_delay=1.0,
    exceptions=(requests.exceptions.RequestException, requests.exceptions.Timeout)
)
def fetch_main_page(ticker: str) -> Optional[BeautifulSoup]:
    """
    네이버 금융 종목 메인 페이지를 수집하여 BeautifulSoup 객체를 반환합니다.

    Args:
        ticker: 종목 코드 (예: '005930', '487240')

    Returns:
        파싱된 BeautifulSoup 객체. 수집 실패 시 None.
    """
    url = NAVER_MAIN_URL.format(ticker=ticker)
    try:
        with _rate_limiter:
            response = requests.get(url, headers=_HEADERS, timeout=10)
            response.raise_for_status()

        # 인코딩 설정: Content-Type charset 명시 시 그것을 따르고,
        # 불명확할 때만 네이버 금융 기본값 EUC-KR로 설정
        content_type = response.headers.get('Content-Type', '').lower()
        if 'utf-8' not in content_type and 'utf8' not in content_type:
            response.encoding = 'euc-kr'
        soup = BeautifulSoup(response.text, 'html.parser')
        logger.debug(f"[naver_finance_scraper] Fetched main page for {ticker}")
        return soup

    except requests.exceptions.HTTPError as e:
        logger.error(f"[naver_finance_scraper] HTTP error for {ticker}: {e}")
        return None
    except Exception as e:
        logger.error(f"[naver_finance_scraper] Unexpected error for {ticker}: {e}")
        return None
