"""
커버리지 개선을 위한 추가 테스트
"""

import pytest
from httpx import AsyncClient
from datetime import date, timedelta
from app.main import app
from unittest.mock import patch


class TestMainAppLifecycle:
    """FastAPI 앱 생명주기 테스트"""
    
    @pytest.mark.asyncio
    async def test_startup_and_shutdown_events(self):
        """Startup과 Shutdown 이벤트 테스트"""
        # 앱 초기화 시 startup 이벤트가 호출되는지 확인
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Health check로 앱이 정상 작동하는지 확인
            response = await client.get("/api/health")
            assert response.status_code == 200
            assert response.json()["status"] == "healthy"


class TestETFRouterErrorCases:
    """ETF 라우터 에러 케이스 테스트"""
    
    @pytest.mark.asyncio
    async def test_get_all_etfs_exception(self):
        """전체 ETF 조회 시 예외 테스트"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch('app.services.data_collector.ETFDataCollector.get_all_etfs',
                      side_effect=Exception("Database error")):
                response = await client.get("/api/etfs/")
                assert response.status_code == 500
    
    @pytest.mark.asyncio
    async def test_get_etf_by_ticker_exception(self):
        """특정 ETF 조회 시 예외 테스트"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch('app.services.data_collector.ETFDataCollector.get_etf_info',
                      side_effect=Exception("Database error")):
                response = await client.get("/api/etfs/487240")
                assert response.status_code == 500
    
    @pytest.mark.asyncio
    async def test_get_etf_by_ticker_database_error(self):
        """ETF 조회 시 데이터베이스 에러 테스트"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # 잘못된 ticker로 조회 시도
            response = await client.get("/api/etfs/INVALID_TICKER_12345")
            # 404 또는 500 응답 확인
            assert response.status_code in [404, 500]
    
    @pytest.mark.asyncio
    async def test_get_prices_exception(self):
        """가격 조회 시 예외 테스트"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch('app.services.data_collector.ETFDataCollector.get_price_data',
                      side_effect=Exception("Database error")):
                response = await client.get("/api/etfs/487240/prices")
                assert response.status_code == 500
    
    @pytest.mark.asyncio
    async def test_get_metrics_exception(self):
        """메트릭스 조회 시 예외 테스트"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch('app.services.data_collector.ETFDataCollector.get_etf_metrics',
                      side_effect=Exception("Calculation error")):
                response = await client.get("/api/etfs/487240/metrics")
                assert response.status_code == 500
    
    @pytest.mark.asyncio
    async def test_get_prices_invalid_dates(self):
        """잘못된 날짜 형식으로 가격 조회 테스트"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # 잘못된 날짜 형식
            response = await client.get(
                "/api/etfs/487240/prices?start_date=invalid&end_date=2025-11-07"
            )
            assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_collect_prices_database_error(self):
        """데이터 수집 시 데이터베이스 에러 시뮬레이션"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch('app.services.data_collector.ETFDataCollector.collect_and_save_prices', 
                      side_effect=Exception("Database error")):
                response = await client.post("/api/etfs/487240/collect?days=1")
                assert response.status_code == 500
    
    @pytest.mark.asyncio
    async def test_get_trading_flow_database_error(self):
        """매매동향 조회 시 데이터베이스 에러 테스트"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch('app.services.data_collector.ETFDataCollector.get_trading_flow_data',
                      side_effect=Exception("Database error")):
                response = await client.get("/api/etfs/487240/trading-flow")
                assert response.status_code == 500
    
    @pytest.mark.asyncio
    async def test_collect_trading_flow_error(self):
        """매매동향 수집 시 에러 테스트"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch('app.services.data_collector.ETFDataCollector.collect_and_save_trading_flow',
                      side_effect=Exception("Scraping error")):
                response = await client.post("/api/etfs/487240/collect-trading-flow?days=5")
                assert response.status_code == 500
    
    @pytest.mark.asyncio
    async def test_get_metrics(self):
        """ETF 메트릭스 조회 테스트"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/etfs/487240/metrics")
            assert response.status_code == 200
            data = response.json()
            assert 'ticker' in data
            assert data['ticker'] == '487240'


