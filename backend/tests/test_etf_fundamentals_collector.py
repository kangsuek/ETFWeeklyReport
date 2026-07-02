"""
ETF 펀더멘털 수집기 테스트 (네이버 모바일 JSON API 기반)

etfAnalysis JSON 응답 파싱(_extract_fundamentals/_extract_holdings)과
DB 저장(collect_all)을 검증한다. 네트워크는 모두 mock 처리.
"""
import pytest
from datetime import date
from unittest.mock import patch, MagicMock

from app.services.etf_fundamentals_collector import (
    ETFFundamentalsCollector,
    _parse_korean_amount,
)
from app.database import get_db_connection


# ───────────────────────────────────────
# 샘플 etfAnalysis 응답 (실제 구조 축약)
# ───────────────────────────────────────

SAMPLE_ANALYSIS = {
    "itemCode": "475300",
    "itemName": "SOL 반도체전공정",
    "etfBaseIndex": "FnGuide 반도체 전공정 지수(PR)",
    "totalNav": "3,340억",
    "nav": "29953.51",
    "deviationSign": "+",
    "deviationRate": 0.51,
    "totalFee": 0.45,
    "chaseErrorRate": 0.78,
    "returnPerformanceReferenceDate": "2026.07.01",
    "navPerformanceList": [
        {"periodTypeCode": "D1", "value": 5.51},
        {"periodTypeCode": "M1", "value": -3.2},
    ],
    "sectorPortfolioList": [
        {"detailTypeCode": "IT", "weight": 86.94},
        {"detailTypeCode": "MATERIALS", "weight": 12.64},
        {"detailTypeCode": "UNCLASSIFIED", "weight": 0.36},
    ],
    "etfTop10MajorConstituentAssets": [
        {"seq": 1, "itemCode": "036930", "itemName": "주성엔지니어링",
         "stockCount": "1,234", "etfWeight": "19.49%"},
        {"seq": 2, "itemCode": "240810", "itemName": "원익IPS",
         "stockCount": "2,345", "etfWeight": "16.21%"},
    ],
    "dividend": {
        "dividendYieldTtm": 0.13,
        "dividendPerShareTtm": 40,
        "dividendCountThisYear": 1,
        "dividendMonthThisYear": "4",
    },
}


# ───────────────────────────────────────
# _parse_korean_amount (조/억 → 억원)
# ───────────────────────────────────────

class TestParseKoreanAmount:
    def test_eok_only(self):
        assert _parse_korean_amount("3,340억") == 3340.0

    def test_jo_and_eok(self):
        assert _parse_korean_amount("27조 9,110억") == 279110.0

    def test_jo_only(self):
        assert _parse_korean_amount("2조") == 20000.0

    def test_plain_number(self):
        assert _parse_korean_amount("1234.5") == 1234.5

    def test_none_and_invalid(self):
        assert _parse_korean_amount(None) is None
        assert _parse_korean_amount("-") is None
        assert _parse_korean_amount("N/A") is None


# ───────────────────────────────────────
# _extract_fundamentals
# ───────────────────────────────────────

class TestExtractFundamentals:
    def setup_method(self):
        self.collector = ETFFundamentalsCollector()
        self.f = self.collector._extract_fundamentals(SAMPLE_ANALYSIS)

    def test_nav_and_date(self):
        assert self.f['nav'] == 29953.51
        assert self.f['date'] == date(2026, 7, 1)

    def test_nav_change_pct_from_d1(self):
        assert self.f['nav_change_pct'] == 5.51

    def test_aum_in_eok(self):
        assert self.f['aum'] == 3340.0

    def test_tracking_error_and_fee(self):
        assert self.f['tracking_error'] == 0.78
        assert self.f['expense_ratio'] == 0.45

    def test_base_index(self):
        assert self.f['base_index'] == "FnGuide 반도체 전공정 지수(PR)"

    def test_dividend(self):
        assert self.f['dividend_yield'] == 0.13
        assert self.f['dividend_per_share'] == 40

    def test_deviation_rate_positive(self):
        assert self.f['deviation_rate'] == 0.51

    def test_deviation_rate_negative_sign(self):
        data = dict(SAMPLE_ANALYSIS, deviationSign="-", deviationRate=0.51)
        f = self.collector._extract_fundamentals(data)
        assert f['deviation_rate'] == -0.51

    def test_sector_portfolio_json(self):
        import json
        sectors = json.loads(self.f['sector_portfolio'])
        assert sectors[0] == {"code": "IT", "weight": 86.94}
        assert len(sectors) == 3


