"""
종목 비교 서비스

여러 종목의 가격 데이터를 비교 분석하는 서비스
- 정규화 가격 계산 (시작일 = 100)
- 수익률, 변동성, 상관관계 등 통계 지표 계산
"""

from typing import List, Dict, Optional, Tuple
from datetime import date
import numpy as np
import pandas as pd
from app.database import get_db_connection
from app.exceptions import ValidationException
import logging

logger = logging.getLogger(__name__)


class ComparisonService:
    """종목 비교 분석 서비스"""

    TRADING_DAYS_PER_YEAR = 252

    def get_comparison_data(
        self,
        tickers: List[str],
        start_date: date,
        end_date: date
    ) -> Dict:
        """
        여러 종목의 비교 데이터 조회

        Args:
            tickers: 비교할 종목 코드 리스트 (2-6개)
            start_date: 시작 날짜
            end_date: 종료 날짜

        Returns:
            {
                "normalized_prices": {...},  # 정규화된 가격
                "statistics": {...},         # 종목별 통계
                "correlation_matrix": {...}  # 상관관계 행렬
            }

        Raises:
            ValidationException: 입력 검증 실패
        """
        # 입력 검증
        self._validate_inputs(tickers, start_date, end_date)

        # 가격 데이터 조회
        prices_data = self._fetch_prices(tickers, start_date, end_date)

        # 데이터가 없는 종목 확인
        missing_tickers = set(tickers) - set(prices_data.keys())
        if missing_tickers:
            logger.warning(f"No data found for tickers: {missing_tickers}")

        if not prices_data:
            raise ValidationException("No price data available for the selected tickers and date range")

        # 정규화 가격 계산
        normalized_prices = self.normalize_prices(prices_data)

        # 통계 계산
        statistics = self.calculate_statistics(prices_data)

        # 상관관계 계산
        correlation_matrix = self.calculate_correlation_matrix(prices_data)

        return {
            "normalized_prices": normalized_prices,
            "statistics": statistics,
            "correlation_matrix": correlation_matrix
        }

    def _validate_inputs(self, tickers: List[str], start_date: date, end_date: date):
        """입력 검증"""
        if not tickers:
            raise ValidationException("At least one ticker is required")

        if len(tickers) < 2:
            raise ValidationException("At least 2 tickers are required for comparison")

        if len(tickers) > 6:
            raise ValidationException("Maximum 6 tickers allowed for comparison")

        if start_date >= end_date:
            raise ValidationException("start_date must be before end_date")

        # 최대 1년 제한
        if (end_date - start_date).days > 365:
            raise ValidationException("Date range cannot exceed 1 year (365 days)")

    def _fetch_prices(
        self,
        tickers: List[str],
        start_date: date,
        end_date: date
    ) -> Dict[str, pd.DataFrame]:
        """
        종목별 가격 데이터 조회

        Returns:
            {ticker: DataFrame(date, close_price)}
        """
        prices_data = {}

        with get_db_connection() as conn:
            for ticker in tickers:
                query = """
                    SELECT date, close_price
                    FROM prices
                    WHERE ticker = ? AND date BETWEEN ? AND ?
                    ORDER BY date ASC
                """

                df = pd.read_sql_query(
                    query,
                    conn,
                    params=(ticker, start_date, end_date),
                    parse_dates=['date']
                )

                if not df.empty:
                    prices_data[ticker] = df
                else:
                    logger.warning(f"No price data for {ticker} in range {start_date} to {end_date}")

        return prices_data

    def normalize_prices(self, prices_data: Dict[str, pd.DataFrame]) -> Dict:
        """
        가격 정규화 (시작일 = 100)

        Args:
            prices_data: {ticker: DataFrame(date, close_price)}

        Returns:
            {
                "dates": ["2025-01-01", ...],
                "data": {
                    "ticker1": [100, 102, ...],
                    "ticker2": [100, 98, ...]
                }
            }
        """
        if not prices_data:
            return {"dates": [], "data": {}}

        # 모든 날짜 합집합 구하기 (정렬)
        all_dates = set()
        for df in prices_data.values():
            all_dates.update(df['date'].dt.date)

        sorted_dates = sorted(all_dates)

        normalized_data = {}

        for ticker, df in prices_data.items():
            # date를 인덱스로 설정
            df_indexed = df.set_index('date')

            # 첫 번째 종가 (기준값)
            first_price = df_indexed['close_price'].iloc[0]

            if first_price == 0:
                logger.warning(f"First price is 0 for {ticker}, skipping normalization")
                continue

            # 정규화: (현재가 / 첫 종가) * 100
            normalized_series = (df_indexed['close_price'] / first_price * 100).round(2)

            # 날짜별로 매핑
            normalized_list = []
            for d in sorted_dates:
                d_datetime = pd.Timestamp(d)
                if d_datetime in normalized_series.index:
                    normalized_list.append(float(normalized_series.loc[d_datetime]))
                else:
                    normalized_list.append(None)  # 해당 날짜 데이터 없음

            normalized_data[ticker] = normalized_list

        return {
            "dates": [d.isoformat() for d in sorted_dates],
            "data": normalized_data
        }

    def calculate_returns(self, prices: pd.Series) -> float:
        """
        기간 수익률 계산

        Args:
            prices: 종가 시리즈

        Returns:
            기간 수익률 (%)
        """
        if len(prices) < 2:
            return 0.0

        first_price = prices.iloc[0]
        last_price = prices.iloc[-1]

        if first_price == 0:
            return 0.0

        return ((last_price - first_price) / first_price * 100).round(2)

    def calculate_annualized_return(self, prices: pd.Series, days: int) -> float:
        """
        연환산 수익률 계산 (복리 효과 반영)

        Args:
            prices: 종가 시리즈
            days: 기간 (일수)

        Returns:
            연환산 수익률 (%)
        """
        if days == 0 or len(prices) < 2:
            return 0.0

        first_price = prices.iloc[0]
        last_price = prices.iloc[-1]

        if first_price == 0:
            return 0.0

        # 기간 수익률 (소수)
        period_return_decimal = (last_price - first_price) / first_price

        # 연환산: (1 + 기간수익률) ^ (365/일수) - 1
        # 복리 효과를 반영한 정확한 연환산 계산
        annualized_decimal = ((1 + period_return_decimal) ** (365 / days)) - 1
        annualized = (annualized_decimal * 100).round(2)

        return annualized

    def calculate_volatility(self, prices: pd.Series) -> float:
        """
        연환산 변동성 계산

        Args:
            prices: 종가 시리즈

        Returns:
            연환산 변동성 (%)
        """
        if len(prices) < 2:
            return 0.0

        # 일일 수익률 계산
        daily_returns = prices.pct_change().dropna()

        if len(daily_returns) == 0:
            return 0.0

        # 표준편차 * sqrt(252) (연환산)
        daily_volatility = daily_returns.std()
        annualized_volatility = (daily_volatility * np.sqrt(self.TRADING_DAYS_PER_YEAR) * 100).round(2)

        return annualized_volatility

    def calculate_max_drawdown(self, prices: pd.Series) -> float:
        """
        최대 낙폭 (Max Drawdown) 계산

        Args:
            prices: 종가 시리즈

        Returns:
            최대 낙폭 (%)
        """
        if len(prices) < 2:
            return 0.0

        # 누적 최고가
        cumulative_max = prices.cummax()

        # 낙폭 계산
        drawdown = ((prices - cumulative_max) / cumulative_max * 100)

        # 최대 낙폭 (가장 큰 손실)
        max_dd = drawdown.min().round(2)

        return max_dd

    def calculate_sharpe_ratio(
        self,
        returns: float,
        volatility: float,
        risk_free_rate: float = 3.0
    ) -> float:
        """
        샤프 비율 계산

        Args:
            returns: 연환산 수익률 (%)
            volatility: 연환산 변동성 (%)
            risk_free_rate: 무위험 수익률 (%, 기본값: 3.0)

        Returns:
            샤프 비율
        """
        if volatility == 0:
            return 0.0

        sharpe = round((returns - risk_free_rate) / volatility, 2)

        return sharpe

    def calculate_statistics(self, prices_data: Dict[str, pd.DataFrame]) -> Dict:
        """
        종목별 통계 계산

        Args:
            prices_data: {ticker: DataFrame(date, close_price)}

        Returns:
            {
                "ticker1": {
                    "period_return": 12.5,
                    "annualized_return": 45.2,
                    "volatility": 25.3,
                    "max_drawdown": -8.2,
                    "sharpe_ratio": 1.67,
                    "data_points": 30
                },
                ...
            }
        """
        statistics = {}

        for ticker, df in prices_data.items():
            prices = df['close_price']

            # 실제 달력일 수 계산 (연환산 수익률 정확도 향상)
            if len(df) < 2:
                calendar_days = 1
            else:
                calendar_days = (df['date'].iloc[-1] - df['date'].iloc[0]).days
                # 같은 날짜인 경우 최소 1일로 처리
                if calendar_days == 0:
                    calendar_days = 1

            period_return = self.calculate_returns(prices)
            annualized_return = self.calculate_annualized_return(prices, calendar_days)
            volatility = self.calculate_volatility(prices)
            max_drawdown = self.calculate_max_drawdown(prices)
            sharpe_ratio = self.calculate_sharpe_ratio(annualized_return, volatility)

            statistics[ticker] = {
                "period_return": float(period_return),
                "annualized_return": float(annualized_return),
                "volatility": float(volatility),
                "max_drawdown": float(max_drawdown),
                "sharpe_ratio": float(sharpe_ratio),
                "data_points": int(len(df))  # 거래일 수 (데이터 포인트 개수)
            }

        return statistics

    def calculate_correlation_matrix(self, prices_data: Dict[str, pd.DataFrame]) -> Dict:
        """
        상관관계 행렬 계산

        Args:
            prices_data: {ticker: DataFrame(date, close_price)}

        Returns:
            {
                "tickers": ["ticker1", "ticker2"],
                "matrix": [
                    [1.0, 0.85],
                    [0.85, 1.0]
                ]
            }
        """
        if len(prices_data) < 2:
            return {"tickers": [], "matrix": []}

        # 모든 데이터를 하나의 DataFrame으로 병합
        merged_df = None

        for ticker, df in prices_data.items():
            df_renamed = df.set_index('date')[[('close_price')]].rename(columns={'close_price': ticker})

            if merged_df is None:
                merged_df = df_renamed
            else:
                merged_df = merged_df.join(df_renamed, how='outer')

        # 상관관계 계산 (일일 수익률 기준)
        returns_df = merged_df.pct_change().dropna()

        if returns_df.empty:
            return {"tickers": list(prices_data.keys()), "matrix": []}

        correlation = returns_df.corr()

        tickers = list(correlation.columns)
        matrix = correlation.round(3).values.tolist()

        return {
            "tickers": tickers,
            "matrix": matrix
        }
