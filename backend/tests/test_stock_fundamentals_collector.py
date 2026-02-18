"""
stock_fundamentals_collector.py 단위 테스트

HTML fixture를 사용하여 실제 네트워크 없이 파싱 로직을 검증합니다.
"""
import pytest
from datetime import date
from unittest.mock import patch, MagicMock
from bs4 import BeautifulSoup

from app.services.stock_fundamentals_collector import (
    _parse_number,
    _find_fundamentals_table,
    _get_latest_annual_idx,
    collect_stock_fundamentals,
)


# ───────────────────────────────────────
# HTML 픽스처 (삼성전자 구조 모방)
# ───────────────────────────────────────

STOCK_MAIN_HTML = """
<html><body>
<table class="tb_type1 tb_num tb_type1_ifrs" summary="기업실적분석에 관한표">
  <thead>
    <tr>
      <th>주요재무정보</th>
      <th colspan="4">최근 연간 실적</th>
      <th colspan="4">최근 분기 실적</th>
    </tr>
    <tr>
      <th>2022.12</th><th>2023.12</th><th>2024.12</th><th>2025.12(E)</th>
      <th>2024.09</th><th>2024.12</th><th>2025.03</th><th>2025.06(E)</th>
    </tr>
    <tr>
      <th>IFRS연결</th><th>IFRS연결</th><th>IFRS연결</th><th>IFRS연결</th>
      <th>IFRS연결</th><th>IFRS연결</th><th>IFRS연결</th><th>IFRS연결</th>
    </tr>
  </thead>
  <tbody>
    <tr><th>매출액</th><td>3,022,314</td><td>2,589,355</td><td>3,008,709</td><td>3,291,027</td><td>790,987</td><td>757,883</td><td>791,405</td><td>745,663</td></tr>
    <tr><th>영업이익</th><td>433,766</td><td>65,670</td><td>327,260</td><td>401,605</td><td>91,834</td><td>64,927</td><td>66,853</td><td>46,761</td></tr>
    <tr><th>당기순이익</th><td>556,541</td><td>154,871</td><td>344,514</td><td>398,255</td><td>101,009</td><td>77,544</td><td>82,229</td><td>51,164</td></tr>
    <tr><th>영업이익률</th><td>14.35</td><td>2.54</td><td>10.88</td><td>12.20</td><td>11.61</td><td>8.57</td><td>8.45</td><td>6.27</td></tr>
    <tr><th>순이익률</th><td>18.41</td><td>5.98</td><td>11.45</td><td>12.10</td><td>12.77</td><td>10.23</td><td>10.39</td><td>6.86</td></tr>
    <tr><th>ROE(지배주주)</th><td>17.07</td><td>4.15</td><td>9.03</td><td>9.53</td><td>8.79</td><td>9.03</td><td>9.24</td><td>7.95</td></tr>
    <tr><th>부채비율</th><td>26.41</td><td>25.36</td><td>27.93</td><td>-</td><td>27.19</td><td>27.93</td><td>26.99</td><td>26.36</td></tr>
    <tr><th>당좌비율</th><td>211.68</td><td>189.46</td><td>187.80</td><td>-</td><td>190.56</td><td>187.80</td><td>187.68</td><td>190.87</td></tr>
    <tr><th>EPS(원)</th><td>8,057</td><td>2,131</td><td>4,950</td><td>5,727</td><td>1,440</td><td>1,115</td><td>1,186</td><td>733</td></tr>
    <tr><th>PER(배)</th><td>6.86</td><td>36.84</td><td>10.75</td><td>22.44</td><td>13.03</td><td>10.75</td><td>11.20</td><td>13.36</td></tr>
    <tr><th>BPS(원)</th><td>50,817</td><td>52,002</td><td>57,981</td><td>63,204</td><td>55,376</td><td>57,981</td><td>59,059</td><td>58,135</td></tr>
    <tr><th>PBR(배)</th><td>1.09</td><td>1.51</td><td>0.92</td><td>2.03</td><td>1.11</td><td>0.92</td><td>0.98</td><td>1.03</td></tr>
    <tr><th>주당배당금(원)</th><td>1,444</td><td>1,444</td><td>1,446</td><td>1,527</td><td>361</td><td>363</td><td>365</td><td>367</td></tr>
    <tr><th>시가배당률(%)</th><td>2.61</td><td>1.84</td><td>2.72</td><td>-</td><td>0.59</td><td>0.68</td><td>0.63</td><td>0.61</td></tr>
    <tr><th>배당성향(%)</th><td>17.92</td><td>67.78</td><td>29.18</td><td>-</td><td>25.07</td><td>32.40</td><td>30.48</td><td>49.73</td></tr>
  </tbody>
</table>
</body></html>
"""

