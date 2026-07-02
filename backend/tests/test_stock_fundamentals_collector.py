"""
stock_fundamentals_collector.py 단위 테스트 (네이버 모바일 JSON API 기반)

finance/annual·quarter JSON 파싱과 결산기 기준 다년치 저장을 검증합니다.
네트워크는 모두 mock 처리, DB는 conftest의 격리 DB를 사용합니다.
"""
import pytest
from datetime import date
from unittest.mock import patch

from app.services.stock_fundamentals_collector import (
    _period_key_to_date,
    _extract_period_rows,
    collect_stock_fundamentals,
)
from app.database import get_db_connection


# ───────────────────────────────────────
# JSON 픽스처 (finance/annual 축약 — 삼성전자 구조 모방)
# ───────────────────────────────────────

def _col(value):
    return {"value": value, "cx": None}


ANNUAL_FINANCE_INFO = {
    "itemCode": "005930",
    "trTitleList": [
        {"key": "202312", "title": "2023.12.", "isConsensus": "N"},
        {"key": "202412", "title": "2024.12.", "isConsensus": "N"},
        {"key": "202512", "title": "2025.12.", "isConsensus": "Y"},  # 추정치 → 제외
    ],
    "rowList": [
        {"title": "매출액", "columns": {
            "202312": _col("2,589,355"), "202412": _col("3,008,709"), "202512": _col("3,291,027")}},
        {"title": "영업이익", "columns": {
            "202312": _col("65,670"), "202412": _col("327,260"), "202512": _col("401,605")}},
        {"title": "당기순이익", "columns": {
            "202312": _col("154,871"), "202412": _col("344,514"), "202512": _col("398,255")}},
        {"title": "영업이익률", "columns": {
            "202312": _col("2.54"), "202412": _col("10.88"), "202512": _col("12.20")}},
        {"title": "순이익률", "columns": {
            "202312": _col("5.98"), "202412": _col("11.45"), "202512": _col("12.10")}},
        {"title": "ROE", "columns": {
            "202312": _col("4.15"), "202412": _col("9.03"), "202512": _col("9.53")}},
        {"title": "부채비율", "columns": {
            "202312": _col("25.36"), "202412": _col("27.93"), "202512": _col("-")}},
        {"title": "당좌비율", "columns": {
            "202312": _col("189.46"), "202412": _col("187.80"), "202512": _col("-")}},
        {"title": "EPS", "columns": {
            "202312": _col("2,131"), "202412": _col("4,950"), "202512": _col("5,727")}},
        {"title": "PER", "columns": {
            "202312": _col("36.84"), "202412": _col("10.75"), "202512": _col("22.44")}},
        {"title": "BPS", "columns": {
            "202312": _col("52,002"), "202412": _col("57,981"), "202512": _col("63,204")}},
        {"title": "PBR", "columns": {
            "202312": _col("1.51"), "202412": _col("0.92"), "202512": _col("2.03")}},
        {"title": "주당배당금", "columns": {
            "202312": _col("1,444"), "202412": _col("1,446"), "202512": _col("1,527")}},
    ],
}

QUARTER_FINANCE_INFO = {
    "itemCode": "005930",
    "trTitleList": [
        {"key": "202412", "title": "2024.12.", "isConsensus": "N"},  # 연간과 결산기 중복
        {"key": "202503", "title": "2025.03.", "isConsensus": "N"},
        {"key": "202506", "title": "2025.06.", "isConsensus": "Y"},  # 추정치 → 제외
    ],
    "rowList": [
        {"title": "매출액", "columns": {
            "202412": _col("757,883"), "202503": _col("791,405"), "202506": _col("745,663")}},
        {"title": "EPS", "columns": {
            "202412": _col("1,115"), "202503": _col("1,186"), "202506": _col("733")}},
        {"title": "PER", "columns": {
            "202412": _col("10.75"), "202503": _col("11.20"), "202506": _col("13.36")}},
    ],
}


# ───────────────────────────────────────
# _period_key_to_date
# ───────────────────────────────────────

class TestPeriodKeyToDate:
    def test_december(self):
        assert _period_key_to_date("202412") == date(2024, 12, 31)

    def test_march_end(self):
        assert _period_key_to_date("202503") == date(2025, 3, 31)

    def test_june_end(self):
        assert _period_key_to_date("202506") == date(2025, 6, 30)

    def test_february_leap(self):
        assert _period_key_to_date("202402") == date(2024, 2, 29)

    def test_invalid(self):
        assert _period_key_to_date("abc") is None
        assert _period_key_to_date("") is None
        assert _period_key_to_date(None) is None


# ───────────────────────────────────────
# TestParseDate — 공용 naver_stock_api.parse_bizdate 검증
# ───────────────────────────────────────

class TestParseDate:
    def test_dot_format(self):
        from app.services.naver_stock_api import parse_bizdate
        assert parse_bizdate("2026.02.13") == date(2026, 2, 13)

    def test_dash_format(self):
        from app.services.naver_stock_api import parse_bizdate
        assert parse_bizdate("2026-02-13") == date(2026, 2, 13)

    def test_bizdate_format(self):
        from app.services.naver_stock_api import parse_bizdate
        assert parse_bizdate("20260213") == date(2026, 2, 13)

    def test_invalid(self):
        from app.services.naver_stock_api import parse_bizdate
        assert parse_bizdate("invalid") is None

    def test_empty(self):
        from app.services.naver_stock_api import parse_bizdate
        assert parse_bizdate("") is None


