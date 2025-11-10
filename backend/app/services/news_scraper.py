from typing import List, Dict, Optional
from datetime import date, datetime, timedelta
from app.models import News
from app.database import get_db_connection
from app.config import Config
from app.utils.retry import retry_with_backoff
from app.utils.rate_limiter import RateLimiter
import logging
import requests
import os
import re
import html

logger = logging.getLogger(__name__)

class NewsScraper:
    """Service for scraping news from Naver Search API"""

    def __init__(self):
        """Initialize Naver News API client"""
        self.client_id = os.getenv("NAVER_CLIENT_ID")
        self.client_secret = os.getenv("NAVER_CLIENT_SECRET")
        
        # Load stock configuration from Config
        self.stock_config = Config.get_stock_config()
        logger.info(f"Loaded {len(self.stock_config)} stocks from configuration")

        if not self.client_id or not self.client_secret:
            logger.warning("Naver API credentials not found in environment variables")
        
        # Rate Limiter 초기화 (API 요청 간 0.1초 대기)
        self.rate_limiter = RateLimiter(min_interval=0.1)

    @retry_with_backoff(
        max_retries=3,
        base_delay=1.0,
        exceptions=(requests.exceptions.RequestException, requests.exceptions.HTTPError)
    )
    def _search_naver_news_api(
        self,
        query: str,
        display: int = 10,
        start: int = 1,
        sort: str = "date"
    ) -> Dict:
        """
        네이버 뉴스 검색 API 호출

        Args:
            query: 검색 키워드
            display: 검색 결과 개수 (1-100)
            start: 검색 시작 위치 (1-1000)
            sort: 정렬 방식 (sim: 정확도, date: 날짜)

        Returns:
            API 응답 JSON
        """
        url = "https://openapi.naver.com/v1/search/news.json"

        headers = {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret
        }

        params = {
            "query": query,
            "display": display,
            "start": start,
            "sort": sort
        }

        try:
            with self.rate_limiter:
                response = requests.get(url, headers=headers, params=params, timeout=10)
                response.raise_for_status()
                return response.json()
        except requests.exceptions.HTTPError as e:
            # 429 (Rate Limit) 에러는 재시도, 401/403은 재시도 안함
            if response.status_code == 401:
                logger.error("Naver API authentication failed: Check Client ID/Secret")
                # 인증 오류는 재시도해도 소용없으므로 다른 예외로 변환
                raise ValueError("Naver API authentication failed") from e
            elif response.status_code == 403:
                logger.error("Naver API permission denied: Enable News API in developer center")
                # 권한 오류도 재시도 불가
                raise ValueError("Naver API permission denied") from e
            elif response.status_code == 429:
                logger.error("Naver API rate limit exceeded: Daily limit is 25,000 calls")
                # 429는 재시도 가능하도록 HTTPError 그대로 raise
                raise
            else:
                logger.error(f"Naver API HTTP error: {e}")
                raise
        except Exception as e:
            logger.error(f"Naver API request failed: {e}")
            raise

    def _clean_html_tags(self, text: str) -> str:
        """
        HTML 태그 및 엔티티 제거

        Args:
            text: HTML 태그가 포함된 문자열

        Returns:
            태그가 제거된 순수 텍스트
        """
        # HTML 태그 제거
        clean_text = re.sub(r'<[^>]+>', '', text)
        # HTML 엔티티 디코딩 (&quot; → ", &amp; → & 등)
        clean_text = html.unescape(clean_text)
        return clean_text

    def _parse_pubdate(self, pubdate_str: str) -> date:
        """
        pubDate를 date 객체로 변환

        Args:
            pubdate_str: "Mon, 08 Nov 2025 14:50:00 +0900" 형식

        Returns:
            date 객체
        """
        dt = datetime.strptime(pubdate_str, "%a, %d %b %Y %H:%M:%S %z")
        return dt.date()

    def _filter_by_date_range(self, news_items: List[Dict], days: int = 7) -> List[Dict]:
        """
        날짜 범위로 뉴스 필터링 (최근 N일 이내)

        Args:
            news_items: 뉴스 아이템 리스트
            days: 필터링할 일수

        Returns:
            필터링된 뉴스 리스트
        """
        cutoff_date = datetime.now().replace(tzinfo=None) - timedelta(days=days)
        filtered = []

        for item in news_items:
            try:
                pub_dt = datetime.strptime(item['pubDate'], "%a, %d %b %Y %H:%M:%S %z")
                pub_dt_naive = pub_dt.replace(tzinfo=None)

                if pub_dt_naive >= cutoff_date:
                    filtered.append(item)
            except Exception as e:
                logger.warning(f"Failed to parse date: {item.get('pubDate')}, error: {e}")
                continue

        return filtered

    def _calculate_relevance_score(self, news_item: Dict, keywords: List[str]) -> float:
        """
        뉴스 아이템의 관련도 점수 계산 (개선된 버전)

        Args:
            news_item: 뉴스 아이템 (title, description 포함)
            keywords: 검색 키워드 리스트

        Returns:
            관련도 점수 (0.0 ~ 1.0)

        개선 사항:
            - 제목 가중치 증가 (2점)
            - 키워드 빈도 고려 (최대 3회까지)
            - 기본 점수 부여로 전체적인 점수 상향
        """
        title = self._clean_html_tags(news_item.get('title', '')).lower()
        description = self._clean_html_tags(news_item.get('description', '')).lower()

        score = 0.0
        max_score = len(keywords) * 5.0  # 제목 3점 + 본문 2점

        for keyword in keywords:
            keyword_lower = keyword.lower()

            # 제목에 키워드 포함: 최대 3점 (빈도에 따라)
            title_count = title.count(keyword_lower)
            if title_count > 0:
                # 1회: 1.5점, 2회: 2.5점, 3회 이상: 3점
                title_score = min(1.5 + (title_count - 1) * 1.0, 3.0)
                score += title_score

            # 본문에 키워드 포함: 최대 2점 (빈도에 따라)
            desc_count = description.count(keyword_lower)
            if desc_count > 0:
                # 1회: 1점, 2회: 1.5점, 3회 이상: 2점
                desc_score = min(1.0 + (desc_count - 1) * 0.5, 2.0)
                score += desc_score

        # 정규화 (0.0 ~ 1.0)
        normalized_score = score / max_score if max_score > 0 else 0.0

        # 기본 점수 부여: 최소 20% 보장 (검색 키워드로 찾은 뉴스이므로)
        # 최종 점수 = 0.2 + (정규화 점수 * 0.8)
        final_score = 0.2 + (normalized_score * 0.8)

        return min(final_score, 1.0)  # 최대값 1.0으로 제한

    def fetch_naver_news(
        self,
        keyword: str,
        days: int = 7,
        relevance_keywords: Optional[List[str]] = None,
        min_relevance: float = 0.0
    ) -> List[dict]:
        """
        네이버 뉴스 검색 API를 사용한 뉴스 수집

        Args:
            keyword: 검색 키워드
            days: 검색할 일수 (기본: 7일)
            relevance_keywords: 관련도 계산용 키워드 리스트
            min_relevance: 최소 관련도 점수 (0.0 ~ 1.0)

        Returns:
            뉴스 데이터 리스트
        """
        logger.info(f"Fetching news for keyword: {keyword} (last {days} days)")

        try:
            # API 호출
            result = self._search_naver_news_api(keyword, display=10, sort="date")
            news_items = result.get('items', [])

            # 날짜 필터링
            if days > 0:
                news_items = self._filter_by_date_range(news_items, days=days)

            # 관련도 점수 계산 및 필터링
            filtered_news = []
            for item in news_items:
                # 관련도 점수 계산
                if relevance_keywords:
                    score = self._calculate_relevance_score(item, relevance_keywords)
                    item['relevance_score'] = score
                else:
                    item['relevance_score'] = 0.5

                # 최소 관련도 필터링
                if item['relevance_score'] >= min_relevance:
                    filtered_news.append(item)

            # 데이터 변환 (News 모델 형식에 맞게)
            news_data = []
            for item in filtered_news:
                news_data.append({
                    'date': self._parse_pubdate(item['pubDate']),
                    'title': self._clean_html_tags(item['title']),
                    'url': item['link'],
                    'source': self._extract_source_from_url(item['link']),
                    'relevance_score': item['relevance_score']
                })

            logger.info(f"Collected {len(news_data)} news items for keyword: {keyword}")
            return news_data

        except Exception as e:
            logger.error(f"Failed to fetch news for keyword '{keyword}': {e}")
            return []

    def _extract_source_from_url(self, url: str) -> str:
        """
        URL에서 뉴스 출처 추출

        Args:
            url: 뉴스 URL

        Returns:
            출처명
        """
        # URL에서 도메인 추출
        match = re.search(r'https?://(?:www\.)?([^/]+)', url)
        if match:
            domain = match.group(1)
            # 주요 언론사 매핑
            source_mapping = {
                'naver.com': '네이버뉴스',
                'yonhapnews.co.kr': '연합뉴스',
                'mk.co.kr': '매일경제',
                'hankyung.com': '한국경제',
                'edaily.co.kr': '이데일리',
                'etnews.com': '전자신문'
            }

            for key, value in source_mapping.items():
                if key in domain:
                    return value

            return domain

        return 'Unknown'

    def save_news_data(self, ticker: str, news_data: List[dict]) -> int:
        """
        뉴스 데이터를 데이터베이스에 저장

        Args:
            ticker: 종목 코드
            news_data: 뉴스 데이터 리스트

        Returns:
            저장된 레코드 수
        """
        if not news_data:
            logger.warning("No news data to save")
            return 0

        saved_count = 0

        with get_db_connection() as conn:
            cursor = conn.cursor()
            try:
                for news in news_data:
                    try:
                        # 중복 체크 (ticker + url)
                        cursor.execute("""
                            SELECT id FROM news WHERE ticker = ? AND url = ?
                        """, (ticker, news['url']))

                        if cursor.fetchone():
                            continue  # 이미 존재하면 건너뜀

                        cursor.execute("""
                            INSERT INTO news (ticker, date, title, url, source, relevance_score)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            ticker,
                            news['date'],
                            news['title'],
                            news['url'],
                            news['source'],
                            news.get('relevance_score', 0.5)
                        ))
                        saved_count += 1

                    except Exception as e:
                        logger.error(f"Failed to save news record: {e}")
                        continue

                conn.commit()
                logger.info(f"Saved {saved_count} news records for {ticker}")

            except Exception as e:
                logger.error(f"Database error saving news: {e}")
                conn.rollback()
                saved_count = 0  # 롤백 시 저장된 레코드 없음

        return saved_count

    def collect_and_save_news(self, ticker: str, days: int = 7) -> Dict:
        """
        종목의 뉴스를 수집하고 저장

        Args:
            ticker: 종목 코드
            days: 수집할 일수

        Returns:
            수집 결과 딕셔너리
        """
        logger.info(f"Starting news collection for {ticker} (last {days} days)")

        stock_config = self.stock_config.get(ticker)

        if not stock_config:
            logger.warning(f"No configuration defined for ticker: {ticker}")
            return {
                'ticker': ticker,
                'collected': 0,
                'keywords_used': [],
                'message': 'No configuration defined'
            }

        # 네이버 뉴스 검색
        news_data = self.fetch_naver_news(
            keyword=stock_config['search_keyword'],
            days=days,
            relevance_keywords=stock_config['relevance_keywords'],
            min_relevance=0.0  # 모든 뉴스 수집 (필터링 안함)
        )

        # 데이터베이스 저장
        saved_count = self.save_news_data(ticker, news_data)

        return {
            'ticker': ticker,
            'collected': saved_count,
            'keywords_used': [stock_config['search_keyword']],
            'message': f'Successfully collected {saved_count} news articles'
        }

    def get_news_for_ticker(self, ticker: str, start_date: date, end_date: date) -> List[News]:
        """
        데이터베이스에서 종목의 뉴스 조회

        Args:
            ticker: 종목 코드
            start_date: 시작 날짜
            end_date: 종료 날짜

        Returns:
            뉴스 리스트
        """
        logger.info(f"Fetching news for {ticker} from {start_date} to {end_date}")

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT date, title, url, source, relevance_score
                FROM news
                WHERE ticker = ? AND date BETWEEN ? AND ?
                ORDER BY date DESC, relevance_score DESC
            """, (ticker, start_date, end_date))

            rows = cursor.fetchall()

            news_list = []
            for row in rows:
                news_list.append(News(
                    date=row['date'],
                    title=row['title'],
                    url=row['url'],
                    source=row['source'],
                    relevance_score=row['relevance_score']
                ))

        logger.info(f"Retrieved {len(news_list)} news articles for {ticker}")
        return news_list
