"""
Stock configuration file (stocks.json) management utilities

This module provides utilities for managing the stocks.json file,
which is the single source of truth for stock/ETF ticker information.
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from app.config import Config
from app.database import get_db_connection, USE_POSTGRES

logger = logging.getLogger(__name__)


def load_stocks() -> Dict[str, Any]:
    """
    Load stock configuration from stocks.json file

    Returns:
        Dict[str, Any]: Stock configuration with ticker as key

    Raises:
        FileNotFoundError: If stocks.json file does not exist
        json.JSONDecodeError: If JSON parsing fails
    """
    return Config.get_stock_config()


def save_stocks(stocks_dict: Dict[str, Any]) -> None:
    """
    Save stock configuration to stocks.json file

    Features:
    - Atomic write (write to temp file, then rename)
    - JSON formatting (indent=2, ensure_ascii=False for Korean characters)

    Args:
        stocks_dict: Stock configuration dictionary

    Raises:
        IOError: If file write fails
    """
    config_path = Path(Config.STOCK_CONFIG_PATH)

    # Atomic write: write to temp file, then rename
    temp_path = config_path.parent / "stocks.json.tmp"

    try:
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(stocks_dict, f, indent=2, ensure_ascii=False)

        # Atomic rename
        temp_path.replace(config_path)
        logger.info(f"Saved {len(stocks_dict)} stocks to {config_path}")

    except Exception as e:
        # Clean up temp file on error
        if temp_path.exists():
            temp_path.unlink()
        logger.error(f"Failed to save stocks.json: {e}")
        raise


def validate_stock_data(stock_dict: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Validate stock/ETF data structure

    Validation rules:
    - Required fields: name, type, theme
    - Type must be "ETF" or "STOCK" or "ALL"
    - purchase_date format: YYYY-MM-DD (if provided)

    Args:
        stock_dict: Stock data dictionary

    Returns:
        tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    # Required fields
    required_fields = ["name", "type", "theme"]
    for field in required_fields:
        if field not in stock_dict:
            return False, f"Missing required field: {field}"

    # Type validation
    stock_type = stock_dict.get("type")
    if stock_type not in ["ETF", "STOCK", "ALL"]:
        return False, f"Invalid type: {stock_type}. Must be 'ETF', 'STOCK', or 'ALL'"

    # purchase_date format validation (if provided)
    purchase_date = stock_dict.get("purchase_date")
    if purchase_date is not None:
        import re
        # 정확히 YYYY-MM-DD 형식인지 검증 (연도 4자리)
        date_pattern = r'^\d{4}-\d{2}-\d{2}$'
        if not re.match(date_pattern, str(purchase_date)):
            return False, f"Invalid purchase_date format: {purchase_date}. Expected YYYY-MM-DD (4-digit year)"
        
        try:
            parsed_date = datetime.strptime(purchase_date, "%Y-%m-%d")
            # 연도가 유효한 범위인지 확인 (1900-2100)
            if parsed_date.year < 1900 or parsed_date.year > 2100:
                return False, f"Invalid year in purchase_date: {purchase_date}. Year must be between 1900 and 2100"
        except ValueError:
            return False, f"Invalid purchase_date: {purchase_date}. Expected valid date in YYYY-MM-DD format"

    return True, None


def sync_stocks_to_db() -> int:
    """
    Synchronize stocks.json to database (etfs table)

    This function:
    1. Loads stocks from stocks.json
    2. Inserts or replaces them in the database
    3. Does NOT delete stocks that are in DB but not in stocks.json
       (that should be done explicitly via DELETE endpoint)

    Returns:
        int: Number of stocks synchronized

    Note:
        This function should be called:
        - On server startup (after init_db)
        - After any CRUD operation on stocks.json
    """
    stocks = load_stocks()

    with get_db_connection() as conn_or_cursor:
        # PostgreSQL과 SQLite 처리 분기
        if USE_POSTGRES:
            cursor = conn_or_cursor
            conn = cursor.connection
        else:
            conn = conn_or_cursor
            cursor = conn.cursor()

        etfs_data = []
        for ticker, info in stocks.items():
            # relevance_keywords를 JSON 문자열로 변환
            relevance_keywords_json = json.dumps(info.get("relevance_keywords", []), ensure_ascii=False) if info.get("relevance_keywords") else None

            etfs_data.append((
                ticker,
                info.get("name"),
                info.get("type"),
                info.get("theme"),
                info.get("purchase_date"),
                info.get("purchase_price"),
                info.get("quantity"),
                info.get("search_keyword"),
                relevance_keywords_json
            ))

        if USE_POSTGRES:
            # PostgreSQL: INSERT ... ON CONFLICT DO UPDATE
            cursor.executemany("""
                INSERT INTO etfs (ticker, name, type, theme, purchase_date, purchase_price, quantity, search_keyword, relevance_keywords)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (ticker) DO UPDATE SET
                    name = EXCLUDED.name,
                    type = EXCLUDED.type,
                    theme = EXCLUDED.theme,
                    purchase_date = EXCLUDED.purchase_date,
                    purchase_price = EXCLUDED.purchase_price,
                    quantity = EXCLUDED.quantity,
                    search_keyword = EXCLUDED.search_keyword,
                    relevance_keywords = EXCLUDED.relevance_keywords
            """, etfs_data)
        else:
            # SQLite: INSERT OR REPLACE
            cursor.executemany("""
                INSERT OR REPLACE INTO etfs (ticker, name, type, theme, purchase_date, purchase_price, quantity, search_keyword, relevance_keywords)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, etfs_data)

        conn.commit()

    logger.info(f"Synchronized {len(stocks)} stocks to database")
    return len(stocks)


