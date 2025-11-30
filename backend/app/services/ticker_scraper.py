"""
네이버 금융에서 종목 정보 스크래핑

종목 코드를 입력하면 자동으로 종목 정보를 수집하여
stocks.json 형식으로 반환합니다.
"""
import re
import logging
import requests
from bs4 import BeautifulSoup
from typing import Dict, Any, List, Optional
from app.utils.retry import retry_with_backoff
from app.utils.rate_limiter import RateLimiter
from app.exceptions import ScraperException
from app.constants import DEFAULT_RATE_LIMITER_INTERVAL

logger = logging.getLogger(__name__)


class TickerScraper:
    """네이버 금융 종목 정보 스크래퍼"""

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.rate_limiter = RateLimiter(min_interval=DEFAULT_RATE_LIMITER_INTERVAL)

    @retry_with_backoff(
        max_retries=3,
        base_delay=1.0,
        exceptions=(requests.exceptions.RequestException, requests.exceptions.Timeout)
    )
    def scrape_ticker_info(self, ticker: str) -> Dict[str, Any]:
        """
        네이버 금융에서 종목 정보 스크래핑

        Args:
            ticker: 종목 코드 (예: "005930", "487240")

        Returns:
            Dict[str, Any]: stocks.json 형식의 종목 정보
            {
                "ticker": "005930",
                "name": "삼성전자",
                "type": "STOCK",
                "theme": "반도체/전자",
                "purchase_date": null,
                "search_keyword": "삼성전자",
                "relevance_keywords": ["삼성전자", "반도체", "전자"]
            }

        Raises:
            ScraperException: 스크래핑 실패 (404, 네트워크 에러, 파싱 실패 등)
        """
        url = f"https://finance.naver.com/item/main.naver?code={ticker}"
        logger.info(f"Scraping ticker info from {url}")

        try:
            with self.rate_limiter:
                response = requests.get(url, headers=self.headers, timeout=10)
                response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # 1. 종목명 추출
            name = self._extract_name(soup, ticker)
            if not name:
                raise ScraperException(f"종목을 찾을 수 없습니다: {ticker}")

            # 2. 종목 타입 감지 (ETF or STOCK)
            stock_type = self._detect_type(name, ticker, soup)

            # 3. 테마/섹터 추출
            theme = self._extract_theme(soup, stock_type)

            # 4. 키워드 생성
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

            logger.info(f"Successfully scraped info for {ticker}: {name} ({stock_type})")
            return stock_info

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise ScraperException(f"종목을 찾을 수 없습니다: {ticker}")
            logger.error(f"HTTP error scraping {ticker}: {e}")
            raise ScraperException(f"네트워크 오류: {e}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error scraping {ticker}: {e}")
            raise ScraperException(f"네트워크 오류: {e}")
        except Exception as e:
            logger.error(f"Unexpected error scraping {ticker}: {e}", exc_info=True)
            raise ScraperException(f"스크래핑 실패: {e}")

    def _extract_name(self, soup: BeautifulSoup, ticker: str) -> Optional[str]:
        """종목명 추출"""
        # 방법 1: .wrap_company h2 a (가장 일반적)
        company_h2 = soup.select_one('.wrap_company h2 a')
        if company_h2:
            return company_h2.get_text(strip=True)

        # 방법 2: title 태그에서 추출 (예: "삼성전자 : 네이버 금융")
        title_tag = soup.find('title')
        if title_tag:
            title_text = title_tag.get_text(strip=True)
            match = re.match(r'^(.+?)\s*[:：]', title_text)
            if match:
                return match.group(1).strip()

        # 방법 3: meta 태그
        meta_title = soup.find('meta', property='og:title')
        if meta_title:
            content = meta_title.get('content', '')
            match = re.match(r'^(.+?)\s*[:：]', content)
            if match:
                return match.group(1).strip()

        logger.warning(f"Failed to extract name for {ticker}")
        return None

    def _detect_type(self, name: str, ticker: str, soup: BeautifulSoup) -> str:
        """종목 타입 감지 (ETF or STOCK)"""
        # 방법 1: 종목명에 "ETF" 포함 여부
        if "ETF" in name.upper():
            return "ETF"

        # 방법 2: 종목코드 길이 (ETF는 6자리, 주식은 6자리)
        # 이 방법은 신뢰성이 낮으므로 다른 방법과 조합

        # 방법 3: 페이지 내용 확인
        page_text = soup.get_text().upper()
        if "ETF" in page_text and "운용보수" in page_text:
            return "ETF"

        # 기본값: STOCK
        return "STOCK"

    def _extract_theme(self, soup: BeautifulSoup, stock_type: str) -> str:
        """테마/섹터 추출"""
        # 방법 1: 업종 정보 (.wrap_company .description)
        description = soup.select_one('.wrap_company .description')
        if description:
            text = description.get_text(strip=True)
            # "업종: 반도체" 형태
            match = re.search(r'업종\s*[:：]\s*(.+)', text)
            if match:
                return match.group(1).strip()

        # 방법 2: 종목 설명에서 추출 (ETF인 경우 더 상세한 설명이 있음)
        if stock_type == "ETF":
            # ETF 상세 설명 영역 찾기
            description_area = soup.find('div', class_='description')
            if description_area:
                text = description_area.get_text(strip=True)
                # 간단한 키워드 추출 (예: "AI", "전력", "반도체" 등)
                keywords = self._extract_keywords_from_text(text)
                if keywords:
                    return "/".join(keywords[:3])  # 최대 3개

        # 기본값: "미분류"
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
