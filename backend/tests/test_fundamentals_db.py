"""
stock_fundamentals / stock_distributions / etf_fundamentals / etf_holdings
DB INSERT・UPDATE・조회 단위 테스트

init_db()로 초기화된 SQLite DB에 직접 SQL을 실행하여
스키마・제약・Upsert 동작을 검증합니다.
"""
import sqlite3
from datetime import date

import pytest

from app.database import init_db, get_db_connection


# ───────────────────────────────────────
# Fixture
# ───────────────────────────────────────

@pytest.fixture(autouse=True)
def fresh_db():
    """각 테스트마다 DB를 초기화한다."""
    init_db()
    yield


def _exec(sql, params=()):
    """get_db_connection을 사용해 SQL을 실행하고 cursor를 반환한다."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        conn.commit()
        return cursor


def _fetchall(sql, params=()):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        return cursor.fetchall()


def _fetchone(sql, params=()):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        return cursor.fetchone()


def _get_valid_ticker():
    """etfs 테이블에 존재하는 종목코드를 하나 반환한다."""
    row = _fetchone("SELECT ticker FROM etfs LIMIT 1")
    assert row is not None, "etfs 테이블이 비어 있습니다."
    return row[0]


# ───────────────────────────────────────
# stock_fundamentals
# ───────────────────────────────────────

class TestStockFundamentalsDB:
    """stock_fundamentals 테이블 INSERT・Upsert・조회 테스트."""

    def _insert_row(self, ticker, record_date="2024-12-31", **kwargs):
        defaults = dict(
            per=10.75, pbr=0.92, roe=9.03, roa=None,
            eps=4950.0, bps=57981.0,
            revenue=3008709.0, operating_profit=327260.0, net_profit=344514.0,
            operating_margin=10.88, net_margin=11.45,
            debt_ratio=27.93, current_ratio=187.80,
            dividend_yield=2.72, payout_ratio=29.18,
        )
        defaults.update(kwargs)
        _exec(
            """
            INSERT OR REPLACE INTO stock_fundamentals
                (ticker, date, per, pbr, roe, roa, eps, bps,
                 revenue, operating_profit, net_profit,
                 operating_margin, net_margin,
                 debt_ratio, current_ratio, dividend_yield, payout_ratio)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ticker, record_date,
                defaults["per"], defaults["pbr"], defaults["roe"], defaults["roa"],
                defaults["eps"], defaults["bps"],
                defaults["revenue"], defaults["operating_profit"], defaults["net_profit"],
                defaults["operating_margin"], defaults["net_margin"],
                defaults["debt_ratio"], defaults["current_ratio"],
                defaults["dividend_yield"], defaults["payout_ratio"],
            ),
        )

    def test_insert_and_query(self):
        """기본 INSERT 후 조회가 성공한다."""
        ticker = _get_valid_ticker()
        self._insert_row(ticker)

        row = _fetchone(
            "SELECT * FROM stock_fundamentals WHERE ticker = ? AND date = ?",
            (ticker, "2024-12-31"),
        )
        assert row is not None
        assert row["ticker"] == ticker
        assert abs(row["per"] - 10.75) < 1e-6
        assert abs(row["pbr"] - 0.92) < 1e-6

    def test_upsert_updates_existing_row(self):
        """동일 (ticker, date)에 INSERT OR REPLACE 시 값이 갱신된다."""
        ticker = _get_valid_ticker()
        self._insert_row(ticker, per=10.75)
        self._insert_row(ticker, per=15.00)  # 갱신

        rows = _fetchall(
            "SELECT * FROM stock_fundamentals WHERE ticker = ? AND date = ?",
            (ticker, "2024-12-31"),
        )
        assert len(rows) == 1
        assert abs(rows[0]["per"] - 15.00) < 1e-6

    def test_multiple_dates_stored_separately(self):
        """서로 다른 날짜는 별개 행으로 저장된다."""
        ticker = _get_valid_ticker()
        self._insert_row(ticker, record_date="2023-12-31", per=36.84)
        self._insert_row(ticker, record_date="2024-12-31", per=10.75)

        rows = _fetchall(
            "SELECT date, per FROM stock_fundamentals WHERE ticker = ? ORDER BY date",
            (ticker,),
        )
        assert len(rows) == 2
        assert rows[0]["date"] in ("2023-12-31", "2023-12-31")
        assert abs(rows[1]["per"] - 10.75) < 1e-6

    def test_nullable_columns_accept_none(self):
        """roa 등 nullable 컬럼에 NULL 저장이 가능하다."""
        ticker = _get_valid_ticker()
        self._insert_row(ticker, roa=None, debt_ratio=None)

        row = _fetchone(
            "SELECT roa, debt_ratio FROM stock_fundamentals WHERE ticker = ?",
            (ticker,),
        )
        assert row["roa"] is None
        assert row["debt_ratio"] is None

    def test_index_exists(self):
        """idx_stock_fundamentals_ticker_date 인덱스가 존재한다."""
        rows = _fetchall(
            "SELECT name FROM sqlite_master WHERE type='index' AND name=?",
            ("idx_stock_fundamentals_ticker_date",),
        )
        assert len(rows) == 1


