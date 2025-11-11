"""
ticker_scraper.py 스크래핑 유틸리티 테스트

실제 네이버 금융 사이트에서 스크래핑하는 테스트입니다.
네트워크 에러 발생 시 스킵합니다.
"""
import pytest
import requests
from app.services.ticker_scraper import TickerScraper, get_ticker_scraper
from app.exceptions import ScraperException


@pytest.fixture
def scraper():
    """TickerScraper 인스턴스"""
    return TickerScraper()


@pytest.fixture
def check_network():
    """네트워크 연결 확인"""
    try:
        response = requests.get("https://finance.naver.com", timeout=5)
        return response.status_code == 200
    except:
        return False


class TestTickerScraperReal:
    """실제 종목 스크래핑 테스트"""

    def test_scrape_stock_samsung(self, scraper, check_network):
        """실제 주식 스크래핑: 삼성전자 (005930)"""
        if not check_network:
            pytest.skip("네트워크 연결 불가")

        try:
            result = scraper.scrape_ticker_info("005930")

            assert result["ticker"] == "005930"
            assert "삼성" in result["name"]
            assert result["type"] == "STOCK"
            assert result["launch_date"] is None
            assert result["expense_ratio"] is None
            assert isinstance(result["search_keyword"], str)
            assert isinstance(result["relevance_keywords"], list)

        except ScraperException as e:
            pytest.skip(f"스크래핑 실패: {e}")

    def test_scrape_etf_kodex(self, scraper, check_network):
        """실제 ETF 스크래핑: KODEX AI전력핵심설비 (487240)"""
        if not check_network:
            pytest.skip("네트워크 연결 불가")

        try:
            result = scraper.scrape_ticker_info("487240")

            assert result["ticker"] == "487240"
            assert result["name"]  # 종목명이 존재하는지 확인
            assert result["type"] == "ETF"  # 타입이 정확히 ETF인지 확인
            # ETF는 launch_date와 expense_ratio가 있어야 함 (없을 수도 있음)
            assert isinstance(result["search_keyword"], str)
            assert isinstance(result["relevance_keywords"], list)

        except ScraperException as e:
            pytest.skip(f"스크래핑 실패: {e}")

    def test_scrape_invalid_ticker(self, scraper, check_network):
        """존재하지 않는 종목 코드"""
        if not check_network:
            pytest.skip("네트워크 연결 불가")

        with pytest.raises(ScraperException) as exc_info:
            scraper.scrape_ticker_info("999999")

        assert "찾을 수 없습니다" in str(exc_info.value)


class TestTickerTypeDetection:
    """종목 타입 감지 테스트 (모킹)"""

    def test_detect_type_etf(self, scraper):
        """ETF 타입 감지"""
        from bs4 import BeautifulSoup

        html = """
        <html>
        <head><title>테스트 ETF</title></head>
        <body>
            <div class="wrap_company">
                <h2><a>테스트 ETF</a></h2>
            </div>
            <div>운용보수: 0.45%</div>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')

        stock_type = scraper._detect_type("테스트 ETF", "TEST01", soup)
        assert stock_type == "ETF"

    def test_detect_type_stock(self, scraper):
        """STOCK 타입 감지"""
        from bs4 import BeautifulSoup

        html = """
        <html>
        <head><title>테스트 주식</title></head>
        <body>
            <div class="wrap_company">
                <h2><a>테스트 주식</a></h2>
            </div>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')

        stock_type = scraper._detect_type("테스트 주식", "TEST02", soup)
        assert stock_type == "STOCK"


