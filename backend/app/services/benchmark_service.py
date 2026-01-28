"""
벤치마크 대비 분석 서비스

ETF와 벤치마크 지수(KOSPI, KOSDAQ, KOSPI200)를 비교하여
초과수익률(Alpha)과 상관계수를 계산합니다.
"""

from typing import Dict, Optional, Tuple
from datetime import date, timedelta
from app.services.data_collector import ETFDataCollector
from app.database import get_db_connection, get_cursor, USE_POSTGRES
import logging
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

# 벤치마크 티커 매핑
BENCHMARK_TICKERS = {
    'KOSPI': 'KS11',  # 코스피 지수
    'KOSDAQ': 'KQ11',  # 코스닥 지수
    'KOSPI200': 'KS200'  # 코스피200 지수
}

# FinanceDataReader를 사용하여 벤치마크 데이터 가져오기
try:
    import FinanceDataReader as fdr
    FDR_AVAILABLE = True
except ImportError:
    logger.warning("FinanceDataReader not available. Install with: pip install finance-datareader")
    FDR_AVAILABLE = False


class BenchmarkService:
    """벤치마크 대비 분석 서비스"""

    def __init__(self):
        self.data_collector = ETFDataCollector()

    def _get_period_days(self, period: str) -> int:
        """기간 문자열을 일수로 변환"""
        period_map = {
            '1w': 7,
            '1m': 30,
            '3m': 90,
            '6m': 180,
            '1y': 365
        }
        return period_map.get(period, 30)

    def _fetch_benchmark_data(
        self,
        benchmark: str,
        start_date: date,
        end_date: date
    ) -> Optional[pd.DataFrame]:
        """
        벤치마크 지수 데이터 가져오기

        Args:
            benchmark: 벤치마크 이름 ('KOSPI', 'KOSDAQ', 'KOSPI200')
            start_date: 시작 날짜
            end_date: 종료 날짜

        Returns:
            DataFrame with columns: date, close_price
        """
        if not FDR_AVAILABLE:
            logger.error("FinanceDataReader not available")
            return None

        ticker = BENCHMARK_TICKERS.get(benchmark)
        if not ticker:
            logger.error(f"Unknown benchmark: {benchmark}")
            return None

        try:
            logger.info(f"Fetching {benchmark} ({ticker}) data from {start_date} to {end_date}")
            
            # FinanceDataReader 세션 문제 해결을 위한 재시도 로직
            max_retries = 3
            df = None
            for attempt in range(max_retries):
                try:
                    df = fdr.DataReader(ticker, start_date, end_date)
                    if df is not None and not df.empty:
                        break
                except Exception as retry_error:
                    error_msg = str(retry_error)
                    if 'LOGOUT' in error_msg or 'session' in error_msg.lower() or '401' in error_msg:
                        if attempt < max_retries - 1:
                            logger.warning(f"Attempt {attempt + 1} failed for {benchmark}: Session expired. Retrying in 2 seconds...")
                            import time
                            time.sleep(2)  # 2초 대기 후 재시도
                        else:
                            logger.warning(f"FinanceDataReader session expired for {benchmark} after {max_retries} attempts. This is a known issue with FinanceDataReader when accessing KRX data.")
                            logger.warning("Possible solutions: 1) Wait and retry later, 2) Use alternative data source, 3) Check network connectivity")
                            return None
                    else:
                        if attempt < max_retries - 1:
                            logger.warning(f"Attempt {attempt + 1} failed for {benchmark}: {retry_error}. Retrying...")
                            import time
                            time.sleep(1)  # 1초 대기 후 재시도
                        else:
                            raise retry_error
            
            if df is None or df.empty:
                logger.warning(f"No data for {benchmark} in range {start_date} to {end_date}")
                return None

            # 날짜를 인덱스에서 컬럼으로 변환
            df = df.reset_index()
            
            # Date 컬럼이 있는지 확인
            if 'Date' not in df.columns:
                # 인덱스가 날짜인 경우
                if df.index.name == 'Date' or isinstance(df.index, pd.DatetimeIndex):
                    df = df.reset_index()
                    if 'Date' not in df.columns and len(df.columns) > 0:
                        # 첫 번째 컬럼이 날짜일 수 있음
                        date_col = df.columns[0]
                        df['date'] = pd.to_datetime(df[date_col]).dt.date
                else:
                    logger.error(f"Could not find date column in {benchmark} data")
                    return None
            else:
                df['date'] = pd.to_datetime(df['Date']).dt.date
            
            # Close 컬럼 확인
            if 'Close' not in df.columns:
                logger.error(f"Could not find Close column in {benchmark} data. Available columns: {df.columns.tolist()}")
                return None
            
            df = df[['date', 'Close']].rename(columns={'Close': 'close_price'})
            df = df.sort_values('date')

            logger.info(f"Fetched {len(df)} records for {benchmark}")
            return df

        except Exception as e:
            error_msg = str(e)
            if 'LOGOUT' in error_msg or 'session' in error_msg.lower() or '401' in error_msg:
                logger.warning(f"FinanceDataReader session expired for {benchmark} (LOGOUT/401 error). This is a known issue with FinanceDataReader when accessing KRX data.")
                logger.warning("Possible solutions: 1) Wait and retry later, 2) Use alternative data source, 3) Check network connectivity")
            else:
                logger.error(f"Error fetching {benchmark} data: {e}", exc_info=True)
            return None

    def _fetch_etf_data(
        self,
        ticker: str,
        start_date: date,
        end_date: date
    ) -> Optional[pd.DataFrame]:
        """
        ETF 가격 데이터 가져오기

        Args:
            ticker: 종목 코드
            start_date: 시작 날짜
            end_date: 종료 날짜

        Returns:
            DataFrame with columns: date, close_price
        """
        try:
            prices = self.data_collector.get_price_data(ticker, start_date, end_date)
            
            if not prices:
                logger.warning(f"No price data for {ticker} in range {start_date} to {end_date}")
                return None

            # PriceData 리스트를 DataFrame으로 변환
            data = [
                {
                    'date': p.date,
                    'close_price': p.close_price
                }
                for p in prices
            ]
            df = pd.DataFrame(data)
            df = df.sort_values('date')

            return df

        except Exception as e:
            logger.error(f"Error fetching ETF data for {ticker}: {e}", exc_info=True)
            return None

    def _calculate_returns(self, prices: pd.Series) -> float:
        """
        수익률 계산 (%)

        Args:
            prices: 종가 시리즈 (시간순 정렬)

        Returns:
            수익률 (%)
        """
        if len(prices) < 2:
            return 0.0

        first_price = prices.iloc[0]
        last_price = prices.iloc[-1]

        if first_price == 0:
            return 0.0

        return ((last_price - first_price) / first_price) * 100

    def _calculate_correlation(
        self,
        etf_returns: pd.Series,
        benchmark_returns: pd.Series
    ) -> float:
        """
        상관계수 계산

        Args:
            etf_returns: ETF 일간 수익률 시리즈
            benchmark_returns: 벤치마크 일간 수익률 시리즈

        Returns:
            상관계수 (-1 ~ 1)
        """
        # 공통 날짜만 사용
        common_dates = etf_returns.index.intersection(benchmark_returns.index)
        
        if len(common_dates) < 2:
            return 0.0

        etf_aligned = etf_returns.loc[common_dates]
        benchmark_aligned = benchmark_returns.loc[common_dates]

        correlation = etf_aligned.corr(benchmark_aligned)
        
        # NaN 처리
        if pd.isna(correlation):
            return 0.0

        return round(correlation, 4)

    def compare_with_benchmark(
        self,
        ticker: str,
        benchmark: str = 'KOSPI',
        period: str = '1m'
    ) -> Dict:
        """
        ETF와 벤치마크 비교 분석

        Args:
            ticker: 종목 코드
            benchmark: 벤치마크 이름 ('KOSPI', 'KOSDAQ', 'KOSPI200')
            period: 분석 기간 ('1w', '1m', '3m', '6m', '1y')

        Returns:
            {
                'ticker': str,
                'benchmark': str,
                'period': str,
                'etf_return': float,
                'benchmark_return': float,
                'alpha': float,  # 초과수익률
                'correlation': float,  # 상관계수
                'start_date': date,
                'end_date': date,
                'data_points': int
            }
        """
        logger.info(f"Comparing {ticker} with {benchmark} (period: {period})")

        # 기간 계산
        period_days = self._get_period_days(period)
        end_date = date.today()
        start_date = end_date - timedelta(days=period_days)

        # ETF 데이터 가져오기
        etf_df = self._fetch_etf_data(ticker, start_date, end_date)
        if etf_df is None or etf_df.empty:
            logger.warning(f"No ETF data available for {ticker}")
            return {
                'ticker': ticker,
                'benchmark': benchmark,
                'period': period,
                'etf_return': None,
                'benchmark_return': None,
                'alpha': None,
                'correlation': None,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'data_points': 0,
                'error': 'No ETF data available'
            }

        # ETF 수익률 계산 (벤치마크 데이터가 없어도 계산)
        etf_return = self._calculate_returns(etf_df['close_price'])

        # 벤치마크 데이터 가져오기
        benchmark_df = self._fetch_benchmark_data(benchmark, start_date, end_date)
        if benchmark_df is None or benchmark_df.empty:
            logger.warning(f"No benchmark data available for {benchmark}")
            return {
                'ticker': ticker,
                'benchmark': benchmark,
                'period': period,
                'etf_return': round(etf_return, 2) if etf_return is not None else None,
                'benchmark_return': None,
                'alpha': None,
                'correlation': None,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'data_points': 0,
                'error': 'No benchmark data available'
            }

        # 벤치마크 수익률 계산
        benchmark_return = self._calculate_returns(benchmark_df['close_price'])

        # Alpha 계산 (초과수익률)
        alpha = round(etf_return - benchmark_return, 2) if etf_return is not None and benchmark_return is not None else None

        # 일간 수익률 계산 (상관계수용)
        etf_df['daily_return'] = etf_df['close_price'].pct_change()
        benchmark_df['daily_return'] = benchmark_df['close_price'].pct_change()

        # 날짜를 인덱스로 설정
        etf_df = etf_df.set_index('date')
        benchmark_df = benchmark_df.set_index('date')

        # 상관계수 계산
        correlation = self._calculate_correlation(
            etf_df['daily_return'],
            benchmark_df['daily_return']
        )

        # 공통 데이터 포인트 수
        common_dates = etf_df.index.intersection(benchmark_df.index)
        data_points = len(common_dates)

        return {
            'ticker': ticker,
            'benchmark': benchmark,
            'period': period,
            'etf_return': round(etf_return, 2) if etf_return is not None else None,
            'benchmark_return': round(benchmark_return, 2) if benchmark_return is not None else None,
            'alpha': alpha,
            'correlation': correlation,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'data_points': data_points
        }
