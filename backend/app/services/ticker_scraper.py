"""
네이버 증권 JSON API에서 종목 정보 수집

종목 코드를 입력하면 자동으로 종목 정보를 수집하여
stocks.json 형식으로 반환합니다. (종목 추가 전 검증용)

- 종목명/타입: /api/stock/{code}/basic (stockName, stockEndType)
- 주식 테마:  /api/stock/{code}/integration → industryCode
              → /api/stocks/industry/{code} → groupInfo.name (업종명)
- ETF 테마:   /api/stock/{code}/etfAnalysis → etfSummary 텍스트 키워드 추출
"""
import re
import logging
import requests
from typing import Dict, Any, List, Optional
from app.utils.retry import retry_with_backoff
from app.utils.rate_limiter import RateLimiter
from app.exceptions import ScraperException
from app.constants import DEFAULT_RATE_LIMITER_INTERVAL
from app.services.naver_stock_api import MOBILE_API_BASE, HEADERS

logger = logging.getLogger(__name__)


class TickerScraper:
    """네이버 증권 JSON API 기반 종목 정보 수집기"""

    def __init__(self):
        self.rate_limiter = RateLimiter(min_interval=DEFAULT_RATE_LIMITER_INTERVAL)

    def _get_json(self, url: str) -> Optional[dict]:
        """JSON GET. 비-JSON/비-dict 응답은 None (네트워크 예외는 전파 → retry)."""
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        try:
            data = response.json()
        except ValueError:
            return None
        return data if isinstance(data, dict) else None

    @retry_with_backoff(
        max_retries=3,
        base_delay=1.0,
        exceptions=(requests.exceptions.RequestException, requests.exceptions.Timeout)
    )
    def scrape_ticker_info(self, ticker: str) -> Dict[str, Any]:
        """
        네이버 증권 JSON API에서 종목 정보 수집

        Args:
            ticker: 종목 코드 (예: "005930", "487240", "0101N0")

        Returns:
            Dict[str, Any]: stocks.json 형식의 종목 정보
            {
                "ticker": "005930",
                "name": "삼성전자",
                "type": "STOCK",
                "theme": "반도체와반도체장비",
                "purchase_date": null,
                "search_keyword": "삼성전자",
                "relevance_keywords": ["삼성전자", "반도체", ...]
            }

        Raises:
            ScraperException: 수집 실패 (미존재 종목, 네트워크 에러 등)
        """
        logger.info(f"Fetching ticker info for {ticker} from Naver JSON API")

        try:
            # 1. 종목명 + 타입 (basic)
            with self.rate_limiter:
                basic = self._get_json(f"{MOBILE_API_BASE}/stock/{ticker}/basic")

            name = (basic or {}).get('stockName')
            if not name:
                raise ScraperException(f"종목을 찾을 수 없습니다: {ticker}")

            end_type = (basic or {}).get('stockEndType', '')
            stock_type = "ETF" if end_type == 'etf' else "STOCK"

            # 2. 테마/섹터 추출
            theme = self._fetch_theme(ticker, stock_type)

            # 3. 키워드 생성
            search_keyword = self._generate_search_keyword(name, theme)
            relevance_keywords = self.generate_keywords(name, theme)

            stock_info = {
                "ticker": ticker,
                "name": name,
                "type": stock_type,
                "theme": theme,
                "purchase_date": None,  # 구매일은 사용자가 직접 입력
                "search_keyword": search_keyword,
                "relevance_keywords": relevance_keywords
            }

            logger.info(f"Successfully fetched info for {ticker}: {name} ({stock_type})")
            return stock_info

        except ScraperException:
            raise
        except requests.exceptions.HTTPError as e:
            # 미존재 종목은 404 외에 409(StockConflict) 등으로도 응답한다
            status = e.response.status_code if e.response is not None else None
            if status is not None and 400 <= status < 500:
                raise ScraperException(f"종목을 찾을 수 없습니다: {ticker}")
            logger.error(f"HTTP error fetching {ticker}: {e}")
            raise ScraperException(f"네트워크 오류: {e}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error fetching {ticker}: {e}")
            raise ScraperException(f"네트워크 오류: {e}")
        except Exception as e:
            logger.error(f"Unexpected error fetching {ticker}: {e}", exc_info=True)
            raise ScraperException(f"수집 실패: {e}")

    def _fetch_theme(self, ticker: str, stock_type: str) -> str:
        """
        테마/섹터 조회. 실패해도 검증 자체는 계속되도록 '미분류'로 폴백한다.

        - STOCK: integration의 industryCode → 업종 목록 API의 groupInfo.name (업종명)
        - ETF:   etfAnalysis의 etfSummary 텍스트에서 키워드 추출 (최대 3개)
        """
        try:
            if stock_type == "ETF":
                with self.rate_limiter:
                    analysis = self._get_json(f"{MOBILE_API_BASE}/stock/{ticker}/etfAnalysis")
                summary = (analysis or {}).get('etfSummary') or ''
                item_name = (analysis or {}).get('itemName') or ''
                keywords = self._extract_keywords_from_text(f"{item_name} {summary}")
                if keywords:
                    return "/".join(keywords[:3])
                return "미분류"

            # STOCK: 업종명 조회
            with self.rate_limiter:
                integration = self._get_json(f"{MOBILE_API_BASE}/stock/{ticker}/integration")
            industry_code = (integration or {}).get('industryCode')
            if industry_code:
                with self.rate_limiter:
                    industry = self._get_json(
                        f"{MOBILE_API_BASE}/stocks/industry/{industry_code}?page=1&pageSize=1"
                    )
                industry_name = ((industry or {}).get('groupInfo') or {}).get('name')
                if industry_name:
                    return industry_name

        except requests.exceptions.RequestException as e:
            logger.warning(f"Theme fetch failed for {ticker}: {e}")

        return "미분류"

    def _generate_search_keyword(self, name: str, theme: str) -> str:
        """뉴스 검색용 키워드 생성"""
        # ETF인 경우: "ETF" 제거, 회사명 제거
        clean_name = re.sub(r'\b(삼성|신한|KB|KoAct|KODEX|SOL|RISE)\b', '', name)
        clean_name = re.sub(r'\bETF\b', '', clean_name).strip()

        # 빈 문자열이면 원래 이름 사용
        if not clean_name:
            clean_name = name

        return clean_name

    def _extract_keywords_from_text(self, text: str) -> List[str]:
        """텍스트에서 핵심 키워드 추출 (간단한 휴리스틱)"""
        # 주요 키워드 목록 (확장 가능)
        keyword_patterns = [
            r'AI', r'인공지능', r'전력', r'데이터센터',
            r'반도체', r'전자', r'IT',
            r'조선', r'선박', r'LNG', r'친환경',
            r'양자컴퓨팅', r'퀀텀', r'혁신',
            r'원자력', r'SMR', r'에너지', r'클린에너지',
            r'방산', r'국방'
        ]

        keywords = []
        for pattern in keyword_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                keywords.append(pattern)

        return keywords

    def generate_keywords(self, name: str, theme: str) -> List[str]:
        """
        종목명과 테마를 기반으로 관련 키워드 자동 생성

        Args:
            name: 종목명
            theme: 테마/섹터

        Returns:
            List[str]: 관련 키워드 목록
        """
        keywords = []

        # 1. 종목명에서 핵심 단어 추출
        # 회사명 제거
        clean_name = re.sub(r'\b(삼성|신한|KB|KoAct|KODEX|SOL|RISE|HD|한화|두산)\b', '', name)
        clean_name = re.sub(r'\bETF\b', '', clean_name).strip()

        # 단어 분리 (공백, 하이픈 등)
        name_words = re.split(r'[\s\-/]+', clean_name)
        keywords.extend([w for w in name_words if len(w) > 1])

        # 2. 테마에서 키워드 추출
        theme_words = re.split(r'[/\s]+', theme)
        keywords.extend([w for w in theme_words if len(w) > 1])

        # 3. 중복 제거 및 원래 이름 추가
        keywords = list(dict.fromkeys(keywords))  # 순서 유지하며 중복 제거
        if name not in keywords:
            keywords.insert(0, name)

        # 4. 최대 10개로 제한
        return keywords[:10]


# 싱글톤 인스턴스
_scraper_instance = None


def get_ticker_scraper() -> TickerScraper:
    """TickerScraper 싱글톤 인스턴스 반환"""
    global _scraper_instance
    if _scraper_instance is None:
        _scraper_instance = TickerScraper()
    return _scraper_instance
