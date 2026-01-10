"""
배치 쿼리 성능 및 기능 테스트 (Phase 7.4)
"""

import pytest
from datetime import date, timedelta
from app.services.data_collector import ETFDataCollector
from app.models import PriceData


class TestBatchQueries:
    """배치 쿼리 테스트"""

    @pytest.fixture
    def collector(self):
        """데이터 수집기 인스턴스"""
        return ETFDataCollector()

    @pytest.fixture
    def test_tickers(self):
        """테스트용 종목 코드"""
        return ["487240", "466920", "042660"]

    @pytest.fixture
    def date_range(self):
        """테스트용 날짜 범위"""
        end_date = date.today()
        start_date = end_date - timedelta(days=7)
        return start_date, end_date

    def test_get_price_data_batch_basic(self, collector, test_tickers, date_range):
        """배치 가격 조회 기본 기능 테스트"""
        start_date, end_date = date_range

        # 배치 조회
        result = collector.get_price_data_batch(test_tickers, start_date, end_date)

        # 검증
        assert isinstance(result, dict)
        assert len(result) == len(test_tickers)

        for ticker in test_tickers:
            assert ticker in result
            assert isinstance(result[ticker], list)
            # 각 항목은 PriceData 타입이어야 함
            for price_data in result[ticker]:
                assert isinstance(price_data, PriceData)

    def test_get_price_data_batch_with_limit(self, collector, test_tickers, date_range):
        """배치 가격 조회 limit 파라미터 테스트"""
        start_date, end_date = date_range
        limit = 3

        # 배치 조회
        result = collector.get_price_data_batch(test_tickers, start_date, end_date, limit=limit)

        # 검증 - 각 종목별로 최대 limit 개수만 반환
        for ticker in test_tickers:
            assert len(result[ticker]) <= limit

    def test_get_price_data_batch_empty_tickers(self, collector, date_range):
        """빈 종목 리스트로 배치 조회 테스트"""
        start_date, end_date = date_range

        result = collector.get_price_data_batch([], start_date, end_date)

        assert result == {}

    def test_get_trading_flow_batch_basic(self, collector, test_tickers, date_range):
        """배치 매매동향 조회 기본 기능 테스트"""
        start_date, end_date = date_range

        # 배치 조회
        result = collector.get_trading_flow_batch(test_tickers, start_date, end_date)

        # 검증
        assert isinstance(result, dict)
        assert len(result) == len(test_tickers)

        for ticker in test_tickers:
            assert ticker in result
            assert isinstance(result[ticker], list)
            # 각 항목은 dict 타입이어야 함
            for flow_data in result[ticker]:
                assert isinstance(flow_data, dict)
                assert "date" in flow_data
                assert "individual_net" in flow_data
                assert "institutional_net" in flow_data
                assert "foreign_net" in flow_data

    def test_get_trading_flow_batch_with_limit(self, collector, test_tickers, date_range):
        """배치 매매동향 조회 limit 파라미터 테스트"""
        start_date, end_date = date_range
        limit = 2

        # 배치 조회
        result = collector.get_trading_flow_batch(test_tickers, start_date, end_date, limit=limit)

        # 검증 - 각 종목별로 최대 limit 개수만 반환
        for ticker in test_tickers:
            assert len(result[ticker]) <= limit

    def test_get_latest_prices_batch_basic(self, collector, test_tickers):
        """배치 최신 가격 조회 기본 기능 테스트"""
        # 배치 조회
        result = collector.get_latest_prices_batch(test_tickers)

        # 검증
        assert isinstance(result, dict)
        assert len(result) == len(test_tickers)

        for ticker in test_tickers:
            assert ticker in result
            # 데이터가 있으면 PriceData, 없으면 None
            if result[ticker] is not None:
                assert isinstance(result[ticker], PriceData)

    def test_batch_vs_single_query_consistency(self, collector, test_tickers, date_range):
        """배치 쿼리와 단일 쿼리 결과 일관성 테스트"""
        start_date, end_date = date_range

        # 배치 쿼리
        batch_result = collector.get_price_data_batch(test_tickers, start_date, end_date)

        # 단일 쿼리 (각각 조회)
        single_results = {}
        for ticker in test_tickers:
            single_results[ticker] = collector.get_price_data(ticker, start_date, end_date)

        # 검증 - 결과가 동일해야 함
        for ticker in test_tickers:
            assert len(batch_result[ticker]) == len(single_results[ticker])
            # 첫 번째 항목 비교 (최신 데이터)
            if batch_result[ticker] and single_results[ticker]:
                batch_first = batch_result[ticker][0]
                single_first = single_results[ticker][0]
                assert batch_first.date == single_first.date
                assert batch_first.close_price == single_first.close_price


class TestQueryLimits:
    """쿼리 결과 크기 제한 테스트"""

    @pytest.fixture
    def collector(self):
        """데이터 수집기 인스턴스"""
        return ETFDataCollector()

    def test_get_price_data_with_limit(self, collector):
        """가격 데이터 조회 limit 파라미터 테스트"""
        ticker = "487240"
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
        limit = 5

        # limit 적용 조회
        result = collector.get_price_data(ticker, start_date, end_date, limit=limit)

        # 검증
        assert len(result) <= limit

    def test_get_trading_flow_with_limit(self, collector):
        """매매동향 조회 limit 파라미터 테스트"""
        ticker = "487240"
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
        limit = 3

        # limit 적용 조회
        result = collector.get_trading_flow(ticker, start_date, end_date, limit=limit)

        # 검증
        assert len(result) <= limit


class TestConnectionPool:
    """Connection Pool 테스트"""

    def test_connection_pool_basic(self):
        """Connection Pool 기본 동작 테스트"""
        from app.database import get_connection_pool

        pool = get_connection_pool()

        # Connection 가져오기
        conn = pool.get_connection()
        assert conn is not None

        # Connection 반환
        pool.return_connection(conn)

        # 재사용 확인
        conn2 = pool.get_connection()
        assert conn2 is not None

    def test_connection_pool_multiple_connections(self):
        """Connection Pool 복수 연결 테스트"""
        from app.database import get_connection_pool

        pool = get_connection_pool()

        # 여러 연결 가져오기
        connections = []
        for _ in range(3):
            conn = pool.get_connection()
            connections.append(conn)
            assert conn is not None

        # 모두 반환
        for conn in connections:
            pool.return_connection(conn)

    def test_get_db_connection_context_manager(self):
        """get_db_connection context manager 테스트"""
        from app.database import get_db_connection

        # Context manager 사용
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM etfs")
            count = cursor.fetchone()[0]
            assert count >= 0

        # Connection이 자동으로 반환되었는지 확인 (에러 없이 실행되면 성공)