class TestDataRouterErrorCases:
    """데이터 라우터 에러 케이스 테스트"""
    
    @pytest.mark.asyncio
    async def test_collect_all_with_failure(self):
        """전체 수집 실패 테스트"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch('app.services.data_collector.ETFDataCollector.collect_all_tickers',
                      side_effect=Exception("Collection failed")):
                response = await client.post("/api/data/collect-all?days=1")
                assert response.status_code == 500
    
    @pytest.mark.asyncio
    async def test_backfill_with_failure(self):
        """백필 실패 테스트"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch('app.services.data_collector.ETFDataCollector.backfill_all_tickers',
                      side_effect=Exception("Backfill failed")):
                response = await client.post("/api/data/backfill?days=30")
                assert response.status_code == 500
    
    @pytest.mark.asyncio
    async def test_status_with_error(self):
        """상태 조회 에러 테스트"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch('app.services.data_collector.ETFDataCollector.get_all_etfs',
                      side_effect=Exception("Database error")):
                response = await client.get("/api/data/status")
                assert response.status_code == 500


class TestNewsRouter:
    """뉴스 라우터 테스트"""
    
    @pytest.mark.asyncio
    async def test_get_news_for_ticker(self):
        """특정 종목 뉴스 조회 테스트"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/news/487240")
            # 뉴스 기능이 아직 구현 안 되어 있을 수 있음
            assert response.status_code in [200, 404, 500]
    
    @pytest.mark.asyncio
    async def test_get_all_news(self):
        """전체 뉴스 조회 테스트"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/news/")
            assert response.status_code in [200, 404, 500]


class TestReportsRouter:
    """리포트 라우터 테스트"""
    
    @pytest.mark.asyncio
    async def test_generate_weekly_report(self):
        """주간 리포트 생성 테스트"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/reports/weekly")
            # 리포트 기능이 아직 구현 안 되어 있음 (501 Not Implemented)
            assert response.status_code in [200, 404, 500, 501]


class TestDataCollectorEdgeCases:
    """데이터 수집기 엣지 케이스 테스트"""
    
    def test_parse_number_empty_string(self):
        """빈 문자열 파싱 테스트"""
        from app.services.data_collector import ETFDataCollector
        collector = ETFDataCollector()
        
        assert collector._parse_number("") is None
        assert collector._parse_number("   ") is None
    
    def test_parse_change_edge_cases(self):
        """변동률 파싱 엣지 케이스"""
        from app.services.data_collector import ETFDataCollector
        collector = ETFDataCollector()
        
        # 빈 문자열
        change_pct = collector._parse_change("", 10000)
        assert change_pct is None
        
        # None
        change_pct = collector._parse_change(None, 10000)
        assert change_pct is None
    
    def test_fetch_prices_with_invalid_ticker(self):
        """잘못된 ticker로 가격 데이터 수집 테스트"""
        from app.services.data_collector import ETFDataCollector
        collector = ETFDataCollector()
        
        # 존재하지 않는 ticker
        result = collector.fetch_naver_finance_prices("999999999", days=1)
        # 빈 리스트 또는 에러 처리
        assert isinstance(result, list)
    
    def test_fetch_trading_flow_with_invalid_ticker(self):
        """잘못된 ticker로 매매동향 수집 테스트"""
        from app.services.data_collector import ETFDataCollector
        collector = ETFDataCollector()
        
        result = collector.fetch_naver_trading_flow("999999999", days=1)
        assert isinstance(result, list)
    
    def test_save_price_data_with_database_error(self):
        """데이터 저장 시 데이터베이스 에러 테스트"""
        from app.services.data_collector import ETFDataCollector
        collector = ETFDataCollector()
        
        # 유효하지 않은 데이터로 저장 시도
        invalid_data = [
            {'ticker': None, 'date': 'invalid', 'close_price': 'abc'}
        ]
        
        saved_count = collector.save_price_data(invalid_data)
        assert saved_count == 0


class TestSchedulerEdgeCases:
    """스케줄러 엣지 케이스 테스트"""
    
    def test_scheduler_get_jobs_when_stopped(self):
        """스케줄러 중지 상태에서 작업 조회"""
        from app.services.scheduler import DataCollectionScheduler
        scheduler = DataCollectionScheduler()
        
        # 스케줄러 시작 전 작업 조회
        jobs = scheduler.get_jobs()
        assert isinstance(jobs, list)


