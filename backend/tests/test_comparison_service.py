"""
Comparison Service Unit Tests
"""
import pytest
import pandas as pd
import numpy as np
from datetime import date, timedelta
from app.services.comparison_service import ComparisonService
from app.exceptions import ValidationException
from app.database import get_db_connection, init_db


@pytest.fixture(autouse=True)
def setup_db():
    """Setup database for each test"""
    init_db()
    yield


@pytest.fixture
def comparison_service():
    """Create ComparisonService instance"""
    return ComparisonService()


@pytest.fixture
def sample_price_data():
    """Create sample price data for testing"""
    dates = pd.date_range(start='2025-01-01', periods=10, freq='D')

    ticker1_data = pd.DataFrame({
        'date': dates,
        'close_price': [100, 102, 101, 105, 103, 107, 106, 110, 108, 112]
    })

    ticker2_data = pd.DataFrame({
        'date': dates,
        'close_price': [200, 198, 202, 204, 200, 206, 208, 205, 210, 212]
    })

    return {
        'ticker1': ticker1_data,
        'ticker2': ticker2_data
    }


class TestValidation:
    """Input validation tests"""

    def test_validate_empty_tickers(self, comparison_service):
        """Test validation with empty tickers list"""
        with pytest.raises(ValidationException) as exc_info:
            comparison_service._validate_inputs(
                [],
                date(2025, 1, 1),
                date(2025, 1, 31)
            )
        assert "at least one ticker" in str(exc_info.value).lower()

    def test_validate_one_ticker(self, comparison_service):
        """Test validation with only one ticker"""
        with pytest.raises(ValidationException) as exc_info:
            comparison_service._validate_inputs(
                ['487240'],
                date(2025, 1, 1),
                date(2025, 1, 31)
            )
        assert "at least 2 tickers" in str(exc_info.value).lower()

    def test_validate_too_many_tickers(self, comparison_service):
        """Test validation with more than 20 tickers"""
        with pytest.raises(ValidationException) as exc_info:
            comparison_service._validate_inputs(
                ['t' + str(i) for i in range(21)],
                date(2025, 1, 1),
                date(2025, 1, 31)
            )
        assert "maximum 20 tickers" in str(exc_info.value).lower()

    def test_validate_invalid_date_range(self, comparison_service):
        """Test validation with start_date >= end_date"""
        with pytest.raises(ValidationException) as exc_info:
            comparison_service._validate_inputs(
                ['t1', 't2'],
                date(2025, 1, 31),
                date(2025, 1, 1)
            )
        assert "before" in str(exc_info.value).lower()

    def test_validate_date_range_too_long(self, comparison_service):
        """Test validation with date range > 1 year"""
        with pytest.raises(ValidationException) as exc_info:
            comparison_service._validate_inputs(
                ['t1', 't2'],
                date(2024, 1, 1),
                date(2025, 2, 1)
            )
        assert "365" in str(exc_info.value) or "1 year" in str(exc_info.value).lower()

    def test_validate_valid_inputs(self, comparison_service):
        """Test validation with valid inputs"""
        # Should not raise exception
        comparison_service._validate_inputs(
            ['t1', 't2'],
            date(2025, 1, 1),
            date(2025, 1, 31)
        )


class TestNormalizePrices:
    """Price normalization tests"""

    def test_normalize_prices_basic(self, comparison_service, sample_price_data):
        """Test basic price normalization"""
        result = comparison_service.normalize_prices(sample_price_data)

        assert "dates" in result
        assert "data" in result
        assert len(result["dates"]) == 10
        assert "ticker1" in result["data"]
        assert "ticker2" in result["data"]

        # First price should be 100
        assert result["data"]["ticker1"][0] == 100.0
        assert result["data"]["ticker2"][0] == 100.0

    def test_normalize_prices_calculation(self, comparison_service):
        """Test price normalization calculation accuracy"""
        dates = pd.date_range(start='2025-01-01', periods=3, freq='D')
        data = {
            'ticker1': pd.DataFrame({
                'date': dates,
                'close_price': [100, 110, 95]  # +10%, -5% from start
            })
        }

        result = comparison_service.normalize_prices(data)

        # Verify calculations
        assert result["data"]["ticker1"][0] == 100.0   # 100/100 * 100
        assert result["data"]["ticker1"][1] == 110.0   # 110/100 * 100
        assert result["data"]["ticker1"][2] == 95.0    # 95/100 * 100

    def test_normalize_prices_empty_data(self, comparison_service):
        """Test normalization with empty data"""
        result = comparison_service.normalize_prices({})

        assert result["dates"] == []
        assert result["data"] == {}

    def test_normalize_prices_zero_first_price(self, comparison_service):
        """Test normalization when first price is 0"""
        dates = pd.date_range(start='2025-01-01', periods=3, freq='D')
        data = {
            'ticker1': pd.DataFrame({
                'date': dates,
                'close_price': [0, 100, 200]
            })
        }

        result = comparison_service.normalize_prices(data)

        # Should skip ticker1 due to zero first price
        assert 'ticker1' not in result["data"]