# ───────────────────────────────────────
# _extract_holdings
# ───────────────────────────────────────

class TestExtractHoldings:
    def setup_method(self):
        self.collector = ETFFundamentalsCollector()
        self.holdings = self.collector._extract_holdings(SAMPLE_ANALYSIS)

    def test_count(self):
        assert len(self.holdings) == 2

    def test_fields(self):
        h = self.holdings[0]
        assert h['stock_code'] == "036930"
        assert h['stock_name'] == "주성엔지니어링"
        assert h['weight'] == 19.49
        assert h['shares'] == 1234

    def test_skips_rows_without_code(self):
        data = dict(SAMPLE_ANALYSIS)
        data['etfTop10MajorConstituentAssets'] = [
            {"itemCode": None, "itemName": "무효"},
            {"itemCode": "005930", "itemName": "삼성전자",
             "stockCount": "10", "etfWeight": "5.0%"},
        ]
        holdings = self.collector._extract_holdings(data)
        assert len(holdings) == 1
        assert holdings[0]['stock_code'] == "005930"

    def test_empty_when_missing(self):
        assert self.collector._extract_holdings({}) == []


# ───────────────────────────────────────
# collect_all (fetch mock + 격리 DB 저장)
# ───────────────────────────────────────

class TestCollectAll:
    TICKER = "475300"

    @pytest.fixture(autouse=True)
    def _clean_tables(self):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM etf_fundamentals WHERE ticker = ?", (self.TICKER,))
            cursor.execute("DELETE FROM etf_holdings WHERE ticker = ?", (self.TICKER,))
            conn.commit()
        yield

    def test_collect_all_saves_fundamentals_and_holdings(self):
        collector = ETFFundamentalsCollector()
        with patch.object(collector, '_fetch_analysis', return_value=SAMPLE_ANALYSIS):
            result = collector.collect_all(self.TICKER)

        assert result['nav'] is True
        assert result['holdings'] is True
        assert result['distributions'] is True   # no-op
        assert result['rebalancing'] is True      # no-op

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT nav, aum, tracking_error, base_index, deviation_rate "
                "FROM etf_fundamentals WHERE ticker = ?", (self.TICKER,))
            row = cursor.fetchone()
            assert row is not None
            assert row[0] == 29953.51
            assert row[1] == 3340.0
            assert row[2] == 0.78
            assert row[3] == "FnGuide 반도체 전공정 지수(PR)"
            assert row[4] == 0.51

            cursor.execute(
                "SELECT COUNT(*) FROM etf_holdings WHERE ticker = ?", (self.TICKER,))
            assert cursor.fetchone()[0] == 2

    def test_collect_all_returns_false_on_fetch_failure(self):
        collector = ETFFundamentalsCollector()
        with patch.object(collector, '_fetch_analysis', return_value=None):
            result = collector.collect_all(self.TICKER)

        assert result['nav'] is False
        assert result['holdings'] is False

    def test_distributions_is_noop(self):
        collector = ETFFundamentalsCollector()
        assert collector.collect_distributions("487240") is True

    def test_rebalancing_is_noop(self):
        collector = ETFFundamentalsCollector()
        assert collector.collect_rebalancing("487240") is True

    def test_fetch_analysis_http_error(self):
        collector = ETFFundamentalsCollector()
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_get.return_value = mock_response
            assert collector._fetch_analysis(self.TICKER) is None

    def test_fetch_analysis_network_error(self):
        collector = ETFFundamentalsCollector()
        with patch('requests.get', side_effect=Exception("boom")):
            assert collector._fetch_analysis(self.TICKER) is None
