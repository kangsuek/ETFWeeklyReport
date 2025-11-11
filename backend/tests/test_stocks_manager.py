"""
stocks_manager.py 유틸리티 테스트
"""
import pytest
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from app.utils.stocks_manager import (
    load_stocks,
    save_stocks,
    validate_stock_data,
    sync_stocks_to_db,
    delete_stock_from_db
)
from app.exceptions import ValidationException
from app.config import Config
from app.database import init_db, get_db_connection


@pytest.fixture
def temp_stocks_file():
    """임시 stocks.json 파일 생성"""
    temp_dir = tempfile.mkdtemp()
    temp_file = Path(temp_dir) / "stocks.json"

    # 테스트 데이터 작성
    test_data = {
        "TEST01": {
            "name": "테스트 ETF",
            "type": "ETF",
            "theme": "테스트",
            "launch_date": "2024-01-01",
            "expense_ratio": 0.005,
            "search_keyword": "테스트",
            "relevance_keywords": ["테스트", "ETF"]
        }
    }

    with open(temp_file, 'w', encoding='utf-8') as f:
        json.dump(test_data, f, indent=2, ensure_ascii=False)

    # Config 경로 임시 변경
    original_path = Config.STOCK_CONFIG_PATH
    Config.STOCK_CONFIG_PATH = str(temp_file)
    Config._stock_config_cache = None  # 캐시 초기화

    yield temp_file

    # 복원
    Config.STOCK_CONFIG_PATH = original_path
    Config._stock_config_cache = None
    shutil.rmtree(temp_dir)


@pytest.fixture(autouse=True)
def setup_db():
    """테스트용 DB 초기화"""
    init_db()
    yield


class TestLoadStocks:
    """load_stocks() 함수 테스트"""

    def test_load_stocks_success(self, temp_stocks_file):
        """stocks.json 파일 로드 성공"""
        stocks = load_stocks()

        assert isinstance(stocks, dict)
        assert "TEST01" in stocks
        assert stocks["TEST01"]["name"] == "테스트 ETF"

    def test_load_stocks_real_file(self):
        """실제 stocks.json 파일 로드"""
        # 임시 파일이 아닌 실제 파일 사용
        Config._stock_config_cache = None
        stocks = Config.get_stock_config()

        assert isinstance(stocks, dict)
        assert len(stocks) >= 6  # 최소 6개 종목
        assert "487240" in stocks


