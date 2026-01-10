"""
투자자별 매매동향 테스트 모듈
"""

import pytest
from unittest.mock import patch, MagicMock
from httpx import AsyncClient
from datetime import date, timedelta
from app.main import app
from app.services.data_collector import ETFDataCollector


class TestTradingFlowScraping:
    """매매동향 스크래핑 테스트"""
    
    def test_parse_trading_volume(self):
        """거래량 파싱 테스트"""
        collector = ETFDataCollector()
        
        # 정상 케이스
        assert collector._parse_trading_volume("1,234") == 1234
        assert collector._parse_trading_volume("-5,678") == -5678
        assert collector._parse_trading_volume("0") == 0
        
        # 빈 값 케이스
        assert collector._parse_trading_volume("") is None
        assert collector._parse_trading_volume("   ") is None
        assert collector._parse_trading_volume("-") is None
        assert collector._parse_trading_volume(None) is None
    
    def test_fetch_naver_trading_flow_success(self):
        """Naver Finance 매매동향 수집 성공 테스트"""
        collector = ETFDataCollector()
        
        # Mock HTML response (실제 Naver Finance 구조: 두 개의 type2 테이블)
        mock_html = """
        <html>
            <table class="type2">
                <!-- 첫 번째 테이블: 증권사별 매매 (건너뜀) -->
                <tr><th>매도상위</th><th>거래량</th></tr>
            </table>
            <table class="type2">
                <!-- 두 번째 테이블: 투자자별 매매동향 -->
                <tr>
                    <th>날짜</th><th>종가</th><th>전일비</th><th>등락률</th>
                    <th>거래량</th><th>기관</th><th>외국인</th><th>보유</th><th>비율</th>
                </tr>
                <tr>
                    <td>2025.11.07</td>
                    <td>10,000</td>
                    <td>상승100</td>
                    <td>+1.0%</td>
                    <td>1,000,000</td>
                    <td>-567</td>
                    <td>890</td>
                    <td>10,000,000</td>
                    <td>10.5%</td>
                </tr>
                <tr>
                    <td>2025.11.06</td>
                    <td>9,900</td>
                    <td>상승50</td>
                    <td>+0.5%</td>
                    <td>900,000</td>
                    <td>789</td>
                    <td>-333</td>
                    <td>9,950,000</td>
                    <td>10.3%</td>
                </tr>
            </table>
        </html>
        """
        
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.text = mock_html
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            result = collector.fetch_naver_trading_flow("487240", days=2)
            
            assert len(result) == 2
            assert result[0]['ticker'] == "487240"
            assert result[0]['date'] == date(2025, 11, 7)
            # 개인 = -(기관 + 외국인) = -(-567 + 890) = -323
            assert result[0]['individual_net'] == -323
            assert result[0]['institutional_net'] == -567
            assert result[0]['foreign_net'] == 890
            
            assert result[1]['date'] == date(2025, 11, 6)
            # 개인 = -(기관 + 외국인) = -(789 + (-333)) = -456
            assert result[1]['individual_net'] == -456
            assert result[1]['institutional_net'] == 789
            assert result[1]['foreign_net'] == -333
    
    def test_fetch_naver_trading_flow_table_not_found(self):
        """매매동향 테이블 없음 테스트"""
        collector = ETFDataCollector()
        
        mock_html = "<html><body>No table here</body></html>"
        
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.text = mock_html
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            result = collector.fetch_naver_trading_flow("487240")
            
            assert result == []
    
    def test_fetch_naver_trading_flow_network_error(self):
        """네트워크 에러 테스트"""
        collector = ETFDataCollector()
        
        with patch('requests.get', side_effect=Exception("Network error")):
            result = collector.fetch_naver_trading_flow("487240")
            assert result == []


class TestTradingFlowValidation:
    """매매동향 데이터 검증 테스트"""
    
    def test_validate_trading_flow_data_valid(self):
        """유효한 매매동향 데이터 검증"""
        collector = ETFDataCollector()
        
        valid_data = {
            'ticker': '487240',
            'date': date(2025, 11, 7),
            'individual_net': 1234,
            'institutional_net': -567,
            'foreign_net': 890
        }
        
        assert collector.validate_trading_flow_data(valid_data) is True
    
    def test_validate_trading_flow_data_missing_ticker(self):
        """ticker 누락 검증"""
        collector = ETFDataCollector()
        
        invalid_data = {
            'date': date(2025, 11, 7),
            'individual_net': 1234
        }
        
        assert collector.validate_trading_flow_data(invalid_data) is False
    
    def test_validate_trading_flow_data_missing_date(self):
        """date 누락 검증"""
        collector = ETFDataCollector()
        
        invalid_data = {
            'ticker': '487240',
            'individual_net': 1234
        }
        
        assert collector.validate_trading_flow_data(invalid_data) is False
    
    def test_validate_trading_flow_data_invalid_date_type(self):
        """잘못된 date 타입 검증"""
        collector = ETFDataCollector()
        
        invalid_data = {
            'ticker': '487240',
            'date': '2025-11-07',  # 문자열은 안됨
            'individual_net': 1234
        }
        
        assert collector.validate_trading_flow_data(invalid_data) is False
    
    def test_validate_trading_flow_data_no_trading_data(self):
        """매매동향 데이터 없음 검증"""
        collector = ETFDataCollector()
        
        invalid_data = {
            'ticker': '487240',
            'date': date(2025, 11, 7),
            'individual_net': None,
            'institutional_net': None,
            'foreign_net': None
        }
        
        assert collector.validate_trading_flow_data(invalid_data) is False
    
    def test_validate_trading_flow_data_partial_data(self):
        """일부 매매동향 데이터만 있는 경우"""
        collector = ETFDataCollector()
        
        # 하나라도 있으면 유효
        partial_data = {
            'ticker': '487240',
            'date': date(2025, 11, 7),
            'individual_net': 1234,
            'institutional_net': None,
            'foreign_net': None
        }
        
        assert collector.validate_trading_flow_data(partial_data) is True


