"""신호 스캔 스케줄러 잡 + 앱 시작 따라잡기 테스트 (Phase 2.6)

크론 잡(run_signal_scan)·따라잡기(_run_signal_scan_catchup)·잡 등록
(_run_signal_scan_if_needed)을 모킹으로 검증한다. Given-When-Then.
"""
from datetime import datetime
from unittest.mock import patch

import pytz

from app.services.scheduler import DataCollectionScheduler

KST = pytz.timezone("Asia/Seoul")


class TestRunSignalScan:
    """평일 16:40 크론 잡"""

    def test_calls_scan_all(self):
        """Given uptrend 규칙 없음 When run_signal_scan Then scan_all 호출"""
        scheduler = DataCollectionScheduler()
        with patch("app.services.signal_detector._get_active_signal_rules",
                   return_value=[]), \
                patch("app.services.signal_detector.scan_all",
                      return_value={"scanned": 0}) as m_scan:
            scheduler.run_signal_scan()
        m_scan.assert_called_once()

    def test_refetches_today_then_scans(self):
        """Given uptrend 규칙 존재 When run_signal_scan Then 당일 재수집 후 scan_all"""
        scheduler = DataCollectionScheduler()
        with patch("app.services.signal_detector._get_active_signal_rules",
                   return_value=[{"id": 1, "ticker": "005930"}]), \
                patch("app.services.signal_detector.scan_all") as m_scan, \
                patch.object(scheduler.collector, "collect_and_save_prices") as m_p, \
                patch.object(scheduler.collector, "collect_and_save_trading_flow") as m_f:
            scheduler.run_signal_scan()
        m_p.assert_called_once_with("005930", days=1)
        m_f.assert_called_once_with("005930", days=1)
        m_scan.assert_called_once()


class TestCatchup:
    """앱 시작 따라잡기"""

    def test_passes_since(self):
        """Given since When 따라잡기 Then scan_all에 since 전달"""
        scheduler = DataCollectionScheduler()
        with patch("app.services.signal_detector.scan_all") as m_scan:
            scheduler._run_signal_scan_catchup(since="2026-01-01")
        assert m_scan.call_args.kwargs["since"] == "2026-01-01"

    def test_after_1640_includes_today(self):
        """Given 16:40 이후 기동 When 따라잡기 Then until=None(오늘 포함)"""
        scheduler = DataCollectionScheduler()
        fake_now = datetime(2026, 7, 6, 17, 0, tzinfo=KST)
        with patch("app.services.scheduler.datetime") as m_dt, \
                patch("app.services.signal_detector.scan_all") as m_scan:
            m_dt.now.return_value = fake_now
            scheduler._run_signal_scan_catchup(since=None)
        assert m_scan.call_args.kwargs["until"] is None

    def test_before_1640_excludes_today(self):
        """Given 16:40 이전 기동 When 따라잡기 Then until 지정(오늘 제외)"""
        scheduler = DataCollectionScheduler()
        fake_now = datetime(2026, 7, 6, 10, 0, tzinfo=KST)
        with patch("app.services.scheduler.datetime") as m_dt, \
                patch("app.services.signal_detector.scan_all") as m_scan:
            m_dt.now.return_value = fake_now
            scheduler._run_signal_scan_catchup(since=None)
        assert m_scan.call_args.kwargs["until"] is not None


class TestRegistration:
    """따라잡기 잡 등록"""

    def test_registers_background_job(self):
        """Given 마커 존재 When _run_signal_scan_if_needed Then 1회성 잡 등록"""
        scheduler = DataCollectionScheduler()
        with patch("app.database.get_app_state", return_value="2026-01-01"), \
                patch.object(scheduler.scheduler, "add_job") as m_add:
            scheduler._run_signal_scan_if_needed()
        m_add.assert_called_once()
        assert m_add.call_args.kwargs["id"] == "signal_scan_catchup"
        assert m_add.call_args.kwargs["kwargs"] == {"since": "2026-01-01"}


class TestStartSmoke:
    """앱 기동 스모크 — 크론 잡 등록"""

    def test_start_registers_signal_scan_cron(self):
        """Given start When 기동 Then signal_scan 크론 잡 등록(즉시수집·따라잡기는 모킹)"""
        scheduler = DataCollectionScheduler()
        with patch.object(scheduler, "collect_periodic_data"), \
                patch.object(scheduler, "_collect_fundamentals_if_needed"), \
                patch.object(scheduler, "_run_signal_scan_if_needed"):
            scheduler.start()
            try:
                job_ids = [j["id"] for j in scheduler.get_jobs()]
                assert "signal_scan" in job_ids
            finally:
                scheduler.stop()
