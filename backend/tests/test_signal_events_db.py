"""signal_events / app_state 테이블 스키마·제약 단위 테스트 (Phase 2.1)

init_db()로 생성되는 상승흐름 신호 상태 머신 테이블과 범용 키-값 상태
테이블의 존재·기본값·UNIQUE 제약·인덱스를 검증한다.
"""
import sqlite3
import pytest

from app.database import init_db, get_db_connection


@pytest.fixture(autouse=True)
def fresh_db():
    """각 테스트마다 대상 테이블을 비운다 (세션 공유 DB 격리)."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM signal_events")
        cursor.execute("DELETE FROM app_state")
        conn.commit()
    yield


def _fetchone(sql, params=()):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        return cursor.fetchone()


def _get_valid_ticker():
    row = _fetchone("SELECT ticker FROM etfs LIMIT 1")
    assert row is not None, "etfs 테이블이 비어 있습니다."
    return row[0]


class TestSignalEventsSchema:
    """signal_events 테이블"""

    def test_table_exists(self):
        """Given init_db When 조회 Then signal_events 테이블 존재"""
        row = _fetchone(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            ("signal_events",),
        )
        assert row is not None

    def test_status_defaults_to_pending(self):
        """Given status 미지정 삽입 When 조회 Then 기본값 'pending'"""
        ticker = _get_valid_ticker()
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO signal_events
                   (ticker, rule_id, breakout_date, breakout_level)
                   VALUES (?, ?, ?, ?)""",
                (ticker, 1, "2026-07-01", 10000.0),
            )
            conn.commit()
        row = _fetchone(
            "SELECT status FROM signal_events WHERE ticker=? AND breakout_date=?",
            (ticker, "2026-07-01"),
        )
        assert row["status"] == "pending"

    def test_unique_ticker_breakout_date(self):
        """Given 동일 (ticker, breakout_date) When 재삽입 Then IntegrityError"""
        ticker = _get_valid_ticker()
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO signal_events
                   (ticker, rule_id, breakout_date, breakout_level)
                   VALUES (?, ?, ?, ?)""",
                (ticker, 1, "2026-07-02", 10000.0),
            )
            conn.commit()
            try:
                cursor.execute(
                    """INSERT INTO signal_events
                       (ticker, rule_id, breakout_date, breakout_level)
                       VALUES (?, ?, ?, ?)""",
                    (ticker, 1, "2026-07-02", 11000.0),
                )
                conn.commit()
                pytest.fail("중복 (ticker, breakout_date) 삽입이 IntegrityError를 내야 함")
            except sqlite3.IntegrityError:
                # 실패한 트랜잭션을 롤백해 풀 커넥션이 락을 쥔 채 반환되지 않도록 정리
                conn.rollback()

    def test_status_index_exists(self):
        """Given init_db When 조회 Then idx_signal_events_status 인덱스 존재"""
        row = _fetchone(
            "SELECT name FROM sqlite_master WHERE type='index' AND name=?",
            ("idx_signal_events_status",),
        )
        assert row is not None


class TestAppStateSchema:
    """app_state 키-값 테이블"""

    def test_table_exists(self):
        """Given init_db When 조회 Then app_state 테이블 존재"""
        row = _fetchone(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            ("app_state",),
        )
        assert row is not None

    def test_key_is_primary_key_upsert(self):
        """Given 동일 key 재삽입 When INSERT OR REPLACE Then 값이 덮어써짐"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO app_state (key, value) VALUES (?, ?)",
                ("last_signal_scan_date", "2026-07-01"),
            )
            cursor.execute(
                "INSERT OR REPLACE INTO app_state (key, value) VALUES (?, ?)",
                ("last_signal_scan_date", "2026-07-03"),
            )
            conn.commit()
        row = _fetchone(
            "SELECT value FROM app_state WHERE key=?", ("last_signal_scan_date",)
        )
        assert row["value"] == "2026-07-03"
