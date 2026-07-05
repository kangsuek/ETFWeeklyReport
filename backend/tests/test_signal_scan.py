"""scan_all 통합 테스트 (Phase 2.3) — 소급 재생·상태 관리·알림 발신.

합성 가격/수급을 DB에 넣고 scan_all을 실행해 signal_events·alert_history·
마커(app_state)·쿨다운 게이트를 검증한다. ensure_recent_history(네트워크)는
모킹한다. Given-When-Then.
"""
from datetime import date, timedelta
from unittest.mock import patch

import pytest

from app.database import (
    init_db, get_db_connection, get_app_state, set_app_state,
)
from app.services.signal_detector import (
    PriceBar, scan_all, _emit_signal_alert, evaluate_watchlist, scan_ticker,
)

BASE = date(2026, 1, 1)


def _valid_ticker():
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT ticker FROM etfs LIMIT 1")
        row = cur.fetchone()
        return row[0]


@pytest.fixture(autouse=True)
def clean(request):
    """테스트 대상 테이블을 비운다 (세션 공유 DB 격리)."""
    init_db()
    with get_db_connection() as conn:
        cur = conn.cursor()
        for t in ("signal_events", "alert_history", "alert_rules",
                  "prices", "trading_flow", "app_state"):
            cur.execute(f"DELETE FROM {t}")
        conn.commit()
    yield


def _insert_prices(ticker, bars):
    with get_db_connection() as conn:
        cur = conn.cursor()
        for d, o, h, low, c, v in bars:
            cur.execute(
                """INSERT OR REPLACE INTO prices
                   (ticker, date, open_price, high_price, low_price,
                    close_price, volume, daily_change_pct)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 0.0)""",
                (ticker, d.isoformat(), o, h, low, c, v),
            )
        conn.commit()


