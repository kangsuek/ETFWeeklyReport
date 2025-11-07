"""
Unit tests for ETFDataCollector
"""
import pytest
from app.services.data_collector import ETFDataCollector
from datetime import date, timedelta


class TestETFDataCollector:
    """Test cases for ETFDataCollector"""
    
    @pytest.fixture
    def collector(self):
        """Fixture to create collector instance"""
        return ETFDataCollector()
    
    def test_init(self, collector):
        """Test collector initialization"""
        assert collector is not None
        assert 'User-Agent' in collector.headers
    
    def test_parse_number(self, collector):
        """Test number parsing"""
        assert collector._parse_number("25,765") == 25765.0
        assert collector._parse_number("1,234,567") == 1234567.0
        assert collector._parse_number("") is None
        assert collector._parse_number("invalid") is None
    
    def test_parse_change_positive(self, collector):
        """Test positive change parsing"""
        result = collector._parse_change("상승205", 25765.0)
        assert result is not None
        assert result > 0  # 상승
        assert round(result, 2) == 0.8
    
    def test_parse_change_negative(self, collector):
        """Test negative change parsing"""
        result = collector._parse_change("하락1,375", 25560.0)
        assert result is not None
        assert result < 0  # 하락
        assert abs(result) > 0
    
    def test_parse_change_zero(self, collector):
        """Test zero change parsing"""
        result = collector._parse_change("보합0", 25765.0)
        assert result == 0.0
    
    def test_fetch_naver_finance_prices(self, collector):
        """Test actual data fetching from Naver Finance"""
        ticker = "487240"  # 삼성 KODEX AI전력핵심설비 ETF
        
        data = collector.fetch_naver_finance_prices(ticker, days=5)
        
        assert len(data) > 0
        assert len(data) <= 5
        
        # Check data structure
        first_record = data[0]
        assert 'ticker' in first_record
        assert 'date' in first_record
        assert 'close_price' in first_record
        assert 'volume' in first_record
        assert first_record['ticker'] == ticker
    
    def test_get_all_etfs(self, collector):
        """Test getting all ETFs from database"""
        etfs = collector.get_all_etfs()
        
        assert len(etfs) == 6  # 4 ETFs + 2 Stocks
        assert all(hasattr(etf, 'ticker') for etf in etfs)
        assert all(hasattr(etf, 'name') for etf in etfs)
        assert all(hasattr(etf, 'type') for etf in etfs)
    
    def test_get_etf_info(self, collector):
        """Test getting specific ETF info"""
        ticker = "487240"
        etf = collector.get_etf_info(ticker)
        
        assert etf is not None
        assert etf.ticker == ticker
        assert etf.type == "ETF"
        assert "KODEX" in etf.name
    
    def test_get_etf_info_not_found(self, collector):
        """Test getting non-existent ETF"""
        etf = collector.get_etf_info("999999")
        assert etf is None
    
    def test_save_price_data(self, collector):
        """Test saving price data to database"""
        test_data = [{
            'ticker': "487240",
            'date': date.today(),
            'open_price': 25000.0,
            'high_price': 26000.0,
            'low_price': 24500.0,
            'close_price': 25500.0,
            'volume': 1000000,
            'daily_change_pct': 2.0
        }]
        
        saved_count = collector.save_price_data(test_data)
        assert saved_count == 1
    
    def test_save_price_data_empty(self, collector):
        """Test saving empty data"""
        saved_count = collector.save_price_data([])
        assert saved_count == 0
    
    def test_get_price_data(self, collector):
        """Test retrieving price data from database"""
        ticker = "487240"
        end_date = date.today()
        start_date = end_date - timedelta(days=10)
        
        prices = collector.get_price_data(ticker, start_date, end_date)
        
        assert isinstance(prices, list)
        if len(prices) > 0:
            assert all(hasattr(p, 'date') for p in prices)
            assert all(hasattr(p, 'close_price') for p in prices)
            assert all(hasattr(p, 'volume') for p in prices)
            assert all(hasattr(p, 'open_price') for p in prices)
            assert all(hasattr(p, 'high_price') for p in prices)
            assert all(hasattr(p, 'low_price') for p in prices)


@pytest.mark.integration
class TestDataCollectionIntegration:
    """Integration tests for data collection"""
    
    def test_collect_and_save_prices(self):
        """Test end-to-end data collection"""
        collector = ETFDataCollector()
        ticker = "487240"
        
        saved_count = collector.collect_and_save_prices(ticker, days=5)
        
        assert saved_count > 0
        assert saved_count <= 5

