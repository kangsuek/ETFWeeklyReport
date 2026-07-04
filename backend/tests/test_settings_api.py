"""
Tests for Settings API (Stock/ETF CRUD)

Integration tests for the /api/settings/stocks endpoints.
"""

import asyncio
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app
from app.database import init_db
from app.constants import DEFAULT_BACKFILL_DAYS
from app.routers.settings import _backfill_new_stock, _schedule_initial_backfill

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    """Setup database for each test"""
    init_db()
    yield


class TestCreateStock:
    """Tests for POST /api/settings/stocks"""

    @patch('app.routers.settings._schedule_initial_backfill')
    @patch('app.routers.settings.stocks_manager.add_stock')
    def test_create_stock_success(self, mock_add, mock_backfill):
        """Test creating a new stock successfully"""
        request_data = {
            "ticker": "TEST01",
            "name": "테스트 종목",
            "type": "STOCK",
            "theme": "테스트",
            "launch_date": None,
            "expense_ratio": None,
            "search_keyword": "테스트",
            "relevance_keywords": ["테스트", "종목"]
        }

        response = client.post("/api/settings/stocks", json=request_data)

        assert response.status_code == 201
        data = response.json()
        assert data["ticker"] == "TEST01"
        assert data["name"] == "테스트 종목"
        assert "message" in data

        # Verify add_stock was called with correct arguments
        mock_add.assert_called_once()
        call_args = mock_add.call_args
        assert call_args[0][0] == "TEST01"  # ticker
        assert call_args[0][1]["name"] == "테스트 종목"

        # 등록 성공 후 해당 티커로 초기 백필이 예약되어야 한다
        mock_backfill.assert_called_once_with("TEST01")

    @patch('app.routers.settings._schedule_initial_backfill')
    @patch('app.routers.settings.stocks_manager.add_stock')
    def test_create_etf_success(self, mock_add, mock_backfill):
        """Test creating a new ETF successfully"""
        request_data = {
            "ticker": "TEST02",
            "name": "테스트 ETF",
            "type": "ETF",
            "theme": "테스트",
            "search_keyword": "테스트 ETF",
            "relevance_keywords": ["테스트", "ETF"]
        }

        response = client.post("/api/settings/stocks", json=request_data)

        assert response.status_code == 201
        data = response.json()
        assert data["ticker"] == "TEST02"
        assert data["type"] == "ETF"
        assert data.get("name") == "테스트 ETF"

    @patch('app.routers.settings.stocks_manager.add_stock')
    def test_create_stock_duplicate(self, mock_add):
        """Test creating duplicate stock fails"""
        mock_add.side_effect = ValueError("Stock with ticker TEST01 already exists")

        request_data = {
            "ticker": "TEST01",
            "name": "중복 종목",
            "type": "STOCK",
            "theme": "테스트",
            "launch_date": None,
            "expense_ratio": None
        }

        response = client.post("/api/settings/stocks", json=request_data)

        assert response.status_code == 400
        data = response.json()
        assert "already exists" in data["detail"]

    @patch('app.routers.settings.stocks_manager.add_stock')
    def test_create_stock_invalid_data(self, mock_add):
        """Test creating stock with invalid data fails"""
        mock_add.side_effect = ValueError("Invalid stock data: Invalid type")

        request_data = {
            "ticker": "TEST01",
            "name": "잘못된 종목",
            "type": "INVALID",  # Invalid type
            "theme": "테스트"
        }

        response = client.post("/api/settings/stocks", json=request_data)

        assert response.status_code == 400

    def test_create_stock_missing_required_field(self):
        """Test creating stock with missing required field fails"""
        request_data = {
            "ticker": "TEST01",
            "type": "STOCK",
            "theme": "테스트"
            # Missing 'name'
        }

        response = client.post("/api/settings/stocks", json=request_data)

        assert response.status_code == 422  # Pydantic validation error


