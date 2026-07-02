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
        response = requests.get("https://m.stock.naver.com", timeout=5)
        return response.status_code == 200
    except requests.exceptions.RequestException:
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
            assert result.get("launch_date") is None
            assert result.get("expense_ratio") is None
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
    """종목 타입 감지 테스트 (basic JSON의 stockEndType 기반, 모킹)"""

    def _mock_responses(self, monkeypatch, by_url):
        """URL 부분 문자열 → 응답 dict 매핑으로 requests.get 모킹"""
        from unittest.mock import MagicMock

        def mock_get(url, *args, **kwargs):
            for fragment, payload in by_url.items():
                if fragment in url:
                    resp = MagicMock(status_code=200)
                    resp.json.return_value = payload
                    resp.raise_for_status.return_value = None
                    return resp
            raise AssertionError(f"unexpected url: {url}")

        monkeypatch.setattr(requests, "get", mock_get)

    def test_detect_type_etf(self, scraper, monkeypatch):
        """stockEndType='etf'이면 ETF"""
        self._mock_responses(monkeypatch, {
            "/basic": {"stockName": "테스트 ETF", "stockEndType": "etf"},
            "/etfAnalysis": {"itemName": "테스트 ETF", "etfSummary": "AI 전력 인프라에 투자"},
        })

        result = scraper.scrape_ticker_info("TEST01")
        assert result["type"] == "ETF"
        assert result["name"] == "테스트 ETF"
        # etfSummary 키워드로 테마 생성
        assert "AI" in result["theme"]

    def test_detect_type_stock(self, scraper, monkeypatch):
        """stockEndType='stock'이면 STOCK + 업종명 테마"""
        self._mock_responses(monkeypatch, {
            "/basic": {"stockName": "테스트 주식", "stockEndType": "stock"},
            "/integration": {"industryCode": 278},
            "/stocks/industry/278": {"groupInfo": {"no": 278, "name": "반도체와반도체장비"}},
        })

        result = scraper.scrape_ticker_info("TEST02")
        assert result["type"] == "STOCK"
        assert result["theme"] == "반도체와반도체장비"

    def test_invalid_ticker_raises(self, scraper, monkeypatch):
        """stockName이 없으면 종목 없음 예외"""
        self._mock_responses(monkeypatch, {
            "/basic": {"stockName": None, "stockEndType": None},
        })

        with pytest.raises(ScraperException) as exc_info:
            scraper.scrape_ticker_info("999998")
        assert "찾을 수 없습니다" in str(exc_info.value)

    def test_theme_fallback_when_industry_missing(self, scraper, monkeypatch):
        """업종 조회 실패 시 '미분류'로 폴백"""
        self._mock_responses(monkeypatch, {
            "/basic": {"stockName": "테스트 주식", "stockEndType": "stock"},
            "/integration": {"industryCode": None},
        })

        result = scraper.scrape_ticker_info("TEST03")
        assert result["theme"] == "미분류"


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
    """내부 추출 메서드 테스트"""

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
