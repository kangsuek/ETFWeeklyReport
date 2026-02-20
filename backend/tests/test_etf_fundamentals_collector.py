"""
etf_fundamentals_collector.py 단위 테스트

HTML fixture를 사용하여 실제 네트워크 없이 파싱 로직을 검증합니다.
"""
import pytest
from datetime import date
from unittest.mock import patch, MagicMock
from bs4 import BeautifulSoup

from app.services.etf_fundamentals_collector import (
    ETFFundamentalsCollector,
    _parse_number,
    _parse_date,
)


# ───────────────────────────────────────
# HTML 픽스처 (KODEX 487240 구조 모방)
# ───────────────────────────────────────

ETF_NAV_HTML = """
<html><body>
  <h4>순자산가치 NAV 추이</h4>
  <table>
    <thead>
      <tr>
        <th>날짜</th><th>종가</th><th>NAV</th><th>괴리율</th>
      </tr>
    </thead>
    <tbody>
      <tr><td></td><td></td></tr>
      <tr><td>2026.02.13</td><td>29,835</td><td>29,726</td><td>+0.37%</td></tr>
      <tr><td>2026.02.12</td><td>30,110</td><td>30,143</td><td>-0.11%</td></tr>
      <tr><td>2026.02.11</td><td>29,825</td><td>29,894</td><td>-0.23%</td></tr>
      <tr><td></td><td></td></tr>
    </tbody>
  </table>
  <table summary="펀드보수 정보" class="tbl_type1">
    <caption>펀드보수</caption>
    <tbody>
      <tr><th>펀드보수</th><td>연 <em>0.39</em>%</td></tr>
    </tbody>
  </table>
</body></html>
"""

ETF_HOLDINGS_HTML = """
<html><body>
  <table class="tb_type1 tb_type1_a">
    <thead>
      <tr>
        <th>구성종목(구성자산)</th>
        <th>주식수(계약수)</th>
        <th>구성비중</th>
        <th>시세</th><th>전일비</th><th>등락률</th>
      </tr>
    </thead>
    <tbody>
      <tr><td></td><td></td></tr>
      <tr>
        <td><a href="/item/main.naver?code=010120">LS ELECTRIC</a></td>
        <td>968</td><td>21.52%</td><td>661,000</td><td>10,000</td><td>-1.49%</td>
      </tr>
      <tr>
        <td><a href="/item/main.naver?code=298040">효성중공업</a></td>
        <td>243</td><td>19.49%</td><td>2,384,000</td><td>21,000</td><td>-0.87%</td>
      </tr>
      <tr>
        <td><a href="/item/main.naver?code=267260">HD현대일렉트릭</a></td>
        <td>569</td><td>18.16%</td><td>949,000</td><td>17,000</td><td>-1.76%</td>
      </tr>
      <tr><td></td><td></td></tr>
    </tbody>
  </table>
</body></html>
"""

ETF_FULL_HTML = ETF_NAV_HTML.replace("</body></html>", "") + ETF_HOLDINGS_HTML.split("<body>")[1]

NO_NAV_HTML = "<html><body><p>데이터 없음</p></body></html>"


# ───────────────────────────────────────
# _parse_number / _parse_date 테스트
# ───────────────────────────────────────

class TestHelpers:
    def test_parse_number_plain(self):
        assert _parse_number("29726") == 29726.0

    def test_parse_number_with_comma(self):
        assert _parse_number("29,726") == 29726.0

    def test_parse_number_with_plus_sign(self):
        assert _parse_number("+0.37") == pytest.approx(0.37)

    def test_parse_number_with_percent(self):
        assert _parse_number("+0.37%") == pytest.approx(0.37)

    def test_parse_number_negative(self):
        assert _parse_number("-0.11%") == pytest.approx(-0.11)

    def test_parse_number_dash(self):
        assert _parse_number("-") is None

    def test_parse_number_empty(self):
        assert _parse_number("") is None

    def test_parse_date_dot_format(self):
        assert _parse_date("2026.02.13") == date(2026, 2, 13)

    def test_parse_date_dash_format(self):
        assert _parse_date("2026-02-13") == date(2026, 2, 13)

    def test_parse_date_invalid(self):
        assert _parse_date("invalid") is None

    def test_parse_date_empty(self):
        assert _parse_date("") is None


# ───────────────────────────────────────
# _parse_expense_ratio 테스트
# ───────────────────────────────────────

class TestParseExpenseRatio:
    def setup_method(self):
        self.collector = ETFFundamentalsCollector()

    def test_parses_expense_ratio(self):
        soup = BeautifulSoup(ETF_NAV_HTML, "html.parser")
        ratio = self.collector._parse_expense_ratio(soup)
        assert ratio == pytest.approx(0.39)

    def test_returns_none_when_no_table(self):
        soup = BeautifulSoup(NO_NAV_HTML, "html.parser")
        ratio = self.collector._parse_expense_ratio(soup)
        assert ratio is None


# ───────────────────────────────────────
# _parse_nav_table 테스트
# ───────────────────────────────────────

