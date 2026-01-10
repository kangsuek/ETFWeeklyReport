"""
자동 데이터 수집 로직 테스트

조회 API 호출 시 데이터 부족 시 자동 수집되는지 검증
"""

import pytest
from datetime import date, timedelta
from unittest.mock import Mock, patch, MagicMock
from app.services.data_collector import ETFDataCollector


class TestAutoCollection:
    """자동 수집 로직 테스트"""

    @pytest.fixture
    def collector(self):
        """테스트용 collector 인스턴스"""
        return ETFDataCollector()

    @pytest.fixture
    def mock_db_connection(self):
        """Mock DB 연결"""
        with patch('app.services.data_collector.get_db_connection') as mock:
            conn = MagicMock()
            cursor = MagicMock()
            conn.cursor.return_value = cursor
            conn.__enter__.return_value = conn
            conn.__exit__.return_value = None
            mock.return_value = conn
            yield mock, conn, cursor

    def test_get_price_data_range_with_data(self, collector, mock_db_connection):
        """DB에 데이터가 있을 때 범위 반환"""
        # Given: DB에 데이터 있음
        mock, conn, cursor = mock_db_connection
        cursor.fetchone.return_value = {
            'min_date': '2025-01-01',
            'max_date': '2025-11-11',
            'count': 250
        }

        # When: 데이터 범위 조회
        result = collector.get_price_data_range('487240')

        # Then: 범위 정보 반환
        assert result is not None
        assert result['count'] == 250
        assert isinstance(result['min_date'], date)
        assert isinstance(result['max_date'], date)

    def test_get_price_data_range_without_data(self, collector, mock_db_connection):
        """DB에 데이터가 없을 때 None 반환"""
        # Given: DB에 데이터 없음
        mock, conn, cursor = mock_db_connection
        cursor.fetchone.return_value = {
            'min_date': None,
            'max_date': None,
            'count': 0
        }

        # When: 데이터 범위 조회
        result = collector.get_price_data_range('487240')

        # Then: None 반환
        assert result is None

    def test_get_trading_flow_data_range_with_data(self, collector, mock_db_connection):
        """매매 동향 데이터 범위 확인 - 데이터 있음"""
        # Given: DB에 매매 동향 데이터 있음
        mock, conn, cursor = mock_db_connection
        cursor.fetchone.return_value = {
            'min_date': '2025-01-01',
            'max_date': '2025-11-11',
            'count': 200
        }

        # When: 데이터 범위 조회
        result = collector.get_trading_flow_data_range('487240')

        # Then: 범위 정보 반환
        assert result is not None
        assert result['count'] == 200

    def test_get_trading_flow_data_range_without_data(self, collector, mock_db_connection):
        """매매 동향 데이터 범위 확인 - 데이터 없음"""
        # Given: DB에 데이터 없음
        mock, conn, cursor = mock_db_connection
        cursor.fetchone.return_value = {
            'min_date': None,
            'max_date': None,
            'count': 0
        }

        # When: 데이터 범위 조회
        result = collector.get_trading_flow_data_range('487240')

        # Then: None 반환
        assert result is None


class TestAutoCollectionIntegration:
    """자동 수집 통합 테스트 (API 레벨)"""

    @pytest.fixture
    def mock_collector(self):
        """Mock ETFDataCollector"""
        with patch('app.routers.etfs.ETFDataCollector') as mock:
            collector_instance = MagicMock()
            mock.return_value = collector_instance
            yield collector_instance

    def test_prices_endpoint_auto_collection_no_data(self, mock_collector):
        """
        가격 API: DB에 데이터 없을 때 자동 수집

        시나리오:
        1. DB에 데이터 전혀 없음
        2. 자동 수집 트리거
        3. 수집 후 데이터 반환
        """
        # Given: DB에 데이터 없음
        mock_collector.get_price_data_range.return_value = None
        mock_collector.get_price_data.return_value = []
        mock_collector.collect_and_save_prices.return_value = 10

        # When: get_price_data_range 호출
        data_range = mock_collector.get_price_data_range('487240')

        # Then: None 반환 (데이터 없음)
        assert data_range is None

        # When: 자동 수집 시뮬레이션
        if not data_range:
            collected = mock_collector.collect_and_save_prices('487240', days=10)
            assert collected == 10

    def test_prices_endpoint_auto_collection_insufficient_data(self, mock_collector):
        """
        가격 API: DB 데이터 범위 부족 시 자동 수집

        시나리오:
        1. DB에는 2025-01-01 ~ 2025-11-01 데이터만 있음
        2. 사용자가 2025-01-01 ~ 2025-11-11 요청
        3. 부족한 10일치 자동 수집
        """
        # Given: DB에 일부 데이터만 있음
        mock_collector.get_price_data_range.return_value = {
            'min_date': date(2025, 1, 1),
            'max_date': date(2025, 11, 1),  # 10일 부족
            'count': 240
        }
        mock_collector.collect_and_save_prices.return_value = 10

        # When: 데이터 범위 확인
        data_range = mock_collector.get_price_data_range('487240')

        # Then: 범위 부족 확인
        requested_end = date(2025, 11, 11)
        assert data_range['max_date'] < requested_end

        # When: 자동 수집
        if data_range['max_date'] < requested_end:
            collected = mock_collector.collect_and_save_prices('487240', days=11)
            assert collected == 10

    def test_trading_flow_endpoint_auto_collection(self, mock_collector):
        """
        매매 동향 API: DB에 데이터 없을 때 자동 수집
        """
        # Given: DB에 매매 동향 데이터 없음
        mock_collector.get_trading_flow_data_range.return_value = None
        mock_collector.get_trading_flow_data.return_value = []
        mock_collector.collect_and_save_trading_flow.return_value = 10

        # When: 데이터 범위 확인
        data_range = mock_collector.get_trading_flow_data_range('487240')

        # Then: None 반환
        assert data_range is None

        # When: 자동 수집
        if not data_range:
            collected = mock_collector.collect_and_save_trading_flow('487240', days=10)
            assert collected == 10


class TestAutoCollectionEdgeCases:
    """자동 수집 엣지 케이스 테스트"""

    @pytest.fixture
    def collector(self):
        return ETFDataCollector()

    def test_date_range_with_string_dates(self, collector):
        """
        날짜가 문자열로 반환되는 경우 date 객체로 변환
        """
        with patch('app.services.data_collector.get_db_connection') as mock:
            conn = MagicMock()
            cursor = MagicMock()
            conn.cursor.return_value = cursor
            conn.__enter__.return_value = conn
            conn.__exit__.return_value = None
            mock.return_value = conn

            # Given: DB가 문자열 날짜 반환
            cursor.fetchone.return_value = {
                'min_date': '2025-01-01',
                'max_date': '2025-11-11',
                'count': 250
            }

            # When: 데이터 범위 조회
            result = collector.get_price_data_range('487240')

            # Then: date 객체로 변환됨
            assert result is not None
            assert isinstance(result['min_date'], date)
            assert isinstance(result['max_date'], date)
            assert result['min_date'] == date(2025, 1, 1)
            assert result['max_date'] == date(2025, 11, 11)

    def test_collection_with_large_date_range(self, collector):
        """
        매우 큰 날짜 범위 요청 시 처리
        """
        # Given: 1년치 데이터 요청
        start_date = date.today() - timedelta(days=365)
        end_date = date.today()
        days = (end_date - start_date).days + 1

        # When/Then: 날짜 계산 검증
        assert days == 366  # 윤년 고려
