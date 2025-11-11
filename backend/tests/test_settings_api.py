"""
Settings API 엔드포인트 통합 테스트
"""
import pytest
import json
import tempfile
import shutil
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app
from app.config import Config
from app.database import init_db, get_db_connection

client = TestClient(app)


@pytest.fixture
def temp_stocks_config():
    """임시 stocks.json 파일 설정"""
    temp_dir = tempfile.mkdtemp()
    temp_file = Path(temp_dir) / "stocks.json"

    # 초기 테스트 데이터
    test_data = {
        "TEST01": {
            "name": "테스트 ETF",
            "type": "ETF",
            "theme": "테스트",
            "launch_date": "2024-01-01",
            "expense_ratio": 0.005,
            "search_keyword": "테스트",
            "relevance_keywords": ["테스트", "ETF"]
        },
        "TEST02": {
            "name": "테스트 주식",
            "type": "STOCK",
            "theme": "테스트",
            "launch_date": None,
            "expense_ratio": None,
            "search_keyword": "테스트 주식",
            "relevance_keywords": ["테스트", "주식"]
        }
    }

    with open(temp_file, 'w', encoding='utf-8') as f:
        json.dump(test_data, f, indent=2, ensure_ascii=False)

    # Config 경로 임시 변경
    original_path = Config.STOCK_CONFIG_PATH
    Config.STOCK_CONFIG_PATH = str(temp_file)
    Config._stock_config_cache = None

    # DB 초기화 및 동기화
    init_db()
    from app.utils.stocks_manager import sync_stocks_to_db
    sync_stocks_to_db()

    yield temp_file

    # 복원
    Config.STOCK_CONFIG_PATH = original_path
    Config._stock_config_cache = None
    shutil.rmtree(temp_dir)