class TestTradingFlowSave:
    """매매동향 데이터 저장 테스트"""
    
    def test_save_trading_flow_data_success(self):
        """매매동향 데이터 저장 성공 테스트"""
        collector = ETFDataCollector()
        
        trading_data = [
            {
                'ticker': '487240',
                'date': date(2025, 11, 7),
                'individual_net': 1234,
                'institutional_net': -567,
                'foreign_net': 890
            }
        ]
        
        saved_count = collector.save_trading_flow_data(trading_data)
        assert saved_count == 1
    
    def test_save_trading_flow_data_empty(self):
        """빈 데이터 저장 테스트"""
        collector = ETFDataCollector()
        
        saved_count = collector.save_trading_flow_data([])
        assert saved_count == 0
    
    def test_save_trading_flow_data_with_invalid(self):
        """유효하지 않은 데이터 포함 시 테스트"""
        collector = ETFDataCollector()
        
        mixed_data = [
            {
                'ticker': '487240',
                'date': date(2025, 11, 7),
                'individual_net': 1234,
                'institutional_net': -567,
                'foreign_net': 890
            },
            {
                'ticker': '487240',
                # date 누락
                'individual_net': 1000
            }
        ]
        
        saved_count = collector.save_trading_flow_data(mixed_data)
        assert saved_count == 1  # 유효한 것만 저장


class TestTradingFlowAPI:
    """매매동향 API 테스트"""
    
    @pytest.mark.asyncio
    async def test_get_trading_flow_success(self):
        """매매동향 조회 성공 테스트"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # 먼저 데이터 수집
            await client.post("/api/etfs/487240/collect-trading-flow?days=5")
            
            # 조회
            response = await client.get("/api/etfs/487240/trading-flow")
            
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_get_trading_flow_with_date_range(self):
        """날짜 범위로 매매동향 조회 테스트"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            start_date = (date.today() - timedelta(days=30)).isoformat()
            end_date = date.today().isoformat()
            
            response = await client.get(
                f"/api/etfs/487240/trading-flow?start_date={start_date}&end_date={end_date}"
            )
            
            assert response.status_code in [200, 404]  # 데이터 없을 수도 있음
    
    @pytest.mark.asyncio
    async def test_get_trading_flow_not_found(self):
        """존재하지 않는 종목 조회 테스트"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/etfs/999999/trading-flow")
            
            assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_collect_trading_flow_success(self):
        """매매동향 수집 성공 테스트"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post("/api/etfs/487240/collect-trading-flow?days=5")
            
            assert response.status_code == 200
            data = response.json()
            assert 'ticker' in data
            assert 'collected' in data
            assert data['ticker'] == '487240'
    
    @pytest.mark.asyncio
    async def test_collect_trading_flow_default_days(self):
        """매매동향 수집 기본 일수 테스트"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post("/api/etfs/487240/collect-trading-flow")
            
            assert response.status_code == 200
            data = response.json()
            assert data['days'] == 10  # 기본값
    
    @pytest.mark.asyncio
    async def test_collect_trading_flow_not_found(self):
        """존재하지 않는 종목 수집 테스트"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post("/api/etfs/999999/collect-trading-flow")
            
            assert response.status_code == 404


class TestTradingFlowIntegration:
    """매매동향 통합 테스트"""
    
    def test_collect_and_retrieve_trading_flow(self):
        """매매동향 수집 및 조회 통합 테스트"""
        collector = ETFDataCollector()
        
        # 수집
        saved_count = collector.collect_and_save_trading_flow("487240", days=5)
        assert saved_count >= 0  # 실제 데이터 여부에 따라 다름
        
        # 조회
        start_date = date.today() - timedelta(days=7)
        end_date = date.today()
        
        retrieved_data = collector.get_trading_flow_data("487240", start_date, end_date)
        assert isinstance(retrieved_data, list)
    
    @pytest.mark.asyncio
    async def test_full_flow_api(self):
        """전체 플로우 API 테스트"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # 1. 수집
            collect_response = await client.post(
                "/api/etfs/487240/collect-trading-flow?days=10"
            )
            assert collect_response.status_code == 200
            
            # 2. 조회
            get_response = await client.get("/api/etfs/487240/trading-flow")
            assert get_response.status_code == 200

