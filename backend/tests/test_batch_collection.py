"""
일괄 데이터 수집 테스트 모듈
"""

import pytest
from unittest.mock import patch, MagicMock
from httpx import AsyncClient
from app.main import app
from app.services.data_collector import ETFDataCollector


class TestBatchCollectAPI:
    """일괄 수집 API 테스트"""
    
    @pytest.mark.asyncio
    async def test_collect_all_success(self):
        """전체 종목 수집 성공 테스트"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Mock the collect_all_tickers method
            with patch.object(ETFDataCollector, 'collect_all_tickers') as mock_collect:
                mock_collect.return_value = {
                    'success_count': 6,
                    'fail_count': 0,
                    'total_records': 60,
                    'total_tickers': 6,
                    'duration_seconds': 5.5,
                    'details': [
                        {'ticker': '487240', 'name': 'KODEX AI전력핵심설비', 'status': 'success', 'collected': 10}
                    ]
                }
                
                response = await client.post("/api/data/collect-all?days=10")
                
                assert response.status_code == 200
                data = response.json()
                assert 'result' in data
                assert data['result']['success_count'] == 6
                assert data['result']['total_records'] == 60
                
                # Mock이 호출되었는지 확인
                mock_collect.assert_called_once_with(days=10)
    
    @pytest.mark.asyncio
    async def test_collect_all_default_days(self):
        """기본 일수(1일)로 수집 테스트"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch.object(ETFDataCollector, 'collect_all_tickers') as mock_collect:
                mock_collect.return_value = {
                    'success_count': 6,
                    'fail_count': 0,
                    'total_records': 6,
                    'total_tickers': 6,
                    'duration_seconds': 3.0,
                    'details': []
                }
                
                response = await client.post("/api/data/collect-all")
                
                assert response.status_code == 200
                # 기본값 days=1로 호출되어야 함
                mock_collect.assert_called_once_with(days=1)
    
    @pytest.mark.asyncio
    async def test_collect_all_partial_failure(self):
        """일부 종목 실패 시 테스트"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch.object(ETFDataCollector, 'collect_all_tickers') as mock_collect:
                mock_collect.return_value = {
                    'success_count': 4,
                    'fail_count': 2,
                    'total_records': 40,
                    'total_tickers': 6,
                    'duration_seconds': 5.0,
                    'details': [
                        {'ticker': '487240', 'status': 'success', 'collected': 10},
                        {'ticker': '466920', 'status': 'failed', 'reason': 'Network error', 'collected': 0}
                    ]
                }
                
                response = await client.post("/api/data/collect-all?days=10")
                
                assert response.status_code == 200
                data = response.json()
                assert data['result']['success_count'] == 4
                assert data['result']['fail_count'] == 2
    
    @pytest.mark.asyncio
    async def test_collect_all_exception(self):
        """수집 중 예외 발생 테스트"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch.object(ETFDataCollector, 'collect_all_tickers') as mock_collect:
                mock_collect.side_effect = Exception("Database connection failed")
                
                response = await client.post("/api/data/collect-all")
                
                assert response.status_code == 500
                assert "Batch collection failed" in response.json()['detail']


class TestBackfillAPI:
    """히스토리 백필 API 테스트"""
    
    @pytest.mark.asyncio
    async def test_backfill_success(self):
        """백필 성공 테스트"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch.object(ETFDataCollector, 'backfill_all_tickers') as mock_backfill:
                mock_backfill.return_value = {
                    'success_count': 6,
                    'fail_count': 0,
                    'total_records': 540,
                    'total_tickers': 6,
                    'days': 90,
                    'duration_seconds': 30.0,
                    'details': []
                }
                
                response = await client.post("/api/data/backfill?days=90")
                
                assert response.status_code == 200
                data = response.json()
                assert data['result']['total_records'] == 540
                assert data['result']['days'] == 90
                
                mock_backfill.assert_called_once_with(days=90)
    
    @pytest.mark.asyncio
    async def test_backfill_default_days(self):
        """기본 백필 일수(90일) 테스트"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch.object(ETFDataCollector, 'backfill_all_tickers') as mock_backfill:
                mock_backfill.return_value = {
                    'success_count': 6,
                    'fail_count': 0,
                    'total_records': 540,
                    'total_tickers': 6,
                    'days': 90,
                    'duration_seconds': 30.0,
                    'details': []
                }
                
                response = await client.post("/api/data/backfill")
                
                assert response.status_code == 200
                mock_backfill.assert_called_once_with(days=90)
    
    @pytest.mark.asyncio
    async def test_backfill_custom_days(self):
        """커스텀 백필 일수 테스트"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch.object(ETFDataCollector, 'backfill_all_tickers') as mock_backfill:
                mock_backfill.return_value = {
                    'success_count': 6,
                    'fail_count': 0,
                    'total_records': 180,
                    'total_tickers': 6,
                    'days': 30,
                    'duration_seconds': 10.0,
                    'details': []
                }
                
                response = await client.post("/api/data/backfill?days=30")
                
                assert response.status_code == 200
                mock_backfill.assert_called_once_with(days=30)


class TestDataCollectionStatus:
    """데이터 수집 상태 조회 테스트"""
    
    @pytest.mark.asyncio
    async def test_get_collection_status(self):
        """수집 상태 조회 테스트"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/data/status")
            
            assert response.status_code == 200
            data = response.json()
            assert 'total_tickers' in data
            assert 'status' in data
            assert isinstance(data['status'], list)
            
            # 6개 종목이 있어야 함
            assert data['total_tickers'] == 6
            assert len(data['status']) == 6
            
            # 각 종목 정보 확인
            for status in data['status']:
                assert 'ticker' in status
                assert 'name' in status
                assert 'type' in status
                assert 'recent_data_count' in status