# 모든 열이 (E) 추정치인 극단적 케이스
ALL_ESTIMATE_HTML = """
<html><body>
<table class="tb_type1 tb_num tb_type1_ifrs">
  <thead>
    <tr>
      <th>주요재무정보</th>
      <th colspan="2">최근 연간 실적</th>
    </tr>
    <tr>
      <th>2025.12(E)</th><th>2026.12(E)</th>
    </tr>
  </thead>
  <tbody>
    <tr><th>매출액</th><td>3,000,000</td><td>3,200,000</td></tr>
  </tbody>
</table>
</body></html>
"""


# ───────────────────────────────────────
# _parse_number 테스트
# ───────────────────────────────────────

class TestParseNumber:
    def test_comma_separated(self):
        assert _parse_number("3,022,314") == 3022314.0

    def test_plain_float(self):
        assert _parse_number("10.88") == 10.88

    def test_empty_string(self):
        assert _parse_number("") is None

    def test_dash(self):
        assert _parse_number("-") is None

    def test_invalid_text(self):
        assert _parse_number("N/A") is None

    def test_positive_with_plus(self):
        assert _parse_number("+0.37") == 0.37

    def test_percent_value(self):
        # stock_fundamentals_collector._parse_number은 % 기호를 처리하지 않는다.
        # 실제 테이블 값은 이미 숫자("10.88")로 노출되므로 None이 올바른 동작.
        assert _parse_number("10.88%") is None


# ───────────────────────────────────────
# _parse_date 테스트 (stock_fundamentals_collector에 없으나
#  etf_fundamentals_collector 공용 헬퍼와 동일한 로직 검증)
# ───────────────────────────────────────

class TestParseDate:
    def test_dot_format(self):
        from app.services.etf_fundamentals_collector import _parse_date as etf_parse_date
        d = etf_parse_date("2026.02.13")
        assert d == date(2026, 2, 13)

    def test_dash_format(self):
        from app.services.etf_fundamentals_collector import _parse_date as etf_parse_date
        d = etf_parse_date("2026-02-13")
        assert d == date(2026, 2, 13)

    def test_invalid(self):
        from app.services.etf_fundamentals_collector import _parse_date as etf_parse_date
        assert etf_parse_date("invalid") is None

    def test_empty(self):
        from app.services.etf_fundamentals_collector import _parse_date as etf_parse_date
        assert etf_parse_date("") is None


# ───────────────────────────────────────
# _find_fundamentals_table 테스트
# ───────────────────────────────────────

class TestFindFundamentalsTable:
    def test_finds_ifrs_table(self):
        soup = BeautifulSoup(STOCK_MAIN_HTML, "html.parser")
        table = _find_fundamentals_table(soup)
        assert table is not None

    def test_returns_none_when_no_table(self):
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")
        table = _find_fundamentals_table(soup)
        assert table is None

    def test_fallback_summary_attribute(self):
        html = """
        <html><body>
        <table summary="기업실적분석 테이블">
          <thead><tr><th>x</th></tr></thead>
          <tbody></tbody>
        </table>
        </body></html>
        """
        soup = BeautifulSoup(html, "html.parser")
        table = _find_fundamentals_table(soup)
        assert table is not None


# ───────────────────────────────────────
# _get_latest_annual_idx 테스트
# ───────────────────────────────────────