class TestCreateStock:
    """POST /api/settings/stocks - 종목 추가"""

    def test_create_stock_success(self, temp_stocks_config):
        """종목 추가 성공"""
        payload = {
            "ticker": "TEST03",
            "name": "새 종목",
            "type": "STOCK",
            "theme": "신규",
            "launch_date": None,
            "expense_ratio": None,
            "search_keyword": "새 종목",
            "relevance_keywords": ["새", "종목"]
        }

        response = client.post("/api/settings/stocks", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["ticker"] == "TEST03"
        assert data["name"] == "새 종목"
        assert "message" in data

        # stocks.json 파일 확인
        with open(temp_stocks_config, 'r', encoding='utf-8') as f:
            stocks = json.load(f)
        assert "TEST03" in stocks

        # DB 확인
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM etfs WHERE ticker = 'TEST03'")
            row = cursor.fetchone()
        assert row is not None

    def test_create_etf_success(self, temp_stocks_config):
        """ETF 추가 성공"""
        payload = {
            "ticker": "TEST04",
            "name": "테스트 ETF 2",
            "type": "ETF",
            "theme": "AI/전력",
            "launch_date": "2024-03-01",
            "expense_ratio": 0.0045,
            "search_keyword": "AI 전력",
            "relevance_keywords": ["AI", "전력"]
        }

        response = client.post("/api/settings/stocks", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["ticker"] == "TEST04"

    def test_create_stock_duplicate_ticker(self, temp_stocks_config):
        """중복 티커 에러"""
        payload = {
            "ticker": "TEST01",  # 이미 존재하는 티커
            "name": "중복 종목",
            "type": "STOCK",
            "theme": "테스트",
            "search_keyword": "중복",
            "relevance_keywords": ["중복"]
        }

        response = client.post("/api/settings/stocks", json=payload)

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_create_stock_missing_required_field(self, temp_stocks_config):
        """필수 필드 누락"""
        payload = {
            "ticker": "TEST05",
            "type": "STOCK",
            "theme": "테스트"
            # name 누락
        }

        response = client.post("/api/settings/stocks", json=payload)

        assert response.status_code == 422  # Pydantic validation error

    def test_create_etf_missing_launch_date(self, temp_stocks_config):
        """ETF launch_date 누락"""
        payload = {
            "ticker": "TEST06",
            "name": "ETF without date",
            "type": "ETF",
            "theme": "테스트",
            "expense_ratio": 0.005
            # launch_date 누락
        }

        response = client.post("/api/settings/stocks", json=payload)

        # ValidationException으로 400 반환
        assert response.status_code == 400


class TestUpdateStock:
    """PUT /api/settings/stocks/{ticker} - 종목 수정"""

    def test_update_stock_success(self, temp_stocks_config):
        """종목 수정 성공"""
        payload = {
            "name": "수정된 이름",
            "theme": "수정된 테마"
        }

        response = client.put("/api/settings/stocks/TEST01", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "TEST01"
        assert "message" in data

        # stocks.json 파일 확인
        with open(temp_stocks_config, 'r', encoding='utf-8') as f:
            stocks = json.load(f)
        assert stocks["TEST01"]["name"] == "수정된 이름"
        assert stocks["TEST01"]["theme"] == "수정된 테마"

        # DB 확인
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM etfs WHERE ticker = 'TEST01'")
            row = cursor.fetchone()
        assert row['name'] == "수정된 이름"

    def test_update_stock_partial(self, temp_stocks_config):
        """부분 업데이트"""
        payload = {
            "theme": "새로운 테마만 수정"
        }

        response = client.put("/api/settings/stocks/TEST02", json=payload)

        assert response.status_code == 200

        # name은 변경되지 않았는지 확인
        with open(temp_stocks_config, 'r', encoding='utf-8') as f:
            stocks = json.load(f)
        assert stocks["TEST02"]["name"] == "테스트 주식"  # 원래 값 유지
        assert stocks["TEST02"]["theme"] == "새로운 테마만 수정"

    def test_update_stock_not_found(self, temp_stocks_config):
        """존재하지 않는 종목 수정"""
        payload = {
            "name": "수정"
        }

        response = client.put("/api/settings/stocks/NONEXISTENT", json=payload)

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


class TestDeleteStock:
    """DELETE /api/settings/stocks/{ticker} - 종목 삭제"""

    def test_delete_stock_success(self, temp_stocks_config):
        """종목 삭제 성공"""
        # 가격 데이터 추가
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO prices (ticker, date, close_price, volume)
                VALUES ('TEST01', '2024-01-01', 10000, 100000)
            """)
            conn.commit()

        response = client.delete("/api/settings/stocks/TEST01")

        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "TEST01"
        assert "deleted" in data
        assert data["deleted"]["prices"] == 1

        # stocks.json 파일 확인
        with open(temp_stocks_config, 'r', encoding='utf-8') as f:
            stocks = json.load(f)
        assert "TEST01" not in stocks

        # DB 확인
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM etfs WHERE ticker = 'TEST01'")
            row = cursor.fetchone()
        assert row is None

    def test_delete_stock_cascade(self, temp_stocks_config):
        """CASCADE 삭제 확인"""
        # 여러 관련 데이터 추가
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO prices (ticker, date, close_price, volume)
                VALUES ('TEST02', '2024-01-01', 10000, 100000),
                       ('TEST02', '2024-01-02', 10100, 110000)
            """)
            cursor.execute("""
                INSERT INTO news (ticker, date, title, url, source)
                VALUES ('TEST02', '2024-01-01', '뉴스', 'http://example.com', 'source')
            """)
            conn.commit()

        response = client.delete("/api/settings/stocks/TEST02")

        assert response.status_code == 200
        data = response.json()
        assert data["deleted"]["prices"] == 2
        assert data["deleted"]["news"] == 1

    def test_delete_stock_not_found(self, temp_stocks_config):
        """존재하지 않는 종목 삭제"""
        response = client.delete("/api/settings/stocks/NONEXISTENT")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


class TestValidateTicker:
    """GET /api/settings/stocks/{ticker}/validate - 종목 검증"""

    def test_validate_ticker_mock_success(self, temp_stocks_config, monkeypatch):
        """종목 검증 성공 (모킹)"""
        from app.services import ticker_scraper

        def mock_scrape_ticker_info(ticker):
            return {
                "ticker": ticker,
                "name": "모킹된 종목",
                "type": "STOCK",
                "theme": "테스트",
                "launch_date": None,
                "expense_ratio": None,
                "search_keyword": "모킹",
                "relevance_keywords": ["모킹", "테스트"]
            }

        # TickerScraper의 scrape_ticker_info 메서드 모킹
        scraper_instance = ticker_scraper.get_ticker_scraper()
        monkeypatch.setattr(scraper_instance, "scrape_ticker_info", mock_scrape_ticker_info)

        response = client.get("/api/settings/stocks/TEST99/validate")

        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "TEST99"
        assert data["name"] == "모킹된 종목"
        assert data["type"] == "STOCK"

    def test_validate_ticker_not_found(self, temp_stocks_config, monkeypatch):
        """종목을 찾을 수 없음"""
        from app.services import ticker_scraper
        from app.exceptions import ScraperException

        def mock_scrape_ticker_info(ticker):
            raise ScraperException(f"종목을 찾을 수 없습니다: {ticker}")

        scraper_instance = ticker_scraper.get_ticker_scraper()
        monkeypatch.setattr(scraper_instance, "scrape_ticker_info", mock_scrape_ticker_info)

        response = client.get("/api/settings/stocks/INVALID/validate")

        assert response.status_code == 404
        assert "찾을 수 없습니다" in response.json()["detail"]

    def test_validate_ticker_scraping_error(self, temp_stocks_config, monkeypatch):
        """스크래핑 에러"""
        from app.services import ticker_scraper
        from app.exceptions import ScraperException

        def mock_scrape_ticker_info(ticker):
            raise ScraperException("네트워크 오류")

        scraper_instance = ticker_scraper.get_ticker_scraper()
        monkeypatch.setattr(scraper_instance, "scrape_ticker_info", mock_scrape_ticker_info)

        response = client.get("/api/settings/stocks/TEST99/validate")

        assert response.status_code == 500


class TestConfigCacheReload:
    """Config 캐시 갱신 테스트"""

    def test_config_reloaded_after_create(self, temp_stocks_config):
        """종목 추가 후 Config 캐시 갱신"""
        payload = {
            "ticker": "CACHE01",
            "name": "캐시 테스트",
            "type": "STOCK",
            "theme": "테스트",
            "search_keyword": "캐시",
            "relevance_keywords": ["캐시"]
        }

        response = client.post("/api/settings/stocks", json=payload)
        assert response.status_code == 201

        # Config에서 새 종목 조회 가능
        config = Config.get_stock_config()
        assert "CACHE01" in config

    def test_config_reloaded_after_delete(self, temp_stocks_config):
        """종목 삭제 후 Config 캐시 갱신"""
        response = client.delete("/api/settings/stocks/TEST01")
        assert response.status_code == 200

        # Config에서 삭제된 종목 확인
        config = Config.get_stock_config()
        assert "TEST01" not in config
