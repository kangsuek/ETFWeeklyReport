from typing import List, Dict, Optional
from datetime import date, datetime, timedelta
from app.models import News
from app.database import get_db_connection, get_cursor, USE_POSTGRES
from app.config import Config
from app.utils.retry import retry_with_backoff
from app.utils.rate_limiter import RateLimiter
from app.constants import NEWS_RATE_LIMITER_INTERVAL
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
        
        # Rate Limiter 초기화
        self.rate_limiter = RateLimiter(min_interval=NEWS_RATE_LIMITER_INTERVAL)

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
        뉴스 아이템의 관련도 점수 계산 (고도화된 버전 v3)

        Args:
            news_item: 뉴스 아이템 (title, description 포함)
            keywords: 검색 키워드 리스트

        Returns:
            관련도 점수 (0.40 ~ 1.0)

        개선 사항 (v3):
            - 단순화된 점수 체계로 높은 점수 보장
            - 제목 키워드 매칭: 즉시 높은 점수 (0.6 이상)
            - 본문 키워드 매칭: 중간 점수 (0.5 이상)
            - 기본 점수 40% 보장 (검색 API로 찾은 뉴스)
            - 목표: 최소 0.40, 평균 0.50~0.60, 최대 1.00
        """
        title = self._clean_html_tags(news_item.get('title', '')).lower()
        description = self._clean_html_tags(news_item.get('description', '')).lower()

        matched_keywords = 0
        title_matches = 0
        desc_matches = 0

        for keyword in keywords:
            keyword_lower = keyword.lower()

            if keyword_lower in title:
                title_matches += 1
                matched_keywords += 1
            elif keyword_lower in description:
                desc_matches += 1
                matched_keywords += 1

        # 키워드 매칭 비율
        keyword_ratio = matched_keywords / len(keywords) if len(keywords) > 0 else 0

        # 점수 계산 로직
        if title_matches == 0 and desc_matches == 0:
            # 매칭 없음 (하지만 검색으로 찾았으므로 기본 점수)
            final_score = 0.40
        elif title_matches >= 2:
            # 제목에 2개 이상 키워드 → 매우 높은 관련도
            final_score = 0.80 + (keyword_ratio * 0.20)
        elif title_matches == 1 and desc_matches >= 1:
            # 제목 1개 + 본문 1개 이상 → 높은 관련도
            final_score = 0.70 + (keyword_ratio * 0.20)
        elif title_matches == 1:
            # 제목에만 1개 → 중상 관련도
            final_score = 0.60 + (keyword_ratio * 0.20)
        elif desc_matches >= 2:
            # 본문에 2개 이상 → 중간 관련도
            final_score = 0.55 + (keyword_ratio * 0.15)
        else:
            # 본문에 1개 → 중하 관련도
            final_score = 0.45 + (keyword_ratio * 0.15)

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
        
        벌크 insert를 사용하여 성능 최적화
        중복 체크는 먼저 수행하고, 새로운 뉴스만 벌크 insert

        Args:
            ticker: 종목 코드
            news_data: 뉴스 데이터 리스트

        Returns:
            저장된 레코드 수
        """
        if not news_data:
            logger.warning("No news data to save")
            return 0

        # 중복 체크 및 새로운 뉴스만 필터링
        # PostgreSQL과 SQLite의 플레이스홀더 차이
        param_placeholder = "%s" if USE_POSTGRES else "?"

        with get_db_connection() as conn_or_cursor:
            # PostgreSQL과 SQLite 처리 분기
            if USE_POSTGRES:
                cursor = conn_or_cursor
                conn = cursor.connection
            else:
                conn = conn_or_cursor
                cursor = conn.cursor()

            try:
                # 기존 뉴스 URL 조회 (중복 체크)
                cursor.execute(f"""
                    SELECT url FROM news WHERE ticker = {param_placeholder}
                """, (ticker,))
                # PostgreSQL RealDictCursor는 dict를 반환
                existing_urls = {row['url'] if USE_POSTGRES else row[0] for row in cursor.fetchall()}

                # 새로운 뉴스만 필터링
                new_news = [
                    news for news in news_data
                    if news.get('url') and news['url'] not in existing_urls
                ]

                if not new_news:
                    logger.info(f"No new news records to save for {ticker} (all duplicates)")
                    return 0

                # 벌크 insert 수행
                if USE_POSTGRES:
                    cursor.executemany("""
                        INSERT INTO news (ticker, date, title, url, source, relevance_score)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, [
                        (
                            ticker,
                            news['date'],
                            news['title'],
                            news['url'],
                            news['source'],
                            news.get('relevance_score', 0.5)
                        )
                        for news in new_news
                    ])
                else:
                    cursor.executemany("""
                        INSERT INTO news (ticker, date, title, url, source, relevance_score)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, [
                        (
                            ticker,
                            news['date'],
                            news['title'],
                            news['url'],
                            news['source'],
                            news.get('relevance_score', 0.5)
                        )
                        for news in new_news
                    ])

                conn.commit()
                saved_count = len(new_news)
                logger.info(f"Saved {saved_count} news records for {ticker} (bulk insert)")

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

        # 최신 설정을 매번 읽어옴 (캐시 무효화)
        Config._stock_config_cache = None
        stock_config = Config.get_stock_config().get(ticker)

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
            min_relevance=0.5  # 중간 이상 관련도 (품질 필터링)
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

        # PostgreSQL과 SQLite의 플레이스홀더 차이
        param_placeholder = "%s" if USE_POSTGRES else "?"

        with get_db_connection() as conn_or_cursor:
            cursor = get_cursor(conn_or_cursor)
            cursor.execute(f"""
                SELECT date, title, url, source, relevance_score
                FROM news
                WHERE ticker = {param_placeholder} AND date BETWEEN {param_placeholder} AND {param_placeholder}
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