class TestGetLatestAnnualIdx:
    def test_returns_non_estimate_column(self):
        """(E) 없는 가장 최신 연간 열을 반환한다."""
        soup = BeautifulSoup(STOCK_MAIN_HTML, "html.parser")
        table = _find_fundamentals_table(soup)
        idx = _get_latest_annual_idx(table)
        # 연간 4개 중 3번째(index 2) = 2024.12 (마지막 실제 데이터)
        assert idx == 2

    def test_all_estimate_returns_fallback(self):
        """모두 (E)이면 마지막-1 인덱스(또는 None)를 반환한다."""
        soup = BeautifulSoup(ALL_ESTIMATE_HTML, "html.parser")
        table = _find_fundamentals_table(soup)
        idx = _get_latest_annual_idx(table)
        # 실제 데이터가 없으면 None
        assert idx is None


# ───────────────────────────────────────
# collect_stock_fundamentals (모킹)
# ───────────────────────────────────────

class TestCollectStockFundamentals:
    """fetch_main_page와 DB를 모킹하여 전체 흐름 검증."""

    @patch("app.services.stock_fundamentals_collector.fetch_main_page")
    @patch("app.services.stock_fundamentals_collector.get_db_connection")
    def test_success_flow(self, mock_db, mock_fetch):
        """정상 HTML이 주어지면 성공 결과를 반환한다."""
        soup = BeautifulSoup(STOCK_MAIN_HTML, "html.parser")
        mock_fetch.return_value = soup

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db.return_value = mock_conn

        result = collect_stock_fundamentals("005930")

        assert result["success"] is True
        assert result["ticker"] == "005930"
        assert result["saved"] is True
        # INSERT가 호출됐는지 확인
        assert mock_cursor.execute.called

    @patch("app.services.stock_fundamentals_collector.fetch_main_page")
    def test_returns_error_when_fetch_fails(self, mock_fetch):
        """페이지 수집 실패 시 success=False를 반환한다."""
        mock_fetch.return_value = None

        result = collect_stock_fundamentals("005930")

        assert result["success"] is False
        assert "error" in result

    @patch("app.services.stock_fundamentals_collector.fetch_main_page")
    def test_returns_error_when_no_table(self, mock_fetch):
        """기업실적분석 테이블이 없는 HTML이면 error를 반환한다."""
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")
        mock_fetch.return_value = soup

        result = collect_stock_fundamentals("005930")

        assert result["success"] is False

    @patch("app.services.stock_fundamentals_collector.fetch_main_page")
    @patch("app.services.stock_fundamentals_collector.get_db_connection")
    def test_parses_correct_annual_values(self, mock_db, mock_fetch):
        """최신 연간 열(2024.12 기준)의 값이 올바르게 파싱된다."""
        soup = BeautifulSoup(STOCK_MAIN_HTML, "html.parser")
        mock_fetch.return_value = soup

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db.return_value = mock_conn

        collect_stock_fundamentals("005930")

        # INSERT 호출 인수 확인
        call_args = mock_cursor.execute.call_args_list[0]
        params = call_args[0][1]  # (sql, params) 중 params

        ticker = params[0]
        assert ticker == "005930"

        # 2024.12 기준 per=10.75, pbr=0.92, roe=9.03, eps=4950, bps=57981
        per_idx = 2   # ticker, date, per, pbr, roe, roa, eps, bps, revenue, ...
        pbr_idx = 3
        roe_idx = 4
        eps_idx = 6
        bps_idx = 7
        revenue_idx = 8

        assert params[per_idx] == pytest.approx(10.75)
        assert params[pbr_idx] == pytest.approx(0.92)
        assert params[roe_idx] == pytest.approx(9.03)
        assert params[eps_idx] == pytest.approx(4950.0)
        assert params[bps_idx] == pytest.approx(57981.0)
        assert params[revenue_idx] == pytest.approx(3008709.0)

    @patch("app.services.stock_fundamentals_collector.fetch_main_page")
    @patch("app.services.stock_fundamentals_collector.get_db_connection")
    def test_saves_dividend_distribution(self, mock_db, mock_fetch):
        """주당배당금이 있으면 stock_distributions에도 저장한다."""
        soup = BeautifulSoup(STOCK_MAIN_HTML, "html.parser")
        mock_fetch.return_value = soup

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db.return_value = mock_conn

        result = collect_stock_fundamentals("005930")

        assert result["dividend_saved"] is True
        # execute 호출 횟수: fundamentals + distributions = 2
        assert mock_cursor.execute.call_count == 2