def _insert_flows(ticker, dates, net=500):
    with get_db_connection() as conn:
        cur = conn.cursor()
        for d in dates:
            cur.execute(
                """INSERT OR REPLACE INTO trading_flow
                   (ticker, date, individual_net, institutional_net, foreign_net)
                   VALUES (?, ?, 0, ?, ?)""",
                (ticker, d.isoformat(), net // 2, net - net // 2),
            )
        conn.commit()


def _create_uptrend_rule(ticker):
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO alert_rules (ticker, alert_type, direction, target_price, is_active)
               VALUES (?, 'uptrend', 'up', 0, 1)""",
            (ticker,),
        )
        conn.commit()
        return cur.lastrowid


def _confirm_series():
    """C2(연속 유지)로 day30 돌파 → day32 확정되는 33거래일 시리즈."""
    bars = [(BASE + timedelta(days=i), 100, 100, 100, 100, 1000) for i in range(30)]
    bars.append((BASE + timedelta(days=30), 101, 105, 101, 104, 2500))  # 돌파
    bars.append((BASE + timedelta(days=31), 103, 104, 102.5, 103, 1200))
    bars.append((BASE + timedelta(days=32), 103, 104, 102.5, 103, 1200))  # 확정
    return bars


def _all_dates(bars):
    return [b[0] for b in bars]


class TestScanAllIntegration:

    def test_replay_creates_confirmed_and_alert(self):
        """Given 확정 시리즈 When scan_all Then confirmed 이벤트·uptrend 알림·마커 갱신"""
        ticker = _valid_ticker()
        bars = _confirm_series()
        _insert_prices(ticker, bars)
        _insert_flows(ticker, _all_dates(bars))
        rule_id = _create_uptrend_rule(ticker)

        with patch(
            "app.services.data_collector.ETFDataCollector.ensure_recent_history",
            return_value=True,
        ):
            result = scan_all(since=None)

        assert result["scanned"] == 1
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT status, confirm_path, confirmed_date FROM signal_events WHERE ticker=?",
                (ticker,),
            )
            ev = cur.fetchone()
            assert ev["status"] == "confirmed"
            assert ev["confirm_path"] == "hold"
            assert str(ev["confirmed_date"])[:10] == (BASE + timedelta(days=32)).isoformat()

            cur.execute(
                "SELECT alert_type, message, triggered_at FROM alert_history WHERE rule_id=?",
                (rule_id,),
            )
            alerts = cur.fetchall()
            assert len(alerts) == 1
            assert alerts[0]["alert_type"] == "uptrend"
            assert "연속 유지" in alerts[0]["message"]

            cur.execute("SELECT last_triggered_at FROM alert_rules WHERE id=?", (rule_id,))
            assert cur.fetchone()["last_triggered_at"] is not None

        assert get_app_state("last_signal_scan_date") == (BASE + timedelta(days=32)).isoformat()

    def test_idempotent_rerun(self):
        """Given 1회 스캔 후 재실행 When scan_all Then 이벤트·알림 중복 없음"""
        ticker = _valid_ticker()
        bars = _confirm_series()
        _insert_prices(ticker, bars)
        _insert_flows(ticker, _all_dates(bars))
        rule_id = _create_uptrend_rule(ticker)

        with patch(
            "app.services.data_collector.ETFDataCollector.ensure_recent_history",
            return_value=True,
        ):
            scan_all(since=None)
            scan_all(since=None)  # 재실행

        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) c FROM signal_events WHERE ticker=?", (ticker,))
            assert cur.fetchone()["c"] == 1
            cur.execute("SELECT COUNT(*) c FROM alert_history WHERE rule_id=?", (rule_id,))
            assert cur.fetchone()["c"] == 1

    def test_old_confirm_suppressed_state_only(self):
        """Given 신선도 초과 확정(소급) When scan_all Then 상태만 기록·알림 억제"""
        ticker = _valid_ticker()
        bars = _confirm_series()  # day30 돌파 → day32 확정
        # 확정 뒤 평탄한 거래일 12개 추가 → 확정이 최신에서 12거래일 전(> FRESH 10)
        for k in range(1, 13):
            bars.append((BASE + timedelta(days=32 + k), 101, 101, 101, 101, 1000))
        _insert_prices(ticker, bars)
        _insert_flows(ticker, _all_dates(bars))
        rule_id = _create_uptrend_rule(ticker)

        with patch(
            "app.services.data_collector.ETFDataCollector.ensure_recent_history",
            return_value=True,
        ):
            scan_all(since=None)

        with get_db_connection() as conn:
            cur = conn.cursor()
            # 상태(signal_events)는 confirmed로 기록
            cur.execute("SELECT status FROM signal_events WHERE ticker=?", (ticker,))
            assert cur.fetchone()["status"] == "confirmed"
            # 사용자 알림은 억제 (오래된 확정)
            cur.execute("SELECT COUNT(*) c FROM alert_history WHERE rule_id=?", (rule_id,))
            assert cur.fetchone()["c"] == 0
            cur.execute("SELECT last_triggered_at FROM alert_rules WHERE id=?", (rule_id,))
            assert cur.fetchone()["last_triggered_at"] is None

    def test_partial_failure_keeps_marker(self):
        """Given 스캔 중 예외 When scan_all Then 마커 미갱신(다음 기동 재따라잡기)"""
        ticker = _valid_ticker()
        _create_uptrend_rule(ticker)
        set_app_state("last_signal_scan_date", "2026-01-01")

        with patch(
            "app.services.data_collector.ETFDataCollector.ensure_recent_history",
            side_effect=Exception("boom"),
        ):
            result = scan_all(since=None)

        assert result["failed"] == 1
        assert get_app_state("last_signal_scan_date") == "2026-01-01"  # 불변


class TestCooldownGate:
    """LV2 확정 알림의 쿨다운 게이트 (§3-4)"""

    def _prices(self, n=40):
        return [PriceBar(date=BASE + timedelta(days=i), open=100, high=100,
                         low=100, close=100, volume=1000) for i in range(n)]

    def test_suppressed_within_cooldown(self):
        """Given 직전 확정이 쿨다운(20거래일) 이내 When 발신 Then 억제(False)"""
        ticker = _valid_ticker()
        rule_id = _create_uptrend_rule(ticker)
        prices = self._prices()
        # 직전 확정일 = index 10
        set_last = prices[10].date.isoformat()
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE alert_rules SET last_triggered_at=? WHERE id=?",
                        (set_last, rule_id))
            conn.commit()

        # 새 확정 index 20 → 거리 10 < 20 → 억제
        emitted = _emit_signal_alert(rule_id, ticker, "종목", 100.0, "hold",
                                     prices[20].date, prices, 20)

        assert emitted is False
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) c FROM alert_history WHERE rule_id=?", (rule_id,))
            assert cur.fetchone()["c"] == 0
            cur.execute("SELECT last_triggered_at t FROM alert_rules WHERE id=?", (rule_id,))
            assert str(cur.fetchone()["t"])[:10] == prices[10].date.isoformat()  # 불변

    def test_allowed_after_cooldown(self):
        """Given 직전 확정이 쿨다운 밖 When 발신 Then 기록(True)"""
        ticker = _valid_ticker()
        rule_id = _create_uptrend_rule(ticker)
        prices = self._prices()
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE alert_rules SET last_triggered_at=? WHERE id=?",
                        (prices[10].date.isoformat(), rule_id))
            conn.commit()

        # 새 확정 index 31 → 거리 21 ≥ 20 → 허용
        emitted = _emit_signal_alert(rule_id, ticker, "종목", 100.0, "hold",
                                     prices[31].date, prices, 31)

        assert emitted is True
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) c FROM alert_history WHERE rule_id=?", (rule_id,))
            assert cur.fetchone()["c"] == 1


class TestWatchlistAndSingleScan:
    """A: 관심종목 일괄 점검(읽기 전용) · B: 단일 종목 즉시 스캔"""

    def test_evaluate_watchlist_reports_without_writing(self):
        """Given 확정 시리즈 When 일괄 점검 Then 상태 리포트·signal_events 미기록"""
        ticker = _valid_ticker()
        bars = _confirm_series()
        _insert_prices(ticker, bars)
        _insert_flows(ticker, _all_dates(bars))

        results = evaluate_watchlist()

        entry = next((r for r in results if r["ticker"] == ticker), None)
        assert entry is not None
        assert entry["status"] == "confirmed"
        assert entry["latest"]["confirm_path"] == "hold"
        # 읽기 전용 — signal_events 미기록
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) c FROM signal_events")
            assert cur.fetchone()["c"] == 0

    def test_evaluate_watchlist_downgrades_stale_confirm(self):
        """Given 오래된 확정 When 일괄 점검 Then status='none'(지금 아님), latest는 유지"""
        ticker = _valid_ticker()
        bars = _confirm_series()  # day32 확정
        for k in range(1, 13):  # 확정 뒤 12거래일 → 신선도(10) 초과
            bars.append((BASE + timedelta(days=32 + k), 101, 101, 101, 101, 1000))
        _insert_prices(ticker, bars)
        _insert_flows(ticker, _all_dates(bars))

        results = evaluate_watchlist()
        entry = next((r for r in results if r["ticker"] == ticker), None)
        assert entry is not None
        assert entry["status"] == "none"  # 지금 상태는 아님
        assert entry["latest"]["status"] == "confirmed"  # 원본 이벤트는 보존

    def test_evaluate_watchlist_insufficient_data(self):
        """Given 데이터 부족 종목 When 일괄 점검 Then insufficient_data"""
        ticker = _valid_ticker()
        results = evaluate_watchlist()
        entry = next((r for r in results if r["ticker"] == ticker), None)
        assert entry is not None
        assert entry["status"] == "insufficient_data"

    def test_scan_ticker_writes_when_rule_active(self):
        """Given 활성 규칙+확정 시리즈 When 단일 스캔 Then signal_events 기록"""
        ticker = _valid_ticker()
        bars = _confirm_series()
        _insert_prices(ticker, bars)
        _insert_flows(ticker, _all_dates(bars))
        _create_uptrend_rule(ticker)

        with patch(
            "app.services.data_collector.ETFDataCollector.ensure_recent_history",
            return_value=True,
        ):
            result = scan_ticker(ticker)

        assert result["scanned"] is True
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT status FROM signal_events WHERE ticker=?", (ticker,))
            row = cur.fetchone()
            assert row is not None and row["status"] == "confirmed"

    def test_scan_ticker_noop_without_rule(self):
        """Given 활성 규칙 없음 When 단일 스캔 Then scanned=False"""
        ticker = _valid_ticker()
        result = scan_ticker(ticker)
        assert result == {"scanned": False, "reason": "no_active_rule"}


def _create_downtrend_rule(ticker):
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO alert_rules (ticker, alert_type, direction, target_price, is_active)
               VALUES (?, 'downtrend', 'down', 0, 1)""",
            (ticker,),
        )
        conn.commit()
        return cur.lastrowid