class TestSaveStocks:
    """save_stocks() 함수 테스트"""

    def test_save_stocks_success(self, temp_stocks_file):
        """stocks.json 파일 저장 성공"""
        new_data = {
            "TEST01": {
                "name": "수정된 ETF",
                "type": "ETF",
                "theme": "수정",
                "launch_date": "2024-02-01",
                "expense_ratio": 0.006,
                "search_keyword": "수정",
                "relevance_keywords": ["수정", "ETF"]
            }
        }

        save_stocks(new_data)

        # 저장된 파일 읽기
        with open(temp_stocks_file, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)

        assert saved_data["TEST01"]["name"] == "수정된 ETF"
        assert saved_data["TEST01"]["expense_ratio"] == 0.006

    def test_save_stocks_creates_backup(self, temp_stocks_file):
        """백업 파일 생성 확인"""
        new_data = {
            "TEST02": {
                "name": "새 종목",
                "type": "STOCK",
                "theme": "테스트",
                "launch_date": None,
                "expense_ratio": None,
                "search_keyword": "새 종목",
                "relevance_keywords": ["새", "종목"]
            }
        }

        save_stocks(new_data)

        # 백업 파일 존재 확인
        backup_files = list(temp_stocks_file.parent.glob("stocks.json.backup.*"))
        assert len(backup_files) > 0

    def test_save_stocks_korean_encoding(self, temp_stocks_file):
        """한글 인코딩 확인"""
        new_data = {
            "TEST03": {
                "name": "한글 테스트",
                "type": "ETF",
                "theme": "한국/테마",
                "launch_date": "2024-01-01",
                "expense_ratio": 0.005,
                "search_keyword": "한글",
                "relevance_keywords": ["한글", "테스트"]
            }
        }

        save_stocks(new_data)

        # 파일 읽기 (ensure_ascii=False 확인)
        with open(temp_stocks_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 한글이 유니코드 이스케이프 없이 저장되었는지 확인
        assert "한글 테스트" in content
        assert "\\u" not in content  # 유니코드 이스케이프 없음


class TestValidateStockData:
    """validate_stock_data() 함수 테스트"""

    def test_validate_etf_success(self):
        """ETF 데이터 검증 성공"""
        data = {
            "name": "테스트 ETF",
            "type": "ETF",
            "theme": "테스트",
            "launch_date": "2024-01-01",
            "expense_ratio": 0.005
        }

        # 예외가 발생하지 않으면 성공
        validate_stock_data(data, "TEST01")

    def test_validate_stock_success(self):
        """STOCK 데이터 검증 성공"""
        data = {
            "name": "테스트 주식",
            "type": "STOCK",
            "theme": "테스트",
            "launch_date": None,
            "expense_ratio": None
        }

        validate_stock_data(data, "TEST02")

    def test_validate_missing_required_field(self):
        """필수 필드 누락 시 예외"""
        data = {
            "type": "ETF",
            "theme": "테스트"
            # name 누락
        }

        with pytest.raises(ValidationException) as exc_info:
            validate_stock_data(data, "TEST03")

        assert "Missing required field: name" in str(exc_info.value)

    def test_validate_invalid_type(self):
        """잘못된 타입"""
        data = {
            "name": "테스트",
            "type": "INVALID",
            "theme": "테스트"
        }

        with pytest.raises(ValidationException) as exc_info:
            validate_stock_data(data, "TEST04")

        assert "Invalid type" in str(exc_info.value)

    def test_validate_etf_missing_launch_date(self):
        """ETF launch_date 누락"""
        data = {
            "name": "테스트 ETF",
            "type": "ETF",
            "theme": "테스트",
            "expense_ratio": 0.005
            # launch_date 누락
        }

        with pytest.raises(ValidationException) as exc_info:
            validate_stock_data(data, "TEST05")

        assert "launch_date" in str(exc_info.value)

    def test_validate_etf_missing_expense_ratio(self):
        """ETF expense_ratio 누락"""
        data = {
            "name": "테스트 ETF",
            "type": "ETF",
            "theme": "테스트",
            "launch_date": "2024-01-01"
            # expense_ratio 누락
        }

        with pytest.raises(ValidationException) as exc_info:
            validate_stock_data(data, "TEST06")

        assert "expense_ratio" in str(exc_info.value)

    def test_validate_invalid_date_format(self):
        """잘못된 날짜 형식"""
        data = {
            "name": "테스트 ETF",
            "type": "ETF",
            "theme": "테스트",
            "launch_date": "2024/01/01",  # 잘못된 형식
            "expense_ratio": 0.005
        }

        with pytest.raises(ValidationException) as exc_info:
            validate_stock_data(data, "TEST07")

        assert "Invalid launch_date format" in str(exc_info.value)


class TestSyncStocksToDb:
    """sync_stocks_to_db() 함수 테스트"""

    def test_sync_to_db_success(self, temp_stocks_file):
        """DB 동기화 성공"""
        synced_count = sync_stocks_to_db()

        assert synced_count == 1  # TEST01 종목

        # DB 확인
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM etfs WHERE ticker = 'TEST01'")
            row = cursor.fetchone()

        assert row is not None
        assert row['name'] == "테스트 ETF"

    def test_sync_multiple_stocks(self, temp_stocks_file):
        """여러 종목 동기화"""
        stocks = load_stocks()
        stocks["TEST02"] = {
            "name": "추가 종목",
            "type": "STOCK",
            "theme": "테스트",
            "launch_date": None,
            "expense_ratio": None
        }
        save_stocks(stocks)

        synced_count = sync_stocks_to_db()
        assert synced_count == 2

    def test_sync_replaces_existing(self, temp_stocks_file):
        """기존 종목 업데이트"""
        # 첫 번째 동기화
        sync_stocks_to_db()

        # 종목 수정
        stocks = load_stocks()
        stocks["TEST01"]["name"] = "수정된 이름"
        save_stocks(stocks)

        # 두 번째 동기화
        sync_stocks_to_db()

        # DB 확인
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM etfs WHERE ticker = 'TEST01'")
            row = cursor.fetchone()

        assert row['name'] == "수정된 이름"


class TestDeleteStockFromDb:
    """delete_stock_from_db() 함수 테스트"""

    def test_delete_stock_cascade(self):
        """종목 삭제 (CASCADE)"""
        # 종목 추가
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO etfs (ticker, name, type, theme, launch_date, expense_ratio)
                VALUES ('DELETE01', '삭제 테스트', 'STOCK', '테스트', NULL, NULL)
            """)
            # 가격 데이터 추가
            cursor.execute("""
                INSERT INTO prices (ticker, date, close_price, volume)
                VALUES ('DELETE01', '2024-01-01', 10000, 100000)
            """)
            conn.commit()

        # 삭제
        deleted_counts = delete_stock_from_db('DELETE01')

        assert deleted_counts['prices'] == 1
        assert deleted_counts['news'] == 0
        assert deleted_counts['trading_flow'] == 0

        # DB 확인
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM etfs WHERE ticker = 'DELETE01'")
            row = cursor.fetchone()

        assert row is None

    def test_delete_nonexistent_stock(self):
        """존재하지 않는 종목 삭제"""
        deleted_counts = delete_stock_from_db('NONEXISTENT')

        assert deleted_counts['prices'] == 0
        assert deleted_counts['news'] == 0
        assert deleted_counts['trading_flow'] == 0
