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

    @retry_with_backoff(
        max_retries=3,
        base_delay=1.0,
        exceptions=(requests.exceptions.RequestException, requests.exceptions.Timeout)
    )
    def _collect_etf_stocks(self) -> List[Dict[str, Any]]:
        """ETF 종목 목록 수집"""
        stocks = []
        page = 1
        max_pages = 20  # ETF는 약 300개 종목, 페이지당 20개
        
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
                    # 디버깅을 위해 페이지 내용 일부 출력
                    logger.debug(f"Page content preview: {response.text[:500]}")
                    break
                
                rows = table.find_all('tr')
                
                if not rows:
                    break
                
                page_stocks = []
                for row in rows:
                    cols = row.find_all('td')
                    # 데이터 행은 td가 여러 개 있어야 함 (보통 10개 이상)
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
            
            # 기존 데이터베이스의 모든 활성 종목 조회
            cursor.execute("SELECT ticker FROM stock_catalog WHERE is_active = 1")
            existing_active_tickers = {row[0] for row in cursor.fetchall()}
            
            # 상장폐지된 종목 찾기 (기존에는 있지만 수집된 목록에는 없음)
            deactivated_tickers = existing_active_tickers - collected_tickers
            
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
            
            # 신규/업데이트 종목 저장
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
            if stock_type:
                cursor.execute("""
                    SELECT ticker, name, type, market, sector
                    FROM stock_catalog
                    WHERE is_active = 1
                      AND type = ?
                      AND (ticker LIKE ? OR name LIKE ?)
                    ORDER BY 
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
                    WHERE is_active = 1
                      AND (ticker LIKE ? OR name LIKE ?)
                    ORDER BY 
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