# ───────────────────────────────────────
# stock_distributions
# ───────────────────────────────────────

class TestStockDistributionsDB:
    """stock_distributions 테이블 INSERT・UNIQUE 제약・조회 테스트."""

    def _insert_dist(self, ticker, record_date="2024-12-31", amount=1446.0):
        _exec(
            """
            INSERT OR IGNORE INTO stock_distributions
                (ticker, record_date, payment_date, ex_date,
                 amount_per_share, distribution_type, yield_pct)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (ticker, record_date, "2025-01-20", "2024-12-27",
             amount, "annual", 2.72),
        )

    def test_insert_and_query(self):
        """기본 INSERT 후 조회가 성공한다."""
        ticker = _get_valid_ticker()
        self._insert_dist(ticker)

        row = _fetchone(
            "SELECT * FROM stock_distributions WHERE ticker = ? AND record_date = ?",
            (ticker, "2024-12-31"),
        )
        assert row is not None
        assert abs(row["amount_per_share"] - 1446.0) < 1e-6
        assert row["distribution_type"] == "annual"

    def test_unique_constraint_on_ticker_record_date(self):
        """(ticker, record_date) 중복 INSERT는 무시된다 (INSERT OR IGNORE)."""
        ticker = _get_valid_ticker()
        self._insert_dist(ticker, amount=1446.0)
        self._insert_dist(ticker, amount=9999.0)  # 중복 → 무시

        rows = _fetchall(
            "SELECT * FROM stock_distributions WHERE ticker = ? AND record_date = ?",
            (ticker, "2024-12-31"),
        )
        assert len(rows) == 1
        assert abs(rows[0]["amount_per_share"] - 1446.0) < 1e-6  # 최초값 유지

    def test_multiple_distributions_stored(self):
        """서로 다른 record_date는 각각 저장된다."""
        ticker = _get_valid_ticker()
        self._insert_dist(ticker, record_date="2023-12-31", amount=1444.0)
        self._insert_dist(ticker, record_date="2024-12-31", amount=1446.0)

        rows = _fetchall(
            "SELECT record_date, amount_per_share FROM stock_distributions WHERE ticker = ? ORDER BY record_date",
            (ticker,),
        )
        assert len(rows) == 2
        assert abs(rows[1]["amount_per_share"] - 1446.0) < 1e-6

    def test_index_exists(self):
        """idx_stock_distributions_ticker_date 인덱스가 존재한다."""
        rows = _fetchall(
            "SELECT name FROM sqlite_master WHERE type='index' AND name=?",
            ("idx_stock_distributions_ticker_date",),
        )
        assert len(rows) == 1


# ───────────────────────────────────────
# etf_fundamentals
# ───────────────────────────────────────

class TestEtfFundamentalsDB:
    """etf_fundamentals 테이블 INSERT・Upsert・조회 테스트."""

    def _get_etf_ticker(self):
        """etfs 테이블에서 type=ETF인 종목을 반환한다."""
        row = _fetchone("SELECT ticker FROM etfs WHERE type = 'ETF' LIMIT 1")
        if row is None:
            row = _fetchone("SELECT ticker FROM etfs LIMIT 1")
        assert row is not None
        return row[0]

    def _insert_nav_row(self, ticker, record_date="2026-02-13", nav=29726.0):
        _exec(
            """
            INSERT OR REPLACE INTO etf_fundamentals
                (ticker, date, nav, nav_change_pct, expense_ratio)
            VALUES (?, ?, ?, ?, ?)
            """,
            (ticker, record_date, nav, 0.37, 0.39),
        )

    def test_insert_and_query(self):
        """기본 INSERT 후 NAV 조회가 성공한다."""
        ticker = self._get_etf_ticker()
        self._insert_nav_row(ticker)

        row = _fetchone(
            "SELECT * FROM etf_fundamentals WHERE ticker = ? AND date = ?",
            (ticker, "2026-02-13"),
        )
        assert row is not None
        assert abs(row["nav"] - 29726.0) < 1e-3
        assert abs(row["expense_ratio"] - 0.39) < 1e-3

    def test_upsert_replaces_row(self):
        """동일 (ticker, date) Upsert 시 값이 갱신된다."""
        ticker = self._get_etf_ticker()
        self._insert_nav_row(ticker, nav=29726.0)
        self._insert_nav_row(ticker, nav=30000.0)

        rows = _fetchall(
            "SELECT nav FROM etf_fundamentals WHERE ticker = ? AND date = ?",
            (ticker, "2026-02-13"),
        )
        assert len(rows) == 1
        assert abs(rows[0]["nav"] - 30000.0) < 1e-3

    def test_multiple_dates(self):
        """날짜별 NAV가 별개 행으로 저장된다."""
        ticker = self._get_etf_ticker()
        self._insert_nav_row(ticker, record_date="2026-02-12", nav=30143.0)
        self._insert_nav_row(ticker, record_date="2026-02-13", nav=29726.0)

        rows = _fetchall(
            "SELECT date, nav FROM etf_fundamentals WHERE ticker = ? ORDER BY date DESC",
            (ticker,),
        )
        assert len(rows) == 2
        assert abs(rows[0]["nav"] - 29726.0) < 1e-3  # 최신 날짜


# ───────────────────────────────────────
# etf_holdings
# ───────────────────────────────────────

class TestEtfHoldingsDB:
    """etf_holdings 테이블 INSERT・조회・중복 처리 테스트."""

    def _get_etf_ticker(self):
        row = _fetchone("SELECT ticker FROM etfs WHERE type = 'ETF' LIMIT 1")
        if row is None:
            row = _fetchone("SELECT ticker FROM etfs LIMIT 1")
        assert row is not None
        return row[0]

    def _insert_holding(self, ticker, record_date="2026-02-13",
                        stock_code="010120", stock_name="LS ELECTRIC",
                        weight=21.52, shares=968):
        _exec(
            """
            INSERT OR REPLACE INTO etf_holdings
                (ticker, date, stock_code, stock_name, weight, shares)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (ticker, record_date, stock_code, stock_name, weight, shares),
        )

    def test_insert_and_query(self):
        """기본 INSERT 후 조회가 성공한다."""
        ticker = self._get_etf_ticker()
        self._insert_holding(ticker)

        row = _fetchone(
            "SELECT * FROM etf_holdings WHERE ticker = ? AND date = ? AND stock_code = ?",
            (ticker, "2026-02-13", "010120"),
        )
        assert row is not None
        assert row["stock_name"] == "LS ELECTRIC"
        assert abs(row["weight"] - 21.52) < 1e-3
        assert row["shares"] == 968

    def test_multiple_holdings_same_date(self):
        """같은 날짜에 여러 구성종목이 저장된다."""
        ticker = self._get_etf_ticker()
        holdings = [
            ("010120", "LS ELECTRIC", 21.52, 968),
            ("298040", "효성중공업", 19.49, 243),
            ("267260", "HD현대일렉트릭", 18.16, 569),
        ]
        for code, name, weight, shares in holdings:
            self._insert_holding(ticker, stock_code=code, stock_name=name,
                                 weight=weight, shares=shares)

        rows = _fetchall(
            "SELECT stock_code FROM etf_holdings WHERE ticker = ? AND date = ?",
            (ticker, "2026-02-13"),
        )
        codes = [r["stock_code"] for r in rows]
        assert "010120" in codes
        assert "298040" in codes
        assert "267260" in codes

    def test_upsert_replaces_holding(self):
        """동일 (ticker, date, stock_code) Upsert 시 weight가 갱신된다."""
        ticker = self._get_etf_ticker()
        self._insert_holding(ticker, weight=21.52)
        self._insert_holding(ticker, weight=22.00)

        rows = _fetchall(
            "SELECT weight FROM etf_holdings WHERE ticker = ? AND date = ? AND stock_code = ?",
            (ticker, "2026-02-13", "010120"),
        )
        assert len(rows) == 1
        assert abs(rows[0]["weight"] - 22.00) < 1e-3
