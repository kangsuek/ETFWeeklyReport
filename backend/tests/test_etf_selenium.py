"""
Tests for Selenium-based ETF collection

Tests for ETF collection using Selenium webdriver.
"""

import pytest
from unittest.mock import patch, MagicMock, Mock
from app.services.ticker_catalog_collector import TickerCatalogCollector, SELENIUM_AVAILABLE


class TestETFSeleniumCollection:
    """Tests for Selenium-based ETF collection"""

    def test_selenium_availability(self):
        """Test that Selenium availability is checked"""
        # SELENIUM_AVAILABLE은 모듈 레벨에서 설정됨
        assert isinstance(SELENIUM_AVAILABLE, bool)

    @pytest.mark.skipif(not SELENIUM_AVAILABLE, reason="Selenium not available")
    def test_collect_etf_stocks_selenium_method_exists(self):
        """Test that _collect_etf_stocks_selenium method exists"""
        collector = TickerCatalogCollector()
        assert hasattr(collector, '_collect_etf_stocks_selenium')
        assert callable(collector._collect_etf_stocks_selenium)

    def test_collect_etf_stocks_fallback(self):
        """Test that _collect_etf_stocks falls back to requests method"""
        collector = TickerCatalogCollector()
        
        # Selenium 실패 시 requests 방식으로 fallback
        with patch.object(collector, '_collect_etf_stocks_selenium', side_effect=Exception("Selenium failed")):
            with patch.object(collector, '_collect_etf_stocks_requests', return_value=[]) as mock_requests:
                result = collector._collect_etf_stocks()
                assert result == []
                mock_requests.assert_called_once()

    def test_collect_etf_stocks_requests_method_exists(self):
        """Test that _collect_etf_stocks_requests method exists"""
        collector = TickerCatalogCollector()
        assert hasattr(collector, '_collect_etf_stocks_requests')
        assert callable(collector._collect_etf_stocks_requests)

    @patch('app.services.ticker_catalog_collector.requests')
    def test_collect_etf_stocks_requests_empty_result(self, mock_requests):
        """Test requests-based ETF collection with empty result"""
        collector = TickerCatalogCollector()
        
        # Mock response
        mock_response = Mock()
        mock_response.text = '<html><body><table class="type_1"></table></body></html>'
        mock_response.raise_for_status = Mock()
        mock_requests.get.return_value = mock_response
        
        result = collector._collect_etf_stocks_requests()
        assert result == []

    def test_etf_collection_integration(self):
        """Test that ETF collection is integrated in collect_all_stocks"""
        collector = TickerCatalogCollector()
        
        # collect_all_stocks가 _collect_etf_stocks를 호출하는지 확인
        with patch.object(collector, '_collect_kospi_stocks', return_value=[]):
            with patch.object(collector, '_collect_kosdaq_stocks', return_value=[]):
                with patch.object(collector, '_collect_etf_stocks', return_value=[]) as mock_etf:
                    with patch.object(collector, '_save_to_database', return_value=0):
                        result = collector.collect_all_stocks()
                        mock_etf.assert_called_once()
                        assert result['etf_count'] == 0

