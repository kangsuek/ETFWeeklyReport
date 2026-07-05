"""alerts 라우터 — uptrend 규칙 수용 + signals 조회 (Phase 2.4)

TestClient로 uptrend 규칙 CRUD와 GET /signals/{ticker} 응답을 검증한다.
Given-When-Then.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import init_db, get_db_connection

client = TestClient(app)


def _valid_ticker():
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT ticker FROM etfs LIMIT 1")
        return cur.fetchone()[0]


@pytest.fixture(autouse=True)
def clean():
    init_db()
    with get_db_connection() as conn:
        cur = conn.cursor()
        for t in ("alert_rules", "signal_events", "alert_history", "app_state"):
            cur.execute(f"DELETE FROM {t}")
        conn.commit()
    yield


class TestUptrendRuleCRUD:
    """uptrend 규칙 생성·조회·삭제"""

    def test_create_uptrend_rule(self):
        """Given uptrend·목표가 0 When 생성 Then 201·목표가 검사 면제"""
        ticker = _valid_ticker()
        payload = {
            "ticker": ticker, "alert_type": "uptrend",
            "direction": "above", "target_price": 0,
        }

        resp = client.post("/api/alerts/", json=payload)

        assert resp.status_code == 200  # response_model 반환(기본 200)
        data = resp.json()
        assert data["alert_type"] == "uptrend"
        assert data["ticker"] == ticker

    def test_buy_rule_still_requires_target(self):
        """Given buy·목표가 0 When 생성 Then 400 (uptrend 면제가 buy엔 미적용)"""
        ticker = _valid_ticker()
        payload = {
            "ticker": ticker, "alert_type": "buy",
            "direction": "above", "target_price": 0,
        }
        resp = client.post("/api/alerts/", json=payload)
        assert resp.status_code == 400

    def test_uptrend_rule_listed_and_deletable(self):
        """Given 생성한 uptrend 규칙 When 조회·삭제 Then 정상 동작"""
        ticker = _valid_ticker()
        created = client.post("/api/alerts/", json={
            "ticker": ticker, "alert_type": "uptrend",
            "direction": "above", "target_price": 0,
        }).json()

        listed = client.get(f"/api/alerts/{ticker}")
        assert listed.status_code == 200
        assert any(r["alert_type"] == "uptrend" for r in listed.json())

        deleted = client.delete(f"/api/alerts/{created['id']}")
        assert deleted.status_code == 200


class TestSignalEventsEndpoint:
    """GET /api/alerts/signals/{ticker}"""

    def _insert_event(self, ticker, breakout_date, status="confirmed"):
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO signal_events
                   (ticker, rule_id, breakout_date, breakout_level, status, confirm_path)
                   VALUES (?, 1, ?, 10000.0, ?, 'hold')""",
                (ticker, breakout_date, status),
            )
            conn.commit()

    def test_returns_events_with_schema(self):
        """Given signal_events 존재 When 조회 Then 이벤트 스키마 반환"""
        ticker = _valid_ticker()
        self._insert_event(ticker, "2026-07-01")

        resp = client.get(f"/api/alerts/signals/{ticker}")

        assert resp.status_code == 200
        rows = resp.json()
        assert len(rows) == 1
        assert rows[0]["breakout_date"][:10] == "2026-07-01"
        assert rows[0]["status"] == "confirmed"
        assert "breakout_level" in rows[0]

    def test_empty_when_no_events(self):
        """Given 이벤트 없음 When 조회 Then 빈 목록 (라우트가 /{ticker}에 안 잡힘)"""
        ticker = _valid_ticker()
        resp = client.get(f"/api/alerts/signals/{ticker}")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_multiple_events_ordered_desc(self):
        """Given 여러 이벤트 When 조회 Then 돌파일 내림차순"""
        ticker = _valid_ticker()
        self._insert_event(ticker, "2026-06-01")
        self._insert_event(ticker, "2026-07-01")

        rows = client.get(f"/api/alerts/signals/{ticker}").json()
        assert [r["breakout_date"][:10] for r in rows] == ["2026-07-01", "2026-06-01"]