class TestCollectorBatchMethods:
    """ETFDataCollector 일괄 수집 메서드 테스트"""
    
    def test_collect_all_tickers(self):
        """collect_all_tickers 메서드 테스트"""
        collector = ETFDataCollector()

        with patch.object(collector, 'collect_and_save_prices') as mock_price, \
             patch.object(collector, 'collect_and_save_trading_flow') as mock_trading:
            mock_price.return_value = 10
            mock_trading.return_value = 10

            result = collector.collect_all_tickers(days=5)

            # 6개 종목에 대해 호출되었는지 확인
            assert mock_price.call_count == 6
            assert mock_trading.call_count == 6

            # 결과 확인
            assert 'success_count' in result
            assert 'fail_count' in result
            assert 'total_price_records' in result
            assert 'total_trading_flow_records' in result
            assert 'total_news_records' in result
            assert 'duration_seconds' in result
            assert result['total_tickers'] == 6
            assert result['total_price_records'] == 60  # 10 * 6
            assert result['total_trading_flow_records'] == 60  # 10 * 6
    
    def test_collect_all_tickers_with_failures(self):
        """일부 실패가 있는 일괄 수집 테스트"""
        collector = ETFDataCollector()

        # 일부는 성공, 일부는 0개 반환
        with patch.object(collector, 'collect_and_save_prices') as mock_price, \
             patch.object(collector, 'collect_and_save_trading_flow') as mock_trading:
            mock_price.side_effect = [10, 0, 10, 10, 0, 10]
            mock_trading.return_value = 5

            result = collector.collect_all_tickers(days=5)

            # 4개 성공, 2개 실패
            assert result['success_count'] == 4
            assert result['fail_count'] == 2
            assert result['total_price_records'] == 40  # 10 * 4
            assert result['total_trading_flow_records'] == 30  # 5 * 6
    
    def test_collect_all_tickers_with_exception(self):
        """예외 발생 시 일괄 수집 테스트"""
        collector = ETFDataCollector()

        with patch.object(collector, 'collect_and_save_prices') as mock_price, \
             patch.object(collector, 'collect_and_save_trading_flow') as mock_trading:
            # 일부는 성공, 일부는 예외 발생
            mock_price.side_effect = [10, Exception("Network error"), 10, 10, 10, 10]
            mock_trading.return_value = 5

            result = collector.collect_all_tickers(days=5)

            # 5개 성공, 1개 실패
            assert result['success_count'] == 5
            assert result['fail_count'] == 1
            assert result['total_price_records'] == 50  # 10 * 5
            assert result['total_trading_flow_records'] == 30  # 5 * 6 (trading은 계속 성공)

            # 실패 상세 확인
            failed_tickers = [ticker for ticker, d in result['details'].items() if not d['success']]
            assert len(failed_tickers) == 1
            failed_detail = result['details'][failed_tickers[0]]
            assert 'Network error' in failed_detail['error']
    
    def test_backfill_all_tickers(self):
        """backfill_all_tickers 메서드 테스트"""
        collector = ETFDataCollector()
        
        with patch.object(collector, 'collect_and_save_prices') as mock_collect:
            mock_collect.return_value = 90
            
            result = collector.backfill_all_tickers(days=90)
            
            # 6개 종목에 대해 호출되었는지 확인
            assert mock_collect.call_count == 6
            
            # 결과 확인
            assert result['success_count'] == 6
            assert result['fail_count'] == 0
            assert result['total_records'] == 540  # 90 * 6
            assert result['days'] == 90
    
    def test_backfill_all_tickers_partial_failure(self):
        """일부 실패가 있는 백필 테스트"""
        collector = ETFDataCollector()
        
        with patch.object(collector, 'collect_and_save_prices') as mock_collect:
            # 일부는 성공, 일부는 예외
            mock_collect.side_effect = [90, 90, Exception("Timeout"), 90, 0, 90]
            
            result = collector.backfill_all_tickers(days=90)
            
            # 4개 성공, 2개 실패 (예외 1개 + 0개 반환 1개)
            assert result['success_count'] == 4
            assert result['fail_count'] == 2
            assert result['total_records'] == 360  # 90 * 4

