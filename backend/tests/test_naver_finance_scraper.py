"""
naver_finance_scraper.py 단위 테스트

fetch_main_page()의 HTTP 요청·응답·파싱 로직을 검증합니다.
실제 네트워크 요청이 필요한 테스트는 network 마킹 후 스킵 처리합니다.
"""
import pytest
import requests
from unittest.mock import patch, MagicMock
from bs4 import BeautifulSoup

from app.services.naver_finance_scraper import fetch_main_page


# ───────────────────────────────────────
# Fixtures
# ───────────────────────────────────────

@pytest.fixture
def check_network():
    """네이버 금융 접속 가능 여부 확인."""
    try:
        r = requests.get("https://finance.naver.com", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


MINIMAL_HTML = """
<html>
<head><title>test</title></head>
<body>
  <h4>NAV</h4>
  <table>
    <tr><td>2026.02.13</td><td>29835</td><td>29726</td><td>+0.37%</td></tr>
  </table>
</body>
</html>
"""


# ───────────────────────────────────────
# 모킹 테스트
# ───────────────────────────────────────

class TestFetchMainPageMocked:
    """HTTP 요청을 모킹한 fetch_main_page 테스트."""

    @patch("app.services.naver_finance_scraper.requests.get")
    def test_returns_soup_on_success(self, mock_get):
        """정상 응답이면 BeautifulSoup 객체를 반환한다."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = MINIMAL_HTML
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        soup = fetch_main_page("487240")

        assert soup is not None
        assert isinstance(soup, BeautifulSoup)

    @patch("app.services.naver_finance_scraper.requests.get")
    def test_returns_none_on_http_error(self, mock_get):
        """HTTP 에러(4xx/5xx)가 발생하면 None을 반환한다."""
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError("404")
        mock_get.return_value = mock_resp

        soup = fetch_main_page("000000")

        assert soup is None

    @patch("app.services.naver_finance_scraper.requests.get")
    def test_returns_none_on_connection_error(self, mock_get):
        """네트워크 오류가 발생하면 None을 반환한다 (retry 소진 후)."""
        mock_get.side_effect = requests.exceptions.ConnectionError("connection failed")

        # retry_with_backoff가 3회 시도하므로 최대 3번 호출됨
        soup = fetch_main_page("487240")

        assert soup is None

    @patch("app.services.naver_finance_scraper.requests.get")
    def test_encoding_set_to_euc_kr(self, mock_get):
        """응답 인코딩이 euc-kr로 설정되는지 확인한다."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "<html><body></body></html>"
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        fetch_main_page("005930")

        assert mock_resp.encoding == "euc-kr"

    @patch("app.services.naver_finance_scraper.requests.get")
    def test_correct_url_is_called(self, mock_get):
        """올바른 URL이 호출되는지 확인한다."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "<html><body></body></html>"
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        fetch_main_page("005930")

        call_url = mock_get.call_args[0][0]
        assert "finance.naver.com" in call_url
        assert "005930" in call_url


# ───────────────────────────────────────
# 실제 네트워크 테스트 (네트워크 있을 때만)
# ───────────────────────────────────────

class TestFetchMainPageReal:
    """실제 네이버 금융을 호출하는 통합 테스트."""

    def test_fetch_stock_page(self, check_network):
        """주식(삼성전자) main 페이지를 가져온다."""
        if not check_network:
            pytest.skip("네트워크 연결 불가")

        soup = fetch_main_page("005930")

        assert soup is not None
        # 기업실적분석 테이블 존재 확인
        table = soup.find("table", class_=lambda c: c and "tb_type1_ifrs" in c)
        assert table is not None, "기업실적분석 테이블이 없음"

    def test_fetch_etf_page(self, check_network):
        """ETF(KODEX AI전력) main 페이지를 가져온다."""
        if not check_network:
            pytest.skip("네트워크 연결 불가")

        soup = fetch_main_page("487240")

        assert soup is not None
        # ETF 페이지에 핵심 요소가 있는지 확인 (헤딩 또는 테이블)
        has_content = (
            soup.find(lambda tag: tag.name in ("h3", "h4") and "NAV" in tag.get_text()) is not None
            or soup.find("table") is not None
        )
        assert has_content, "ETF 페이지에 예상 컨텐츠가 없음"

    def test_fetch_invalid_ticker(self, check_network):
        """존재하지 않는 종목은 None 또는 빈 soup을 반환한다."""
        if not check_network:
            pytest.skip("네트워크 연결 불가")

        soup = fetch_main_page("000000")

        # 종목이 없어도 HTML은 반환되지만 핵심 테이블이 없어야 함
        # (None이거나 핵심 테이블이 비어 있어야 함)
        if soup is not None:
            table = soup.find("table", class_=lambda c: c and "tb_type1_ifrs" in c)
            assert table is None, "존재하지 않는 종목에 기업실적분석 테이블이 있으면 안 됨"
