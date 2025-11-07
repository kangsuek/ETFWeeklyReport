from typing import List, Dict, Optional
from datetime import date, datetime, timedelta
from app.models import News
from app.database import get_db_connection
import logging
import requests
from bs4 import BeautifulSoup
import time
import re
from urllib.parse import quote

logger = logging.getLogger(__name__)

class NewsScraper:
    """Service for scraping news from various sources"""
    
    # 6개 종목별 테마 키워드
    THEME_KEYWORDS = {
        "487240": ["AI", "전력", "인공지능", "데이터센터", "반도체"],
        "466920": ["조선", "선박", "해운", "HD현대", "한화오션", "삼성중공업"],
        "0020H0": ["양자컴퓨팅", "양자컴퓨터", "퀀텀", "quantum"],
        "442320": ["원자력", "원전", "핵발전", "SMR", "원자로"],
        "042660": ["한화오션", "조선", "선박", "방산", "잠수함"],
        "034020": ["두산에너빌리티", "발전", "전력", "에너지", "가스터빈"]
    }
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
    
    def fetch_naver_news(self, keyword: str, days: int = 7) -> List[dict]:
        """
        Naver 뉴스 검색 결과 스크래핑
        
        **Note**: Naver 뉴스는 JavaScript 기반 동적 로딩을 사용하므로,
        실제 스크래핑을 위해서는 Selenium 또는 Playwright 같은 도구가 필요합니다.
        현재는 Mock 데이터로 구현되어 있습니다.
        
        Args:
            keyword: 검색 키워드
            days: 검색할 일수 (기본: 7일)
        
        Returns:
            뉴스 데이터 리스트
        """
        logger.info(f"Fetching news for keyword: {keyword} (Mock implementation)")
        
        # TODO: Selenium/Playwright를 사용한 실제 스크래핑 구현 필요
        # 현재는 Mock 데이터 반환
        
        news_data = []
        base_date = date.today()
        
        # Mock 뉴스 데이터 생성 (키워드에 따라 3-5개)
        mock_news_count = min(5, days)
        
        for i in range(mock_news_count):
            news_date = base_date - timedelta(days=i)
            
            news_data.append({
                'date': news_date,
                'title': f'{keyword} 관련 뉴스 {i+1} - 최신 동향 및 시장 전망',
                'url': f'https://news.naver.com/mock/{keyword.replace(" ", "_")}/{i+1}',
                'source': ['뉴스1', '연합뉴스', '이데일리', '매일경제', '한국경제'][i % 5],
                'relevance_score': 0.9 - (i * 0.1)
            })
        
        logger.info(f"Collected {len(news_data)} mock news items for keyword: {keyword}")
        return news_data
    
    def _parse_news_date(self, date_str: str) -> Optional[date]:
        """
        뉴스 날짜 문자열을 date 객체로 변환
        
        Args:
            date_str: 날짜 문자열 (예: "1시간 전", "2일 전", "2025.11.07")
        
        Returns:
            date 객체 또는 None
        """
        try:
            # "N시간 전" 패턴
            if '시간' in date_str and '전' in date_str:
                return date.today()
            
            # "N분 전" 패턴
            if '분' in date_str and '전' in date_str:
                return date.today()
            
            # "N일 전" 패턴
            if '일' in date_str and '전' in date_str:
                match = re.search(r'(\d+)일', date_str)
                if match:
                    days_ago = int(match.group(1))
                    return date.today() - timedelta(days=days_ago)
            
            # "YYYY.MM.DD" 패턴
            if '.' in date_str:
                date_str_clean = date_str.split()[0]  # 시간 부분 제거
                return datetime.strptime(date_str_clean, '%Y.%m.%d').date()
            
            # 기본값: 오늘
            return date.today()
            
        except Exception as e:
            logger.warning(f"Failed to parse date: {date_str}, error: {e}")
            return date.today()
    
    def _calculate_relevance(self, title: str, keyword: str) -> float:
        """
        제목과 키워드 기반 관련도 점수 계산
        
        Args:
            title: 뉴스 제목
            keyword: 검색 키워드
        
        Returns:
            관련도 점수 (0.0 ~ 1.0)
        """
        title_lower = title.lower()
        keyword_lower = keyword.lower()
        
        # 키워드가 제목에 포함되면 1.0
        if keyword_lower in title_lower:
            return 1.0
        
        # 부분 일치 점수
        keyword_words = keyword_lower.split()
        matches = sum(1 for word in keyword_words if word in title_lower)
        
        if len(keyword_words) > 0:
            return matches / len(keyword_words)
        
        return 0.5  # 기본 점수
    
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
        
        conn = get_db_connection()
        cursor = conn.cursor()
        saved_count = 0
        
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
        
        finally:
            conn.close()
        
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
        
        keywords = self.THEME_KEYWORDS.get(ticker, [])
        
        if not keywords:
            logger.warning(f"No keywords defined for ticker: {ticker}")
            return {
                'ticker': ticker,
                'collected': 0,
                'keywords_used': [],
                'message': 'No keywords defined'
            }
        
        all_news = []
        
        # 각 키워드로 뉴스 검색
        for keyword in keywords[:2]:  # 주요 키워드 2개만 사용
            news_data = self.fetch_naver_news(keyword, days)
            all_news.extend(news_data)
            time.sleep(0.5)  # Rate limiting
        
        # 중복 제거 (URL 기준)
        unique_news = []
        seen_urls = set()
        for news in all_news:
            if news['url'] not in seen_urls:
                unique_news.append(news)
                seen_urls.add(news['url'])
        
        # 데이터베이스 저장
        saved_count = self.save_news_data(ticker, unique_news)
        
        return {
            'ticker': ticker,
            'collected': saved_count,
            'keywords_used': keywords[:2],
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
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT date, title, url, source, relevance_score
            FROM news
            WHERE ticker = ? AND date BETWEEN ? AND ?
            ORDER BY date DESC, relevance_score DESC
        """, (ticker, start_date, end_date))
        
        rows = cursor.fetchall()
        conn.close()
        
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
