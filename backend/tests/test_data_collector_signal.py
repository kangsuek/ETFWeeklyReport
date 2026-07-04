"""ensure_recent_history() — 신호 감지용 데이터 갭 보충 헬퍼 테스트

Given-When-Then, 클래스 기반. collect/조회 메서드를 모킹해 요청 일수와
자기치유·판정 로직만 검증한다 (실제 스크레이핑/DB 없음).
"""
import pytest
from datetime import date, timedelta
from unittest.mock import patch, MagicMock
from app.services.data_collector import ETFDataCollector
from app.constants import DEFAULT_BACKFILL_DAYS, SIGNAL_MIN_DATA_DAYS


class TestEnsureRecentHistory:
    """ensure_recent_history() 갭 보충·자기치유·판정"""

    @pytest.fixture
    def collector(self):
        return ETFDataCollector()

    def _run(self, collector, status, range_side_effect):
        """collect/조회 메서드를 모킹하고 ensure_recent_history 실행.

        range_side_effect: get_price_data_range의 반환값(또는 순차 반환 리스트).
        """
        with patch('app.database.get_collection_status', return_value=status), \
                patch.object(collector, 'collect_and_save_prices', return_value=1) as m_price, \
                patch.object(collector, 'collect_and_save_trading_flow', return_value=1) as m_flow, \
                patch.object(collector, 'get_price_data_range') as m_range:
            if isinstance(range_side_effect, list):
                m_range.side_effect = range_side_effect
            else:
                m_range.return_value = range_side_effect
            result = collector.ensure_recent_history('487240')
        return result, m_price, m_flow

    def test_gap_five_days_requests_five(self, collector):
        """Given 마지막 수집 5일 전 When 실행 Then 5일치 가격·수급 요청"""
        # Given
        last = (date.today() - timedelta(days=5)).isoformat()
        status = {'last_price_date': last}
        full = {'min_date': None, 'max_date': None, 'count': 40}

        # When
        result, m_price, m_flow = self._run(collector, status, full)

        # Then
        assert result is True
        m_price.assert_called_once_with('487240', days=5)
        m_flow.assert_called_once_with('487240', days=5)

    def test_up_to_date_skips_collection(self, collector):
        """Given 오늘까지 수집됨(갭 0) When 실행 Then 수집 스킵, 판정만"""
        # Given
        status = {'last_price_date': date.today().isoformat()}
        full = {'min_date': None, 'max_date': None, 'count': 40}

        # When
        result, m_price, m_flow = self._run(collector, status, full)

        # Then
        assert result is True
        m_price.assert_not_called()
        m_flow.assert_not_called()

    def test_insufficient_rows_retries_backfill_then_false(self, collector):
        """Given 보충 후에도 행 부족 When 실행 Then 90일 백필 재시도 후 False"""
        # Given: 갭 없음(오늘 기준)이지만 행 수가 계속 부족
        status = {'last_price_date': date.today().isoformat()}
        low = {'min_date': None, 'max_date': None, 'count': 10}

        # When: 첫 판정·재판정 모두 10행
        result, m_price, m_flow = self._run(collector, status, [low, low])

        # Then: 자기치유 백필 1회, 최종 False
        assert result is False
        m_price.assert_called_once_with('487240', days=DEFAULT_BACKFILL_DAYS)
        m_flow.assert_called_once_with('487240', days=DEFAULT_BACKFILL_DAYS)

    def test_insufficient_then_recovers_true(self, collector):
        """Given 부족했다가 백필 후 충족 When 실행 Then True"""
        # Given
        status = {'last_price_date': date.today().isoformat()}
        low = {'min_date': None, 'max_date': None, 'count': 10}
        ok = {'min_date': None, 'max_date': None, 'count': SIGNAL_MIN_DATA_DAYS}

        # When
        result, m_price, _ = self._run(collector, status, [low, ok])

        # Then
        assert result is True
        m_price.assert_called_once_with('487240', days=DEFAULT_BACKFILL_DAYS)

    def test_new_ticker_uses_default_backfill(self, collector):
        """Given 수집 이력 없음 When 실행 Then 기본 백필 일수로 초기 수집"""
        # Given
        status = None
        full = {'min_date': None, 'max_date': None, 'count': 90}

        # When
        result, m_price, m_flow = self._run(collector, status, full)

        # Then
        assert result is True
        m_price.assert_called_once_with('487240', days=DEFAULT_BACKFILL_DAYS)
        m_flow.assert_called_once_with('487240', days=DEFAULT_BACKFILL_DAYS)


class TestTradingFlowStatusRecording:
    """_collect_single_ticker의 매매동향 수집 상태 기록 정확성 (Phase 1.3)"""

    @pytest.fixture
    def collector(self):
        return ETFDataCollector()

    def _run(self, collector, flow_return=None, flow_error=None):
        """가격은 성공 고정, 매매동향 결과만 바꿔가며 _collect_single_ticker 실행.

        Returns: update_collection_status 모킹 객체
        """
        etf = MagicMock()
        etf.name = '테스트'
        with patch('app.database.update_collection_status') as m_status, \
                patch.object(collector, 'get_etf_info', return_value=etf), \
                patch.object(collector, 'collect_and_save_prices', return_value=5), \
                patch.object(collector, 'collect_and_save_trading_flow') as m_flow, \
                patch.object(collector.news_scraper, 'collect_and_save_news',
                             return_value={'collected': 0}):
            if flow_error is not None:
                m_flow.side_effect = flow_error
            else:
                m_flow.return_value = flow_return
            collector._collect_single_ticker('487240', days=1)
        return m_status

    def test_flow_success_records_date(self, collector):
        """Given 매매동향 수집 성공 When 수집 Then trading_flow_date·success=True 기록"""
        # When
        m_status = self._run(collector, flow_return=3)

        # Then: 매매동향 날짜와 성공이 기록됨
        flow_calls = [
            c for c in m_status.call_args_list
            if c.kwargs.get('trading_flow_date')
        ]
        assert len(flow_calls) == 1
        assert flow_calls[0].kwargs['trading_flow_date'] == date.today().isoformat()
        assert flow_calls[0].kwargs['success'] is True

    def test_flow_failure_records_failure(self, collector):
        """Given 매매동향 수집 예외 When 수집 Then success=False로 실패 기록(무음 금지)"""
        # When
        m_status = self._run(collector, flow_error=Exception("network"))

        # Then: success=False 호출이 존재해야 함
        fail_calls = [
            c for c in m_status.call_args_list
            if c.kwargs.get('success') is False
        ]
        assert len(fail_calls) >= 1