class TestParseNavTable:
    def setup_method(self):
        self.collector = ETFFundamentalsCollector()

    def test_parses_nav_rows(self):
        soup = BeautifulSoup(ETF_NAV_HTML, "html.parser")
        rows = self.collector._parse_nav_table(soup)

        assert len(rows) == 3
        assert rows[0]["date"] == date(2026, 2, 13)
        assert rows[0]["nav"] == pytest.approx(29726.0)
        assert rows[0]["nav_change_pct"] == pytest.approx(0.37)

    def test_parses_negative_nav_change(self):
        soup = BeautifulSoup(ETF_NAV_HTML, "html.parser")
        rows = self.collector._parse_nav_table(soup)

        assert rows[1]["date"] == date(2026, 2, 12)
        assert rows[1]["nav_change_pct"] == pytest.approx(-0.11)

    def test_skips_empty_rows(self):
        """빈 tr 행은 파싱 결과에 포함되지 않는다."""
        soup = BeautifulSoup(ETF_NAV_HTML, "html.parser")
        rows = self.collector._parse_nav_table(soup)

        dates = [r["date"] for r in rows]
        assert None not in dates

    def test_returns_empty_when_no_table(self):
        soup = BeautifulSoup(NO_NAV_HTML, "html.parser")
        rows = self.collector._parse_nav_table(soup)
        assert rows == []


# ───────────────────────────────────────
# _parse_holdings_table 테스트
# ───────────────────────────────────────

class TestParseHoldingsTable:
    def setup_method(self):
        self.collector = ETFFundamentalsCollector()

    def test_parses_holdings(self):
        soup = BeautifulSoup(ETF_HOLDINGS_HTML, "html.parser")
        holdings = self.collector._parse_holdings_table(soup)

        assert len(holdings) == 3
        assert holdings[0]["stock_code"] == "010120"
        assert holdings[0]["stock_name"] == "LS ELECTRIC"
        assert holdings[0]["weight"] == pytest.approx(21.52)
        assert holdings[0]["shares"] == 968

    def test_parses_stock_code_from_link(self):
        soup = BeautifulSoup(ETF_HOLDINGS_HTML, "html.parser")
        holdings = self.collector._parse_holdings_table(soup)

        codes = [h["stock_code"] for h in holdings]
        assert "010120" in codes
        assert "298040" in codes
        assert "267260" in codes

    def test_skips_empty_rows(self):
        soup = BeautifulSoup(ETF_HOLDINGS_HTML, "html.parser")
        holdings = self.collector._parse_holdings_table(soup)

        assert all(h["stock_code"] for h in holdings)

    def test_returns_empty_when_no_table(self):
        soup = BeautifulSoup(NO_NAV_HTML, "html.parser")
        holdings = self.collector._parse_holdings_table(soup)
        assert holdings == []

    def test_limit_to_10_holdings(self):
        """구성종목은 최대 10개만 수집한다."""
        rows_html = "\n".join(
            f'<tr><td><a href="/item/main.naver?code=00{i:04d}">종목{i}</a></td>'
            f'<td>{i * 100}</td><td>{i * 2}.0%</td>'
            f'<td>10,000</td><td>100</td><td>+1.0%</td></tr>'
            for i in range(1, 16)
        )
        html = f'<html><body><table class="tb_type1 tb_type1_a"><tbody>{rows_html}</tbody></table></body></html>'
        soup = BeautifulSoup(html, "html.parser")
        holdings = self.collector._parse_holdings_table(soup)
        assert len(holdings) <= 10


# ───────────────────────────────────────
# collect_all (모킹)
# ───────────────────────────────────────

class TestCollectAll:
    """fetch_main_page와 DB를 모킹하여 전체 흐름 검증."""

    @patch("app.services.etf_fundamentals_collector.fetch_main_page")
    @patch("app.services.etf_fundamentals_collector.get_db_connection")
    def test_collect_all_success(self, mock_db, mock_fetch):
        """정상 HTML이면 nav와 holdings 모두 True를 반환한다."""
        soup = BeautifulSoup(ETF_FULL_HTML, "html.parser")
        mock_fetch.return_value = soup

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db.return_value = mock_conn

        collector = ETFFundamentalsCollector()
        result = collector.collect_all("487240")

        assert result["nav"] is True
        assert result["holdings"] is True
        assert result["distributions"] is True   # no-op
        assert result["rebalancing"] is True      # no-op

    @patch("app.services.etf_fundamentals_collector.fetch_main_page")
    def test_collect_all_returns_false_on_fetch_failure(self, mock_fetch):
        """페이지 수집 실패 시 nav=False를 반환한다."""
        mock_fetch.return_value = None

        collector = ETFFundamentalsCollector()
        result = collector.collect_all("487240")

        assert result["nav"] is False
        assert result["holdings"] is False

    @patch("app.services.etf_fundamentals_collector.fetch_main_page")
    @patch("app.services.etf_fundamentals_collector.get_db_connection")
    def test_distributions_is_noop(self, mock_db, mock_fetch):
        """collect_distributions는 항상 True를 반환한다 (no-op)."""
        mock_fetch.return_value = MagicMock()
        collector = ETFFundamentalsCollector()
        assert collector.collect_distributions("487240") is True

    @patch("app.services.etf_fundamentals_collector.fetch_main_page")
    @patch("app.services.etf_fundamentals_collector.get_db_connection")
    def test_rebalancing_is_noop(self, mock_db, mock_fetch):
        """collect_rebalancing는 항상 True를 반환한다 (no-op)."""
        mock_fetch.return_value = MagicMock()
        collector = ETFFundamentalsCollector()
        assert collector.collect_rebalancing("487240") is True

    @patch("app.services.etf_fundamentals_collector.fetch_main_page")
    @patch("app.services.etf_fundamentals_collector.get_db_connection")
    def test_fetches_page_only_once(self, mock_db, mock_fetch):
        """collect_all은 main 페이지를 한 번만 요청한다."""
        soup = BeautifulSoup(ETF_FULL_HTML, "html.parser")
        mock_fetch.return_value = soup

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = MagicMock()
        mock_db.return_value = mock_conn

        collector = ETFFundamentalsCollector()
        collector.collect_all("487240")

        assert mock_fetch.call_count == 1
