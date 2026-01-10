"""
Tests for Ticker Catalog functionality

Tests for stock catalog collection and search functionality.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app
from app.database import init_db, get_db_connection

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    """Setup database for each test"""
    init_db()
    yield


class TestTickerCatalogCollection:
    """Tests for POST /api/settings/ticker-catalog/collect"""

    @patch('app.routers.settings.ticker_catalog_collector.collect_all_stocks')
    def test_collect_ticker_catalog_success(self, mock_collect):
        """Test collecting ticker catalog successfully"""
        mock_collect.return_value = {
            "total_collected": 100,
            "kospi_count": 40,
            "kosdaq_count": 50,
            "etf_count": 10,
            "saved_count": 100,
            "timestamp": "2025-01-15T10:30:00"
        }

        response = client.post("/api/settings/ticker-catalog/collect")

        assert response.status_code == 200
        data = response.json()
        assert data["total_collected"] == 100
        assert data["kospi_count"] == 40
        assert data["kosdaq_count"] == 50
        assert data["etf_count"] == 10
        assert data["saved_count"] == 100
        assert "timestamp" in data

        mock_collect.assert_called_once()

    @patch('app.routers.settings.ticker_catalog_collector.collect_all_stocks')
    def test_collect_ticker_catalog_error(self, mock_collect):
        """Test collecting ticker catalog with error"""
        from app.exceptions import ScraperException
        mock_collect.side_effect = ScraperException("수집 실패")

        response = client.post("/api/settings/ticker-catalog/collect")

        assert response.status_code == 500
        assert "수집 실패" in response.json()["detail"]


class TestStockSearch:
    """Tests for GET /api/settings/stocks/search"""

    def setup_method(self):
        """Setup test data in stock_catalog table"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Insert test data
            test_stocks = [
                ("005930", "삼성전자", "STOCK", "KOSPI", None),
                ("005935", "삼성전자우", "STOCK", "KOSPI", None),
                ("487240", "삼성 KODEX AI전력핵심설비 ETF", "ETF", "ETF", None),
                ("000660", "SK하이닉스", "STOCK", "KOSPI", None),
            ]
            cursor.executemany("""
                INSERT OR REPLACE INTO stock_catalog 
                (ticker, name, type, market, sector, is_active)
                VALUES (?, ?, ?, ?, ?, 1)
            """, test_stocks)
            conn.commit()

    def test_search_stocks_by_name(self):
        """Test searching stocks by name"""
        response = client.get("/api/settings/stocks/search?q=삼성")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        
        # Check that results contain "삼성"
        for stock in data:
            assert "삼성" in stock["name"] or "삼성" in stock["ticker"]
            assert "ticker" in stock
            assert "name" in stock
            assert "type" in stock
            assert "market" in stock

    def test_search_stocks_by_ticker(self):
        """Test searching stocks by ticker code"""
        response = client.get("/api/settings/stocks/search?q=005930")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        
        # Check that results contain the ticker
        tickers = [stock["ticker"] for stock in data]
        assert "005930" in tickers

    def test_search_stocks_with_type_filter(self):
        """Test searching stocks with type filter"""
        response = client.get("/api/settings/stocks/search?q=삼성&type=ETF")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # All results should be ETF type
        for stock in data:
            assert stock["type"] == "ETF"

    def test_search_stocks_short_query(self):
        """Test searching with query too short"""
        response = client.get("/api/settings/stocks/search?q=삼")

        assert response.status_code == 400
        assert "최소 2자" in response.json()["detail"]

    def test_search_stocks_no_query(self):
        """Test searching without query parameter"""
        response = client.get("/api/settings/stocks/search")

        assert response.status_code == 422  # Validation error

    def test_search_stocks_limit(self):
        """Test that search results are limited"""
        response = client.get("/api/settings/stocks/search?q=삼성")

        assert response.status_code == 200
        data = response.json()
        # Should be limited to 20 results
        assert len(data) <= 20

    def test_search_stocks_empty_result(self):
        """Test searching with no matching results"""
        response = client.get("/api/settings/stocks/search?q=존재하지않는종목명12345")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0


class TestTickerCatalogService:
    """Tests for TickerCatalogCollector service"""

    def test_search_stocks_empty_query(self):
        """Test search_stocks with empty query"""
        from app.services.ticker_catalog_collector import TickerCatalogCollector
        
        collector = TickerCatalogCollector()
        result = collector.search_stocks("", limit=10)
        
        assert result == []

    def test_search_stocks_short_query(self):
        """Test search_stocks with query too short"""
        from app.services.ticker_catalog_collector import TickerCatalogCollector
        
        collector = TickerCatalogCollector()
        result = collector.search_stocks("삼", limit=10)
        
        assert result == []

    def test_search_stocks_with_data(self):
        """Test search_stocks with actual data"""
        from app.services.ticker_catalog_collector import TickerCatalogCollector
        
        # Setup test data
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO stock_catalog 
                (ticker, name, type, market, sector, is_active)
                VALUES (?, ?, ?, ?, ?, 1)
            """, ("005930", "삼성전자", "STOCK", "KOSPI", None))
            conn.commit()
        
        collector = TickerCatalogCollector()
        result = collector.search_stocks("삼성", limit=10)
        
        assert isinstance(result, list)
        assert len(result) > 0
        
        # Check that the result contains our test data
        tickers = [stock["ticker"] for stock in result]
        names = [stock["name"] for stock in result]
        assert "005930" in tickers or "삼성전자" in names

    def test_save_to_database(self):
        """Test saving stocks to database"""
        from app.services.ticker_catalog_collector import TickerCatalogCollector
        
        collector = TickerCatalogCollector()
        test_stocks = [
            {
                "ticker": "TEST01",
                "name": "테스트 종목 1",
                "type": "STOCK",
                "market": "KOSPI",
                "sector": None,
                "listed_date": None,
                "is_active": 1
            },
            {
                "ticker": "TEST02",
                "name": "테스트 종목 2",
                "type": "ETF",
                "market": "ETF",
                "sector": None,
                "listed_date": None,
                "is_active": 1
            }
        ]
        
        saved_count = collector._save_to_database(test_stocks)
        
        assert saved_count == 2
        
        # Verify data was saved
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM stock_catalog WHERE ticker IN ('TEST01', 'TEST02')")
            rows = cursor.fetchall()
            assert len(rows) == 2


class TestDatabaseSchema:
    """Tests for stock_catalog table schema"""

    def test_stock_catalog_table_exists(self):
        """Test that stock_catalog table exists"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='stock_catalog'
            """)
            result = cursor.fetchone()
            assert result is not None

    def test_stock_catalog_indexes_exist(self):
        """Test that indexes exist on stock_catalog table"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='index' AND tbl_name='stock_catalog'
            """)
            indexes = [row[0] for row in cursor.fetchall()]
            
            assert 'idx_stock_catalog_name' in indexes
            assert 'idx_stock_catalog_type' in indexes
            assert 'idx_stock_catalog_active' in indexes

    def test_stock_catalog_table_structure(self):
        """Test stock_catalog table structure"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(stock_catalog)")
            columns = {row[1]: row[2] for row in cursor.fetchall()}
            
            assert 'ticker' in columns
            assert 'name' in columns
            assert 'type' in columns
            assert 'market' in columns
            assert 'sector' in columns
            assert 'listed_date' in columns
            assert 'last_updated' in columns
            assert 'is_active' in columns

