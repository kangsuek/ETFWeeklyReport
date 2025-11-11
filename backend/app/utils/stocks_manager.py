"""
stocks.json 파일 관리 유틸리티

Single Source of Truth로 stocks.json 파일을 관리하고
데이터베이스와 동기화합니다.
"""
import json
import shutil
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from app.config import Config
from app.database import get_db_connection
from app.exceptions import ValidationException

logger = logging.getLogger(__name__)


def load_stocks() -> Dict[str, Any]:
    """
    stocks.json 파일에서 종목 정보 로드

    Returns:
        Dict[str, Any]: 종목 정보 딕셔너리 (ticker: stock_info)

    Raises:
        FileNotFoundError: stocks.json 파일이 없는 경우
        json.JSONDecodeError: JSON 파싱 실패
    """
    return Config.get_stock_config()


def save_stocks(stocks_dict: Dict[str, Any]) -> None:
    """
    stocks.json 파일에 종목 정보 저장

    자동 백업 및 원자적 쓰기를 수행합니다.

    Args:
        stocks_dict: 저장할 종목 정보 딕셔너리

    Raises:
        IOError: 파일 쓰기 실패
        json.JSONEncodeError: JSON 인코딩 실패
    """
    config_path = Path(Config.STOCK_CONFIG_PATH)

    # 1. 기존 파일 백업 (파일이 있는 경우만)
    if config_path.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = config_path.parent / f"stocks.json.backup.{timestamp}"

        try:
            shutil.copy2(config_path, backup_path)
            logger.info(f"Created backup: {backup_path}")
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            # 백업 실패는 치명적이지 않으므로 계속 진행

    # 2. 원자적 쓰기 (임시 파일 → rename)
    temp_path = config_path.parent / f"{config_path.name}.tmp"

    try:
        # JSON 포매팅: indent=2, ensure_ascii=False (한글 유지)
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(stocks_dict, f, indent=2, ensure_ascii=False)

        # 원자적 rename (데이터 손실 방지)
        temp_path.replace(config_path)
        logger.info(f"Successfully saved stocks.json with {len(stocks_dict)} stocks")

    except Exception as e:
        logger.error(f"Failed to save stocks.json: {e}")
        # 임시 파일 정리
        if temp_path.exists():
            temp_path.unlink()
        raise IOError(f"Failed to save stocks.json: {e}")


def validate_stock_data(stock_dict: Dict[str, Any], ticker: Optional[str] = None) -> None:
    """
    종목 데이터 유효성 검증

    Args:
        stock_dict: 검증할 종목 데이터
        ticker: 종목 코드 (선택, 에러 메시지에 포함)

    Raises:
        ValidationException: 필수 필드 누락 또는 형식 오류
    """
    ticker_info = f" (ticker: {ticker})" if ticker else ""

    # 필수 필드 체크
    required_fields = ["name", "type", "theme"]
    for field in required_fields:
        if field not in stock_dict or not stock_dict[field]:
            raise ValidationException(f"Missing required field: {field}{ticker_info}")

    # 타입 검증
    stock_type = stock_dict["type"]
    if stock_type not in ["ETF", "STOCK"]:
        raise ValidationException(f"Invalid type: {stock_type}. Must be 'ETF' or 'STOCK'{ticker_info}")

    # ETF 필수 필드 체크
    if stock_type == "ETF":
        if "launch_date" not in stock_dict or not stock_dict["launch_date"]:
            raise ValidationException(f"ETF must have launch_date{ticker_info}")
        if "expense_ratio" not in stock_dict or stock_dict["expense_ratio"] is None:
            raise ValidationException(f"ETF must have expense_ratio{ticker_info}")

        # 날짜 형식 검증 (YYYY-MM-DD)
        launch_date = stock_dict["launch_date"]
        if not isinstance(launch_date, str) or len(launch_date) != 10:
            raise ValidationException(f"Invalid launch_date format: {launch_date}. Expected YYYY-MM-DD{ticker_info}")

        try:
            datetime.strptime(launch_date, "%Y-%m-%d")
        except ValueError:
            raise ValidationException(f"Invalid launch_date format: {launch_date}. Expected YYYY-MM-DD{ticker_info}")

        # expense_ratio 타입 검증
        if not isinstance(stock_dict["expense_ratio"], (int, float)):
            raise ValidationException(f"Invalid expense_ratio type: {type(stock_dict['expense_ratio'])}. Expected number{ticker_info}")

    # STOCK 필수 필드 체크 (launch_date, expense_ratio는 null이어야 함)
    elif stock_type == "STOCK":
        if stock_dict.get("launch_date") is not None:
            logger.warning(f"STOCK should have launch_date=null{ticker_info}, but got: {stock_dict.get('launch_date')}")
        if stock_dict.get("expense_ratio") is not None:
            logger.warning(f"STOCK should have expense_ratio=null{ticker_info}, but got: {stock_dict.get('expense_ratio')}")

    logger.info(f"Validation passed for stock{ticker_info}")


