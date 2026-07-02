from typing import List, Optional, Dict
from datetime import date, datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.models import ETF, PriceData, TradingFlow, ETFMetrics
from app.database import get_db_connection, get_cursor
from app.utils.retry import retry_with_backoff
from app.utils.rate_limiter import RateLimiter
from app.constants import (
    DAYS_IN_YEAR,
    TRADING_DAYS_PER_YEAR,
    PERCENT_MULTIPLIER,
    DEFAULT_RATE_LIMITER_INTERVAL
)
from app.services.naver_stock_api import (
    fetch_price_page,
    fetch_trend_page,
    parse_bizdate,
    parse_int as api_parse_int,
    parse_number as api_parse_number,
)
import logging
import requests

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
        네이버 모바일 JSON API(/stock/{code}/price)에서 일별 시세 수집

        sise_day.naver HTML 파싱 대비:
        - 등락률(fluctuationsRatio)을 직접 제공 → "상승205" 전일비 텍스트 파싱 불필요
        - 문자 포함 신형 코드(예: 0101N0)도 동일하게 동작

        Args:
            ticker: 종목 코드 (예: "487240")
            days: 수집할 일수 (기본: 10일)

        Returns:
            수집된 가격 데이터 리스트 (최신순)
        """
        price_data = []
        page = 1
        # JSON API pageSize 최대 60 — 필요 일수만큼 페이지 계산 (여유 +2)
        page_size = min(max(days, 10), 60)
        max_pages = (days // page_size) + 2

        logger.debug(f"Fetching up to {days} days of prices from Naver JSON API for {ticker}")

        try:
            while len(price_data) < days and page <= max_pages:
                with self.rate_limiter:
                    rows = fetch_price_page(ticker, page=page, page_size=page_size)

                if not rows:
                    logger.info(f"No more price data for {ticker} after page {page}")
                    break

                for row in rows:
                    if len(price_data) >= days:
                        break

                    try:
                        date_obj = parse_bizdate(row.get('localTradedAt'))
                        close_price = api_parse_number(row.get('closePrice'))
                        if not date_obj or close_price is None:
                            continue

                        price_data.append({
                            'ticker': ticker,
                            'date': date_obj,
                            'open_price': api_parse_number(row.get('openPrice')),
                            'high_price': api_parse_number(row.get('highPrice')),
                            'low_price': api_parse_number(row.get('lowPrice')),
                            'close_price': close_price,
                            'volume': api_parse_int(row.get('accumulatedTradingVolume')),
                            'daily_change_pct': api_parse_number(row.get('fluctuationsRatio')),
                        })
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Failed to parse price row for {ticker}: {e}")
                        continue

                page += 1

            logger.debug(f"Collected {len(price_data)} price records for {ticker} from {page-1} pages")
            return price_data

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error while fetching {ticker}: {e}")
            return price_data  # 수집된 데이터라도 반환
        except Exception as e:
            logger.error(f"Unexpected error while fetching {ticker}: {e}")
            return price_data  # 수집된 데이터라도 반환

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
            conn = conn_or_cursor
            cursor = conn.cursor()

            try:
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
                logger.debug(f"Saved {saved_count} price records to database (bulk insert)")

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
        logger.debug(f"Starting price collection for {ticker} (last {days} days)")
        
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

            # stocks.json의 순서대로 정렬 (stocks.json이 소스 오브 트루스)
            stock_config = Config.get_stock_config()
            ordered_etfs = []
            for ticker in stock_config.keys():
                if ticker in etfs_dict:
                    ordered_etfs.append(etfs_dict[ticker])

            return ordered_etfs
    
    def get_etf_info(self, ticker: str) -> Optional[ETF]:
        """Get basic info for specific ETF"""
        import json
        param_placeholder = "?"
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
        p = "?"
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
        p = "?"
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
        logger.debug(f"Fetching prices for {ticker} from {start_date} to {end_date}" + (f" (limit: {limit})" if limit else ""))
        p = "?"

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
        logger.debug(f"Fetching trading flow for {ticker} from {start_date} to {end_date}" + (f" (limit: {limit})" if limit else ""))
        p = "?"

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
        logger.debug(f"Calculating metrics for {ticker}")
        p = "?"

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
                # 날짜가 date 객체/문자열 어느 쪽이든 안전하게 처리
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

                # Calculate Max Drawdown
                max_drawdown = None
                if len(prices) >= 2:
                    import pandas as pd
                    price_series = pd.Series([p['close_price'] for p in prices])
                    cumulative_max = price_series.cummax()
                    drawdown = ((price_series - cumulative_max) / cumulative_max * 100)
                    max_drawdown = round(drawdown.min(), 2)

                # Calculate Sharpe Ratio (표준 방식: 전체 일간수익률 기반 연환산)
                # 변동성과 동일한 표본(일간수익률 전체)을 사용해 일관성을 유지한다.
                # 분자를 단일 1개월 수익률로 만들면 표본 1개에 과민 반응(예: 월 +48% -> 샤프 폭등)하므로,
                # 일평균 수익률 x 거래일수로 연환산한다.
                sharpe_ratio = None
                if volatility and volatility > 0 and len(daily_changes) >= 10:
                    # 일평균 수익률(%) x 연간 거래일수 = 연환산 수익률(%)
                    mean_daily_return = sum(daily_changes) / len(daily_changes)
                    annualized_return = mean_daily_return * TRADING_DAYS_PER_YEAR
                    risk_free_rate = 3.0  # 무위험 수익률 3%
                    sharpe_ratio = round((annualized_return - risk_free_rate) / volatility, 2)

                return ETFMetrics(
                    ticker=ticker,
                    aum=None,  # AUM data not available from scraping
                    returns=returns,
                    volatility=volatility,
                    max_drawdown=max_drawdown,
                    sharpe_ratio=sharpe_ratio
                )

        except Exception as e:
            logger.error(f"Error calculating metrics for {ticker}: {e}", exc_info=True)
            return ETFMetrics(
                ticker=ticker,
                aum=None,
                returns={"1w": None, "1m": None, "ytd": None},
                volatility=None
            )
    
    def _collect_single_ticker(self, ticker: str, days: int) -> dict:
        """
        단일 종목의 가격, 매매동향, 뉴스 데이터를 수집 (ThreadPoolExecutor용)

        Args:
            ticker: 종목 코드
            days: 수집할 일수

        Returns:
            종목별 수집 결과 딕셔너리
        """
        from app.database import update_collection_status

        try:
            etf_info = self.get_etf_info(ticker)
            if not etf_info:
                logger.warning(f"[일괄 수집] 종목 정보 없음: {ticker}")
                return {
                    'name': ticker,
                    'success': False,
                    'price_records': 0,
                    'trading_flow_records': 0,
                    'news_records': 0,
                    'error': 'ETF info not found'
                }

            price_count = 0
            trading_flow_count = 0
            news_count = 0
            ticker_success = True
            error_msg = None

            # 가격 데이터 수집
            try:
                price_count = self.collect_and_save_prices(ticker, days)
                logger.info(f"[일괄 수집] {ticker} - 가격: {price_count}건")
                if price_count > 0:
                    update_collection_status(
                        ticker,
                        price_date=date.today().isoformat(),
                        success=True
                    )
            except Exception as e:
                logger.error(f"[일괄 수집] {ticker} 가격 수집 실패: {e}")
                ticker_success = False
                error_msg = f"Price collection failed: {str(e)}"
                update_collection_status(ticker, success=False)

            # 매매동향 수집
            try:
                trading_flow_count = self.collect_and_save_trading_flow(ticker, days)
                logger.info(f"[일괄 수집] {ticker} - 매매동향: {trading_flow_count}건")
                if trading_flow_count > 0:
                    update_collection_status(
                        ticker,
                        trading_flow_date=date.today().isoformat(),
                        success=True
                    )
            except Exception as e:
                logger.error(f"[일괄 수집] {ticker} 매매동향 수집 실패: {e}")

            # 뉴스 수집
            try:
                logger.info(f"[일괄 수집] {ticker} - 뉴스 수집 시작 (최근 {days}일)")
                news_result = self.news_scraper.collect_and_save_news(ticker, days)
                news_count = news_result.get('collected', 0)
                logger.info(f"[일괄 수집] {ticker} - 뉴스: {news_count}건 수집 완료")
            except Exception as e:
                logger.error(f"[일괄 수집] {ticker} 뉴스 수집 실패: {e}", exc_info=True)
                news_count = 0

            success = ticker_success and price_count > 0
            if success:
                logger.info(f"[일괄 수집] {ticker} ({etf_info.name}): 성공")
            else:
                logger.warning(f"[일괄 수집] {ticker} ({etf_info.name}): 실패")

            return {
                'name': etf_info.name,
                'success': success,
                'price_records': price_count,
                'trading_flow_records': trading_flow_count,
                'news_records': news_count,
                'error': error_msg
            }

        except Exception as e:
            logger.error(f"[일괄 수집] {ticker} 실패: {e}")
            return {
                'name': ticker,
                'success': False,
                'price_records': 0,
                'trading_flow_records': 0,
                'news_records': 0,
                'error': str(e)
            }

    def collect_all_tickers(self, days: int = 1, max_workers: int = 5) -> dict:
        """
        모든 종목의 가격, 매매동향, 뉴스 데이터를 병렬 일괄 수집

        ThreadPoolExecutor를 사용하여 종목별 병렬 수집.
        공유 rate_limiter로 API 호출 속도 제한 유지.

        Args:
            days: 수집할 일수 (기본: 1일 - 당일 데이터)
            max_workers: 병렬 처리 워커 수 (기본: 5)

        Returns:
            수집 결과 딕셔너리
        """
        from app.services.progress import update_progress, clear_progress

        start_time = datetime.now()
        logger.info(f"[일괄 수집] 시작: {days}일치 데이터 (병렬 {max_workers} workers)")

        all_etfs = self.get_all_etfs()
        tickers = [etf.ticker for etf in all_etfs]
        # ticker → name 매핑 (진행률 표시용)
        ticker_names = {etf.ticker: etf.name for etf in all_etfs}
        total = len(tickers)

        success_count = 0
        fail_count = 0
        total_price_records = 0
        total_trading_flow_records = 0
        total_news_records = 0
        details = {}
        completed = 0

        update_progress("collect-all", {
            "status": "in_progress",
            "current": 0,
            "total": total,
            "current_ticker": "",
            "current_ticker_name": "",
            "message": "수집 준비 중..."
        })

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self._collect_single_ticker, ticker, days): ticker
                for ticker in tickers
            }
            for future in as_completed(futures):
                ticker = futures[future]
                try:
                    result = future.result()
                    details[ticker] = result

                    if result['success']:
                        success_count += 1
                    else:
                        fail_count += 1

                    total_price_records += result['price_records']
                    total_trading_flow_records += result['trading_flow_records']
                    total_news_records += result['news_records']
                except Exception as e:
                    logger.error(f"[일괄 수집] {ticker} future 실패: {e}")
                    fail_count += 1
                    details[ticker] = {
                        'name': ticker,
                        'success': False,
                        'price_records': 0,
                        'trading_flow_records': 0,
                        'news_records': 0,
                        'error': str(e)
                    }
                    result = details[ticker]

                completed += 1
                ticker_name = result.get('name', ticker_names.get(ticker, ticker))
                update_progress("collect-all", {
                    "status": "in_progress",
                    "current": completed,
                    "total": total,
                    "current_ticker": ticker,
                    "current_ticker_name": ticker_name,
                    "message": f"{ticker_name} 수집 완료 ({completed}/{total})"
                })

        update_progress("collect-all", {
            "status": "completed",
            "current": total,
            "total": total,
            "current_ticker": "",
            "current_ticker_name": "",
            "message": "수집 완료"
        })

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
    
    def _backfill_single_ticker(self, ticker: str, days: int) -> dict:
        """
        단일 종목의 히스토리 데이터를 백필 (ThreadPoolExecutor용)

        Args:
            ticker: 종목 코드
            days: 백필할 일수

        Returns:
            종목별 백필 결과 딕셔너리
        """
        try:
            etf_info = self.get_etf_info(ticker)
            if not etf_info:
                logger.warning(f"[백필] 종목 정보 없음: {ticker}")
                return {
                    'ticker': ticker,
                    'status': 'failed',
                    'reason': 'ETF info not found',
                    'collected': 0
                }

            collected_count = self.collect_and_save_prices(ticker, days)

            if collected_count > 0:
                logger.info(f"[백필] {ticker} ({etf_info.name}): {collected_count}개 수집")
                return {
                    'ticker': ticker,
                    'name': etf_info.name,
                    'status': 'success',
                    'collected': collected_count
                }
            else:
                logger.warning(f"[백필] {ticker}: 수집 데이터 없음")
                return {
                    'ticker': ticker,
                    'name': etf_info.name,
                    'status': 'failed',
                    'reason': 'No data collected',
                    'collected': 0
                }

        except Exception as e:
            logger.error(f"[백필] {ticker} 실패: {e}")
            return {
                'ticker': ticker,
                'status': 'failed',
                'reason': str(e),
                'collected': 0
            }

    def backfill_all_tickers(self, days: int = 90, max_workers: int = 3) -> dict:
        """
        모든 종목의 히스토리 데이터를 병렬 백필

        Args:
            days: 백필할 일수 (기본: 90일)
            max_workers: 병렬 처리 워커 수 (기본: 3)

        Returns:
            백필 결과 딕셔너리
        """
        start_time = datetime.now()
        logger.info(f"[백필] 시작: {days}일치 데이터 (병렬 {max_workers} workers)")

        all_etfs = self.get_all_etfs()
        tickers = [etf.ticker for etf in all_etfs]

        success_count = 0
        fail_count = 0
        total_records = 0
        details = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self._backfill_single_ticker, ticker, days): ticker
                for ticker in tickers
            }
            for future in as_completed(futures):
                ticker = futures[future]
                try:
                    result = future.result()
                    details.append(result)

                    if result['status'] == 'success':
                        success_count += 1
                        total_records += result['collected']
                    else:
                        fail_count += 1
                except Exception as e:
                    logger.error(f"[백필] {ticker} future 실패: {e}")
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
        네이버 모바일 JSON API(/stock/{code}/trend)에서 투자자별 매매동향 수집

        HTML(frgn.naver) 파싱 대비 장점:
        - 개인 순매수 실측값 제공 (기존에는 -(기관+외국인) 근사치)
        - 외국인 보유율(foreignerHoldRatio) 추가 제공

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
        # JSON API pageSize 최대 60 — 필요 일수만큼 페이지 계산 (여유 +2)
        page_size = min(max(days, 10), 60)
        max_pages = (days // page_size) + 2
        
        # 날짜 범위가 지정된 경우, 실제 필요한 최대 데이터 수 계산
        # (주말 제외를 고려하여 days보다 작을 수 있음)
        target_count = days
        if start_date and end_date:
            # 날짜 범위 내의 실제 거래일 수를 대략적으로 계산 (주말 제외)
            # 최대 days일이지만, 주말이 포함되면 더 적을 수 있음
            target_count = days  # 여전히 days를 목표로 하되, 날짜 범위를 벗어나면 종료

        logger.debug(f"Fetching trading flow from Naver Finance for {ticker} (target: {target_count} days, max pages: {max_pages}, date range: {start_date} to {end_date})")

        should_stop = False  # 전체 루프 종료 플래그

        while len(trading_data) < target_count and page <= max_pages and not should_stop:
            try:
                # 네이버 모바일 JSON API 호출 (페이지 단위)
                logger.debug(f"Fetching trading flow page {page} for {ticker}")

                with self.rate_limiter:
                    rows = fetch_trend_page(ticker, page=page, page_size=page_size)

                if not rows:
                    logger.info(f"No trend data on page {page} for {ticker}, stopping pagination")
                    break

                page_data_count = 0

                for row in rows:
                    # 이미 충분한 데이터를 수집했으면 중단
                    if len(trading_data) >= target_count:
                        break

                    try:
                        # 날짜 파싱 (bizdate: YYYYMMDD)
                        trade_date = parse_bizdate(row.get('bizdate'))
                        if not trade_date:
                            continue

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

                        # 투자자별 순매수 (주 단위) — API 실측값
                        institutional_net = api_parse_int(row.get('organPureBuyQuant'))
                        foreign_net = api_parse_int(row.get('foreignerPureBuyQuant'))
                        # 개인: 기존 -(기관+외국인) 근사치 대신 실측값 사용
                        individual_net = api_parse_int(row.get('individualPureBuyQuant'))
                        # 외국인 보유율 (%)
                        foreign_hold_ratio = api_parse_number(row.get('foreignerHoldRatio'))

                        trading_data.append({
                            'ticker': ticker,
                            'date': trade_date,
                            'individual_net': individual_net,
                            'institutional_net': institutional_net,
                            'foreign_net': foreign_net,
                            'foreign_hold_ratio': foreign_hold_ratio
                        })

                        page_data_count += 1

                    except (ValueError, AttributeError, IndexError) as e:
                        logger.warning(f"Failed to parse trading flow row for {ticker} on page {page}: {e}")
                        continue

                logger.debug(f"Collected {page_data_count} trading flow records from page {page} for {ticker} (total: {len(trading_data)})")

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

        logger.debug(f"Collected total {len(trading_data)} trading flow records for {ticker} from {page-1} pages")
        return trading_data
    
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
            conn = conn_or_cursor
            cursor = conn.cursor()

            try:
                cursor.executemany("""
                    INSERT OR REPLACE INTO trading_flow
                    (ticker, date, individual_net, institutional_net, foreign_net,
                     foreign_hold_ratio)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, [
                    (
                        data['ticker'],
                        data['date'],
                        data.get('individual_net'),
                        data.get('institutional_net'),
                        data.get('foreign_net'),
                        data.get('foreign_hold_ratio')
                    )
                    for data in valid_data
                ])

                conn.commit()
                saved_count = len(valid_data)
                logger.debug(f"Saved {saved_count} trading flow records (bulk insert)")

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
        logger.debug(f"Starting trading flow collection for {ticker} (last {days} days, date range: {start_date} to {end_date})")

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
        logger.debug(f"Fetching trading flow for {ticker} from {start_date} to {end_date}" + (f" (limit: {limit})" if limit else ""))
        p = "?"

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

        logger.debug(f"Batch fetching prices for {len(tickers)} tickers from {start_date} to {end_date}")
        p = "?"

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

            logger.debug(f"Batch fetched {sum(len(v) for v in result.values())} total price records")
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

        logger.debug(f"Batch fetching trading flow for {len(tickers)} tickers from {start_date} to {end_date}")
        p = "?"

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

            logger.debug(f"Batch fetched {sum(len(v) for v in result.values())} total trading flow records")
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
        p = "?"

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

            logger.debug(f"Batch fetched latest prices for {len([v for v in result.values() if v])} tickers")
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

        # 날짜가 date 객체/문자열 어느 쪽이든 안전하게 처리
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
            # 날짜가 date 객체/문자열 어느 쪽이든 안전하게 처리
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