def _down_confirm_series():
    """C2(연속 유지)로 day30 하향 이탈 → day32 확정되는 33거래일 시리즈."""
    bars = [(BASE + timedelta(days=i), 100, 100, 100, 100, 1000) for i in range(30)]
    bars.append((BASE + timedelta(days=30), 99, 99, 95, 95.5, 2500))  # 이탈
    bars.append((BASE + timedelta(days=31), 96, 97, 95, 96, 1200))
    bars.append((BASE + timedelta(days=32), 96, 97, 95, 96, 1200))    # 확정
    return bars


class TestDowntrendScan:
    """하락흐름 스캔 — 상승과 같은 엔진의 거울상"""

    def test_downtrend_confirms_and_alerts(self):
        """Given 하향 이탈 시리즈+downtrend 규칙 When scan_all Then 하락 확정·알림"""
        ticker = _valid_ticker()
        bars = _down_confirm_series()
        _insert_prices(ticker, bars)
        _insert_flows(ticker, _all_dates(bars), net=-500)
        rule_id = _create_downtrend_rule(ticker)

        with patch(
            "app.services.data_collector.ETFDataCollector.ensure_recent_history",
            return_value=True,
        ):
            scan_all(since=None)

        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT status, confirm_path, direction FROM signal_events WHERE ticker=?",
                (ticker,),
            )
            ev = cur.fetchone()
            assert ev["status"] == "confirmed"
            assert ev["direction"] == "down"
            assert ev["confirm_path"] == "hold"

            cur.execute(
                "SELECT alert_type, message FROM alert_history WHERE rule_id=?", (rule_id,)
            )
            alert = cur.fetchone()
            assert alert["alert_type"] == "downtrend"
            assert "하락흐름 확정" in alert["message"]

    def test_evaluate_watchlist_down_direction(self):
        """Given 하향 이탈 시리즈 When 하락 방향 일괄 점검 Then confirmed 리포트"""
        ticker = _valid_ticker()
        bars = _down_confirm_series()
        _insert_prices(ticker, bars)
        _insert_flows(ticker, _all_dates(bars), net=-500)

        results = evaluate_watchlist(direction="down")
        entry = next((r for r in results if r["ticker"] == ticker), None)
        assert entry is not None
        assert entry["status"] == "confirmed"
        # 상승 방향으로 보면 신호 없음(대칭 확인)
        up = next((r for r in evaluate_watchlist(direction="up") if r["ticker"] == ticker), None)
        assert up["status"] != "confirmed"