def sync_stocks_to_db() -> int:
    """
    stocks.json 파일의 종목 정보를 데이터베이스에 동기화

    기존 init_db() 로직을 활용하여 INSERT OR REPLACE 수행.
    Config 캐시도 갱신합니다.

    Returns:
        int: 동기화된 종목 수

    Raises:
        sqlite3.Error: 데이터베이스 오류
    """
    try:
        # 1. stocks.json 파일 로드
        stock_config = load_stocks()

        # 2. DB에 동기화
        etfs_data = []
        for ticker, info in stock_config.items():
            # 유효성 검증 (선택사항, 이미 검증된 데이터라고 가정)
            try:
                validate_stock_data(info, ticker)
            except ValidationException as e:
                logger.error(f"Validation failed for {ticker}: {e}")
                continue

            etfs_data.append((
                ticker,
                info.get("name"),
                info.get("type"),
                info.get("theme"),
                info.get("launch_date"),
                info.get("expense_ratio")
            ))

        # 3. DB에 INSERT OR REPLACE
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany("""
                INSERT OR REPLACE INTO etfs (ticker, name, type, theme, launch_date, expense_ratio)
                VALUES (?, ?, ?, ?, ?, ?)
            """, etfs_data)
            conn.commit()

        logger.info(f"Successfully synced {len(etfs_data)} stocks to database")

        # 4. Config 캐시 갱신
        Config.reload_stock_config()

        return len(etfs_data)

    except Exception as e:
        logger.error(f"Failed to sync stocks to database: {e}")
        raise


def delete_stock_from_db(ticker: str) -> Dict[str, int]:
    """
    데이터베이스에서 종목 및 관련 데이터 삭제 (CASCADE)

    Args:
        ticker: 삭제할 종목 코드

    Returns:
        Dict[str, int]: 삭제된 레코드 수 통계
            {"prices": 150, "news": 20, "trading_flow": 30}
    """
    deleted_counts = {
        "prices": 0,
        "news": 0,
        "trading_flow": 0
    }

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # 1. prices 삭제
            cursor.execute("DELETE FROM prices WHERE ticker = ?", (ticker,))
            deleted_counts["prices"] = cursor.rowcount

            # 2. news 삭제
            cursor.execute("DELETE FROM news WHERE ticker = ?", (ticker,))
            deleted_counts["news"] = cursor.rowcount

            # 3. trading_flow 삭제
            cursor.execute("DELETE FROM trading_flow WHERE ticker = ?", (ticker,))
            deleted_counts["trading_flow"] = cursor.rowcount

            # 4. etfs 삭제
            cursor.execute("DELETE FROM etfs WHERE ticker = ?", (ticker,))

            conn.commit()

        logger.info(f"Deleted stock {ticker} from DB: {deleted_counts}")
        return deleted_counts

    except Exception as e:
        logger.error(f"Failed to delete stock {ticker} from DB: {e}")
        raise
