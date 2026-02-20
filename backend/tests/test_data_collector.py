"""
Unit tests for ETFDataCollector
"""
import pytest
import requests
from unittest.mock import patch
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
        
        assert len(etfs) >= 1  # DB에 등록된 종목 수 (환경에 따라 다름)
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


class TestErrorHandling:
    """에러 처리 테스트"""
    
    @pytest.fixture
    def collector(self):
        """Fixture to create collector instance"""
        return ETFDataCollector()
    
    def test_fetch_naver_finance_prices_table_not_found(self, collector):
        """Test handling when price table is not found"""
        with patch('requests.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.text = "<html><body>No table here</body></html>"
            
            price_data = collector.fetch_naver_finance_prices("487240", days=5)
            
            assert len(price_data) == 0
    
    def test_fetch_naver_finance_prices_network_timeout(self, collector):
        """Test handling network timeout"""
        with patch('requests.get') as mock_get:
            mock_get.side_effect = requests.exceptions.Timeout("Connection timeout")
            
            price_data = collector.fetch_naver_finance_prices("487240", days=5)
            
            assert len(price_data) == 0
    
    def test_fetch_naver_finance_prices_connection_error(self, collector):
        """Test handling connection error"""
        with patch('requests.get') as mock_get:
            mock_get.side_effect = requests.exceptions.ConnectionError("Connection failed")
            
            price_data = collector.fetch_naver_finance_prices("487240", days=5)
            
            assert len(price_data) == 0
    
    def test_fetch_naver_finance_prices_http_error(self, collector):
        """Test handling HTTP error"""
        with patch('requests.get') as mock_get:
            mock_get.side_effect = requests.exceptions.HTTPError("404 Not Found")
            
            price_data = collector.fetch_naver_finance_prices("487240", days=5)
            
            assert len(price_data) == 0
    
    def test_fetch_naver_finance_prices_parsing_error(self, collector):
        """Test handling data parsing error"""
        html = """
        <html>
        <body>
            <table class="type2">
                <tr><th>날짜</th><th>종가</th><th>전일비</th><th>시가</th><th>고가</th><th>저가</th><th>거래량</th></tr>
                <tr><td>2025.11.07</td><td>invalid_price</td><td>상승205</td><td>25,700</td><td>25,765</td><td>25,000</td><td>1,036,539</td></tr>
            </table>
        </body>
        </html>
        """
        
        with patch('requests.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.text = html
            
            price_data = collector.fetch_naver_finance_prices("487240", days=5)
            
            # 파싱 실패 시 None이 포함된 행이 수집될 수 있음 (구현에 따라 행 수 상이)
            assert len(price_data) >= 1
            has_invalid = any(r.get('close_price') is None for r in price_data)
            assert has_invalid, "invalid_price 행에서 close_price가 None이어야 함"
            saved_count = collector.save_price_data(price_data)
            assert saved_count == 0  # close_price가 None이면 검증 실패로 저장 0
    
    def test_fetch_naver_finance_prices_invalid_date_format(self, collector):
        """Test handling invalid date format"""
        html = """
        <html>
        <body>
            <table class="type2">
                <tr><th>날짜</th><th>종가</th><th>전일비</th><th>시가</th><th>고가</th><th>저가</th><th>거래량</th></tr>
                <tr><td>invalid_date</td><td>25,050</td><td>상승205</td><td>25,700</td><td>25,765</td><td>25,000</td><td>1,036,539</td></tr>
            </table>
        </body>
        </html>
        """
        
        with patch('requests.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.text = html
            
            price_data = collector.fetch_naver_finance_prices("487240", days=5)
            
            # 날짜 형식이 잘못된 행은 건너뛰고 빈 리스트 반환
            assert len(price_data) == 0
    
    def test_parse_change_edge_cases(self, collector):
        """Test _parse_change with edge cases"""
        # 빈 문자열
        assert collector._parse_change("", 10000.0) is None
        
        # None 입력
        assert collector._parse_change(None, 10000.0) is None
        
        # close_price가 0인 경우
        assert collector._parse_change("상승100", 0.0) is None
        
        # close_price가 None인 경우
        assert collector._parse_change("상승100", None) is None
        
        # 변화량을 파싱할 수 없는 경우
        assert collector._parse_change("보합", 10000.0) == 0.0
        
        # 이전 가격이 0이 되는 경우 (change_amount == close_price)
        result = collector._parse_change("상승10000", 10000.0)
        # prev_price = 10000 - 10000 = 0, division by zero 방지
        assert result is None
    
    def test_parse_number_edge_cases(self, collector):
        """Test _parse_number with edge cases"""
        # 빈 문자열
        assert collector._parse_number("") is None
        
        # None
        assert collector._parse_number(None) is None
        
        # 공백만 있는 문자열
        assert collector._parse_number("   ") is None
        
        # 숫자가 아닌 문자
        assert collector._parse_number("abc") is None
        assert collector._parse_number("N/A") is None
        
        # 음수
        assert collector._parse_number("-100") == -100.0
        
        # 소수점
        assert collector._parse_number("1,234.56") == 1234.56
    
    def test_save_price_data_database_error(self, collector):
        """Test handling database error during save"""
        invalid_data = [{
            'ticker': '487240',
            'date': 'invalid_date_type',  # 잘못된 타입 (검증 통과하지 못함)
            'close_price': 25000.0
        }]
        
        # 검증 실패로 저장되지 않음
        saved_count = collector.save_price_data(invalid_data)
        assert saved_count == 0
    
    def test_collect_and_save_prices_fetch_failure(self, collector):
        """Test collect_and_save_prices when fetch fails"""
        with patch.object(collector, 'fetch_naver_finance_prices', return_value=[]):
            saved_count = collector.collect_and_save_prices("487240", days=5)
            
            assert saved_count == 0
    
    def test_collect_and_save_prices_partial_failure(self, collector):
        """Test collect_and_save_prices with partial data"""
        mock_data = [
            # 정상 데이터
            {
                'ticker': '487240',
                'date': date(2025, 11, 14),
                'close_price': 25000.0,
                'volume': 100000
            }
        ]
        
        with patch.object(collector, 'fetch_naver_finance_prices', return_value=mock_data):
            saved_count = collector.collect_and_save_prices("487240", days=5)
            
            assert saved_count == 1


# ========== Step 3: 데이터 검증 및 정제 테스트 ==========

class TestDataValidation:
    """데이터 검증 테스트"""
    
    @pytest.fixture
    def collector(self):
        """Fixture to create collector instance"""
        return ETFDataCollector()
    
    def test_validate_price_data_valid(self, collector):
        """Test validation with valid data"""
        valid_data = {
            'ticker': '487240',
            'date': date(2025, 11, 7),
            'open_price': 25700.0,
            'high_price': 25765.0,
            'low_price': 25000.0,
            'close_price': 25050.0,
            'volume': 1036539,
            'daily_change_pct': -2.78
        }
        
        is_valid, error_msg = collector.validate_price_data(valid_data)
        
        assert is_valid is True
        assert error_msg is None
    
    def test_validate_price_data_missing_ticker(self, collector):
        """Test validation with missing ticker"""
        invalid_data = {
            'date': date(2025, 11, 7),
            'close_price': 25050.0
        }
        
        is_valid, error_msg = collector.validate_price_data(invalid_data)
        
        assert is_valid is False
        assert 'ticker' in error_msg
    
    def test_validate_price_data_missing_date(self, collector):
        """Test validation with missing date"""
        invalid_data = {
            'ticker': '487240',
            'close_price': 25050.0
        }
        
        is_valid, error_msg = collector.validate_price_data(invalid_data)
        
        assert is_valid is False
        assert 'date' in error_msg
    
    def test_validate_price_data_missing_close_price(self, collector):
        """Test validation with missing close_price"""
        invalid_data = {
            'ticker': '487240',
            'date': date(2025, 11, 7)
        }
        
        is_valid, error_msg = collector.validate_price_data(invalid_data)
        
        assert is_valid is False
        assert 'close_price' in error_msg
    
    def test_validate_price_data_invalid_date_type(self, collector):
        """Test validation with invalid date type"""
        invalid_data = {
            'ticker': '487240',
            'date': '2025-11-07',  # 문자열 (잘못된 타입)
            'close_price': 25050.0
        }
        
        is_valid, error_msg = collector.validate_price_data(invalid_data)
        
        assert is_valid is False
        assert 'Invalid date type' in error_msg
    
    def test_validate_price_data_negative_close_price(self, collector):
        """Test validation with negative close_price"""
        invalid_data = {
            'ticker': '487240',
            'date': date(2025, 11, 7),
            'close_price': -100.0
        }
        
        is_valid, error_msg = collector.validate_price_data(invalid_data)
        
        assert is_valid is False
        assert 'Invalid close_price' in error_msg
    
    def test_validate_price_data_zero_close_price(self, collector):
        """Test validation with zero close_price"""
        invalid_data = {
            'ticker': '487240',
            'date': date(2025, 11, 7),
            'close_price': 0.0
        }
        
        is_valid, error_msg = collector.validate_price_data(invalid_data)
        
        assert is_valid is False
        assert 'Invalid close_price' in error_msg
    
    def test_validate_price_data_negative_open_price(self, collector):
        """Test validation with negative open_price"""
        invalid_data = {
            'ticker': '487240',
            'date': date(2025, 11, 7),
            'open_price': -25700.0,
            'close_price': 25050.0
        }
        
        is_valid, error_msg = collector.validate_price_data(invalid_data)
        
        assert is_valid is False
        assert 'Invalid open_price' in error_msg
    
    def test_validate_price_data_negative_volume(self, collector):
        """Test validation with negative volume"""
        invalid_data = {
            'ticker': '487240',
            'date': date(2025, 11, 7),
            'close_price': 25050.0,
            'volume': -100
        }
        
        is_valid, error_msg = collector.validate_price_data(invalid_data)
        
        assert is_valid is False
        assert 'Invalid volume' in error_msg
    
    def test_validate_price_data_high_less_than_low(self, collector):
        """Test validation with high < low"""
        invalid_data = {
            'ticker': '487240',
            'date': date(2025, 11, 7),
            'close_price': 25050.0,
            'high_price': 25000.0,
            'low_price': 25765.0
        }
        
        is_valid, error_msg = collector.validate_price_data(invalid_data)
        
        assert is_valid is False
        assert 'high_price' in error_msg and 'low_price' in error_msg
    
    def test_validate_price_data_open_price_out_of_range(self, collector):
        """Test validation with open_price out of range"""
        invalid_data = {
            'ticker': '487240',
            'date': date(2025, 11, 7),
            'open_price': 26000.0,  # 범위 밖
            'high_price': 25765.0,
            'low_price': 25000.0,
            'close_price': 25050.0
        }
        
        is_valid, error_msg = collector.validate_price_data(invalid_data)
        
        assert is_valid is False
        assert 'open_price' in error_msg and 'out of range' in error_msg
    
    def test_validate_price_data_close_price_out_of_range(self, collector):
        """Test validation with close_price out of range"""
        invalid_data = {
            'ticker': '487240',
            'date': date(2025, 11, 7),
            'high_price': 25765.0,
            'low_price': 25000.0,
            'close_price': 26000.0  # 범위 밖
        }
        
        is_valid, error_msg = collector.validate_price_data(invalid_data)
        
        assert is_valid is False
        assert 'close_price' in error_msg and 'out of range' in error_msg


class TestDataCleaning:
    """데이터 정제 테스트"""
    
    @pytest.fixture
    def collector(self):
        """Fixture to create collector instance"""
        return ETFDataCollector()
    
    def test_clean_price_data_none_volume(self, collector):
        """Test cleaning data with None volume"""
        data = {
            'ticker': '487240',
            'date': date(2025, 11, 7),
            'close_price': 25050.0,
            'volume': None
        }
        
        cleaned = collector.clean_price_data(data)
        
        assert cleaned['volume'] == 0
    
    def test_clean_price_data_float_volume(self, collector):
        """Test cleaning data with float volume"""
        data = {
            'ticker': '487240',
            'date': date(2025, 11, 7),
            'close_price': 25050.0,
            'volume': 1036539.0  # float
        }
        
        cleaned = collector.clean_price_data(data)
        
        assert isinstance(cleaned['volume'], int)
        assert cleaned['volume'] == 1036539
    
    def test_clean_price_data_round_prices(self, collector):
        """Test cleaning data with price rounding"""
        data = {
            'ticker': '487240',
            'date': date(2025, 11, 7),
            'open_price': 25700.123456,
            'high_price': 25765.987654,
            'low_price': 25000.555555,
            'close_price': 25050.777777
        }
        
        cleaned = collector.clean_price_data(data)
        
        assert cleaned['open_price'] == 25700.12
        assert cleaned['high_price'] == 25765.99
        assert cleaned['low_price'] == 25000.56
        assert cleaned['close_price'] == 25050.78
    
    def test_clean_price_data_round_change_pct(self, collector):
        """Test cleaning data with change_pct rounding"""
        data = {
            'ticker': '487240',
            'date': date(2025, 11, 7),
            'close_price': 25050.0,
            'daily_change_pct': -2.78123456
        }
        
        cleaned = collector.clean_price_data(data)
        
        assert cleaned['daily_change_pct'] == -2.78
    
    def test_clean_price_data_preserves_other_fields(self, collector):
        """Test that cleaning preserves other fields"""
        data = {
            'ticker': '487240',
            'date': date(2025, 11, 7),
            'close_price': 25050.0,
            'volume': 1000000
        }
        
        cleaned = collector.clean_price_data(data)
        
        assert cleaned['ticker'] == data['ticker']
        assert cleaned['date'] == data['date']
        assert cleaned['close_price'] == data['close_price']


class TestValidationIntegration:
    """검증 통합 테스트"""
    
    @pytest.fixture
    def collector(self):
        """Fixture to create collector instance"""
        return ETFDataCollector()
    
    def test_save_price_data_with_invalid_data(self, collector):
        """Test saving mixed valid/invalid data"""
        mixed_data = [
            # 정상 데이터
            {
                'ticker': '487240',
                'date': date(2025, 11, 10),
                'close_price': 25000.0,
                'volume': 100000
            },
            # 비정상 데이터 (음수 가격)
            {
                'ticker': '487240',
                'date': date(2025, 11, 11),
                'close_price': -25000.0,
                'volume': 100000
            },
            # 정상 데이터
            {
                'ticker': '487240',
                'date': date(2025, 11, 12),
                'close_price': 26000.0,
                'volume': 200000
            }
        ]
        
        saved_count = collector.save_price_data(mixed_data)
        
        # 정상 데이터 2개만 저장되어야 함
        assert saved_count == 2
    
    def test_save_price_data_with_cleaning(self, collector):
        """Test that save applies data cleaning"""
        data = [{
            'ticker': '487240',
            'date': date(2025, 11, 13),
            'open_price': 25700.999,
            'high_price': 25765.111,
            'low_price': 25000.222,
            'close_price': 25050.333,
            'volume': 1036539.0,  # float
            'daily_change_pct': -2.78888
        }]
        
        saved_count = collector.save_price_data(data)
        assert saved_count == 1
        
        # Verify data was cleaned and saved correctly
        prices = collector.get_price_data('487240', 
                                         date(2025, 11, 13), 
                                         date(2025, 11, 13))
        
        assert len(prices) == 1
        price = prices[0]
        
        # Check that volume is integer
        assert isinstance(price.volume, int)
        assert price.volume == 1036539
        
        # Check that prices are rounded to 2 decimals
        assert price.open_price == 25701.0  # Rounded
        assert price.close_price == 25050.33

