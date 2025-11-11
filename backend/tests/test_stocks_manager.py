"""
Tests for stocks_manager utility

Tests for stocks.json file management, validation, and database synchronization.
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
from app.utils import stocks_manager
from app.config import Config


@pytest.fixture
def temp_stocks_file():
    """Create a temporary stocks.json file for testing"""
    # Create temporary directory
    temp_dir = tempfile.mkdtemp()
    temp_file = Path(temp_dir) / "stocks.json"

    # Create sample data
    sample_data = {
        "TEST01": {
            "name": "테스트 ETF",
            "type": "ETF",
            "theme": "테스트",
            "launch_date": "2024-01-01",
            "expense_ratio": 0.0050,
            "search_keyword": "테스트",
            "relevance_keywords": ["테스트", "ETF"]
        }
    }

    # Write sample data
    with open(temp_file, 'w', encoding='utf-8') as f:
        json.dump(sample_data, f, indent=2, ensure_ascii=False)

    # Mock the config path
    original_path = Config.STOCK_CONFIG_PATH
    Config.STOCK_CONFIG_PATH = str(temp_file)
    Config._stock_config_cache = None  # Clear cache

    yield temp_file

    # Cleanup
    Config.STOCK_CONFIG_PATH = original_path
    Config._stock_config_cache = None
    shutil.rmtree(temp_dir)


class TestLoadStocks:
    """Tests for load_stocks() function"""

    def test_load_stocks_success(self, temp_stocks_file):
        """Test loading stocks from file"""
        stocks = stocks_manager.load_stocks()

        assert isinstance(stocks, dict)
        assert "TEST01" in stocks
        assert stocks["TEST01"]["name"] == "테스트 ETF"
        assert stocks["TEST01"]["type"] == "ETF"


class TestSaveStocks:
    """Tests for save_stocks() function"""

    def test_save_stocks_success(self, temp_stocks_file):
        """Test saving stocks to file"""
        new_stocks = {
            "TEST01": {
                "name": "테스트 ETF (수정)",
                "type": "ETF",
                "theme": "테스트",
                "launch_date": "2024-01-01",
                "expense_ratio": 0.0050,
                "search_keyword": "테스트",
                "relevance_keywords": ["테스트"]
            },
            "TEST02": {
                "name": "테스트 주식",
                "type": "STOCK",
                "theme": "테스트",
                "launch_date": None,
                "expense_ratio": None,
                "search_keyword": "테스트주식",
                "relevance_keywords": ["테스트", "주식"]
            }
        }

        stocks_manager.save_stocks(new_stocks)

        # Reload and verify
        Config._stock_config_cache = None
        loaded_stocks = stocks_manager.load_stocks()

        assert len(loaded_stocks) == 2
        assert loaded_stocks["TEST01"]["name"] == "테스트 ETF (수정)"
        assert loaded_stocks["TEST02"]["type"] == "STOCK"

    def test_save_stocks_creates_backup(self, temp_stocks_file):
        """Test that save_stocks creates backup file"""
        backup_dir = temp_stocks_file.parent

        # Save new data
        new_stocks = {
            "TEST01": {
                "name": "수정됨",
                "type": "ETF",
                "theme": "테스트",
                "launch_date": "2024-01-01",
                "expense_ratio": 0.0050
            }
        }
        stocks_manager.save_stocks(new_stocks)

        # Check if backup was created
        backup_files = list(backup_dir.glob("stocks.json.backup.*"))
        assert len(backup_files) > 0

    def test_save_stocks_preserves_korean(self, temp_stocks_file):
        """Test that Korean characters are preserved (ensure_ascii=False)"""
        new_stocks = {
            "TEST01": {
                "name": "한글 종목명",
                "type": "ETF",
                "theme": "한글 테마",
                "launch_date": "2024-01-01",
                "expense_ratio": 0.0050,
                "search_keyword": "한글",
                "relevance_keywords": ["한글", "테스트"]
            }
        }

        stocks_manager.save_stocks(new_stocks)

        # Read raw file content
        with open(temp_stocks_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Should contain Korean characters, not Unicode escapes
        assert "한글 종목명" in content
        assert "\\u" not in content  # No Unicode escapes


class TestValidateStockData:
    """Tests for validate_stock_data() function"""

    def test_validate_etf_success(self):
        """Test validation of valid ETF data"""
        etf_data = {
            "name": "테스트 ETF",
            "type": "ETF",
            "theme": "테스트",
            "launch_date": "2024-01-01",
            "expense_ratio": 0.0050,
            "search_keyword": "테스트",
            "relevance_keywords": ["테스트"]
        }

        is_valid, error = stocks_manager.validate_stock_data(etf_data)
        assert is_valid is True
        assert error is None

    def test_validate_stock_success(self):
        """Test validation of valid STOCK data"""
        stock_data = {
            "name": "테스트 주식",
            "type": "STOCK",
            "theme": "테스트",
            "launch_date": None,
            "expense_ratio": None,
            "search_keyword": "테스트",
            "relevance_keywords": ["테스트"]
        }

        is_valid, error = stocks_manager.validate_stock_data(stock_data)
        assert is_valid is True
        assert error is None

    def test_validate_missing_required_field(self):
        """Test validation fails when required field is missing"""
        invalid_data = {
            "type": "ETF",
            "theme": "테스트"
            # Missing 'name'
        }

        is_valid, error = stocks_manager.validate_stock_data(invalid_data)
        assert is_valid is False
        assert "name" in error.lower()

    def test_validate_invalid_type(self):
        """Test validation fails with invalid type"""
        invalid_data = {
            "name": "테스트",
            "type": "INVALID",  # Invalid type
            "theme": "테스트"
        }

        is_valid, error = stocks_manager.validate_stock_data(invalid_data)
        assert is_valid is False
        assert "type" in error.lower()

    def test_validate_etf_missing_launch_date(self):
        """Test validation fails when ETF is missing launch_date"""
        invalid_etf = {
            "name": "테스트 ETF",
            "type": "ETF",
            "theme": "테스트",
            "launch_date": None,  # Should not be None for ETF
            "expense_ratio": 0.0050
        }

        is_valid, error = stocks_manager.validate_stock_data(invalid_etf)
        assert is_valid is False
        assert "launch_date" in error.lower()

    def test_validate_etf_missing_expense_ratio(self):
        """Test validation fails when ETF is missing expense_ratio"""
        invalid_etf = {
            "name": "테스트 ETF",
            "type": "ETF",
            "theme": "테스트",
            "launch_date": "2024-01-01",
            "expense_ratio": None  # Should not be None for ETF
        }

        is_valid, error = stocks_manager.validate_stock_data(invalid_etf)
        assert is_valid is False
        assert "expense_ratio" in error.lower()

    def test_validate_stock_with_launch_date(self):
        """Test validation fails when STOCK has launch_date"""
        invalid_stock = {
            "name": "테스트 주식",
            "type": "STOCK",
            "theme": "테스트",
            "launch_date": "2024-01-01",  # Should be None for STOCK
            "expense_ratio": None
        }

        is_valid, error = stocks_manager.validate_stock_data(invalid_stock)
        assert is_valid is False
        assert "launch_date" in error.lower()

    def test_validate_invalid_date_format(self):
        """Test validation fails with invalid date format"""
        invalid_etf = {
            "name": "테스트 ETF",
            "type": "ETF",
            "theme": "테스트",
            "launch_date": "2024/01/01",  # Wrong format
            "expense_ratio": 0.0050
        }

        is_valid, error = stocks_manager.validate_stock_data(invalid_etf)
        assert is_valid is False
        assert "date" in error.lower()


class TestSyncStocksToDb:
    """Tests for sync_stocks_to_db() function"""

    @patch('app.utils.stocks_manager.get_db_connection')
    @patch('app.utils.stocks_manager.load_stocks')
    def test_sync_stocks_to_db(self, mock_load, mock_db):
        """Test synchronizing stocks to database"""
        # Mock stocks data
        mock_load.return_value = {
            "TEST01": {
                "name": "테스트 ETF",
                "type": "ETF",
                "theme": "테스트",
                "launch_date": "2024-01-01",
                "expense_ratio": 0.0050
            },
            "TEST02": {
                "name": "테스트 주식",
                "type": "STOCK",
                "theme": "테스트",
                "launch_date": None,
                "expense_ratio": None
            }
        }

        # Mock database connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db.return_value.__enter__.return_value = mock_conn

        # Run sync
        count = stocks_manager.sync_stocks_to_db()

        # Verify
        assert count == 2
        mock_cursor.executemany.assert_called_once()
        mock_conn.commit.assert_called_once()


class TestAddStock:
    """Tests for add_stock() function"""

    @patch('app.utils.stocks_manager.sync_stocks_to_db')
    @patch('app.utils.stocks_manager.save_stocks')
    @patch('app.utils.stocks_manager.Config.reload_stock_config')
    def test_add_stock_success(self, mock_reload, mock_save, mock_sync, temp_stocks_file):
        """Test adding a new stock"""
        new_stock_data = {
            "name": "새 종목",
            "type": "STOCK",
            "theme": "테스트",
            "launch_date": None,
            "expense_ratio": None,
            "search_keyword": "새종목",
            "relevance_keywords": ["새", "종목"]
        }

        stocks_manager.add_stock("NEW01", new_stock_data)

        # Verify save was called
        mock_save.assert_called_once()
        saved_stocks = mock_save.call_args[0][0]
        assert "NEW01" in saved_stocks
        assert saved_stocks["NEW01"]["name"] == "새 종목"

        # Verify sync and reload were called
        mock_sync.assert_called_once()
        mock_reload.assert_called_once()

    @patch('app.utils.stocks_manager.load_stocks')
    def test_add_stock_duplicate(self, mock_load):
        """Test adding duplicate ticker fails"""
        mock_load.return_value = {"TEST01": {"name": "기존 종목", "type": "ETF", "theme": "테스트"}}

        with pytest.raises(ValueError, match="already exists"):
            stocks_manager.add_stock("TEST01", {
                "name": "중복 종목",
                "type": "ETF",
                "theme": "테스트",
                "launch_date": "2024-01-01",
                "expense_ratio": 0.0050
            })

    def test_add_stock_invalid_data(self):
        """Test adding invalid stock data fails"""
        invalid_data = {
            "name": "잘못된 종목",
            "type": "INVALID",  # Invalid type
            "theme": "테스트"
        }

        with pytest.raises(ValueError, match="Invalid stock data"):
            stocks_manager.add_stock("INVALID", invalid_data)


class TestUpdateStock:
    """Tests for update_stock() function"""

    @patch('app.utils.stocks_manager.sync_stocks_to_db')
    @patch('app.utils.stocks_manager.save_stocks')
    @patch('app.utils.stocks_manager.Config.reload_stock_config')
    def test_update_stock_success(self, mock_reload, mock_save, mock_sync, temp_stocks_file):
        """Test updating an existing stock"""
        updated_data = {
            "name": "수정된 ETF",
            "type": "ETF",
            "theme": "수정됨",
            "launch_date": "2024-01-01",
            "expense_ratio": 0.0060  # Changed
        }

        stocks_manager.update_stock("TEST01", updated_data)

        # Verify save was called
        mock_save.assert_called_once()
        saved_stocks = mock_save.call_args[0][0]
        assert saved_stocks["TEST01"]["expense_ratio"] == 0.0060

    @patch('app.utils.stocks_manager.load_stocks')
    def test_update_stock_not_found(self, mock_load):
        """Test updating non-existent ticker fails"""
        mock_load.return_value = {}

        with pytest.raises(ValueError, match="not found"):
            stocks_manager.update_stock("NOTFOUND", {
                "name": "존재하지 않음",
                "type": "ETF",
                "theme": "테스트",
                "launch_date": "2024-01-01",
                "expense_ratio": 0.0050
            })


class TestDeleteStock:
    """Tests for delete_stock() function"""

    @patch('app.utils.stocks_manager.get_db_connection')
    @patch('app.utils.stocks_manager.save_stocks')
    @patch('app.utils.stocks_manager.Config.reload_stock_config')
    def test_delete_stock_success(self, mock_reload, mock_save, mock_db, temp_stocks_file):
        """Test deleting a stock"""
        # Mock database connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db.return_value.__enter__.return_value = mock_conn

        # Mock fetchone to return counts
        mock_cursor.fetchone.side_effect = [(10,), (5,), (3,)]  # prices, news, trading_flow

        # Delete stock
        deleted_counts = stocks_manager.delete_stock("TEST01")

        # Verify counts
        assert deleted_counts["prices"] == 10
        assert deleted_counts["news"] == 5
        assert deleted_counts["trading_flow"] == 3

        # Verify saves were called
        mock_save.assert_called_once()
        mock_reload.assert_called_once()

    @patch('app.utils.stocks_manager.load_stocks')
    def test_delete_stock_not_found(self, mock_load):
        """Test deleting non-existent ticker fails"""
        mock_load.return_value = {}

        with pytest.raises(ValueError, match="not found"):
            stocks_manager.delete_stock("NOTFOUND")
