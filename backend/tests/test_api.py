"""
API Integration Tests
"""
from datetime import date, timedelta

import pytest
from app.database import init_db
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    """Setup database for each test"""
    init_db()
    yield


class TestHealthCheck:
    """Health check endpoint tests"""

    def test_health_check(self):
        """Test health check endpoint"""
        response = client.get("/api/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "message" in data

    def test_root_endpoint(self):
        """Test root endpoint"""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "docs" in data
        assert "health" in data


class TestETFEndpoints:
    """ETF endpoints tests"""

    def test_get_all_etfs(self):
        """Test GET /api/etfs/"""
        response = client.get("/api/etfs/")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # 종목 수는 stocks.json 기준 (변동 가능)
        assert len(data) >= 1, "At least one ETF/stock should be returned"

        # Check first ETF structure
        if len(data) > 0:
            etf = data[0]
            assert "ticker" in etf
            assert "name" in etf
            assert "type" in etf

    def test_get_etf_by_ticker_success(self):
        """Test GET /api/etfs/{ticker} with valid ticker"""
        response = client.get("/api/etfs/487240")

        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "487240"
        assert "KODEX" in data["name"]
        assert data["type"] == "ETF"

    def test_get_etf_by_ticker_not_found(self):
        """Test GET /api/etfs/{ticker} with invalid ticker"""
        response = client.get("/api/etfs/999999")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()


class TestPriceEndpoints:
    """Price data endpoints tests"""

    def test_get_prices_success(self):
        """Test GET /api/etfs/{ticker}/prices with valid ticker"""
        # First, collect some data
        collect_response = client.post("/api/etfs/487240/collect?days=5")
        assert collect_response.status_code == 200

        # Then retrieve it
        response = client.get("/api/etfs/487240/prices")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        if len(data) > 0:
            price = data[0]
            assert "date" in price
            assert "close_price" in price
            assert "volume" in price
            assert "open_price" in price
            assert "high_price" in price
            assert "low_price" in price

    def test_get_prices_with_date_range(self):
        """Test GET /api/etfs/{ticker}/prices with date range"""
        # Collect data
        client.post("/api/etfs/487240/collect?days=10")

        # Get prices with date range
        start_date = (date.today() - timedelta(days=7)).isoformat()
        end_date = date.today().isoformat()

        response = client.get(
            f"/api/etfs/487240/prices?start_date={start_date}&end_date={end_date}"
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_prices_not_found(self):
        """Test GET /api/etfs/{ticker}/prices with invalid ticker"""
        response = client.get("/api/etfs/999999/prices")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    def test_get_prices_empty_result(self):
        """Test GET /api/etfs/{ticker}/prices when no data exists"""
        # Clear existing data and query
        response = client.get("/api/etfs/466920/prices")

        # Should return 200 with empty list or fetch from DB
        assert response.status_code in [200, 404]


class TestCollectEndpoint:
    """Data collection endpoint tests"""

    def test_collect_prices_success(self):
        """Test POST /api/etfs/{ticker}/collect with valid ticker"""
        response = client.post("/api/etfs/487240/collect?days=5")

        assert response.status_code == 200
        data = response.json()
        assert "ticker" in data
        assert "collected" in data
        assert "message" in data
        assert data["ticker"] == "487240"
        assert data["collected"] >= 0

    def test_collect_prices_different_days(self):
        """Test POST /api/etfs/{ticker}/collect with different days parameter"""
        response = client.post("/api/etfs/487240/collect?days=3")

        assert response.status_code == 200
        data = response.json()
        assert data["collected"] >= 0
        assert data["collected"] <= 3

    def test_collect_prices_not_found(self):
        """Test POST /api/etfs/{ticker}/collect with invalid ticker"""
        response = client.post("/api/etfs/999999/collect?days=5")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    def test_collect_prices_for_stock(self):
        """Test POST /api/etfs/{ticker}/collect for a stock (not ETF)"""
        response = client.post("/api/etfs/042660/collect?days=5")

        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "042660"
        assert data["collected"] >= 0


class TestErrorHandling:
    """API error handling tests"""

    def test_invalid_endpoint(self):
        """Test accessing non-existent endpoint"""
        response = client.get("/api/invalid-endpoint")

        assert response.status_code == 404

    def test_invalid_http_method(self):
        """Test using wrong HTTP method"""
        # GET on POST endpoint
        response = client.get("/api/etfs/487240/collect")

        assert response.status_code == 405  # Method Not Allowed

    def test_invalid_date_format(self):
        """Test with invalid date format"""
        response = client.get("/api/etfs/487240/prices?start_date=invalid-date")

        # Should return 422 (Validation Error)
        assert response.status_code == 422


class TestComparisonEndpoint:
    """Comparison endpoint tests"""

    def test_compare_etfs_success(self):
        """Test GET /api/etfs/compare with valid tickers"""
        # First, collect data for multiple tickers
        tickers = ["487240", "466920", "042660"]
        for ticker in tickers:
            client.post(f"/api/etfs/{ticker}/collect?days=30")

        # Compare tickers
        tickers_str = ",".join(tickers)
        start_date = (date.today() - timedelta(days=20)).isoformat()
        end_date = date.today().isoformat()

        response = client.get(
            f"/api/etfs/compare?tickers={tickers_str}&start_date={start_date}&end_date={end_date}"
        )

        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert "normalized_prices" in data
        assert "statistics" in data
        assert "correlation_matrix" in data

        # Check normalized_prices structure
        assert "dates" in data["normalized_prices"]
        assert "data" in data["normalized_prices"]
        assert isinstance(data["normalized_prices"]["dates"], list)
        assert isinstance(data["normalized_prices"]["data"], dict)

        # Check statistics structure
        for ticker in tickers:
            if ticker in data["statistics"]:
                stats = data["statistics"][ticker]
                assert "period_return" in stats
                assert "annualized_return" in stats
                assert "volatility" in stats
                assert "max_drawdown" in stats
                assert "sharpe_ratio" in stats
                assert "data_points" in stats

        # Check correlation_matrix structure
        assert "tickers" in data["correlation_matrix"]
        assert "matrix" in data["correlation_matrix"]

    def test_compare_two_tickers(self):
        """Test comparison with minimum (2) tickers"""
        tickers = ["487240", "466920"]
        for ticker in tickers:
            client.post(f"/api/etfs/{ticker}/collect?days=30")

        tickers_str = ",".join(tickers)
        response = client.get(f"/api/etfs/compare?tickers={tickers_str}")

        assert response.status_code == 200
        data = response.json()
        assert "normalized_prices" in data
        assert "statistics" in data

    def test_compare_six_tickers(self):
        """Test comparison with maximum (6) tickers"""
        tickers = ["487240", "466920", "0020H0", "442320", "042660", "034020"]
        for ticker in tickers:
            client.post(f"/api/etfs/{ticker}/collect?days=30")

        tickers_str = ",".join(tickers)
        response = client.get(f"/api/etfs/compare?tickers={tickers_str}")

        assert response.status_code == 200
        data = response.json()
        assert "normalized_prices" in data

    def test_compare_one_ticker_error(self):
        """Test comparison with only 1 ticker (should fail)"""
        response = client.get("/api/etfs/compare?tickers=487240")

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "at least 2" in data["detail"].lower()

    def test_compare_too_many_tickers_error(self):
        """Test comparison with more than 6 tickers (should fail)"""
        tickers = ["487240", "466920", "0020H0", "442320", "042660", "034020", "123456"]
        tickers_str = ",".join(tickers)

        response = client.get(f"/api/etfs/compare?tickers={tickers_str}")

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "maximum 6" in data["detail"].lower()

    def test_compare_invalid_date_range(self):
        """Test comparison with invalid date range (start > end)"""
        tickers_str = "487240,466920"
        start_date = date.today().isoformat()
        end_date = (date.today() - timedelta(days=10)).isoformat()

        response = client.get(
            f"/api/etfs/compare?tickers={tickers_str}&start_date={start_date}&end_date={end_date}"
        )

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data

    def test_compare_date_range_too_long(self):
        """Test comparison with date range exceeding 1 year"""
        tickers_str = "487240,466920"
        start_date = (date.today() - timedelta(days=400)).isoformat()
        end_date = date.today().isoformat()

        response = client.get(
            f"/api/etfs/compare?tickers={tickers_str}&start_date={start_date}&end_date={end_date}"
        )

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "365" in data["detail"] or "1 year" in data["detail"].lower()

    def test_compare_default_dates(self):
        """Test comparison with default date range (30 days)"""
        tickers = ["487240", "466920"]
        for ticker in tickers:
            client.post(f"/api/etfs/{ticker}/collect?days=35")

        tickers_str = ",".join(tickers)
        response = client.get(f"/api/etfs/compare?tickers={tickers_str}")

        assert response.status_code == 200
        data = response.json()
        assert "normalized_prices" in data

    def test_compare_normalized_prices_start_at_100(self):
        """Test that normalized prices start at 100 for all tickers"""
        tickers = ["487240", "466920"]
        for ticker in tickers:
            client.post(f"/api/etfs/{ticker}/collect?days=30")

        tickers_str = ",".join(tickers)
        response = client.get(f"/api/etfs/compare?tickers={tickers_str}")

        assert response.status_code == 200
        data = response.json()

        # Check that first non-None value is 100 for each ticker
        for ticker in tickers:
            if ticker in data["normalized_prices"]["data"]:
                prices = data["normalized_prices"]["data"][ticker]
                first_price = next((p for p in prices if p is not None), None)
                if first_price is not None:
                    assert abs(first_price - 100.0) < 0.01  # Allow small floating point error


@pytest.mark.integration
class TestEndToEndFlow:
    """End-to-end integration tests"""

    def test_complete_flow_collect_and_retrieve(self):
        """Test complete flow: collect data -> retrieve data"""
        ticker = "487240"

        # Step 1: Collect data
        collect_response = client.post(f"/api/etfs/{ticker}/collect?days=5")
        assert collect_response.status_code == 200
        assert "collected" in collect_response.json()

        # Step 2: Retrieve data
        prices_response = client.get(f"/api/etfs/{ticker}/prices")
        assert prices_response.status_code == 200
        prices = prices_response.json()

        # Should have some data
        assert len(prices) > 0

        # Step 3: Get ETF info
        etf_response = client.get(f"/api/etfs/{ticker}")
        assert etf_response.status_code == 200
        etf = etf_response.json()
        assert etf["ticker"] == ticker

    def test_multiple_stocks_collection(self):
        """Test collecting data for multiple stocks"""
        tickers = ["487240", "466920", "042660"]

        for ticker in tickers:
            response = client.post(f"/api/etfs/{ticker}/collect?days=3")
            assert response.status_code == 200
            data = response.json()
            assert data["ticker"] == ticker
            assert data["collected"] >= 0


class TestBatchSummaryEndpoint:
    """Batch Summary endpoint tests (N+1 query optimization)"""

    def test_batch_summary_success(self):
        """Test POST /api/etfs/batch-summary with valid tickers"""
        # Collect data for tickers
        tickers = ["487240", "466920"]
        for ticker in tickers:
            client.post(f"/api/etfs/{ticker}/collect?days=5")

        # Request batch summary
        response = client.post(
            "/api/etfs/batch-summary", json={"tickers": tickers, "price_days": 5, "news_limit": 5}
        )

        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert "data" in data
        assert isinstance(data["data"], dict)

        # Check each ticker's summary
        for ticker in tickers:
            assert ticker in data["data"]
            summary = data["data"][ticker]

            # Check summary structure
            assert "ticker" in summary
            assert "latest_price" in summary
            assert "prices" in summary
            assert "weekly_return" in summary
            assert "latest_trading_flow" in summary
            assert "latest_news" in summary

            assert summary["ticker"] == ticker

    def test_batch_summary_with_data(self):
        """Test batch summary returns expected data structure"""
        tickers = ["487240"]

        # Collect price and trading flow data
        client.post(f"/api/etfs/{tickers[0]}/collect?days=5")
        client.post(f"/api/etfs/{tickers[0]}/collect-trading-flow?days=5")

        response = client.post(
            "/api/etfs/batch-summary", json={"tickers": tickers, "price_days": 5, "news_limit": 5}
        )

        assert response.status_code == 200
        data = response.json()
        summary = data["data"][tickers[0]]

        # If data was collected successfully
        if summary["prices"]:
            # Check prices structure
            assert isinstance(summary["prices"], list)
            if len(summary["prices"]) > 0:
                price = summary["prices"][0]
                assert "date" in price
                assert "close_price" in price
                assert "volume" in price

            # Check latest_price
            if summary["latest_price"]:
                assert "date" in summary["latest_price"]
                assert "close_price" in summary["latest_price"]

            # Check weekly_return calculation
            if len(summary["prices"]) >= 2:
                assert summary["weekly_return"] is not None
                assert isinstance(summary["weekly_return"], (int, float))

    def test_batch_summary_empty_tickers(self):
        """Test batch summary with empty tickers list"""
        response = client.post(
            "/api/etfs/batch-summary", json={"tickers": [], "price_days": 5, "news_limit": 5}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"] == {}

    def test_batch_summary_single_ticker(self):
        """Test batch summary with single ticker"""
        ticker = "487240"
        client.post(f"/api/etfs/{ticker}/collect?days=5")

        response = client.post(
            "/api/etfs/batch-summary", json={"tickers": [ticker], "price_days": 5, "news_limit": 5}
        )

        assert response.status_code == 200
        data = response.json()
        assert ticker in data["data"]

    def test_batch_summary_all_tickers(self):
        """Test batch summary with all 6 tickers"""
        tickers = ["487240", "466920", "0020H0", "442320", "042660", "034020"]

        # Collect data for all
        for ticker in tickers:
            client.post(f"/api/etfs/{ticker}/collect?days=5")

        response = client.post(
            "/api/etfs/batch-summary", json={"tickers": tickers, "price_days": 5, "news_limit": 5}
        )

        assert response.status_code == 200
        data = response.json()

        # All tickers should be in response
        for ticker in tickers:
            assert ticker in data["data"]

    def test_batch_summary_custom_params(self):
        """Test batch summary with custom price_days and news_limit"""
        ticker = "487240"
        client.post(f"/api/etfs/{ticker}/collect?days=10")

        response = client.post(
            "/api/etfs/batch-summary", json={"tickers": [ticker], "price_days": 10, "news_limit": 3}
        )

        assert response.status_code == 200
        data = response.json()
        summary = data["data"][ticker]

        # Check that prices respect price_days parameter
        if summary["prices"]:
            assert len(summary["prices"]) <= 10

    def test_batch_summary_nonexistent_ticker(self):
        """Test batch summary with non-existent ticker (should not error)"""
        response = client.post(
            "/api/etfs/batch-summary",
            json={"tickers": ["INVALID999"], "price_days": 5, "news_limit": 5},
        )

        # Should still return 200 with empty summary
        assert response.status_code == 200
        data = response.json()
        assert "INVALID999" in data["data"]
        summary = data["data"]["INVALID999"]
        assert summary["ticker"] == "INVALID999"
        assert summary["latest_price"] is None
        assert summary["prices"] == []

    def test_batch_summary_default_params(self):
        """Test batch summary with default parameters"""
        ticker = "487240"
        client.post(f"/api/etfs/{ticker}/collect?days=5")

        # Use default price_days=5, news_limit=5
        response = client.post("/api/etfs/batch-summary", json={"tickers": [ticker]})

        assert response.status_code == 200
        data = response.json()
        assert ticker in data["data"]