# ───────────────────────────────────────
# _extract_period_rows
# ───────────────────────────────────────

class TestExtractPeriodRows:
    def test_excludes_consensus_periods(self):
        rows = _extract_period_rows(ANNUAL_FINANCE_INFO)
        dates = [r['date'] for r in rows]
        assert dates == [date(2023, 12, 31), date(2024, 12, 31)]  # 2025.12(E) 제외

    def test_maps_fields(self):
        rows = _extract_period_rows(ANNUAL_FINANCE_INFO)
        latest = rows[-1]  # 2024.12
        assert latest['revenue'] == 3008709
        assert latest['operating_profit'] == 327260
        assert latest['net_profit'] == 344514
        assert latest['roe'] == 9.03
        assert latest['eps'] == 4950
        assert latest['per'] == 10.75
        assert latest['bps'] == 57981
        assert latest['pbr'] == 0.92
        assert latest['current_ratio'] == 187.80

    def test_dash_becomes_none(self):
        rows = _extract_period_rows(ANNUAL_FINANCE_INFO)
        # 202512는 컨센서스라 제외됐고, 확정분에는 '-' 없음 → 2023년 값으로 확인
        assert rows[0]['debt_ratio'] == 25.36

    def test_payout_ratio_computed(self):
        rows = _extract_period_rows(ANNUAL_FINANCE_INFO)
        latest = rows[-1]
        # 배당성향 = 1,446 / 4,950 × 100 ≈ 29.21%
        assert latest['dividend_per_share'] == 1446
        assert latest['payout_ratio'] == pytest.approx(29.21, abs=0.01)

    def test_empty_input(self):
        assert _extract_period_rows(None) == []
        assert _extract_period_rows({}) == []
        assert _extract_period_rows({"trTitleList": [], "rowList": []}) == []


# ───────────────────────────────────────
# collect_stock_fundamentals (fetch mock + 격리 DB)
# ───────────────────────────────────────

_MOD = 'app.services.stock_fundamentals_collector'


class TestCollectStockFundamentals:
    TICKER = "005930"

    @pytest.fixture(autouse=True)
    def _clean_tables(self):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM stock_fundamentals WHERE ticker = ?", (self.TICKER,))
            cursor.execute("DELETE FROM stock_distributions WHERE ticker = ?", (self.TICKER,))
            conn.commit()
        yield

    def _collect(self, annual=ANNUAL_FINANCE_INFO, quarter=QUARTER_FINANCE_INFO, yield_pct=0.58):
        def fake_fetch(ticker, period_type):
            return annual if period_type == 'annual' else quarter

        with patch(f'{_MOD}._fetch_finance', side_effect=fake_fetch), \
             patch(f'{_MOD}._fetch_current_dividend_yield', return_value=yield_pct):
            return collect_stock_fundamentals(self.TICKER)

    def test_success_flow(self):
        result = self._collect()
        assert result['success'] is True
        assert result['saved'] is True
        assert result['dividend_saved'] is True
        assert result['error'] is None

    def test_saves_multi_period_rows(self):
        self._collect()
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT date FROM stock_fundamentals WHERE ticker = ? ORDER BY date",
                (self.TICKER,))
            dates = [row[0] for row in cursor.fetchall()]
        # 연간 2 (2023-12, 2024-12) + 분기 1 (2025-03; 2024-12는 연간과 중복 병합)
        assert dates == ['2023-12-31', '2024-12-31', '2025-03-31']

    def test_annual_overrides_duplicate_quarter(self):
        self._collect()
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT revenue FROM stock_fundamentals WHERE ticker = ? AND date = ?",
                (self.TICKER, '2024-12-31'))
            # 연간 매출(3,008,709)이 분기 매출(757,883)을 덮어써야 함
            assert cursor.fetchone()[0] == 3008709

    def test_latest_row_gets_current_dividend_yield(self):
        self._collect(yield_pct=0.58)
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT date, dividend_yield FROM stock_fundamentals "
                "WHERE ticker = ? ORDER BY date DESC",
                (self.TICKER,))
            rows = cursor.fetchall()
        assert rows[0][1] == 0.58            # 최신 행에만
        assert all(r[1] is None for r in rows[1:])

    def test_replaces_legacy_today_dated_rows(self):
        # 구 수집기가 남긴 date=오늘 행이 새 결산기 행으로 교체되는지
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO stock_fundamentals (ticker, date, per) VALUES (?, ?, ?)",
                (self.TICKER, str(date.today()), 99.9))
            conn.commit()

        self._collect()

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM stock_fundamentals WHERE ticker = ? AND per = 99.9",
                (self.TICKER,))
            assert cursor.fetchone()[0] == 0

    def test_saves_dividend_distributions_per_year(self):
        self._collect()
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT record_date, amount_per_share FROM stock_distributions "
                "WHERE ticker = ? ORDER BY record_date",
                (self.TICKER,))
            rows = cursor.fetchall()
        assert ('2023-12-31', 1444.0) in [(r[0], r[1]) for r in rows]
        assert ('2024-12-31', 1446.0) in [(r[0], r[1]) for r in rows]

    def test_error_when_no_data(self):
        result = self._collect(annual=None, quarter=None)
        assert result['success'] is False
        assert result['saved'] is False
        assert 'No fundamental data' in result['error']