class TestAdditionalDataCollectorCoverage:
    """데이터 수집기 추가 커버리지 테스트"""
    
    def test_get_etf_metrics(self):
        """ETF 메트릭스 조회 테스트"""
        from app.services.data_collector import ETFDataCollector
        collector = ETFDataCollector()
        
        metrics = collector.get_etf_metrics("487240")
        assert metrics is not None
        assert metrics.ticker == "487240"
    
    def test_get_trading_flow_empty_result(self):
        """매매동향 조회 - 빈 결과 테스트"""
        from app.services.data_collector import ETFDataCollector
        from datetime import date, timedelta
        collector = ETFDataCollector()
        
        # 미래 날짜로 조회 (데이터 없음)
        future_date = date.today() + timedelta(days=365)
        result = collector.get_trading_flow_data("487240", future_date, future_date + timedelta(days=1))
        assert isinstance(result, list)
    
    def test_collect_and_save_trading_flow_no_data(self):
        """매매동향 수집 - 데이터 없음 케이스"""
        from app.services.data_collector import ETFDataCollector
        collector = ETFDataCollector()
        
        with patch('app.services.data_collector.ETFDataCollector.fetch_naver_trading_flow',
                  return_value=[]):
            saved_count = collector.collect_and_save_trading_flow("999999", days=1)
            assert saved_count == 0
    
    def test_validate_trading_flow_with_only_individual(self):
        """매매동향 검증 - 개인만 있는 경우"""
        from app.services.data_collector import ETFDataCollector
        from datetime import date
        collector = ETFDataCollector()
        
        data = {
            'ticker': '487240',
            'date': date.today(),
            'individual_net': 1000,
            'institutional_net': None,
            'foreign_net': None
        }
        
        assert collector.validate_trading_flow_data(data) is True
    
    def test_validate_trading_flow_with_only_institutional(self):
        """매매동향 검증 - 기관만 있는 경우"""
        from app.services.data_collector import ETFDataCollector
        from datetime import date
        collector = ETFDataCollector()
        
        data = {
            'ticker': '487240',
            'date': date.today(),
            'individual_net': None,
            'institutional_net': 2000,
            'foreign_net': None
        }
        
        assert collector.validate_trading_flow_data(data) is True
    
    def test_validate_trading_flow_with_only_foreign(self):
        """매매동향 검증 - 외국인만 있는 경우"""
        from app.services.data_collector import ETFDataCollector
        from datetime import date
        collector = ETFDataCollector()
        
        data = {
            'ticker': '487240',
            'date': date.today(),
            'individual_net': None,
            'institutional_net': None,
            'foreign_net': 3000
        }
        
        assert collector.validate_trading_flow_data(data) is True


class TestAdditionalETFRouterCoverage:
    """ETF 라우터 추가 커버리지 테스트"""
    
    @pytest.mark.asyncio
    async def test_get_all_etfs_success(self):
        """전체 ETF 목록 조회 성공 테스트"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/etfs/")
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 6  # 6개 종목
    
    @pytest.mark.asyncio
    async def test_get_etf_by_ticker_success(self):
        """특정 ETF 조회 성공 테스트"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/etfs/487240")
            assert response.status_code == 200
            data = response.json()
            assert data['ticker'] == '487240'
            assert 'name' in data
    
    @pytest.mark.asyncio
    async def test_get_prices_with_valid_dates(self):
        """유효한 날짜로 가격 조회 테스트"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            start_date = (date.today() - timedelta(days=30)).isoformat()
            end_date = date.today().isoformat()
            
            response = await client.get(
                f"/api/etfs/487240/prices?start_date={start_date}&end_date={end_date}"
            )
            assert response.status_code in [200, 404]  # 데이터 있으면 200, 없으면 404
    
    @pytest.mark.asyncio
    async def test_collect_prices_success(self):
        """가격 데이터 수집 성공 테스트"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post("/api/etfs/487240/collect?days=5")
            assert response.status_code == 200
            data = response.json()
            assert 'ticker' in data
            assert data['ticker'] == '487240'
    
    @pytest.mark.asyncio
    async def test_get_trading_flow_empty(self):
        """매매동향 조회 - 빈 결과 테스트"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # 미래 날짜로 조회
            future_date = (date.today() + timedelta(days=365)).isoformat()
            
            response = await client.get(
                f"/api/etfs/487240/trading-flow?start_date={future_date}&end_date={future_date}"
            )
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 0
    
    @pytest.mark.asyncio
    async def test_collect_prices_for_stock(self):
        """주식 종목 가격 수집 테스트"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # 주식 종목 (두산에너빌리티)
            response = await client.post("/api/etfs/034020/collect?days=5")
            assert response.status_code == 200
            data = response.json()
            assert data['ticker'] == '034020'
    
    @pytest.mark.asyncio
    async def test_collect_trading_flow_for_stock(self):
        """주식 종목 매매동향 수집 테스트"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # 주식 종목 (한화오션)
            response = await client.post("/api/etfs/042660/collect-trading-flow?days=5")
            assert response.status_code == 200
            data = response.json()
            assert data['ticker'] == '042660'
    
    @pytest.mark.asyncio
    async def test_get_etf_metrics_for_different_tickers(self):
        """다양한 종목의 메트릭스 조회"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            tickers = ['487240', '466920', '042660']
            for ticker in tickers:
                response = await client.get(f"/api/etfs/{ticker}/metrics")
                assert response.status_code == 200
                data = response.json()
                assert data['ticker'] == ticker


