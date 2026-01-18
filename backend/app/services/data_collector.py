from typing import List, Optional, Dict
from datetime import date, datetime, timedelta
from app.models import ETF, PriceData, TradingFlow, ETFMetrics
from app.database import get_db_connection, get_cursor, USE_POSTGRES
from app.utils.retry import retry_with_backoff
from app.utils.rate_limiter import RateLimiter
from app.constants import (
    DAYS_IN_YEAR,
    TRADING_DAYS_PER_YEAR,
    PERCENT_MULTIPLIER,
    DEFAULT_RATE_LIMITER_INTERVAL
)
import logging
import requests
from bs4 import BeautifulSoup
import time
import re

logger = logging.getLogger(__name__)

class ETFDataCollector:
    """Service for collecting ETF/Stock data from various sources"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        # Rate Limiter 초기화
        self.rate_limiter = RateLimiter(min_interval=DEFAULT_RATE_LIMITER_INTERVAL)
        # NewsScraper 초기화 (뉴스 수집용)
        from app.services.news_scraper import NewsScraper
        self.news_scraper = NewsScraper()
    
    @retry_with_backoff(
        max_retries=3,
        base_delay=1.0,
        exceptions=(requests.exceptions.RequestException, requests.exceptions.Timeout)
    )
    def fetch_naver_finance_prices(self, ticker: str, days: int = 10) -> List[dict]:
        """
        Naver Finance에서 가격 데이터 수집

        Args:
            ticker: 종목 코드 (예: "487240")
            days: 수집할 일수 (기본: 10일)

        Returns:
            수집된 가격 데이터 리스트
        """
        price_data = []
        page = 1
        max_pages = (days // 10) + 2  # 한 페이지당 10개씩, 여유있게 +2

        try:
            logger.info(f"Fetching up to {days} days of data from Naver Finance for {ticker}")

            while len(price_data) < days and page <= max_pages:
                url = f"https://finance.naver.com/item/sise_day.naver?code={ticker}&page={page}"
                logger.debug(f"Fetching page {page} for {ticker}")

                with self.rate_limiter:
                    response = requests.get(url, headers=self.headers, timeout=10)
                    response.raise_for_status()

                soup = BeautifulSoup(response.text, 'html.parser')

                # 시세 테이블 찾기
                table = soup.find('table', {'class': 'type2'})
                if not table:
                    logger.warning(f"Price table not found for {ticker} on page {page}")
                    break

                # 데이터 행 추출
                rows = table.find_all('tr')
                rows_parsed_this_page = 0

                for row in rows:
                    # 이미 충분한 데이터를 수집했으면 종료
                    if len(price_data) >= days:
                        break

                    cols = row.find_all('td')
                    if len(cols) >= 7:  # 날짜, 종가, 전일비, 시가, 고가, 저가, 거래량
                        date_cell = cols[0].get_text(strip=True)

                        # 날짜 형식 확인 (YYYY.MM.DD)
                        if date_cell and '.' in date_cell:
                            try:
                                # 데이터 파싱
                                date_str = date_cell  # 2025.11.07
                                close_price = self._parse_number(cols[1].get_text(strip=True))
                                change_str = cols[2].get_text(strip=True)  # 예: "상승205" 또는 "하락1,375"
                                open_price = self._parse_number(cols[3].get_text(strip=True))
                                high_price = self._parse_number(cols[4].get_text(strip=True))
                                low_price = self._parse_number(cols[5].get_text(strip=True))
                                volume = self._parse_number(cols[6].get_text(strip=True))

                                # 등락률 계산
                                daily_change_pct = self._parse_change(change_str, close_price)

                                # 날짜 변환 (YYYY.MM.DD → YYYY-MM-DD)
                                date_obj = datetime.strptime(date_str, '%Y.%m.%d').date()

                                price_data.append({
                                    'ticker': ticker,
                                    'date': date_obj,
                                    'open_price': open_price,
                                    'high_price': high_price,
                                    'low_price': low_price,
                                    'close_price': close_price,
                                    'volume': volume,
                                    'daily_change_pct': daily_change_pct
                                })
                                rows_parsed_this_page += 1

                            except Exception as e:
                                logger.warning(f"Failed to parse row for {ticker} on page {page}: {e}")
                                continue

                # 이번 페이지에서 아무 데이터도 파싱하지 못했으면 더 이상 페이지가 없는 것
                if rows_parsed_this_page == 0:
                    logger.info(f"No more data available for {ticker} after page {page}")
                    break

                page += 1

            logger.info(f"Collected {len(price_data)} price records for {ticker} from {page-1} pages")
            return price_data

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error while fetching {ticker}: {e}")
            return price_data  # 수집된 데이터라도 반환
        except Exception as e:
            logger.error(f"Unexpected error while fetching {ticker}: {e}")
            return price_data  # 수집된 데이터라도 반환
    
    def _parse_number(self, text: str) -> Optional[float]:
        """숫자 문자열을 float로 변환 (쉼표 제거)"""
        if not text or not text.strip():
            return None
        try:
            # 쉼표 제거 후 숫자로 변환
            cleaned = text.replace(',', '')
            return float(cleaned)
        except (ValueError, AttributeError):
            return None
    
    def _parse_change(self, change_str: str, close_price: Optional[float]) -> Optional[float]:
        """
        전일비 문자열을 등락률(%)로 변환
        
        Args:
            change_str: "상승205", "하락1,375", "보합0" 형식
            close_price: 현재 종가
        
        Returns:
            등락률 (%) 또는 None
        """
        if not change_str or not close_price or close_price == 0:
            return None
        
        try:
            # "상승", "하락", "보합" 제거하고 숫자만 추출
            number_str = re.sub(r'[^0-9,-]', '', change_str)
            if not number_str or number_str == '0':
                return 0.0
            
            change_amount = float(number_str.replace(',', ''))
            
            # 하락이면 음수로
            if '하락' in change_str:
                change_amount = -change_amount
            
            # 등락률 계산: (전일비 / (종가 - 전일비)) * 100
            prev_price = close_price - change_amount
            if prev_price != 0:
                return round((change_amount / prev_price) * 100, 2)
            
            return None
        except Exception as e:
            logger.warning(f"Failed to parse change string '{change_str}': {e}")
            return None
    
    def validate_price_data(self, data: dict) -> tuple[bool, Optional[str]]:
        """
        가격 데이터 유효성 검증
        
        Args:
            data: 검증할 가격 데이터
        
        Returns:
            (is_valid, error_message) 튜플
        """
        # 필수 필드 확인
        required_fields = ['ticker', 'date', 'close_price']
        for field in required_fields:
            if field not in data or data[field] is None:
                return False, f"Missing required field: {field}"
        
        # 날짜 타입 확인
        if not isinstance(data['date'], date):
            return False, f"Invalid date type: {type(data['date'])}"
        
        # 종가 검증 (양수)
        if data['close_price'] <= 0:
            return False, f"Invalid close_price: {data['close_price']} (must be > 0)"
        
        # 시가/고가/저가 검증 (있는 경우)
        for price_field in ['open_price', 'high_price', 'low_price']:
            if price_field in data and data[price_field] is not None:
                if data[price_field] <= 0:
                    return False, f"Invalid {price_field}: {data[price_field]} (must be > 0)"
        
        # 거래량 검증 (0 이상)
        if 'volume' in data and data['volume'] is not None:
            if data['volume'] < 0:
                return False, f"Invalid volume: {data['volume']} (must be >= 0)"
        
        # 고가 >= 저가 검증
        if (data.get('high_price') is not None and 
            data.get('low_price') is not None):
            if data['high_price'] < data['low_price']:
                return False, f"high_price ({data['high_price']}) < low_price ({data['low_price']})"
        
        # 시가/고가/저가가 모두 있는 경우 범위 검증
        if (data.get('open_price') is not None and 
            data.get('high_price') is not None and 
            data.get('low_price') is not None):
            if not (data['low_price'] <= data['open_price'] <= data['high_price']):
                return False, f"open_price ({data['open_price']}) out of range [{data['low_price']}, {data['high_price']}]"
        
        # 종가 범위 검증
        if (data.get('high_price') is not None and 
            data.get('low_price') is not None):
            if not (data['low_price'] <= data['close_price'] <= data['high_price']):
                return False, f"close_price ({data['close_price']}) out of range [{data['low_price']}, {data['high_price']}]"
        
        return True, None
    
    def clean_price_data(self, data: dict) -> dict:
        """
        가격 데이터 정제 및 정규화
        
        Args:
            data: 정제할 가격 데이터
        
        Returns:
            정제된 가격 데이터
        """
        cleaned = data.copy()
        
        # 거래량이 None인 경우 0으로 처리
        if cleaned.get('volume') is None:
            cleaned['volume'] = 0
        
        # 거래량을 정수로 변환
        if isinstance(cleaned.get('volume'), float):
            cleaned['volume'] = int(cleaned['volume'])
        
        # 가격 필드를 소수점 2자리로 반올림 (누락된 필드는 None으로 유지)
        price_fields = ['open_price', 'high_price', 'low_price', 'close_price']
        for field in price_fields:
            if field not in cleaned:
                cleaned[field] = None
            elif cleaned[field] is not None:
                cleaned[field] = round(float(cleaned[field]), 2)
        
        # 등락률을 소수점 2자리로 반올림 (누락된 경우 None)
        if 'daily_change_pct' not in cleaned:
            cleaned['daily_change_pct'] = None
        elif cleaned['daily_change_pct'] is not None:
            cleaned['daily_change_pct'] = round(float(cleaned['daily_change_pct']), 2)
        
        return cleaned
    
    def save_price_data(self, price_data: List[dict]) -> int:
        """
        가격 데이터를 데이터베이스에 저장 (검증 및 정제 포함)
        
        벌크 insert를 사용하여 성능 최적화

        Args:
            price_data: 저장할 가격 데이터 리스트

        Returns:
            저장된 레코드 수
        """
        if not price_data:
            return 0

        # 모든 데이터를 먼저 검증하고 정제
        valid_data = []
        for data in price_data:
            # 데이터 검증
            is_valid, error_msg = self.validate_price_data(data)
            if not is_valid:
                logger.warning(f"Skipping invalid data for {data.get('ticker')} on {data.get('date')}: {error_msg}")
                continue

            # 데이터 정제
            cleaned_data = self.clean_price_data(data)
            valid_data.append(cleaned_data)

        if not valid_data:
            logger.warning("No valid price data to save after validation")
            return 0

        # 벌크 insert 수행
        with get_db_connection() as conn_or_cursor:
            # PostgreSQL과 SQLite 처리 분기
            if USE_POSTGRES:
                cursor = conn_or_cursor
                conn = cursor.connection
            else:
                conn = conn_or_cursor
                cursor = conn.cursor()

            try:
                # PostgreSQL과 SQLite의 문법 차이
                if USE_POSTGRES:
                    cursor.executemany("""
                        INSERT INTO prices
                        (ticker, date, open_price, high_price, low_price, close_price, volume, daily_change_pct)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (ticker, date) DO UPDATE SET
                            open_price = EXCLUDED.open_price,
                            high_price = EXCLUDED.high_price,
                            low_price = EXCLUDED.low_price,
                            close_price = EXCLUDED.close_price,
                            volume = EXCLUDED.volume,
                            daily_change_pct = EXCLUDED.daily_change_pct
                    """, [
                        (
                            data['ticker'],
                            data['date'],
                            data['open_price'],
                            data['high_price'],
                            data['low_price'],
                            data['close_price'],
                            data['volume'],
                            data['daily_change_pct']
                        )
                        for data in valid_data
                    ])
                else:
                    cursor.executemany("""
                        INSERT OR REPLACE INTO prices
                        (ticker, date, open_price, high_price, low_price, close_price, volume, daily_change_pct)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, [
                        (
                            data['ticker'],
                            data['date'],
                            data['open_price'],
                            data['high_price'],
                            data['low_price'],
                            data['close_price'],
                            data['volume'],
                            data['daily_change_pct']
                        )
                        for data in valid_data
                    ])

                conn.commit()
                saved_count = len(valid_data)
                logger.info(f"Saved {saved_count} price records to database (bulk insert)")

            except Exception as e:
                conn.rollback()
                logger.error(f"Database error while saving price data: {e}")
                saved_count = 0  # 롤백 시 저장된 레코드 없음

        return saved_count
    
    def collect_and_save_prices(self, ticker: str, days: int = 10) -> int:
        """
        Naver Finance에서 데이터 수집 후 데이터베이스에 저장
        
        Args:
            ticker: 종목 코드
            days: 수집할 일수
        
        Returns:
            저장된 레코드 수
        """
        logger.info(f"Starting price collection for {ticker} (last {days} days)")
        
        # 데이터 수집
        price_data = self.fetch_naver_finance_prices(ticker, days)
        
        if not price_data:
            logger.warning(f"No data collected for {ticker}")
            return 0
        
        # 데이터 저장
        saved_count = self.save_price_data(price_data)
        
        # Rate limiting은 fetch 함수에서 RateLimiter로 처리
        return saved_count
    
    def get_all_etfs(self) -> List[ETF]:
        """
        Get list of all ETFs from database, ordered by stocks.json configuration
        
        Returns:
            List[ETF]: ETFs ordered by stocks.json file
        """
        import json
        from app.config import Config
        from app.database import get_cursor
        
        with get_db_connection() as conn_or_cursor:
            cursor = get_cursor(conn_or_cursor)
            cursor.execute("SELECT * FROM etfs")
            rows = cursor.fetchall()

            # DB 데이터를 ticker를 키로 하는 딕셔너리로 변환
            etfs_dict = {}
            for row in rows:
                row_dict = dict(row)
                # relevance_keywords를 JSON 문자열에서 리스트로 파싱
                if row_dict.get('relevance_keywords'):
                    try:
                        row_dict['relevance_keywords'] = json.loads(row_dict['relevance_keywords'])
                    except json.JSONDecodeError:
                        row_dict['relevance_keywords'] = []
                etfs_dict[row_dict['ticker']] = ETF(**row_dict)

            # stocks.json의 순서대로 정렬
            stock_config = Config.get_stock_config()
            ordered_etfs = []
            for ticker in stock_config.keys():
                if ticker in etfs_dict:
                    ordered_etfs.append(etfs_dict[ticker])
            
            # stocks.json에 없지만 DB에 있는 종목들은 뒤에 추가 (fallback)
            for ticker, etf in etfs_dict.items():
                if ticker not in stock_config:
                    ordered_etfs.append(etf)

            return ordered_etfs
    
    def get_etf_info(self, ticker: str) -> Optional[ETF]:
        """Get basic info for specific ETF"""
        import json
        from app.database import USE_POSTGRES
        param_placeholder = "%s" if USE_POSTGRES else "?"
        with get_db_connection() as conn_or_cursor:
            cursor = get_cursor(conn_or_cursor)
            cursor.execute(f"SELECT * FROM etfs WHERE ticker = {param_placeholder}", (ticker,))
            row = cursor.fetchone()
            if row:
                row_dict = dict(row)
                # relevance_keywords를 JSON 문자열에서 리스트로 파싱
                if row_dict.get('relevance_keywords'):
                    try:
                        row_dict['relevance_keywords'] = json.loads(row_dict['relevance_keywords'])
                    except json.JSONDecodeError:
                        row_dict['relevance_keywords'] = []
                return ETF(**row_dict)
            return None
    
    def get_price_data_range(self, ticker: str) -> Optional[Dict[str, date]]:
        """
        DB에 저장된 가격 데이터의 날짜 범위 확인

        Args:
            ticker: 종목 코드

        Returns:
            {'min_date': date, 'max_date': date, 'count': int} 또는 None (데이터 없는 경우)
        """
        p = "%s" if USE_POSTGRES else "?"
        with get_db_connection() as conn_or_cursor:
            cursor = get_cursor(conn_or_cursor)
            cursor.execute(f"""
                SELECT MIN(date) as min_date, MAX(date) as max_date, COUNT(*) as count
                FROM prices
                WHERE ticker = {p}
            """, (ticker,))
            row = cursor.fetchone()

            if row and row['min_date'] and row['max_date']:
                return {
                    'min_date': datetime.strptime(row['min_date'], '%Y-%m-%d').date() if isinstance(row['min_date'], str) else row['min_date'],
                    'max_date': datetime.strptime(row['max_date'], '%Y-%m-%d').date() if isinstance(row['max_date'], str) else row['max_date'],
                    'count': row['count']
                }
            return None

    def get_trading_flow_data_range(self, ticker: str) -> Optional[Dict[str, date]]:
        """
        DB에 저장된 매매 동향 데이터의 날짜 범위 확인

        Args:
            ticker: 종목 코드

        Returns:
            {'min_date': date, 'max_date': date, 'count': int} 또는 None (데이터 없는 경우)
        """
        p = "%s" if USE_POSTGRES else "?"
        with get_db_connection() as conn_or_cursor:
            cursor = get_cursor(conn_or_cursor)
            cursor.execute(f"""
                SELECT MIN(date) as min_date, MAX(date) as max_date, COUNT(*) as count
                FROM trading_flow
                WHERE ticker = {p}
            """, (ticker,))
            row = cursor.fetchone()

            if row and row['min_date'] and row['max_date']:
                return {
                    'min_date': datetime.strptime(row['min_date'], '%Y-%m-%d').date() if isinstance(row['min_date'], str) else row['min_date'],
                    'max_date': datetime.strptime(row['max_date'], '%Y-%m-%d').date() if isinstance(row['max_date'], str) else row['max_date'],
                    'count': row['count']
                }
            return None

    def get_price_data(self, ticker: str, start_date: date, end_date: date, limit: Optional[int] = None) -> List[PriceData]:
        """
        데이터베이스에서 가격 데이터 조회

        지정된 날짜 범위의 가격 데이터를 데이터베이스에서 조회합니다.
        데이터 수집은 collect_and_save_prices 메서드를 통해 별도로 수행됩니다.

        Args:
            ticker: 종목 코드
            start_date: 시작 날짜
            end_date: 종료 날짜
            limit: 결과 개수 제한 (선택)

        Returns:
            PriceData 리스트 (날짜 내림차순 정렬)
        """
        logger.info(f"Fetching prices for {ticker} from {start_date} to {end_date}" + (f" (limit: {limit})" if limit else ""))
        p = "%s" if USE_POSTGRES else "?"

        with get_db_connection() as conn_or_cursor:
            cursor = get_cursor(conn_or_cursor)

            query = f"""
                SELECT date, open_price, high_price, low_price, close_price, volume, daily_change_pct
                FROM prices
                WHERE ticker = {p} AND date BETWEEN {p} AND {p}
                ORDER BY date DESC
            """

            if limit is not None:
                query += f" LIMIT {limit}"

            cursor.execute(query, (ticker, start_date, end_date))
            rows = cursor.fetchall()
            return [PriceData(**dict(row)) for row in rows]

    def get_trading_flow(self, ticker: str, start_date: date, end_date: date, limit: Optional[int] = None) -> List[TradingFlow]:
        """
        데이터베이스에서 매매 동향 데이터 조회

        지정된 날짜 범위의 매매 동향 데이터를 데이터베이스에서 조회합니다.
        데이터 수집은 collect_and_save_trading_flow 메서드를 통해 별도로 수행됩니다.

        Args:
            ticker: 종목 코드
            start_date: 시작 날짜
            end_date: 종료 날짜
            limit: 결과 개수 제한 (선택)

        Returns:
            TradingFlow 리스트 (날짜 내림차순 정렬)
        """
        logger.info(f"Fetching trading flow for {ticker} from {start_date} to {end_date}" + (f" (limit: {limit})" if limit else ""))
        p = "%s" if USE_POSTGRES else "?"

        with get_db_connection() as conn_or_cursor:
            cursor = get_cursor(conn_or_cursor)

            query = f"""
                SELECT date, individual_net, institutional_net, foreign_net
                FROM trading_flow
                WHERE ticker = {p} AND date BETWEEN {p} AND {p}
                ORDER BY date DESC
            """

            if limit is not None:
                query += f" LIMIT {limit}"

            cursor.execute(query, (ticker, start_date, end_date))
            rows = cursor.fetchall()
            return [TradingFlow(**dict(row)) for row in rows]
    
    def get_etf_metrics(self, ticker: str) -> ETFMetrics:
        """
        Calculate key metrics for ETF

        Calculates:
        - Returns: 1 week, 1 month, year-to-date
        - Volatility: Standard deviation of daily returns (annualized)

        Args:
            ticker: Stock/ETF ticker code

        Returns:
            ETFMetrics with calculated values
        """
        logger.info(f"Calculating metrics for {ticker}")
        p = "%s" if USE_POSTGRES else "?"

        try:
            with get_db_connection() as conn_or_cursor:
                cursor = get_cursor(conn_or_cursor)

                # Get price data for calculations
                today = date.today()
                one_year_ago = today - timedelta(days=DAYS_IN_YEAR)

                cursor.execute(f"""
                    SELECT date, close_price, daily_change_pct
                    FROM prices
                    WHERE ticker = {p} AND date >= {p}
                    ORDER BY date DESC
                """, (ticker, one_year_ago))

                rows = cursor.fetchall()

                if not rows:
                    logger.warning(f"No price data available for {ticker}")
                    return ETFMetrics(
                        ticker=ticker,
                        aum=None,
                        returns={"1w": None, "1m": None, "ytd": None},
                        volatility=None
                    )

                # Convert to list for easier indexing
                prices = [dict(row) for row in rows]

                # Calculate returns
                returns = {}

                # 1 week return
                if len(prices) >= 7:
                    week_ago_price = prices[min(6, len(prices)-1)]['close_price']
                    current_price = prices[0]['close_price']
                    if week_ago_price and current_price:
                        returns['1w'] = ((current_price - week_ago_price) / week_ago_price) * PERCENT_MULTIPLIER
                    else:
                        returns['1w'] = None
                else:
                    returns['1w'] = None

                # 1 month return
                if len(prices) >= 30:
                    month_ago_price = prices[min(29, len(prices)-1)]['close_price']
                    current_price = prices[0]['close_price']
                    if month_ago_price and current_price:
                        returns['1m'] = ((current_price - month_ago_price) / month_ago_price) * PERCENT_MULTIPLIER
                    else:
                        returns['1m'] = None
                else:
                    returns['1m'] = None

                # Year-to-date return
                year_start = date(today.year, 1, 1)
                # Handle both date objects (PostgreSQL) and strings (SQLite)
                def get_date(d):
                    return d if isinstance(d, date) else date.fromisoformat(d)
                ytd_prices = [p for p in prices if get_date(p['date']) >= year_start]
                if len(ytd_prices) >= 2:
                    ytd_start_price = ytd_prices[-1]['close_price']
                    current_price = ytd_prices[0]['close_price']
                    if ytd_start_price and current_price:
                        returns['ytd'] = ((current_price - ytd_start_price) / ytd_start_price) * PERCENT_MULTIPLIER
                    else:
                        returns['ytd'] = None
                else:
                    returns['ytd'] = None

                # Calculate volatility (annualized standard deviation of daily returns)
                daily_changes = [p['daily_change_pct'] for p in prices if p['daily_change_pct'] is not None]
                volatility = None

                if len(daily_changes) >= 10:  # Need at least 10 data points for meaningful volatility
                    import math
                    mean_change = sum(daily_changes) / len(daily_changes)
                    variance = sum((x - mean_change) ** 2 for x in daily_changes) / len(daily_changes)
                    std_dev = math.sqrt(variance)
                    # Annualize: daily std * sqrt(trading days per year)
                    volatility = std_dev * math.sqrt(TRADING_DAYS_PER_YEAR)

                return ETFMetrics(
                    ticker=ticker,
                    aum=None,  # AUM data not available from scraping
                    returns=returns,
                    volatility=volatility
                )

        except Exception as e:
            logger.error(f"Error calculating metrics for {ticker}: {e}", exc_info=True)
            return ETFMetrics(
                ticker=ticker,
                aum=None,
                returns={"1w": None, "1m": None, "ytd": None},
                volatility=None
            )
    
    def collect_all_tickers(self, days: int = 1) -> dict:
        """
        모든 종목의 가격, 매매동향, 뉴스 데이터를 일괄 수집

        Args:
            days: 수집할 일수 (기본: 1일 - 당일 데이터)

        Returns:
            수집 결과 딕셔너리 {
                'total_tickers': 전체 종목 수,
                'success_count': 성공한 종목 수,
                'fail_count': 실패한 종목 수,
                'total_price_records': 총 가격 레코드 수,
                'total_trading_flow_records': 총 매매동향 레코드 수,
                'total_news_records': 총 뉴스 수,
                'duration_seconds': 소요 시간(초),
                'details': 종목별 상세 결과
            }
        """
        start_time = datetime.now()
        logger.info(f"[일괄 수집] 시작: {days}일치 데이터")

        # 전체 종목 조회
        all_etfs = self.get_all_etfs()
        tickers = [etf.ticker for etf in all_etfs]

        success_count = 0
        fail_count = 0
        total_price_records = 0
        total_trading_flow_records = 0
        total_news_records = 0
        details = {}

        for ticker in tickers:
            try:
                # 종목 정보 확인
                etf_info = self.get_etf_info(ticker)
                if not etf_info:
                    logger.warning(f"[일괄 수집] 종목 정보 없음: {ticker}")
                    fail_count += 1
                    details[ticker] = {
                        'name': ticker,
                        'success': False,
                        'price_records': 0,
                        'trading_flow_records': 0,
                        'news_records': 0,
                        'error': 'ETF info not found'
                    }
                    continue

                # 가격 데이터 수집
                price_count = 0
                trading_flow_count = 0
                news_count = 0
                ticker_success = True
                error_msg = None

                try:
                    # 스마트 수집 사용 - 중복 방지
                    price_count = self.collect_and_save_prices_smart(ticker, days)
                    logger.info(f"[일괄 수집-스마트] {ticker} - 가격: {price_count}건")
                except Exception as e:
                    logger.error(f"[일괄 수집] {ticker} 가격 수집 실패: {e}")
                    ticker_success = False
                    error_msg = f"Price collection failed: {str(e)}"

                # 매매동향 수집 (스마트)
                try:
                    trading_flow_count = self.collect_and_save_trading_flow_smart(ticker, days)
                    logger.info(f"[일괄 수집-스마트] {ticker} - 매매동향: {trading_flow_count}건")
                except Exception as e:
                    logger.error(f"[일괄 수집] {ticker} 매매동향 수집 실패: {e}")
                    # 매매동향 실패는 경고로만 처리 (가격 데이터가 있으면 성공으로 간주)

                # 뉴스 수집
                try:
                    logger.info(f"[일괄 수집] {ticker} - 뉴스 수집 시작 (최근 {days}일)")
                    news_result = self.news_scraper.collect_and_save_news(ticker, days)
                    news_count = news_result.get('collected', 0)
                    logger.info(f"[일괄 수집] {ticker} - 뉴스: {news_count}건 수집 완료 (결과: {news_result})")
                except Exception as e:
                    logger.error(f"[일괄 수집] {ticker} 뉴스 수집 실패: {e}", exc_info=True)
                    # 뉴스 실패는 경고로만 처리 (가격 데이터가 있으면 성공으로 간주)
                    news_count = 0

                # 통계 업데이트
                total_price_records += price_count
                total_trading_flow_records += trading_flow_count
                total_news_records += news_count

                if ticker_success and price_count > 0:
                    success_count += 1
                    logger.info(f"[일괄 수집] {ticker} ({etf_info.name}): 성공")
                else:
                    fail_count += 1
                    logger.warning(f"[일괄 수집] {ticker} ({etf_info.name}): 실패")

                details[ticker] = {
                    'name': etf_info.name,
                    'success': ticker_success and price_count > 0,
                    'price_records': price_count,
                    'trading_flow_records': trading_flow_count,
                    'news_records': news_count,
                    'error': error_msg
                }

            except Exception as e:
                logger.error(f"[일괄 수집] {ticker} 실패: {e}")
                fail_count += 1
                details[ticker] = {
                    'name': ticker,
                    'success': False,
                    'price_records': 0,
                    'trading_flow_records': 0,
                    'news_records': 0,
                    'error': str(e)
                }

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        result = {
            'total_tickers': len(tickers),
            'success_count': success_count,
            'fail_count': fail_count,
            'total_price_records': total_price_records,
            'total_trading_flow_records': total_trading_flow_records,
            'total_news_records': total_news_records,
            'duration_seconds': round(duration, 2),
            'details': details
        }

        logger.info(
            f"[일괄 수집] 완료: 성공 {success_count}/{len(tickers)}, "
            f"가격 {total_price_records}건, 매매동향 {total_trading_flow_records}건, 뉴스 {total_news_records}건, "
            f"소요 시간 {duration:.2f}초"
        )

        return result
    
    def backfill_all_tickers(self, days: int = 90) -> dict:
        """
        모든 종목의 히스토리 데이터를 백필
        
        Args:
            days: 백필할 일수 (기본: 90일)
        
        Returns:
            백필 결과 딕셔너리
        """
        start_time = datetime.now()
        logger.info(f"[백필] 시작: {days}일치 데이터")
        
        # 전체 종목 조회
        all_etfs = self.get_all_etfs()
        tickers = [etf.ticker for etf in all_etfs]
        
        success_count = 0
        fail_count = 0
        total_records = 0
        details = []
        
        for ticker in tickers:
            try:
                etf_info = self.get_etf_info(ticker)
                if not etf_info:
                    logger.warning(f"[백필] 종목 정보 없음: {ticker}")
                    fail_count += 1
                    details.append({
                        'ticker': ticker,
                        'status': 'failed',
                        'reason': 'ETF info not found',
                        'collected': 0
                    })
                    continue
                
                # 히스토리 데이터 수집
                collected_count = self.collect_and_save_prices(ticker, days)
                
                if collected_count > 0:
                    logger.info(f"[백필] {ticker} ({etf_info.name}): {collected_count}개 수집")
                    total_records += collected_count
                    success_count += 1
                    details.append({
                        'ticker': ticker,
                        'name': etf_info.name,
                        'status': 'success',
                        'collected': collected_count
                    })
                else:
                    logger.warning(f"[백필] {ticker}: 수집 데이터 없음")
                    fail_count += 1
                    details.append({
                        'ticker': ticker,
                        'name': etf_info.name,
                        'status': 'failed',
                        'reason': 'No data collected',
                        'collected': 0
                    })
                    
            except Exception as e:
                logger.error(f"[백필] {ticker} 실패: {e}")
                fail_count += 1
                details.append({
                    'ticker': ticker,
                    'status': 'failed',
                    'reason': str(e),
                    'collected': 0
                })
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        result = {
            'success_count': success_count,
            'fail_count': fail_count,
            'total_records': total_records,
            'total_tickers': len(tickers),
            'days': days,
            'duration_seconds': round(duration, 2),
            'details': details
        }
        
        logger.info(
            f"[백필] 완료: 성공 {success_count}/{len(tickers)}, "
            f"총 {total_records}개 레코드, 소요 시간 {duration:.2f}초"
        )
        
        return result
    
    @retry_with_backoff(
        max_retries=3,
        base_delay=1.0,
        exceptions=(requests.exceptions.RequestException, requests.exceptions.Timeout)
    )
    def fetch_naver_trading_flow(self, ticker: str, days: int = 10, start_date: Optional[date] = None, end_date: Optional[date] = None) -> List[dict]:
        """
        Naver Finance에서 투자자별 매매동향 데이터 수집 (다중 페이지 지원)

        Args:
            ticker: 종목 코드
            days: 수집할 일수 (기본: 10일)
            start_date: 시작 날짜 (선택, 지정 시 해당 날짜 이후 데이터만 수집)
            end_date: 종료 날짜 (선택, 지정 시 해당 날짜까지 데이터만 수집)

        Returns:
            수집된 매매동향 데이터 리스트
        """
        trading_data = []
        page = 1
        # 페이지당 약 10개 데이터, 여유있게 2페이지 추가
        max_pages = (days // 10) + 2
        
        # 날짜 범위가 지정된 경우, 실제 필요한 최대 데이터 수 계산
        # (주말 제외를 고려하여 days보다 작을 수 있음)
        target_count = days
        if start_date and end_date:
            # 날짜 범위 내의 실제 거래일 수를 대략적으로 계산 (주말 제외)
            # 최대 days일이지만, 주말이 포함되면 더 적을 수 있음
            target_count = days  # 여전히 days를 목표로 하되, 날짜 범위를 벗어나면 종료

        logger.info(f"Fetching trading flow from Naver Finance for {ticker} (target: {target_count} days, max pages: {max_pages}, date range: {start_date} to {end_date})")

        should_stop = False  # 전체 루프 종료 플래그

        while len(trading_data) < target_count and page <= max_pages and not should_stop:
            try:
                # Naver Finance 투자자별 매매동향 페이지 (페이지 파라미터 포함)
                url = f"https://finance.naver.com/item/frgn.naver?code={ticker}&page={page}"
                logger.info(f"Fetching trading flow page {page} for {ticker}")

                with self.rate_limiter:
                    response = requests.get(url, headers=self.headers, timeout=10)
                    response.raise_for_status()

                soup = BeautifulSoup(response.text, 'html.parser')

                # 매매동향 테이블 찾기 (두 번째 type2 테이블)
                # 첫 번째는 증권사별 매매, 두 번째가 투자자별 매매동향
                tables = soup.find_all('table', {'class': 'type2'})
                if len(tables) < 2:
                    logger.warning(f"Trading flow table not found for {ticker} on page {page}")
                    break

                table = tables[1]  # 두 번째 테이블 선택

                # 데이터 행 추출
                rows = table.find_all('tr')
                page_data_count = 0

                for row in rows:
                    # 이미 충분한 데이터를 수집했으면 중단
                    if len(trading_data) >= target_count:
                        break

                    cols = row.find_all('td')
                    # 실제 데이터 행은 7개 이상의 컬럼을 가짐
                    # [0]날짜 [1]종가 [2]전일비 [3]등락률 [4]거래량 [5]기관 [6]외국인 [7]외국인보유 [8]지분율
                    if len(cols) < 7:
                        continue

                    try:
                        # 날짜 추출
                        date_text = cols[0].get_text(strip=True)
                        if not date_text or date_text == '날짜' or '.' not in date_text:
                            continue

                        # 날짜 파싱 (YYYY.MM.DD 형식)
                        trade_date = datetime.strptime(date_text, '%Y.%m.%d').date()

                        # 날짜 범위 필터링 (지정된 경우)
                        if start_date and trade_date < start_date:
                            # 시작 날짜 이전 데이터를 만나면 더 이상 필요한 데이터가 없음
                            # (Naver Finance는 최신순으로 데이터 제공)
                            if len(trading_data) > 0:
                                # 이미 일부 데이터를 수집했으면 전체 루프 종료
                                should_stop = True
                                break
                            continue  # 시작 날짜 이전 데이터는 건너뜀
                        if end_date and trade_date > end_date:
                            continue  # 종료 날짜 이후 데이터는 건너뜀 (더 오래된 데이터가 나올 수 있으므로 계속 진행)

                        # 투자자별 순매수 추출 (천주 단위)
                        # 기관 (5번 컬럼)
                        institutional_text = cols[5].get_text(strip=True)
                        institutional_net = self._parse_trading_volume(institutional_text)

                        # 외국인 (6번 컬럼)
                        foreign_text = cols[6].get_text(strip=True)
                        foreign_net = self._parse_trading_volume(foreign_text)

                        # 개인 = -(기관 + 외국인)
                        # None 처리: 기관이나 외국인이 None이면 개인도 None
                        if institutional_net is not None and foreign_net is not None:
                            individual_net = -(institutional_net + foreign_net)
                        else:
                            individual_net = None

                        trading_data.append({
                            'ticker': ticker,
                            'date': trade_date,
                            'individual_net': individual_net,
                            'institutional_net': institutional_net,
                            'foreign_net': foreign_net
                        })

                        page_data_count += 1

                    except (ValueError, AttributeError, IndexError) as e:
                        logger.warning(f"Failed to parse trading flow row for {ticker} on page {page}: {e}")
                        continue

                logger.info(f"Collected {page_data_count} trading flow records from page {page} for {ticker} (total: {len(trading_data)})")

                # 현재 페이지에서 데이터가 없으면 더 이상 페이지가 없는 것으로 간주
                if page_data_count == 0:
                    logger.info(f"No more data found on page {page} for {ticker}, stopping pagination")
                    break

                page += 1

            except requests.exceptions.Timeout:
                logger.error(f"Timeout fetching trading flow page {page} for {ticker}")
                break
            except requests.exceptions.RequestException as e:
                logger.error(f"Request error fetching trading flow page {page} for {ticker}: {e}")
                break
            except Exception as e:
                logger.error(f"Unexpected error fetching trading flow page {page} for {ticker}: {e}")
                break

        logger.info(f"Collected total {len(trading_data)} trading flow records for {ticker} from {page-1} pages")
        return trading_data
    
    def _parse_trading_volume(self, text: str) -> Optional[int]:
        """
        거래량 텍스트를 정수로 변환 (천주 단위)
        
        Args:
            text: 거래량 텍스트 (예: "1,234", "-5,678")
        
        Returns:
            정수로 변환된 거래량 (천주 단위), 실패 시 None
        """
        try:
            if not text or text.strip() == '':
                return None
            
            # 쉼표 제거 및 숫자 추출
            cleaned = text.replace(',', '').strip()
            
            # 빈 문자열이면 None
            if not cleaned or cleaned == '-':
                return None
            
            return int(cleaned)
            
        except (ValueError, AttributeError):
            return None
    
    def validate_trading_flow_data(self, data: dict) -> bool:
        """
        매매동향 데이터 유효성 검증
        
        Args:
            data: 매매동향 데이터 딕셔너리
        
        Returns:
            유효하면 True, 아니면 False
        """
        # 필수 필드 확인
        required_fields = ['ticker', 'date']
        for field in required_fields:
            if field not in data or data[field] is None:
                logger.warning(f"Missing required field: {field}")
                return False
        
        # 날짜 타입 확인
        if not isinstance(data['date'], date):
            logger.warning(f"Invalid date type: {type(data['date'])}")
            return False
        
        # 적어도 하나의 매매동향 데이터가 있어야 함
        has_data = (
            data.get('individual_net') is not None or
            data.get('institutional_net') is not None or
            data.get('foreign_net') is not None
        )
        
        if not has_data:
            logger.warning("No trading flow data available")
            return False
        
        return True
    
    def save_trading_flow_data(self, trading_data: List[dict]) -> int:
        """
        매매동향 데이터를 데이터베이스에 저장

        Args:
            trading_data: 매매동향 데이터 리스트

        Returns:
            저장된 레코드 수
        """
        if not trading_data:
            logger.warning("No trading flow data to save")
            return 0

        # 데이터 검증
        valid_data = []
        for data in trading_data:
            if self.validate_trading_flow_data(data):
                valid_data.append(data)

        if not valid_data:
            logger.warning("No valid trading flow data after validation")
            return 0

        # 벌크 insert 수행
        with get_db_connection() as conn_or_cursor:
            # PostgreSQL과 SQLite 처리 분기
            if USE_POSTGRES:
                cursor = conn_or_cursor
                conn = cursor.connection
            else:
                conn = conn_or_cursor
                cursor = conn.cursor()

            try:
                # PostgreSQL과 SQLite의 문법 차이
                if USE_POSTGRES:
                    cursor.executemany("""
                        INSERT INTO trading_flow
                        (ticker, date, individual_net, institutional_net, foreign_net)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (ticker, date) DO UPDATE SET
                            individual_net = EXCLUDED.individual_net,
                            institutional_net = EXCLUDED.institutional_net,
                            foreign_net = EXCLUDED.foreign_net
                    """, [
                        (
                            data['ticker'],
                            data['date'],
                            data.get('individual_net'),
                            data.get('institutional_net'),
                            data.get('foreign_net')
                        )
                        for data in valid_data
                    ])
                else:
                    cursor.executemany("""
                        INSERT OR REPLACE INTO trading_flow
                        (ticker, date, individual_net, institutional_net, foreign_net)
                        VALUES (?, ?, ?, ?, ?)
                    """, [
                        (
                            data['ticker'],
                            data['date'],
                            data.get('individual_net'),
                            data.get('institutional_net'),
                            data.get('foreign_net')
                        )
                        for data in valid_data
                    ])

                conn.commit()
                saved_count = len(valid_data)
                logger.info(f"Saved {saved_count} trading flow records (bulk insert)")

            except Exception as e:
                logger.error(f"Database error saving trading flow: {e}")
                conn.rollback()
                saved_count = 0  # 롤백 시 저장된 레코드 없음

        return saved_count

    def collect_and_save_trading_flow(self, ticker: str, days: int = 10, start_date: Optional[date] = None, end_date: Optional[date] = None) -> int:
        """
        매매동향 데이터를 수집하고 저장
        
        Args:
            ticker: 종목 코드
            days: 수집할 일수
            start_date: 시작 날짜 (선택)
            end_date: 종료 날짜 (선택)
        
        Returns:
            저장된 레코드 수
        """
        logger.info(f"Starting trading flow collection for {ticker} (last {days} days, date range: {start_date} to {end_date})")
        
        # 데이터 수집
        trading_data = self.fetch_naver_trading_flow(ticker, days, start_date, end_date)
        
        if not trading_data:
            logger.warning(f"No trading flow data collected for {ticker}")
            return 0
        
        # 데이터 저장
        saved_count = self.save_trading_flow_data(trading_data)
        
        # Rate limiting은 fetch 함수에서 RateLimiter로 처리
        return saved_count
    
    def get_trading_flow_data(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        데이터베이스에서 매매동향 데이터 조회

        Args:
            ticker: 종목 코드
            start_date: 시작 날짜
            end_date: 종료 날짜
            limit: 결과 개수 제한 (선택)

        Returns:
            매매동향 데이터 리스트
        """
        logger.info(f"Fetching trading flow for {ticker} from {start_date} to {end_date}" + (f" (limit: {limit})" if limit else ""))
        p = "%s" if USE_POSTGRES else "?"

        with get_db_connection() as conn_or_cursor:
            cursor = get_cursor(conn_or_cursor)

            query = f"""
                SELECT date, individual_net, institutional_net, foreign_net
                FROM trading_flow
                WHERE ticker = {p} AND date BETWEEN {p} AND {p}
                ORDER BY date DESC
            """

            if limit is not None:
                query += f" LIMIT {limit}"

            cursor.execute(query, (ticker, start_date, end_date))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_price_data_batch(
        self,
        tickers: List[str],
        start_date: date,
        end_date: date,
        limit: Optional[int] = None
    ) -> Dict[str, List[PriceData]]:
        """
        배치 쿼리로 여러 종목의 가격 데이터를 한 번에 조회 (IN 절 활용)

        Args:
            tickers: 종목 코드 리스트
            start_date: 시작 날짜
            end_date: 종료 날짜
            limit: 종목별 결과 개수 제한 (선택)

        Returns:
            종목별 가격 데이터 딕셔너리 {ticker: [PriceData, ...]}
        """
        if not tickers:
            return {}

        logger.info(f"Batch fetching prices for {len(tickers)} tickers from {start_date} to {end_date}")
        p = "%s" if USE_POSTGRES else "?"

        with get_db_connection() as conn_or_cursor:
            cursor = get_cursor(conn_or_cursor)

            # IN 절을 위한 플레이스홀더 생성
            placeholders = ','.join([p] * len(tickers))

            # 쿼리 구성
            query = f"""
                SELECT ticker, date, open_price, high_price, low_price, close_price, volume, daily_change_pct
                FROM prices
                WHERE ticker IN ({placeholders}) AND date BETWEEN {p} AND {p}
                ORDER BY ticker, date DESC
            """

            # 파라미터 구성
            params = list(tickers) + [start_date, end_date]

            cursor.execute(query, params)
            rows = cursor.fetchall()

            # 종목별로 그룹화
            result = {ticker: [] for ticker in tickers}
            for row in rows:
                row_dict = dict(row)
                ticker = row_dict.pop('ticker')
                price_data = PriceData(**row_dict)
                result[ticker].append(price_data)

            # limit 적용 (종목별로)
            if limit is not None:
                for ticker in result:
                    result[ticker] = result[ticker][:limit]

            logger.info(f"Batch fetched {sum(len(v) for v in result.values())} total price records")
            return result

    def get_trading_flow_batch(
        self,
        tickers: List[str],
        start_date: date,
        end_date: date,
        limit: Optional[int] = None
    ) -> Dict[str, List[Dict]]:
        """
        배치 쿼리로 여러 종목의 매매동향 데이터를 한 번에 조회 (IN 절 활용)

        Args:
            tickers: 종목 코드 리스트
            start_date: 시작 날짜
            end_date: 종료 날짜
            limit: 종목별 결과 개수 제한 (선택)

        Returns:
            종목별 매매동향 데이터 딕셔너리 {ticker: [dict, ...]}
        """
        if not tickers:
            return {}

        logger.info(f"Batch fetching trading flow for {len(tickers)} tickers from {start_date} to {end_date}")
        p = "%s" if USE_POSTGRES else "?"

        with get_db_connection() as conn_or_cursor:
            cursor = get_cursor(conn_or_cursor)

            # IN 절을 위한 플레이스홀더 생성
            placeholders = ','.join([p] * len(tickers))

            # 쿼리 구성
            query = f"""
                SELECT ticker, date, individual_net, institutional_net, foreign_net
                FROM trading_flow
                WHERE ticker IN ({placeholders}) AND date BETWEEN {p} AND {p}
                ORDER BY ticker, date DESC
            """

            # 파라미터 구성
            params = list(tickers) + [start_date, end_date]

            cursor.execute(query, params)
            rows = cursor.fetchall()

            # 종목별로 그룹화
            result = {ticker: [] for ticker in tickers}
            for row in rows:
                row_dict = dict(row)
                ticker = row_dict.pop('ticker')
                result[ticker].append(row_dict)

            # limit 적용 (종목별로)
            if limit is not None:
                for ticker in result:
                    result[ticker] = result[ticker][:limit]

            logger.info(f"Batch fetched {sum(len(v) for v in result.values())} total trading flow records")
            return result

    def get_latest_prices_batch(
        self,
        tickers: List[str]
    ) -> Dict[str, Optional[PriceData]]:
        """
        배치 쿼리로 여러 종목의 최신 가격을 한 번에 조회

        Args:
            tickers: 종목 코드 리스트

        Returns:
            종목별 최신 가격 딕셔너리 {ticker: PriceData or None}
        """
        if not tickers:
            return {}

        logger.info(f"Batch fetching latest prices for {len(tickers)} tickers")
        p = "%s" if USE_POSTGRES else "?"

        with get_db_connection() as conn_or_cursor:
            cursor = get_cursor(conn_or_cursor)

            # IN 절을 위한 플레이스홀더 생성
            placeholders = ','.join([p] * len(tickers))

            # 각 종목의 최신 날짜만 조회하는 서브쿼리 사용
            query = f"""
                SELECT p.ticker, p.date, p.open_price, p.high_price, p.low_price,
                       p.close_price, p.volume, p.daily_change_pct
                FROM prices p
                INNER JOIN (
                    SELECT ticker, MAX(date) as max_date
                    FROM prices
                    WHERE ticker IN ({placeholders})
                    GROUP BY ticker
                ) latest ON p.ticker = latest.ticker AND p.date = latest.max_date
            """

            cursor.execute(query, tickers)
            rows = cursor.fetchall()

            # 종목별로 매핑
            result = {ticker: None for ticker in tickers}
            for row in rows:
                row_dict = dict(row)
                ticker = row_dict.pop('ticker')
                result[ticker] = PriceData(**row_dict)

            logger.info(f"Batch fetched latest prices for {len([v for v in result.values() if v])} tickers")
            return result

    def calculate_missing_days(self, ticker: str, requested_days: int) -> int:
        """
        실제로 수집해야 할 일수 계산 (중복 방지 최적화)

        Args:
            ticker: 종목 코드
            requested_days: 사용자가 요청한 일수

        Returns:
            실제로 수집해야 할 일수 (0이면 수집 불필요)
        """
        from datetime import date, timedelta
        from app.database import get_collection_status

        # collection_status에서 마지막 수집 날짜 확인
        status = get_collection_status(ticker)

        if not status or not status.get('last_price_date'):
            # 수집 이력이 없으면 요청한 일수만큼 수집
            logger.info(f"[{ticker}] 수집 이력 없음 → {requested_days}일 수집 필요")
            return requested_days

        # Handle both date objects (PostgreSQL) and strings (SQLite)
        last_price_date = status['last_price_date']
        last_date = last_price_date if isinstance(last_price_date, date) else date.fromisoformat(last_price_date)
        today = date.today()

        # 마지막 수집 날짜가 오늘이면 수집 불필요
        if last_date >= today:
            logger.info(f"[{ticker}] 이미 최신 데이터 보유 ({last_date}) → 수집 불필요")
            return 0

        # 누락 일수 계산
        days_gap = (today - last_date).days

        # 요청한 일수보다 갭이 작으면 갭만큼만 수집
        actual_days = min(days_gap, requested_days)

        logger.info(f"[{ticker}] 마지막 수집: {last_date}, 오늘: {today}, "
                   f"갭: {days_gap}일 → {actual_days}일 수집")

        return actual_days

    def collect_and_save_prices_smart(self, ticker: str, days: int = 10) -> int:
        """
        스마트 가격 데이터 수집 (중복 방지)

        기존 데이터 확인 후 실제로 필요한 부분만 수집합니다.

        Args:
            ticker: 종목 코드
            days: 수집할 일수 (최대값)

        Returns:
            저장된 레코드 수
        """
        from datetime import date
        from app.database import update_collection_status

        # 실제로 수집해야 할 일수 계산
        actual_days = self.calculate_missing_days(ticker, days)

        if actual_days == 0:
            logger.info(f"[{ticker}] 스마트 수집: 최신 데이터 보유 → 스킵")
            return 0

        # 데이터 수집
        logger.info(f"[{ticker}] 스마트 수집: {actual_days}일치 데이터 수집 시작")
        price_data = self.fetch_naver_finance_prices(ticker, actual_days)

        if not price_data:
            logger.warning(f"[{ticker}] 스마트 수집: 데이터 없음")
            update_collection_status(ticker, success=False)
            return 0

        # 데이터 저장
        saved_count = self.save_price_data(price_data)

        # 수집 상태 업데이트
        if saved_count > 0:
            latest_date = max(d['date'] for d in price_data)
            update_collection_status(
                ticker,
                price_date=latest_date.isoformat(),
                success=True
            )
            logger.info(f"[{ticker}] 스마트 수집 완료: {saved_count}건 저장, "
                       f"마지막 날짜: {latest_date}")

        return saved_count

    def collect_and_save_trading_flow_smart(self, ticker: str, days: int = 10) -> int:
        """
        스마트 매매동향 데이터 수집 (중복 방지)

        Args:
            ticker: 종목 코드
            days: 수집할 일수 (최대값)

        Returns:
            저장된 레코드 수
        """
        from datetime import date, timedelta
        from app.database import update_collection_status, get_collection_status

        # collection_status에서 마지막 수집 날짜 확인
        status = get_collection_status(ticker)

        if status and status.get('last_trading_flow_date'):
            # Handle both date objects (PostgreSQL) and strings (SQLite)
            last_flow_date = status['last_trading_flow_date']
            last_date = last_flow_date if isinstance(last_flow_date, date) else date.fromisoformat(last_flow_date)
            today = date.today()

            if last_date >= today:
                logger.info(f"[{ticker}] 매매동향: 이미 최신 데이터 보유 → 스킵")
                return 0

            days_gap = (today - last_date).days
            actual_days = min(days_gap, days)
            logger.info(f"[{ticker}] 매매동향: {actual_days}일치 수집")
        else:
            actual_days = days
            logger.info(f"[{ticker}] 매매동향: 수집 이력 없음 → {actual_days}일 수집")

        # 데이터 수집
        trading_data = self.fetch_naver_trading_flow(ticker, actual_days)

        if not trading_data:
            logger.warning(f"[{ticker}] 매매동향: 데이터 없음")
            return 0

        # 데이터 저장
        saved_count = self.save_trading_flow_data(trading_data)

        # 수집 상태 업데이트
        if saved_count > 0:
            latest_date = max(d['date'] for d in trading_data)
            update_collection_status(
                ticker,
                trading_flow_date=latest_date.isoformat(),
                success=True
            )

        return saved_count
