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

            # 종목이 있어야 함
            assert data['total_tickers'] > 0
            assert len(data['status']) == data['total_tickers']

            # 각 종목 정보 확인
            for status in data['status']:
                assert 'ticker' in status
                assert 'name' in status
                assert 'type' in status
                assert 'recent_data_count' in status


class TestCollectorBatchMethods:
    """ETFDataCollector 일괄 수집 메서드 테스트 (병렬 처리 호환)"""

    def test_collect_all_tickers(self):
        """collect_all_tickers 메서드 테스트"""
        collector = ETFDataCollector()
        num_tickers = len(collector.get_all_etfs())

        with patch.object(collector, 'collect_and_save_prices') as mock_price, \
             patch.object(collector, 'collect_and_save_trading_flow') as mock_trading, \
             patch.object(collector.news_scraper, 'collect_and_save_news') as mock_news, \
             patch('app.database.update_collection_status'):
            mock_price.return_value = 10
            mock_trading.return_value = 10
            mock_news.return_value = {'collected': 0}

            result = collector.collect_all_tickers(days=5)

            # 종목 수만큼 호출되었는지 확인
            assert mock_price.call_count == num_tickers
            assert mock_trading.call_count == num_tickers

            # 결과 확인
            assert 'success_count' in result
            assert 'fail_count' in result
            assert 'total_price_records' in result
            assert 'total_trading_flow_records' in result
            assert 'total_news_records' in result
            assert 'duration_seconds' in result
            assert result['total_tickers'] == num_tickers
            assert result['total_price_records'] == 10 * num_tickers
            assert result['total_trading_flow_records'] == 10 * num_tickers

    def test_collect_all_tickers_with_failures(self):
        """일부 실패가 있는 일괄 수집 테스트"""
        collector = ETFDataCollector()
        tickers = [etf.ticker for etf in collector.get_all_etfs()]
        num_tickers = len(tickers)

        # 처음 2개 종목은 실패 (0건 반환)
        fail_tickers = set(tickers[:2])

        def price_side_effect(ticker, days):
            return 0 if ticker in fail_tickers else 10

        with patch.object(collector, 'collect_and_save_prices') as mock_price, \
             patch.object(collector, 'collect_and_save_trading_flow') as mock_trading, \
             patch.object(collector.news_scraper, 'collect_and_save_news') as mock_news, \
             patch('app.database.update_collection_status'):
            mock_price.side_effect = price_side_effect
            mock_trading.return_value = 5
            mock_news.return_value = {'collected': 0}

            result = collector.collect_all_tickers(days=5)

            expected_success = num_tickers - len(fail_tickers)
            assert result['success_count'] == expected_success
            assert result['fail_count'] == len(fail_tickers)
            assert result['total_price_records'] == 10 * expected_success
            assert result['total_trading_flow_records'] == 5 * num_tickers

    def test_collect_all_tickers_with_exception(self):
        """예외 발생 시 일괄 수집 테스트"""
        collector = ETFDataCollector()
        tickers = [etf.ticker for etf in collector.get_all_etfs()]
        num_tickers = len(tickers)

        # 첫 번째 종목만 예외 발생
        fail_ticker = tickers[0]

        def price_side_effect(ticker, days):
            if ticker == fail_ticker:
                raise Exception("Network error")
            return 10

        with patch.object(collector, 'collect_and_save_prices') as mock_price, \
             patch.object(collector, 'collect_and_save_trading_flow') as mock_trading, \
             patch.object(collector.news_scraper, 'collect_and_save_news') as mock_news, \
             patch('app.database.update_collection_status'):
            mock_price.side_effect = price_side_effect
            mock_trading.return_value = 5
            mock_news.return_value = {'collected': 0}

            result = collector.collect_all_tickers(days=5)

            assert result['success_count'] == num_tickers - 1
            assert result['fail_count'] == 1
            assert result['total_price_records'] == 10 * (num_tickers - 1)
            # 예외 발생 종목도 trading_flow는 시도됨
            assert result['total_trading_flow_records'] == 5 * num_tickers

            # 실패 상세 확인
            failed_tickers = [t for t, d in result['details'].items() if not d['success']]
            assert len(failed_tickers) == 1
            failed_detail = result['details'][failed_tickers[0]]
            assert 'Network error' in failed_detail['error']

    def test_backfill_all_tickers(self):
        """backfill_all_tickers 메서드 테스트"""
        collector = ETFDataCollector()
        num_tickers = len(collector.get_all_etfs())

        with patch.object(collector, 'collect_and_save_prices') as mock_collect:
            mock_collect.return_value = 90

            result = collector.backfill_all_tickers(days=90)

            # 종목 수만큼 호출되었는지 확인
            assert mock_collect.call_count == num_tickers

            # 결과 확인
            assert result['success_count'] == num_tickers
            assert result['fail_count'] == 0
            assert result['total_records'] == 90 * num_tickers
            assert result['days'] == 90

    def test_backfill_all_tickers_partial_failure(self):
        """일부 실패가 있는 백필 테스트"""
        collector = ETFDataCollector()
        tickers = [etf.ticker for etf in collector.get_all_etfs()]
        num_tickers = len(tickers)

        # 첫 번째: 예외, 두 번째: 0건 반환
        exception_ticker = tickers[0]
        zero_ticker = tickers[1] if num_tickers > 1 else None

        def collect_side_effect(ticker, days):
            if ticker == exception_ticker:
                raise Exception("Timeout")
            if ticker == zero_ticker:
                return 0
            return 90

        with patch.object(collector, 'collect_and_save_prices') as mock_collect:
            mock_collect.side_effect = collect_side_effect

            result = collector.backfill_all_tickers(days=90)

            fail_count = 1 + (1 if zero_ticker else 0)
            expected_success = num_tickers - fail_count
            assert result['success_count'] == expected_success
            assert result['fail_count'] == fail_count
            assert result['total_records'] == 90 * expected_success

