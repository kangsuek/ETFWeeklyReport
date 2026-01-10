"""
네이버 금융에서 전체 종목 목록 수집

한국 주식/ETF 전체 목록을 수집하여 stock_catalog 테이블에 저장합니다.
"""
import logging
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from app.utils.retry import retry_with_backoff
from app.utils.rate_limiter import RateLimiter
from app.constants import DEFAULT_RATE_LIMITER_INTERVAL
from app.database import get_db_connection
from app.exceptions import ScraperException

logger = logging.getLogger(__name__)

# Selenium 선택적 사용 (설치되어 있으면 사용)
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    logger.warning("Selenium not available. ETF collection will use fallback method.")

# 검색 결과 캐시 (최대 128개 쿼리 캐싱, 5분 TTL)
_search_cache: Dict[str, tuple[List[Dict[str, Any]], datetime]] = {}
_CACHE_TTL = timedelta(minutes=5)
_MAX_CACHE_SIZE = 128


class TickerCatalogCollector:
    """네이버 금융에서 종목 목록 수집 서비스"""

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.rate_limiter = RateLimiter(min_interval=DEFAULT_RATE_LIMITER_INTERVAL)

    def collect_all_stocks(self) -> Dict[str, Any]:
        """
        전체 종목 목록 수집 (코스피, 코스닥, ETF)
        
        Returns:
            Dict with collection statistics
        """
        logger.info("Starting ticker catalog collection from Naver Finance")
        
        all_stocks = []
        
        try:
            # 1. 코스피 종목 수집
            logger.info("Collecting KOSPI stocks...")
            kospi_stocks = self._collect_kospi_stocks()
            all_stocks.extend(kospi_stocks)
            logger.info(f"Collected {len(kospi_stocks)} KOSPI stocks")
            
            # 2. 코스닥 종목 수집
            logger.info("Collecting KOSDAQ stocks...")
            kosdaq_stocks = self._collect_kosdaq_stocks()
            all_stocks.extend(kosdaq_stocks)
            logger.info(f"Collected {len(kosdaq_stocks)} KOSDAQ stocks")
            
            # 3. ETF 종목 수집
            logger.info("Collecting ETF stocks...")
            etf_stocks = self._collect_etf_stocks()
            all_stocks.extend(etf_stocks)
            logger.info(f"Collected {len(etf_stocks)} ETF stocks")
            
            # 4. 데이터베이스에 저장
            logger.info(f"Saving {len(all_stocks)} stocks to database...")
            saved_count = self._save_to_database(all_stocks)
            
            # 5. 검색 캐시 무효화 (새로운 데이터가 추가되었으므로)
            self.clear_search_cache()
            
            result = {
                "total_collected": len(all_stocks),
                "kospi_count": len(kospi_stocks),
                "kosdaq_count": len(kosdaq_stocks),
                "etf_count": len(etf_stocks),
                "saved_count": saved_count,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Ticker catalog collection completed: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error collecting ticker catalog: {e}", exc_info=True)
            raise ScraperException(f"종목 목록 수집 실패: {e}")

    @retry_with_backoff(
        max_retries=3,
        base_delay=1.0,
        exceptions=(requests.exceptions.RequestException, requests.exceptions.Timeout)
    )
    def _collect_kospi_stocks(self) -> List[Dict[str, Any]]:
        """코스피 종목 목록 수집"""
        stocks = []
        page = 1
        max_pages = 50  # 코스피는 약 800개 종목, 페이지당 20개
        
        while page <= max_pages:
            url = f"https://finance.naver.com/sise/sise_market_sum.naver?sosok=0&page={page}"
            
            try:
                with self.rate_limiter:
                    response = requests.get(url, headers=self.headers, timeout=10)
                    response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 여러 가능한 테이블 클래스 시도
                table = soup.find('table', {'class': 'type_2'})
                if not table:
                    table = soup.find('table', {'class': 'type2'})
                if not table:
                    # 모든 테이블 찾기
                    tables = soup.find_all('table')
                    if tables:
                        # 종목 목록이 있는 테이블 찾기 (a 태그가 많은 테이블)
                        for t in tables:
                            links = t.find_all('a', href=True)
                            if len(links) > 5:  # 종목 링크가 여러 개 있는 테이블
                                table = t
                                break
                
                if not table:
                    logger.warning(f"KOSPI table not found on page {page}, URL: {url}")
                    break
                
                rows = table.find_all('tr')
                
                if not rows:
                    break
                
                page_stocks = []
                for row in rows:
                    cols = row.find_all('td')
                    # 데이터 행은 td가 여러 개 있어야 함 (보통 10개 이상)
                    if len(cols) < 10:
                        continue
                    
                    # 모든 링크 찾기 (종목 링크는 /item/main.naver?code= 형태)
                    links = row.find_all('a', href=True)
                    for link in links:
                        href = link.get('href', '')
                        if '/item/main.naver?code=' in href:
                            ticker = href.split('code=')[-1].split('&')[0]  # code= 뒤의 값, & 이전까지
                            name = link.get_text(strip=True)
                            
                            if ticker and name and len(ticker) >= 5:  # 티커는 최소 5자리
                                page_stocks.append({
                                    "ticker": ticker,
                                    "name": name,
                                    "type": "STOCK",
                                    "market": "KOSPI",
                                    "sector": None,
                                    "listed_date": None,
                                    "is_active": 1
                                })
                                break  # 한 행에서 하나의 종목만 수집
                
                if not page_stocks:
                    break
                
                stocks.extend(page_stocks)
                logger.debug(f"KOSPI page {page}: collected {len(page_stocks)} stocks")
                page += 1
                
            except Exception as e:
                logger.error(f"Error collecting KOSPI page {page}: {e}")
                break
        
        return stocks

    @retry_with_backoff(
        max_retries=3,
        base_delay=1.0,
        exceptions=(requests.exceptions.RequestException, requests.exceptions.Timeout)
    )
    def _collect_kosdaq_stocks(self) -> List[Dict[str, Any]]:
        """코스닥 종목 목록 수집"""
        stocks = []
        page = 1
        max_pages = 100  # 코스닥은 약 1500개 종목, 페이지당 20개
        
        while page <= max_pages:
            url = f"https://finance.naver.com/sise/sise_market_sum.naver?sosok=1&page={page}"
            
            try:
                with self.rate_limiter:
                    response = requests.get(url, headers=self.headers, timeout=10)
                    response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 여러 가능한 테이블 클래스 시도
                table = soup.find('table', {'class': 'type_2'})
                if not table:
                    table = soup.find('table', {'class': 'type2'})
                if not table:
                    # 모든 테이블 찾기
                    tables = soup.find_all('table')
                    if tables:
                        # 종목 목록이 있는 테이블 찾기 (a 태그가 많은 테이블)
                        for t in tables:
                            links = t.find_all('a', href=True)
                            if len(links) > 5:  # 종목 링크가 여러 개 있는 테이블
                                table = t
                                break
                
                if not table:
                    logger.warning(f"KOSDAQ table not found on page {page}, URL: {url}")
                    break
                
                rows = table.find_all('tr')
                
                if not rows:
                    break
                
                page_stocks = []
                for row in rows:
                    cols = row.find_all('td')
                    # 데이터 행은 td가 여러 개 있어야 함 (보통 10개 이상)
                    if len(cols) < 10:
                        continue
                    
                    # 모든 링크 찾기 (종목 링크는 /item/main.naver?code= 형태)
                    links = row.find_all('a', href=True)
                    for link in links:
                        href = link.get('href', '')
                        if '/item/main.naver?code=' in href:
                            ticker = href.split('code=')[-1].split('&')[0]  # code= 뒤의 값, & 이전까지
                            name = link.get_text(strip=True)
                            
                            if ticker and name and len(ticker) >= 5:  # 티커는 최소 5자리
                                page_stocks.append({
                                    "ticker": ticker,
                                    "name": name,
                                    "type": "STOCK",
                                    "market": "KOSDAQ",
                                    "sector": None,
                                    "listed_date": None,
                                    "is_active": 1
                                })
                                break  # 한 행에서 하나의 종목만 수집
                
                if not page_stocks:
                    break
                
                stocks.extend(page_stocks)
                logger.debug(f"KOSDAQ page {page}: collected {len(page_stocks)} stocks")
                page += 1
                
            except Exception as e:
                logger.error(f"Error collecting KOSDAQ page {page}: {e}")
                break
        
        return stocks

    def _collect_etf_stocks(self) -> List[Dict[str, Any]]:
        """
        ETF 종목 목록 수집
        
        Selenium을 사용하여 JavaScript로 동적 로드되는 ETF 목록을 수집합니다.
        Selenium이 없으면 기본 requests 방식으로 시도합니다.
        """
        if SELENIUM_AVAILABLE:
            try:
                return self._collect_etf_stocks_selenium()
            except Exception as e:
                logger.warning(f"Selenium ETF collection failed, falling back to requests: {e}")
                return self._collect_etf_stocks_requests()
        else:
            return self._collect_etf_stocks_requests()
    
    def _collect_etf_stocks_selenium(self) -> List[Dict[str, Any]]:
        """Selenium을 사용한 ETF 종목 목록 수집"""
        stocks = []
        driver = None
        
        try:
            # Chrome 옵션 설정 (headless 모드)
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            
            # WebDriver 초기화
            try:
                driver_path = ChromeDriverManager().install()
                # chromedriver 실행 파일 찾기 (디렉토리 내에서)
                import os
                if os.path.isdir(driver_path):
                    # 디렉토리인 경우 chromedriver 실행 파일 찾기
                    for root, dirs, files in os.walk(driver_path):
                        for file in files:
                            if file == 'chromedriver' or file.startswith('chromedriver'):
                                driver_path = os.path.join(root, file)
                                break
                        if driver_path != ChromeDriverManager().install():
                            break
                
                service = Service(driver_path)
                driver = webdriver.Chrome(service=service, options=chrome_options)
            except Exception as e:
                # ChromeDriverManager 실패 시 시스템 PATH에서 chromedriver 찾기
                logger.warning(f"ChromeDriverManager failed: {e}, trying system chromedriver")
                driver = webdriver.Chrome(options=chrome_options)
            
            driver.implicitly_wait(5)
            
            page = 1
            max_pages = 20  # ETF는 약 300개 종목, 페이지당 20개
            
            while page <= max_pages:
                url = f"https://finance.naver.com/sise/etf.naver?&page={page}"
                logger.debug(f"Loading ETF page {page}: {url}")
                
                driver.get(url)
                
                # 테이블이 로드될 때까지 대기
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.TAG_NAME, "table"))
                    )
                except Exception:
                    logger.warning(f"Table not found on ETF page {page}")
                    break
                
                # 페이지 소스 가져오기
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                
                # 테이블 찾기
                table = soup.find('table', {'class': 'type_2'})
                if not table:
                    table = soup.find('table', {'class': 'type2'})
                if not table:
                    # 모든 테이블 중 종목 링크가 많은 테이블 찾기
                    tables = soup.find_all('table')
                    for t in tables:
                        links = t.find_all('a', href=True)
                        if len(links) > 5:
                            table = t
                            break
                
                if not table:
                    logger.warning(f"ETF table not found on page {page}")
                    break
                
                rows = table.find_all('tr')
                page_stocks = []
                
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) < 5:
                        continue
                    
                    # 종목 링크 찾기
                    links = row.find_all('a', href=True)
                    for link in links:
                        href = link.get('href', '')
                        if '/item/main.naver?code=' in href:
                            ticker = href.split('code=')[-1].split('&')[0]
                            name = link.get_text(strip=True)
                            
                            if ticker and name and len(ticker) >= 5:
                                page_stocks.append({
                                    "ticker": ticker,
                                    "name": name,
                                    "type": "ETF",
                                    "market": "ETF",
                                    "sector": None,
                                    "listed_date": None,
                                    "is_active": 1
                                })
                                break
                
                if not page_stocks:
                    break
                
                stocks.extend(page_stocks)
                logger.debug(f"ETF page {page}: collected {len(page_stocks)} stocks")
                page += 1
                
                # 페이지 간 대기 (Rate limiting)
                import time
                time.sleep(0.5)
            
            # 중복 제거 (티커 코드 기준)
            seen_tickers = set()
            unique_stocks = []
            for stock in stocks:
                ticker = stock["ticker"]
                if ticker not in seen_tickers:
                    seen_tickers.add(ticker)
                    unique_stocks.append(stock)
            
            logger.info(f"Collected {len(unique_stocks)} unique ETF stocks using Selenium (total: {len(stocks)}, duplicates removed: {len(stocks) - len(unique_stocks)})")
            return unique_stocks
            
        except Exception as e:
            logger.error(f"Error collecting ETF stocks with Selenium: {e}", exc_info=True)
            raise
        finally:
            if driver:
                driver.quit()
    
    @retry_with_backoff(
        max_retries=3,
        base_delay=1.0,
        exceptions=(requests.exceptions.RequestException, requests.exceptions.Timeout)
    )
    def _collect_etf_stocks_requests(self) -> List[Dict[str, Any]]:
        """requests를 사용한 ETF 종목 목록 수집 (fallback)"""
        stocks = []
        page = 1
        max_pages = 20
        
        while page <= max_pages:
            url = f"https://finance.naver.com/sise/etf.naver?&page={page}"
            
            try:
                with self.rate_limiter:
                    response = requests.get(url, headers=self.headers, timeout=10)
                    response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 여러 가능한 테이블 클래스 시도
                table = soup.find('table', {'class': 'type_2'})
                if not table:
                    table = soup.find('table', {'class': 'type2'})
                if not table:
                    # 모든 테이블 찾기
                    tables = soup.find_all('table')
                    if tables:
                        # 종목 목록이 있는 테이블 찾기 (a 태그가 많은 테이블)
                        for t in tables:
                            links = t.find_all('a', href=True)
                            if len(links) > 5:  # 종목 링크가 여러 개 있는 테이블
                                table = t
                                break
                
                if not table:
                    logger.warning(f"ETF table not found on page {page}, URL: {url}")
                    break
                
                rows = table.find_all('tr')
                
                if not rows:
                    break
                
                page_stocks = []
                for row in rows:
                    cols = row.find_all('td')
                    # 데이터 행은 td가 여러 개 있어야 함
                    if len(cols) < 5:  # ETF는 컬럼이 적을 수 있음
                        continue
                    
                    # 모든 링크 찾기 (종목 링크는 /item/main.naver?code= 형태)
                    links = row.find_all('a', href=True)
                    for link in links:
                        href = link.get('href', '')
                        if '/item/main.naver?code=' in href:
                            ticker = href.split('code=')[-1].split('&')[0]  # code= 뒤의 값, & 이전까지
                            name = link.get_text(strip=True)
                            
                            if ticker and name and len(ticker) >= 5:  # 티커는 최소 5자리
                                page_stocks.append({
                                    "ticker": ticker,
                                    "name": name,
                                    "type": "ETF",
                                    "market": "ETF",
                                    "sector": None,
                                    "listed_date": None,
                                    "is_active": 1
                                })
                                break  # 한 행에서 하나의 종목만 수집
                
                if not page_stocks:
                    break
                
                stocks.extend(page_stocks)
                logger.debug(f"ETF page {page}: collected {len(page_stocks)} stocks")
                page += 1
                
            except Exception as e:
                logger.error(f"Error collecting ETF page {page}: {e}")
                break
        
        return stocks

    def _save_to_database(self, stocks: List[Dict[str, Any]]) -> int:
        """
        수집한 종목 목록을 데이터베이스에 저장
        
        기존 종목과 비교하여:
        - 신규 종목: 추가
        - 기존 종목: 업데이트 (종목명 변경 반영)
        - 상장폐지 종목: is_active = 0으로 표시
        """
        if not stocks:
            return 0
        
        saved_count = 0
        updated_count = 0
        deactivated_count = 0
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # 현재 수집된 종목의 티커 코드 집합
            collected_tickers = {stock["ticker"] for stock in stocks}
            
            # 1단계: 먼저 수집된 종목을 모두 저장 (is_active = 1로 설정)
            for stock in stocks:
                try:
                    # 기존 종목인지 확인
                    cursor.execute("SELECT name FROM stock_catalog WHERE ticker = ?", (stock["ticker"],))
                    existing = cursor.fetchone()
                    
                    if existing:
                        # 기존 종목 업데이트 (종목명 변경 반영)
                        if existing[0] != stock["name"]:
                            logger.debug(f"Updating stock name: {stock['ticker']} - {existing[0]} -> {stock['name']}")
                        updated_count += 1
                    else:
                        # 신규 종목 추가
                        logger.debug(f"Adding new stock: {stock['ticker']} - {stock['name']}")
                    
                    cursor.execute("""
                        INSERT OR REPLACE INTO stock_catalog 
                        (ticker, name, type, market, sector, listed_date, last_updated, is_active)
                        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
                    """, (
                        stock["ticker"],
                        stock["name"],
                        stock["type"],
                        stock["market"],
                        stock["sector"],
                        stock["listed_date"],
                        stock["is_active"]
                    ))
                    saved_count += 1
                except Exception as e:
                    logger.warning(f"Failed to save stock {stock.get('ticker')}: {e}")
                    continue
            
            # 2단계: 수집된 종목 저장 후, 상장폐지 종목 찾기 및 비활성화
            # 기존 데이터베이스의 모든 종목 조회 (수집 전 상태)
            cursor.execute("SELECT ticker FROM stock_catalog")
            all_existing_tickers = {row[0] for row in cursor.fetchall()}
            
            # 상장폐지된 종목 찾기 (기존에는 있지만 수집된 목록에는 없음)
            deactivated_tickers = all_existing_tickers - collected_tickers
            
            # 상장폐지 종목 비활성화
            if deactivated_tickers:
                placeholders = ','.join(['?'] * len(deactivated_tickers))
                cursor.execute(f"""
                    UPDATE stock_catalog 
                    SET is_active = 0, last_updated = CURRENT_TIMESTAMP
                    WHERE ticker IN ({placeholders})
                """, list(deactivated_tickers))
                deactivated_count = cursor.rowcount
                logger.info(f"Deactivated {deactivated_count} stocks (delisted)")
            
            conn.commit()
        
        logger.info(
            f"Saved {saved_count} stocks to stock_catalog table "
            f"(updated: {updated_count}, deactivated: {deactivated_count})"
        )
        return saved_count

    def search_stocks(self, query: str, stock_type: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        """
        종목 목록 검색 (자동완성용)
        
        검색 결과는 5분간 캐싱되어 빠른 응답을 제공합니다.
        
        Args:
            query: 검색어 (티커 코드 또는 종목명)
            stock_type: 종목 타입 필터 (STOCK, ETF)
            limit: 최대 결과 수
        
        Returns:
            검색 결과 리스트
        """
        if not query or len(query) < 2:
            return []
        
        # 캐시 키 생성
        cache_key = f"{query.lower()}:{stock_type or 'all'}:{limit}"
        now = datetime.now()
        
        # 캐시 확인
        if cache_key in _search_cache:
            cached_result, cache_time = _search_cache[cache_key]
            if now - cache_time < _CACHE_TTL:
                logger.debug(f"Cache hit for query: {query}")
                return cached_result
            else:
                # 만료된 캐시 제거
                del _search_cache[cache_key]
        
        # 캐시 크기 제한 (LRU 방식)
        if len(_search_cache) >= _MAX_CACHE_SIZE:
            # 가장 오래된 항목 제거
            oldest_key = min(_search_cache.keys(), key=lambda k: _search_cache[k][1])
            del _search_cache[oldest_key]
        
        # 데이터베이스에서 검색
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # 티커 코드 또는 종목명으로 검색
            # 검색 시에는 is_active 필터를 제거하여 모든 종목 검색 가능
            # (활성 종목 우선 정렬)
            if stock_type:
                cursor.execute("""
                    SELECT ticker, name, type, market, sector
                    FROM stock_catalog
                    WHERE type = ?
                      AND (ticker LIKE ? OR name LIKE ?)
                    ORDER BY 
                        is_active DESC,
                        CASE 
                            WHEN ticker = ? THEN 1
                            WHEN ticker LIKE ? THEN 2
                            WHEN name LIKE ? THEN 3
                            ELSE 4
                        END,
                        name
                    LIMIT ?
                """, (
                    stock_type,
                    f"%{query}%",
                    f"%{query}%",
                    query,
                    f"{query}%",
                    f"{query}%",
                    limit
                ))
            else:
                cursor.execute("""
                    SELECT ticker, name, type, market, sector
                    FROM stock_catalog
                    WHERE (ticker LIKE ? OR name LIKE ?)
                    ORDER BY 
                        is_active DESC,
                        CASE 
                            WHEN ticker = ? THEN 1
                            WHEN ticker LIKE ? THEN 2
                            WHEN name LIKE ? THEN 3
                            ELSE 4
                        END,
                        name
                    LIMIT ?
                """, (
                    f"%{query}%",
                    f"%{query}%",
                    query,
                    f"{query}%",
                    f"{query}%",
                    limit
                ))
            
            rows = cursor.fetchall()
            
            result = [
                {
                    "ticker": row["ticker"],
                    "name": row["name"],
                    "type": row["type"],
                    "market": row["market"],
                    "sector": row["sector"]
                }
                for row in rows
            ]
            
            # 결과 캐싱
            _search_cache[cache_key] = (result, now)
            logger.debug(f"Cached search result for query: {query} ({len(result)} results)")
            
            return result

    @staticmethod
    def clear_search_cache():
        """검색 결과 캐시 초기화"""
        global _search_cache
        _search_cache.clear()
        logger.info("Search cache cleared")