class TestCalculateReturns:
    """Returns calculation tests"""

    def test_calculate_returns_positive(self, comparison_service):
        """Test returns calculation with positive return"""
        prices = pd.Series([100, 110, 120])
        result = comparison_service.calculate_returns(prices)

        # (120 - 100) / 100 * 100 = 20%
        assert result == 20.0

    def test_calculate_returns_negative(self, comparison_service):
        """Test returns calculation with negative return"""
        prices = pd.Series([100, 90, 80])
        result = comparison_service.calculate_returns(prices)

        # (80 - 100) / 100 * 100 = -20%
        assert result == -20.0

    def test_calculate_returns_no_change(self, comparison_service):
        """Test returns calculation with no change"""
        prices = pd.Series([100, 105, 100])
        result = comparison_service.calculate_returns(prices)

        assert result == 0.0

    def test_calculate_returns_insufficient_data(self, comparison_service):
        """Test returns with less than 2 data points"""
        prices = pd.Series([100])
        result = comparison_service.calculate_returns(prices)

        assert result == 0.0

    def test_calculate_returns_zero_first_price(self, comparison_service):
        """Test returns when first price is 0"""
        prices = pd.Series([0, 100])
        result = comparison_service.calculate_returns(prices)

        assert result == 0.0


class TestCalculateAnnualizedReturn:
    """Annualized return calculation tests"""

    def test_annualized_return_30_days(self, comparison_service):
        """Test annualized return with 30-day period: 3개월 미만이므로 None 반환"""
        prices = pd.Series([100, 110])
        days = 30
        result = comparison_service.calculate_annualized_return(prices, days)
        # 서비스 정책: 90일 미만은 연환산 계산 안 함
        assert result is None

    def test_annualized_return_365_days(self, comparison_service):
        """Test annualized return with 365-day period"""
        # 20% return over 365 days should remain 20%
        prices = pd.Series([100, 120])
        days = 365
        result = comparison_service.calculate_annualized_return(prices, days)

        # (1.20)^(365/365) - 1 = 0.20 = 20%
        assert result == 20.0

    def test_annualized_return_negative(self, comparison_service):
        """Test annualized return with negative return: 3개월 미만이므로 None 반환"""
        prices = pd.Series([100, 90])
        days = 30
        result = comparison_service.calculate_annualized_return(prices, days)
        assert result is None

    def test_annualized_return_small_gain_short_period(self, comparison_service):
        """Test annualized return with small gain over short period: 90일 미만이므로 None"""
        prices = pd.Series([100, 102])
        days = 7
        result = comparison_service.calculate_annualized_return(prices, days)
        assert result is None

    def test_annualized_return_zero_days(self, comparison_service):
        """Test annualized return with zero days -> None"""
        prices = pd.Series([100, 110])
        days = 0
        result = comparison_service.calculate_annualized_return(prices, days)
        assert result is None

    def test_annualized_return_insufficient_data(self, comparison_service):
        """Test annualized return with insufficient data -> None"""
        prices = pd.Series([100])
        days = 30
        result = comparison_service.calculate_annualized_return(prices, days)
        assert result is None


class TestCalculateVolatility:
    """Volatility calculation tests"""

    def test_calculate_volatility_basic(self, comparison_service):
        """Test basic volatility calculation"""
        # Constant prices = 0 volatility
        prices = pd.Series([100, 100, 100, 100, 100])
        result = comparison_service.calculate_volatility(prices)

        assert result == 0.0

    def test_calculate_volatility_variable_prices(self, comparison_service):
        """Test volatility with variable prices"""
        prices = pd.Series([100, 105, 95, 110, 90, 100])
        result = comparison_service.calculate_volatility(prices)

        # Should return a positive value
        assert result > 0

    def test_calculate_volatility_insufficient_data(self, comparison_service):
        """Test volatility with less than 2 data points"""
        prices = pd.Series([100])
        result = comparison_service.calculate_volatility(prices)

        assert result == 0.0


class TestCalculateMaxDrawdown:
    """Max drawdown calculation tests"""

    def test_max_drawdown_no_loss(self, comparison_service):
        """Test max drawdown with only increasing prices"""
        prices = pd.Series([100, 110, 120, 130])
        result = comparison_service.calculate_max_drawdown(prices)

        assert result == 0.0

    def test_max_drawdown_with_loss(self, comparison_service):
        """Test max drawdown with price drop"""
        prices = pd.Series([100, 120, 90, 110])
        result = comparison_service.calculate_max_drawdown(prices)

        # Max drawdown: (90 - 120) / 120 * 100 = -25%
        assert result < 0
        assert abs(result - (-25.0)) < 0.1

    def test_max_drawdown_recovery(self, comparison_service):
        """Test max drawdown with recovery"""
        prices = pd.Series([100, 150, 75, 150])
        result = comparison_service.calculate_max_drawdown(prices)

        # Max drawdown: (75 - 150) / 150 * 100 = -50%
        assert abs(result - (-50.0)) < 0.1

    def test_max_drawdown_insufficient_data(self, comparison_service):
        """Test max drawdown with insufficient data"""
        prices = pd.Series([100])
        result = comparison_service.calculate_max_drawdown(prices)

        assert result == 0.0


