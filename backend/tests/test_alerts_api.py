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
        cur.execute("DELETE FROM alert_rules")
        cur.execute("DELETE FROM signal_events")
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