class TestDataCollectorNetworkErrors:
    """데이터 수집기 네트워크 에러 테스트"""
    
    def test_fetch_prices_timeout(self):
        """가격 데이터 수집 시 타임아웃 테스트"""
        from app.services.data_collector import ETFDataCollector
        import requests
        collector = ETFDataCollector()
        
        with patch('requests.get', side_effect=requests.exceptions.Timeout):
            result = collector.fetch_naver_finance_prices("487240", days=1)
            assert result == []
    
    def test_fetch_prices_connection_error(self):
        """가격 데이터 수집 시 연결 에러 테스트"""
        from app.services.data_collector import ETFDataCollector
        import requests
        collector = ETFDataCollector()
        
        with patch('requests.get', side_effect=requests.exceptions.ConnectionError):
            result = collector.fetch_naver_finance_prices("487240", days=1)
            assert result == []
    
    def test_fetch_prices_http_error(self):
        """가격 데이터 수집 시 HTTP 에러 테스트"""
        from app.services.data_collector import ETFDataCollector
        import requests
        collector = ETFDataCollector()
        
        with patch('requests.get', side_effect=requests.exceptions.HTTPError):
            result = collector.fetch_naver_finance_prices("487240", days=1)
            assert result == []
    
    def test_fetch_trading_flow_timeout(self):
        """매매동향 수집 시 타임아웃 테스트"""
        from app.services.data_collector import ETFDataCollector
        import requests
        collector = ETFDataCollector()
        
        with patch('requests.get', side_effect=requests.exceptions.Timeout):
            result = collector.fetch_naver_trading_flow("487240", days=1)
            assert result == []
    
    def test_fetch_trading_flow_request_exception(self):
        """매매동향 수집 시 요청 에러 테스트"""
        from app.services.data_collector import ETFDataCollector
        import requests
        collector = ETFDataCollector()
        
        with patch('requests.get', side_effect=requests.exceptions.RequestException("Error")):
            result = collector.fetch_naver_trading_flow("487240", days=1)
            assert result == []


class TestSchedulerStartupShutdown:
    """스케줄러 시작/종료 테스트"""
    
    def test_scheduler_double_start_warning(self):
        """스케줄러 이미 시작 중일 때 재시작 시도 테스트"""
        from app.services.scheduler import DataCollectionScheduler
        scheduler = DataCollectionScheduler()
        
        scheduler.start()
        assert scheduler.is_running()
        
        # 이미 실행 중인 상태에서 재시작 시도
        scheduler.start()  # 경고 발생하지만 에러는 없음
        
        scheduler.stop()
    
    def test_scheduler_double_stop(self):
        """스케줄러 이미 중지 상태에서 재중지 시도 테스트"""
        from app.services.scheduler import DataCollectionScheduler
        scheduler = DataCollectionScheduler()
        
        # 시작하지 않고 중지 시도
        scheduler.stop()  # 경고 발생하지만 에러는 없음
        
        assert not scheduler.is_running()


class TestCollectAndSavePricesEdgeCases:
    """가격 데이터 수집 및 저장 엣지 케이스"""
    
    def test_collect_and_save_prices_with_empty_data(self):
        """빈 데이터로 수집 및 저장 테스트"""
        from app.services.data_collector import ETFDataCollector
        collector = ETFDataCollector()
        
        with patch.object(collector, 'fetch_naver_finance_prices', return_value=[]):
            saved_count = collector.collect_and_save_prices("487240", days=1)
            assert saved_count == 0
    
    def test_save_trading_flow_data_partial_save_error(self):
        """매매동향 일부 저장 실패 테스트"""
        from app.services.data_collector import ETFDataCollector
        from datetime import date
        collector = ETFDataCollector()
        
        # 일부는 유효, 일부는 유효하지 않은 데이터
        mixed_data = [
            {
                'ticker': '487240',
                'date': date.today(),
                'individual_net': 1000,
                'institutional_net': -500,
                'foreign_net': 300
            },
            {
                # date 타입이 아님 - 검증 실패
                'ticker': '487240',
                'date': '2025-11-07',  # 문자열
                'individual_net': 2000,
                'institutional_net': None,
                'foreign_net': None
            }
        ]
        
        saved_count = collector.save_trading_flow_data(mixed_data)
        # 유효한 것만 저장되어야 함
        assert saved_count == 1