class TestCalculateSharpeRatio:
    """Sharpe ratio calculation tests"""

    def test_sharpe_ratio_positive(self, comparison_service):
        """Test Sharpe ratio with positive excess return"""
        returns = 15.0  # 15% annual return
        volatility = 10.0  # 10% volatility
        result = comparison_service.calculate_sharpe_ratio(returns, volatility)

        # (15 - 3) / 10 = 1.2
        assert result == 1.2

    def test_sharpe_ratio_negative(self, comparison_service):
        """Test Sharpe ratio with negative excess return"""
        returns = 2.0  # 2% annual return (less than risk-free)
        volatility = 10.0
        result = comparison_service.calculate_sharpe_ratio(returns, volatility)

        # (2 - 3) / 10 = -0.1
        assert result == -0.1

    def test_sharpe_ratio_zero_volatility(self, comparison_service):
        """Test Sharpe ratio with zero volatility"""
        returns = 10.0
        volatility = 0.0
        result = comparison_service.calculate_sharpe_ratio(returns, volatility)

        assert result == 0.0

    def test_sharpe_ratio_custom_risk_free_rate(self, comparison_service):
        """Test Sharpe ratio with custom risk-free rate"""
        returns = 10.0
        volatility = 5.0
        result = comparison_service.calculate_sharpe_ratio(returns, volatility, risk_free_rate=2.0)

        # (10 - 2) / 5 = 1.6
        assert result == 1.6


class TestCalculateStatistics:
    """Statistics calculation tests"""

    def test_calculate_statistics_basic(self, comparison_service, sample_price_data):
        """Test basic statistics calculation"""
        result = comparison_service.calculate_statistics(sample_price_data)

        assert "ticker1" in result
        assert "ticker2" in result

        for ticker in ['ticker1', 'ticker2']:
            stats = result[ticker]
            assert "period_return" in stats
            assert "annualized_return" in stats
            assert "volatility" in stats
            assert "max_drawdown" in stats
            assert "sharpe_ratio" in stats
            assert "data_points" in stats
            assert stats["data_points"] == 10

    def test_calculate_statistics_empty_data(self, comparison_service):
        """Test statistics with empty data"""
        result = comparison_service.calculate_statistics({})

        assert result == {}


class TestCalculateCorrelationMatrix:
    """Correlation matrix calculation tests"""

    def test_correlation_matrix_basic(self, comparison_service, sample_price_data):
        """Test basic correlation matrix calculation"""
        result = comparison_service.calculate_correlation_matrix(sample_price_data)

        assert "tickers" in result
        assert "matrix" in result
        assert len(result["tickers"]) == 2
        assert len(result["matrix"]) == 2
        assert len(result["matrix"][0]) == 2

        # Diagonal should be 1.0 (self-correlation)
        assert result["matrix"][0][0] == 1.0
        assert result["matrix"][1][1] == 1.0

    def test_correlation_matrix_one_ticker(self, comparison_service):
        """Test correlation with only one ticker"""
        dates = pd.date_range(start='2025-01-01', periods=5, freq='D')
        data = {
            'ticker1': pd.DataFrame({
                'date': dates,
                'close_price': [100, 102, 104, 106, 108]
            })
        }

        result = comparison_service.calculate_correlation_matrix(data)

        # Should return empty result for single ticker
        assert result["tickers"] == []
        assert result["matrix"] == []

    def test_correlation_matrix_perfect_correlation(self, comparison_service):
        """Test correlation with perfectly correlated prices"""
        dates = pd.date_range(start='2025-01-01', periods=5, freq='D')
        prices1 = [100, 110, 105, 115, 120]
        prices2 = [50, 55, 52.5, 57.5, 60]  # Exactly 50% of ticker1

        data = {
            'ticker1': pd.DataFrame({'date': dates, 'close_price': prices1}),
            'ticker2': pd.DataFrame({'date': dates, 'close_price': prices2})
        }

        result = comparison_service.calculate_correlation_matrix(data)

        # Should be perfectly correlated (1.0 or very close)
        correlation = result["matrix"][0][1]
        assert abs(correlation - 1.0) < 0.01


class TestGetComparisonData:
    """Integration tests for get_comparison_data"""

    def test_get_comparison_data_validation_error(self, comparison_service):
        """Test get_comparison_data with invalid inputs"""
        with pytest.raises(ValidationException):
            comparison_service.get_comparison_data(
                ['ticker1'],  # Only 1 ticker
                date(2025, 1, 1),
                date(2025, 1, 31)
            )

    def test_get_comparison_data_no_data(self, comparison_service):
        """Test get_comparison_data with non-existent tickers"""
        with pytest.raises(ValidationException) as exc_info:
            comparison_service.get_comparison_data(
                ['nonexistent1', 'nonexistent2'],
                date(2025, 1, 1),
                date(2025, 1, 31)
            )
        assert "no price data" in str(exc_info.value).lower()