class TestUptrendHistory:
    """상승흐름 알림 이력·읽음 API (Phase 2.5)"""

    def _insert_uptrend_history(self, ticker, triggered_at, message="확정"):
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO alert_history (rule_id, ticker, alert_type, message, triggered_at)
                   VALUES (1, ?, 'uptrend', ?, ?)""",
                (ticker, message, triggered_at),
            )
            conn.commit()

    def test_all_unread_when_no_marker(self):
        """Given 마커 부재 When 조회 Then 전체가 미읽음"""
        ticker = _valid_ticker()
        self._insert_uptrend_history(ticker, "2026-07-01")
        self._insert_uptrend_history(ticker, "2026-07-02")

        resp = client.get("/api/alerts/uptrend")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["unread_count"] == 2

    def test_unread_zero_after_read(self):
        """Given 읽음 처리 후 When 조회 Then 미읽음 0"""
        ticker = _valid_ticker()
        self._insert_uptrend_history(ticker, "2026-07-01")

        client.post("/api/alerts/uptrend/read")
        data = client.get("/api/alerts/uptrend").json()

        assert data["unread_count"] == 0

    def test_new_signal_after_read_is_unread(self):
        """Given 읽음 후 더 늦은 신호 When 조회 Then 미읽음 1"""
        ticker = _valid_ticker()
        self._insert_uptrend_history(ticker, "2026-07-01")
        client.post("/api/alerts/uptrend/read")
        self._insert_uptrend_history(ticker, "2999-12-31")  # 마커 이후

        data = client.get("/api/alerts/uptrend").json()
        assert data["unread_count"] == 1

    def test_only_uptrend_type_counted(self):
        """Given 다른 타입 이력 혼재 When 조회 Then uptrend만 집계"""
        ticker = _valid_ticker()
        self._insert_uptrend_history(ticker, "2026-07-01")
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO alert_history (rule_id, ticker, alert_type, message, triggered_at)
                   VALUES (1, ?, 'buy', '목표가', '2026-07-01')""",
                (ticker,),
            )
            conn.commit()

        data = client.get("/api/alerts/uptrend").json()
        assert len(data["items"]) == 1
        assert data["items"][0]["alert_type"] == "uptrend"

    def test_delete_single(self):
        """Given 이력 1건 When 단건 삭제 Then 제거"""
        ticker = _valid_ticker()
        self._insert_uptrend_history(ticker, "2026-07-01")
        item = client.get("/api/alerts/uptrend").json()["items"][0]

        resp = client.delete(f"/api/alerts/uptrend/{item['id']}")

        assert resp.status_code == 200
        assert client.get("/api/alerts/uptrend").json()["items"] == []

    def test_delete_before(self):
        """Given 여러 이력 When before로 정리 Then 이전 것만 삭제"""
        ticker = _valid_ticker()
        self._insert_uptrend_history(ticker, "2026-06-01")
        self._insert_uptrend_history(ticker, "2026-07-10")

        resp = client.delete("/api/alerts/uptrend", params={"before": "2026-07-01"})

        assert resp.status_code == 200
        remaining = client.get("/api/alerts/uptrend").json()["items"]
        assert [r["triggered_at"][:10] for r in remaining] == ["2026-07-10"]

    def test_uptrend_route_not_shadowed_by_ticker(self):
        """Given uptrend 경로 When GET Then /{ticker} 규칙조회에 안 잡히고 이력 형태 반환"""
        resp = client.get("/api/alerts/uptrend")
        assert resp.status_code == 200
        # 규칙 리스트가 아니라 {items, unread_count} 형태여야 함
        assert "unread_count" in resp.json()


class TestWatchlistAndScanEndpoints:
    """A: GET /uptrend/watchlist · B: POST /signals/{ticker}/scan"""

    def test_watchlist_returns_items(self):
        """Given 등록 종목 When 일괄 점검 Then items 리스트(각 ticker·status)"""
        resp = client.get("/api/alerts/uptrend/watchlist")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data and isinstance(data["items"], list)
        if data["items"]:
            assert "ticker" in data["items"][0]
            assert "status" in data["items"][0]

    def test_scan_ticker_noop_without_rule(self):
        """Given 활성 규칙 없음 When 단일 스캔 Then scanned=False"""
        ticker = _valid_ticker()
        resp = client.post(f"/api/alerts/signals/{ticker}/scan")
        assert resp.status_code == 200
        assert resp.json() == {"scanned": False, "reason": "no_active_rule"}


class TestDowntrendEndpoints:
    """하락흐름 규칙·이력·읽음·일괄점검 (거울상)"""

    def _insert_down_history(self, ticker, triggered_at, message="하락 확정"):
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO alert_history (rule_id, ticker, alert_type, message, triggered_at)
                   VALUES (1, ?, 'downtrend', ?, ?)""",
                (ticker, message, triggered_at),
            )
            conn.commit()

    def test_create_downtrend_rule(self):
        """Given downtrend·목표가 0 When 생성 Then 200·검사 면제"""
        ticker = _valid_ticker()
        resp = client.post("/api/alerts/", json={
            "ticker": ticker, "alert_type": "downtrend",
            "direction": "below", "target_price": 0,
        })
        assert resp.status_code == 200
        assert resp.json()["alert_type"] == "downtrend"

    def test_downtrend_history_unread_and_read(self):
        """Given 하락 이력 When 조회·읽음 Then 미읽음 집계 후 0"""
        ticker = _valid_ticker()
        self._insert_down_history(ticker, "2026-07-01")
        self._insert_down_history(ticker, "2026-07-02")

        data = client.get("/api/alerts/downtrend").json()
        assert len(data["items"]) == 2
        assert data["unread_count"] == 2

        client.post("/api/alerts/downtrend/read")
        assert client.get("/api/alerts/downtrend").json()["unread_count"] == 0

    def test_downtrend_separated_from_uptrend(self):
        """Given up·down 이력 혼재 When downtrend 조회 Then downtrend만"""
        ticker = _valid_ticker()
        self._insert_down_history(ticker, "2026-07-01")
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO alert_history (rule_id, ticker, alert_type, message, triggered_at)
                   VALUES (1, ?, 'uptrend', '상승', '2026-07-01')""",
                (ticker,),
            )
            conn.commit()
        data = client.get("/api/alerts/downtrend").json()
        assert len(data["items"]) == 1
        assert data["items"][0]["alert_type"] == "downtrend"

    def test_downtrend_watchlist_returns_items(self):
        """Given 등록 종목 When 하락 일괄 점검 Then items 반환"""
        resp = client.get("/api/alerts/downtrend/watchlist")
        assert resp.status_code == 200
        assert "items" in resp.json()

    def test_delete_downtrend_single(self):
        """Given 하락 이력 When 단건 삭제 Then 제거"""
        ticker = _valid_ticker()
        self._insert_down_history(ticker, "2026-07-01")
        item = client.get("/api/alerts/downtrend").json()["items"][0]
        assert client.delete(f"/api/alerts/downtrend/{item['id']}").status_code == 200
        assert client.get("/api/alerts/downtrend").json()["items"] == []