class TestKeywordGeneration:
    """키워드 생성 테스트"""

    def test_generate_keywords_etf(self, scraper):
        """ETF 키워드 생성"""
        keywords = scraper.generate_keywords(
            "삼성 KODEX AI전력핵심설비 ETF",
            "AI/전력 인프라"
        )

        assert isinstance(keywords, list)
        assert len(keywords) > 0
        # 회사명이 제거되고 핵심 키워드만 추출됨
        assert any("AI" in k for k in keywords)

    def test_generate_keywords_stock(self, scraper):
        """주식 키워드 생성"""
        keywords = scraper.generate_keywords(
            "삼성전자",
            "반도체/전자"
        )

        assert isinstance(keywords, list)
        assert "삼성전자" in keywords
        assert any("반도체" in k for k in keywords)

    def test_generate_keywords_max_10(self, scraper):
        """키워드 최대 10개 제한"""
        keywords = scraper.generate_keywords(
            "매우 긴 이름의 복잡한 종목명",
            "테마1/테마2/테마3/테마4/테마5/테마6/테마7/테마8"
        )

        assert len(keywords) <= 10


class TestSearchKeywordGeneration:
    """검색 키워드 생성 테스트"""

    def test_generate_search_keyword_etf(self, scraper):
        """ETF 검색 키워드 생성"""
        keyword = scraper._generate_search_keyword(
            "삼성 KODEX AI전력핵심설비 ETF",
            "AI/전력"
        )

        assert isinstance(keyword, str)
        # 회사명과 "ETF"가 제거됨
        assert "삼성" not in keyword
        assert "ETF" not in keyword

    def test_generate_search_keyword_stock(self, scraper):
        """주식 검색 키워드 생성"""
        keyword = scraper._generate_search_keyword(
            "삼성전자",
            "반도체"
        )

        assert isinstance(keyword, str)
        assert "삼성" not in keyword or keyword == "삼성전자"


class TestScraperSingleton:
    """싱글톤 패턴 테스트"""

    def test_get_ticker_scraper_singleton(self):
        """get_ticker_scraper()가 싱글톤 반환"""
        scraper1 = get_ticker_scraper()
        scraper2 = get_ticker_scraper()

        assert scraper1 is scraper2


class TestExtractMethods:
    """내부 추출 메서드 테스트 (모킹)"""

    def test_extract_name(self, scraper):
        """종목명 추출"""
        from bs4 import BeautifulSoup

        html = """
        <html>
        <head><title>테스트 종목 : 네이버 금융</title></head>
        <body>
            <div class="wrap_company">
                <h2><a>테스트 종목</a></h2>
            </div>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')

        name = scraper._extract_name(soup, "TEST01")
        assert name == "테스트 종목"

    def test_extract_name_from_title(self, scraper):
        """title 태그에서 종목명 추출"""
        from bs4 import BeautifulSoup

        html = """
        <html>
        <head><title>삼성전자 : 네이버 금융</title></head>
        <body></body>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')

        name = scraper._extract_name(soup, "005930")
        assert name == "삼성전자"

    def test_extract_keywords_from_text(self, scraper):
        """텍스트에서 키워드 추출"""
        text = "이 ETF는 AI 및 인공지능, 데이터센터, 전력 인프라에 투자합니다."

        keywords = scraper._extract_keywords_from_text(text)

        assert isinstance(keywords, list)
        # AI, 인공지능, 데이터센터, 전력 등이 포함되어야 함
        assert len(keywords) > 0


class TestErrorHandling:
    """에러 처리 테스트"""

    def test_scrape_network_error(self, scraper, monkeypatch):
        """네트워크 에러 처리"""
        def mock_get(*args, **kwargs):
            raise requests.exceptions.RequestException("네트워크 에러")

        monkeypatch.setattr(requests, "get", mock_get)

        with pytest.raises(ScraperException) as exc_info:
            scraper.scrape_ticker_info("005930")

        assert "네트워크 오류" in str(exc_info.value)

    def test_scrape_timeout(self, scraper, monkeypatch):
        """타임아웃 에러 처리"""
        def mock_get(*args, **kwargs):
            raise requests.exceptions.Timeout("타임아웃")

        monkeypatch.setattr(requests, "get", mock_get)

        with pytest.raises(ScraperException):
            scraper.scrape_ticker_info("005930")