def add_stock(ticker: str, stock_data: Dict[str, Any]) -> None:
    """
    Add a new stock to stocks.json and sync to database

    Args:
        ticker: Stock ticker code (e.g., "005930")
        stock_data: Stock information dictionary

    Raises:
        ValueError: If stock_data is invalid or ticker already exists
    """
    # Validate data
    is_valid, error_msg = validate_stock_data(stock_data)
    if not is_valid:
        raise ValueError(f"Invalid stock data: {error_msg}")

    # Load current stocks
    stocks = load_stocks()

    # Check for duplicates
    if ticker in stocks:
        raise ValueError(f"Stock with ticker {ticker} already exists")

    # Add new stock
    stocks[ticker] = stock_data

    # Save to file
    save_stocks(stocks)

    # Sync to database
    sync_stocks_to_db()

    # Reload cache
    Config.reload_stock_config()

    logger.info(f"Added stock: {ticker}")


def update_stock(ticker: str, stock_data: Dict[str, Any]) -> None:
    """
    Update an existing stock in stocks.json and sync to database

    Args:
        ticker: Stock ticker code
        stock_data: Updated stock information dictionary

    Raises:
        ValueError: If stock_data is invalid or ticker does not exist
    """
    # Validate data
    is_valid, error_msg = validate_stock_data(stock_data)
    if not is_valid:
        raise ValueError(f"Invalid stock data: {error_msg}")

    # Load current stocks
    stocks = load_stocks()

    # Check if stock exists
    if ticker not in stocks:
        raise ValueError(f"Stock with ticker {ticker} not found")

    # Update stock
    stocks[ticker] = stock_data

    # Save to file
    save_stocks(stocks)

    # Sync to database
    sync_stocks_to_db()

    # Reload cache
    Config.reload_stock_config()

    logger.info(f"Updated stock: {ticker}")


def delete_stock(ticker: str) -> Dict[str, int]:
    """
    Delete a stock from stocks.json and cascade delete from database

    Args:
        ticker: Stock ticker code

    Returns:
        Dict[str, int]: Deleted record counts by table
            {
                "prices": 150,
                "news": 20,
                "trading_flow": 30
            }

    Raises:
        ValueError: If ticker does not exist
    """
    # Load current stocks
    stocks = load_stocks()

    # Check if stock exists
    if ticker not in stocks:
        raise ValueError(f"Stock with ticker {ticker} not found")

    # Remove from stocks.json
    del stocks[ticker]

    # Save to file
    save_stocks(stocks)

    # CASCADE delete from database
    deleted_counts = {}

    # PostgreSQL과 SQLite의 플레이스홀더 차이
    param_placeholder = "%s" if USE_POSTGRES else "?"

    with get_db_connection() as conn_or_cursor:
        # PostgreSQL과 SQLite 처리 분기
        if USE_POSTGRES:
            cursor = conn_or_cursor
            conn = cursor.connection
        else:
            conn = conn_or_cursor
            cursor = conn.cursor()

        # Count and delete prices
        cursor.execute(f"SELECT COUNT(*) as cnt FROM prices WHERE ticker = {param_placeholder}", (ticker,))
        result = cursor.fetchone()
        deleted_counts["prices"] = result['cnt'] if USE_POSTGRES else result[0]
        cursor.execute(f"DELETE FROM prices WHERE ticker = {param_placeholder}", (ticker,))

        # Count and delete news
        cursor.execute(f"SELECT COUNT(*) as cnt FROM news WHERE ticker = {param_placeholder}", (ticker,))
        result = cursor.fetchone()
        deleted_counts["news"] = result['cnt'] if USE_POSTGRES else result[0]
        cursor.execute(f"DELETE FROM news WHERE ticker = {param_placeholder}", (ticker,))

        # Count and delete trading_flow
        cursor.execute(f"SELECT COUNT(*) as cnt FROM trading_flow WHERE ticker = {param_placeholder}", (ticker,))
        result = cursor.fetchone()
        deleted_counts["trading_flow"] = result['cnt'] if USE_POSTGRES else result[0]
        cursor.execute(f"DELETE FROM trading_flow WHERE ticker = {param_placeholder}", (ticker,))

        # Delete all tables that FK-reference etfs(ticker), before deleting etfs row
        # alert_history references alert_rules, so delete it first
        cursor.execute(f"""
            DELETE FROM alert_history WHERE rule_id IN (
                SELECT id FROM alert_rules WHERE ticker = {param_placeholder}
            )
        """, (ticker,))
        cursor.execute(f"DELETE FROM alert_rules WHERE ticker = {param_placeholder}", (ticker,))
        cursor.execute(f"DELETE FROM collection_status WHERE ticker = {param_placeholder}", (ticker,))
        cursor.execute(f"DELETE FROM intraday_prices WHERE ticker = {param_placeholder}", (ticker,))
        cursor.execute(f"DELETE FROM etf_fundamentals WHERE ticker = {param_placeholder}", (ticker,))
        cursor.execute(f"DELETE FROM etf_rebalancing WHERE ticker = {param_placeholder}", (ticker,))
        cursor.execute(f"DELETE FROM etf_distributions WHERE ticker = {param_placeholder}", (ticker,))
        cursor.execute(f"DELETE FROM etf_holdings WHERE ticker = {param_placeholder}", (ticker,))
        cursor.execute(f"DELETE FROM stock_fundamentals WHERE ticker = {param_placeholder}", (ticker,))
        cursor.execute(f"DELETE FROM stock_distributions WHERE ticker = {param_placeholder}", (ticker,))

        # Delete from etfs table
        cursor.execute(f"DELETE FROM etfs WHERE ticker = {param_placeholder}", (ticker,))

        conn.commit()

    # Reload cache
    Config.reload_stock_config()

    logger.info(f"Deleted stock {ticker} and related data: {deleted_counts}")
    return deleted_counts
