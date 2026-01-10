"""
Tests for Ticker Catalog Scheduler

Tests for scheduled ticker catalog collection functionality.
"""

import pytest
from unittest.mock import patch, MagicMock
from app.services.scheduler import DataCollectionScheduler


class TestTickerCatalogScheduler:
    """Tests for ticker catalog collection scheduler"""

    def test_collect_ticker_catalog_method_exists(self):
        """Test that collect_ticker_catalog method exists"""
        scheduler = DataCollectionScheduler()
        assert hasattr(scheduler, 'collect_ticker_catalog')
        assert callable(scheduler.collect_ticker_catalog)

    @patch('app.services.scheduler.TickerCatalogCollector')
    def test_collect_ticker_catalog_success(self, mock_collector_class):
        """Test successful ticker catalog collection"""
        mock_collector = MagicMock()
        mock_collector_class.return_value = mock_collector
        mock_collector.collect_all_stocks.return_value = {
            "total_collected": 100,
            "kospi_count": 40,
            "kosdaq_count": 50,
            "etf_count": 10,
            "saved_count": 100,
            "timestamp": "2025-01-15T10:30:00"
        }

        scheduler = DataCollectionScheduler()
        result = scheduler.collect_ticker_catalog()

        assert result is not None
        assert result["total_collected"] == 100
        assert scheduler.last_catalog_collection_time is not None
        mock_collector.collect_all_stocks.assert_called_once()

    @patch('app.services.scheduler.TickerCatalogCollector')
    def test_collect_ticker_catalog_error_handling(self, mock_collector_class):
        """Test error handling in ticker catalog collection"""
        mock_collector = MagicMock()
        mock_collector_class.return_value = mock_collector
        mock_collector.collect_all_stocks.side_effect = Exception("Collection failed")

        scheduler = DataCollectionScheduler()
        
        with pytest.raises(Exception):
            scheduler.collect_ticker_catalog()

    def test_scheduler_has_ticker_catalog_collector(self):
        """Test that scheduler has ticker_catalog_collector instance"""
        scheduler = DataCollectionScheduler()
        assert hasattr(scheduler, 'ticker_catalog_collector')
        assert scheduler.ticker_catalog_collector is not None

    def test_last_catalog_collection_time_initialized(self):
        """Test that last_catalog_collection_time is initialized"""
        scheduler = DataCollectionScheduler()
        assert scheduler.last_catalog_collection_time is None  # 초기값은 None