class TestUpdateStock:
    """Tests for PUT /api/settings/stocks/{ticker}"""

    @patch('app.routers.settings.stocks_manager.update_stock')
    @patch('app.routers.settings.stocks_manager.load_stocks')
    def test_update_stock_success(self, mock_load, mock_update):
        """Test updating a stock successfully"""
        # Mock existing stock
        mock_load.return_value = {
            "TEST01": {
                "name": "기존 종목",
                "type": "STOCK",
                "theme": "기존 테마",
                "launch_date": None,
                "expense_ratio": None
            }
        }

        request_data = {
            "theme": "수정된 테마",
            "search_keyword": "새 키워드"
        }

        response = client.put("/api/settings/stocks/TEST01", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "TEST01"
        assert data["theme"] == "수정된 테마"
        assert "message" in data

        # Verify update was called
        mock_update.assert_called_once()

    @patch('app.routers.settings.stocks_manager.load_stocks')
    def test_update_stock_not_found(self, mock_load):
        """Test updating non-existent stock fails"""
        mock_load.return_value = {}

        request_data = {
            "theme": "수정된 테마"
        }

        response = client.put("/api/settings/stocks/NOTFOUND", json=request_data)

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    @patch('app.routers.settings.stocks_manager.update_stock')
    @patch('app.routers.settings.stocks_manager.load_stocks')
    def test_update_stock_partial(self, mock_load, mock_update):
        """Test partial update (only some fields)"""
        # Mock existing stock
        mock_load.return_value = {
            "TEST01": {
                "name": "기존 종목",
                "type": "STOCK",
                "theme": "기존 테마",
                "launch_date": None,
                "expense_ratio": None,
                "search_keyword": "기존 키워드"
            }
        }

        # Update only theme
        request_data = {
            "theme": "새 테마"
        }

        response = client.put("/api/settings/stocks/TEST01", json=request_data)

        assert response.status_code == 200

        # Verify merged data was passed to update
        call_args = mock_update.call_args[0][1]
        assert call_args["theme"] == "새 테마"
        assert call_args["name"] == "기존 종목"  # Unchanged


class TestDeleteStock:
    """Tests for DELETE /api/settings/stocks/{ticker}"""

    @patch('app.routers.settings.stocks_manager.delete_stock')
    def test_delete_stock_success(self, mock_delete):
        """Test deleting a stock successfully"""
        # Mock deletion counts
        mock_delete.return_value = {
            "prices": 150,
            "news": 20,
            "trading_flow": 30
        }

        response = client.delete("/api/settings/stocks/TEST01")

        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "TEST01"
        assert data["deleted"]["prices"] == 150
        assert data["deleted"]["news"] == 20
        assert data["deleted"]["trading_flow"] == 30

        # Verify delete was called
        mock_delete.assert_called_once_with("TEST01")

    @patch('app.routers.settings.stocks_manager.delete_stock')
    def test_delete_stock_not_found(self, mock_delete):
        """Test deleting non-existent stock fails"""
        mock_delete.side_effect = ValueError("Stock with ticker NOTFOUND not found")

        response = client.delete("/api/settings/stocks/NOTFOUND")

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    @patch('app.routers.settings.stocks_manager.delete_stock')
    def test_delete_stock_with_no_data(self, mock_delete):
        """Test deleting stock with no related data"""
        # Mock deletion counts (all zeros)
        mock_delete.return_value = {
            "prices": 0,
            "news": 0,
            "trading_flow": 0
        }

        response = client.delete("/api/settings/stocks/TEST01")

        assert response.status_code == 200
        data = response.json()
        assert data["deleted"]["prices"] == 0


class TestValidateTicker:
    """Tests for GET /api/settings/stocks/{ticker}/validate"""

    def test_validate_ticker(self):
        """Test ticker validation endpoint (구현됨: 200 유효 종목, 404 미존재)"""
        response = client.get("/api/settings/stocks/005930/validate")
        # 200: 스크래핑 성공, 404: 종목 없음, 500: 스크래핑 오류
        assert response.status_code in [200, 404, 500]
        if response.status_code == 200:
            data = response.json()
            assert "ticker" in data
            assert data["ticker"] == "005930"


class TestSettingsIntegration:
    """Integration tests for Settings API workflow"""

    @patch('app.routers.settings._schedule_initial_backfill')
    @patch('app.routers.settings.stocks_manager.add_stock')
    @patch('app.routers.settings.stocks_manager.update_stock')
    @patch('app.routers.settings.stocks_manager.delete_stock')
    @patch('app.routers.settings.stocks_manager.load_stocks')
    def test_full_crud_workflow(self, mock_load, mock_delete, mock_update, mock_add, mock_backfill):
        """Test complete CRUD workflow"""
        # 1. Create a stock
        create_data = {
            "ticker": "TEST99",
            "name": "테스트 종목",
            "type": "STOCK",
            "theme": "테스트",
            "launch_date": None,
            "expense_ratio": None
        }
        create_response = client.post("/api/settings/stocks", json=create_data)
        assert create_response.status_code == 201

        # 2. Update the stock
        mock_load.return_value = {
            "TEST99": {
                "name": "테스트 종목",
                "type": "STOCK",
                "theme": "테스트",
                "launch_date": None,
                "expense_ratio": None
            }
        }
        update_data = {"theme": "수정된 테마"}
        update_response = client.put("/api/settings/stocks/TEST99", json=update_data)
        assert update_response.status_code == 200

        # 3. Delete the stock
        mock_delete.return_value = {"prices": 0, "news": 0, "trading_flow": 0}
        delete_response = client.delete("/api/settings/stocks/TEST99")
        assert delete_response.status_code == 200


class TestErrorHandling:
    """Tests for error handling"""

    @patch('app.routers.settings.stocks_manager.add_stock')
    def test_create_stock_server_error(self, mock_add):
        """Test server error during stock creation"""
        mock_add.side_effect = Exception("Database connection failed")

        request_data = {
            "ticker": "TEST01",
            "name": "테스트 종목",
            "type": "STOCK",
            "theme": "테스트",
            "launch_date": None,
            "expense_ratio": None
        }

        response = client.post("/api/settings/stocks", json=request_data)

        assert response.status_code == 500
        data = response.json()
        assert "Failed to create stock" in data["detail"]

    @patch('app.routers.settings.stocks_manager.delete_stock')
    def test_delete_stock_server_error(self, mock_delete):
        """Test server error during stock deletion"""
        mock_delete.side_effect = Exception("Database error")

        response = client.delete("/api/settings/stocks/TEST01")

        assert response.status_code == 500
        data = response.json()
        assert "Failed to delete stock" in data["detail"]


class TestInitialBackfill:
    """신규 종목 등록 시 초기 백필 헬퍼"""

    @patch('app.services.data_collector.ETFDataCollector')
    def test_backfill_collects_price_and_flow(self, mock_collector_cls):
        """Given 신규 티커 When 백필 실행 Then 가격·매매동향을 기본 백필 일수로 수집"""
        # Given
        collector = MagicMock()
        mock_collector_cls.return_value = collector

        # When
        asyncio.run(_backfill_new_stock("005930"))

        # Then
        collector.collect_and_save_prices.assert_called_once_with(
            "005930", DEFAULT_BACKFILL_DAYS
        )
        collector.collect_and_save_trading_flow.assert_called_once_with(
            "005930", DEFAULT_BACKFILL_DAYS
        )

    @patch('app.services.data_collector.ETFDataCollector')
    def test_backfill_swallows_errors(self, mock_collector_cls):
        """Given 수집 예외 When 백필 실행 Then 예외를 삼키고 조용히 종료(등록은 성공)"""
        # Given
        collector = MagicMock()
        collector.collect_and_save_prices.side_effect = Exception("network")
        mock_collector_cls.return_value = collector

        # When / Then: 예외가 밖으로 전파되지 않음
        asyncio.run(_backfill_new_stock("005930"))

    @patch('app.routers.settings._backfill_new_stock')
    def test_schedule_without_running_loop_is_safe(self, mock_backfill):
        """Given 실행 중 이벤트 루프 없음 When 예약 호출 Then 예외 없이 건너뜀"""
        # When / Then: 동기 컨텍스트(루프 없음)에서 예외 없이 반환
        _schedule_initial_backfill("005930")
