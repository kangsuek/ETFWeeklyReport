import sqlite3
from pathlib import Path
import logging
import os
from contextlib import contextmanager
from threading import Lock
from queue import Queue, Empty
from app.config import Config
from app.exceptions import DatabaseException

logger = logging.getLogger(__name__)

# SQLite 전용 빌드. DATABASE_URL(sqlite:///...)로 경로 재정의 가능.
DATABASE_URL = os.getenv("DATABASE_URL")
DB_PATH = None

if DATABASE_URL and DATABASE_URL.startswith("sqlite:///"):
    # sqlite:///path/to/db.db 형식에서 경로 추출
    db_path_str = DATABASE_URL.replace("sqlite:///", "")
    if Path(db_path_str).is_absolute():
        DB_PATH = Path(db_path_str)
    else:
        # 상대 경로는 프로젝트 루트(backend/app/database.py에서 2단계 위) 기준으로 해석
        project_root = Path(__file__).parent.parent.parent
        DB_PATH = project_root / db_path_str.lstrip("./")
    logger.info(f"Using SQLite database: {DB_PATH} (resolved from: {DATABASE_URL})")
else:
    if DATABASE_URL:
        logger.warning(
            f"Non-SQLite DATABASE_URL ignored (SQLite-only build): {DATABASE_URL}"
        )
    # 기본값: SQLite
    DB_PATH = Path(__file__).parent.parent / "data" / "etf_data.db"
    logger.info(f"Using default SQLite database path: {DB_PATH}")


class ConnectionPool:
    """SQLite connection pool."""

    def __init__(self, max_connections: int = 10):
        self.max_connections = max_connections
        self.pool = Queue(maxsize=max_connections)
        self.lock = Lock()
        self.current_connections = 0
        logger.info(f"SQLite connection pool initialized with max_connections={max_connections}")

    def get_connection(self):
        """Get a connection from the pool or create a new one"""
        try:
            # Try to get an existing connection from the pool (non-blocking)
            conn = self.pool.get_nowait()
            logger.debug("Reusing connection from pool")
            return conn
        except Empty:
            # Pool is empty, create a new connection if below max
            with self.lock:
                if self.current_connections < self.max_connections:
                    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
                    conn.row_factory = sqlite3.Row
                    self.current_connections += 1
                    logger.debug(f"Created new connection ({self.current_connections}/{self.max_connections})")
                    return conn
            # Pool full, wait for a connection to become available (with timeout)
            logger.debug("Pool full, waiting for connection...")
            try:
                conn = self.pool.get(block=True, timeout=30)
                logger.debug("Got connection after waiting")
                return conn
            except Empty:
                logger.error("Connection pool timeout: no connection available after 30s")
                raise TimeoutError("Database connection pool exhausted. Please try again later.")

    def return_connection(self, conn):
        """Return a connection to the pool"""
        try:
            self.pool.put_nowait(conn)
            logger.debug("Returned connection to pool")
        except Exception:
            # Pool is full, close the connection
            conn.close()
            with self.lock:
                self.current_connections -= 1
            logger.debug("Pool full, closed connection")

    def close_all(self):
        """Close all connections in the pool"""
        while not self.pool.empty():
            try:
                conn = self.pool.get_nowait()
                conn.close()
            except Empty:
                break
        self.current_connections = 0
        logger.info("All SQLite connections closed")


# Global connection pool instance
_connection_pool = None
_pool_lock = Lock()


def get_connection_pool() -> ConnectionPool:
    """Get the global connection pool instance (singleton)"""
    global _connection_pool
    if _connection_pool is None:
        with _pool_lock:
            if _connection_pool is None:
                max_conn = int(os.getenv("DB_POOL_SIZE", "10"))
                _connection_pool = ConnectionPool(max_connections=max_conn)
    return _connection_pool


def close_connection_pool():
    """앱 종료 시 전역 커넥션 풀을 닫는다 (미초기화 상태면 아무것도 안 함)"""
    global _connection_pool
    with _pool_lock:
        if _connection_pool is not None:
            _connection_pool.close_all()
            _connection_pool = None


@contextmanager
def get_db_connection():
    """
    Get database connection as a context manager.
    Uses connection pooling for improved performance.
    Ensures connection is properly returned even if an exception occurs.

    Usage:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM etfs")
            rows = cursor.fetchall()
    """
    pool = get_connection_pool()
    conn = pool.get_connection()
    try:
        # SQLite connection already has row_factory set to sqlite3.Row
        yield conn
    except sqlite3.Error as e:
        # DB 구현 세부(sqlite3)를 상위 계층에 노출하지 않도록 앱 예외로 변환
        raise DatabaseException(str(e)) from e
    finally:
        pool.return_connection(conn)


def get_cursor(conn):
    """
    Get a cursor from a SQLite connection.

    Args:
        conn: Connection from get_db_connection()

    Returns:
        cursor: Database cursor
    """
    return conn.cursor()


def init_db():
    """Initialize database with schema (SQLite)"""
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # SQLite 스키마 타입
    id_type = "INTEGER PRIMARY KEY AUTOINCREMENT"
    text_type = "TEXT"
    real_type = "REAL"
    integer_type = "INTEGER"
    timestamp_default = "DEFAULT CURRENT_TIMESTAMP"
    insert_ignore = "OR IGNORE"

    # Create tables
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS etfs (
            ticker {text_type} PRIMARY KEY,
            name {text_type} NOT NULL,
            type {text_type} NOT NULL,
            theme {text_type},
            purchase_date DATE,
            purchase_price {real_type},
            quantity {integer_type},
            search_keyword {text_type},
            relevance_keywords {text_type}
        )
    """)

    # quantity, purchase_price 등 컬럼이 없으면 추가 (마이그레이션)
    columns_to_add = [
        ("quantity", integer_type),
        ("purchase_price", real_type),
        ("search_keyword", text_type),
        ("relevance_keywords", text_type),
    ]
    for col_name, col_type in columns_to_add:
        try:
            cursor.execute(f"ALTER TABLE etfs ADD COLUMN {col_name} {col_type}")
            logger.info(f"Added {col_name} column to etfs table")
        except Exception as e:
            if "duplicate column" not in str(e).lower() and "already exists" not in str(e).lower():
                logger.warning(f"Could not add {col_name} column: {e}")

    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS prices (
            id {id_type},
            ticker {text_type} NOT NULL,
            date DATE NOT NULL,
            open_price {real_type},
            high_price {real_type},
            low_price {real_type},
            close_price {real_type},
            volume {integer_type},
            daily_change_pct {real_type},
            FOREIGN KEY (ticker) REFERENCES etfs(ticker),
            UNIQUE(ticker, date)
        )
    """)

    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS trading_flow (
            id {id_type},
            ticker {text_type} NOT NULL,
            date DATE NOT NULL,
            individual_net {integer_type},
            institutional_net {integer_type},
            foreign_net {integer_type},
            FOREIGN KEY (ticker) REFERENCES etfs(ticker),
            UNIQUE(ticker, date)
        )
    """)

    # trading_flow 컬럼 마이그레이션 (네이버 /trend JSON 수집 항목)
    try:
        cursor.execute(f"ALTER TABLE trading_flow ADD COLUMN foreign_hold_ratio {real_type}")
        logger.info("Added foreign_hold_ratio column to trading_flow table")
    except Exception as e:
        if "duplicate column" not in str(e).lower() and "already exists" not in str(e).lower():
            logger.warning(f"Could not add foreign_hold_ratio column to trading_flow: {e}")

    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS news (
            id {id_type},
            ticker {text_type} NOT NULL,
            date DATE NOT NULL,
            published_at TIMESTAMP,
            title {text_type},
            url {text_type},
            source {text_type},
            relevance_score {real_type},
            FOREIGN KEY (ticker) REFERENCES etfs(ticker)
        )
    """)

    # news 테이블에 published_at 컬럼 추가 (기존 DB 마이그레이션)
    news_columns_to_add = [("published_at", "TIMESTAMP")]
    for col_name, col_type in news_columns_to_add:
        try:
            cursor.execute(f"ALTER TABLE news ADD COLUMN {col_name} {col_type}")
            logger.info(f"Added {col_name} column to news table")
        except Exception as e:
            if "duplicate column" not in str(e).lower() and "already exists" not in str(e).lower():
                logger.warning(f"Could not add {col_name} column to news: {e}")

    # Create stock_catalog table for ticker catalog
    is_active_type = f"{integer_type} DEFAULT 1"

    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS stock_catalog (
            ticker {text_type} PRIMARY KEY,
            name {text_type} NOT NULL,
            type {text_type} NOT NULL,
            market {text_type},
            sector {text_type},
            listed_date DATE,
            last_updated TIMESTAMP {timestamp_default},
            is_active {is_active_type}
        )
    """)

    # Create collection_status table for tracking data collection
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS collection_status (
            ticker {text_type} PRIMARY KEY,
            last_price_date DATE,
            last_trading_flow_date DATE,
            last_news_collected_at TIMESTAMP,
            price_records_count {integer_type} DEFAULT 0,
            trading_flow_records_count {integer_type} DEFAULT 0,
            news_records_count {integer_type} DEFAULT 0,
            last_collection_attempt TIMESTAMP,
            last_successful_collection TIMESTAMP,
            consecutive_failures {integer_type} DEFAULT 0,
            created_at TIMESTAMP {timestamp_default},
            updated_at TIMESTAMP {timestamp_default},
            FOREIGN KEY (ticker) REFERENCES etfs(ticker)
        )
    """)

    # Create indexes for improved query performance on date-based queries
    logger.info("Creating database indexes for performance optimization")

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_prices_ticker_date
        ON prices(ticker, date DESC)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_trading_flow_ticker_date
        ON trading_flow(ticker, date DESC)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_news_ticker_date
        ON news(ticker, date DESC)
    """)

    # news 테이블에 UNIQUE 인덱스 추가 (ON CONFLICT 패턴 지원)
    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_news_ticker_url
        ON news(ticker, url)
    """)

    # Create indexes for stock_catalog
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_stock_catalog_name
        ON stock_catalog(name)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_stock_catalog_type
        ON stock_catalog(type)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_stock_catalog_active
        ON stock_catalog(is_active)
    """)

    # stock_catalog 스크리닝용 컬럼 마이그레이션
    screening_columns = [
        ("close_price", real_type),
        ("daily_change_pct", real_type),
        ("volume", "INTEGER"),
        ("weekly_return", real_type),
        ("foreign_net", "INTEGER"),
        ("institutional_net", "INTEGER"),
        ("catalog_updated_at", "TIMESTAMP"),
        ("week_base_price", real_type),
        ("week_base_date", "TEXT"),
    ]
    for col_name, col_type in screening_columns:
        try:
            cursor.execute(f"ALTER TABLE stock_catalog ADD COLUMN {col_name} {col_type}")
            logger.info(f"Added {col_name} column to stock_catalog table")
        except Exception as e:
            if "duplicate column" not in str(e).lower() and "already exists" not in str(e).lower():
                logger.warning(f"Could not add {col_name} column to stock_catalog: {e}")

    # stock_catalog 스크리닝용 인덱스
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_stock_catalog_screening
        ON stock_catalog(type, is_active, weekly_return)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_stock_catalog_sector
        ON stock_catalog(sector, is_active)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_stock_catalog_catalog_updated
        ON stock_catalog(catalog_updated_at)
    """)

    # Create indexes for collection_status
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_collection_status_last_dates
        ON collection_status(last_price_date, last_trading_flow_date)
    """)

    # Create intraday_prices table for minute-level price data (분봉)
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS intraday_prices (
            id {id_type},
            ticker {text_type} NOT NULL,
            datetime TIMESTAMP NOT NULL,
            price {real_type} NOT NULL,
            change_amount {real_type},
            volume {integer_type},
            bid_volume {integer_type},
            ask_volume {integer_type},
            FOREIGN KEY (ticker) REFERENCES etfs(ticker),
            UNIQUE(ticker, datetime)
        )
    """)

    # Create index for intraday_prices
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_intraday_prices_ticker_datetime
        ON intraday_prices(ticker, datetime DESC)
    """)

    # intraday_prices 컬럼 마이그레이션 (네이버 차트 JSON API의 분당 OHLC)
    for col_name in ("open_price", "high_price", "low_price"):
        try:
            cursor.execute(f"ALTER TABLE intraday_prices ADD COLUMN {col_name} {real_type}")
            logger.info(f"Added {col_name} column to intraday_prices table")
        except Exception as e:
            if "duplicate column" not in str(e).lower() and "already exists" not in str(e).lower():
                logger.warning(f"Could not add {col_name} column to intraday_prices: {e}")

    # Create alert_rules table for price alerts
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS alert_rules (
            id {id_type},
            ticker {text_type} NOT NULL,
            alert_type {text_type} NOT NULL,
            direction {text_type} NOT NULL,
            target_price {real_type} NOT NULL,
            memo {text_type},
            is_active {integer_type} DEFAULT 1,
            created_at TIMESTAMP {timestamp_default},
            last_triggered_at TIMESTAMP,
            FOREIGN KEY (ticker) REFERENCES etfs(ticker)
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_alert_rules_ticker
        ON alert_rules(ticker, is_active)
    """)

    # Create alert_history table for alert logs
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS alert_history (
            id {id_type},
            rule_id {integer_type} NOT NULL,
            ticker {text_type} NOT NULL,
            alert_type {text_type} NOT NULL,
            message {text_type},
            triggered_at TIMESTAMP {timestamp_default},
            FOREIGN KEY (rule_id) REFERENCES alert_rules(id)
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_alert_history_ticker
        ON alert_history(ticker, triggered_at DESC)
    """)

    # Create signal_events table for uptrend signal state machine
    # (상승흐름 신호 상태 머신 저장소 — docs/UPTREND_SIGNAL_DESIGN.md §3-2)
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS signal_events (
            id {id_type},
            ticker {text_type} NOT NULL,
            rule_id {integer_type} NOT NULL,
            breakout_date DATE NOT NULL,
            breakout_level {real_type} NOT NULL,
            volume_ratio {real_type},
            candle_pos {real_type},
            flow_net_3d {integer_type},
            status {text_type} NOT NULL DEFAULT 'pending',
            confirmed_date DATE,
            confirm_path {text_type},
            created_at TIMESTAMP {timestamp_default},
            updated_at TIMESTAMP {timestamp_default},
            FOREIGN KEY (ticker) REFERENCES etfs(ticker),
            FOREIGN KEY (rule_id) REFERENCES alert_rules(id),
            UNIQUE(ticker, breakout_date)
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_signal_events_status
        ON signal_events(status, ticker)
    """)

    # Create app_state key-value table for persistent markers
    # (마지막 신호 스캔일, uptrend 읽음 마커 등 앱 재시작 간 영속 상태 — §3-2)
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS app_state (
            key {text_type} PRIMARY KEY,
            value {text_type},
            updated_at TIMESTAMP {timestamp_default}
        )
    """)

    # Create etf_fundamentals table for NAV, AUM tracking
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS etf_fundamentals (
            ticker {text_type} NOT NULL,
            date DATE NOT NULL,
            nav {real_type},
            nav_change_pct {real_type},
            aum {real_type},
            tracking_error {real_type},
            expense_ratio {real_type},
            created_at TIMESTAMP {timestamp_default},
            PRIMARY KEY (ticker, date),
            FOREIGN KEY (ticker) REFERENCES etfs(ticker)
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_etf_fundamentals_ticker_date
        ON etf_fundamentals(ticker, date DESC)
    """)

    # etf_fundamentals 컬럼 마이그레이션 (네이버 etfAnalysis JSON 수집 항목)
    etf_fundamentals_columns = [
        ("base_index", text_type),          # 기초지수
        ("dividend_yield", real_type),      # 분배율(TTM, %)
        ("dividend_per_share", real_type),  # 주당 분배금(TTM)
        ("sector_portfolio", text_type),    # 펀드 섹터 배분(JSON: [{code, weight}])
        ("deviation_rate", real_type),      # 괴리율(부호 포함 %, 네이버 동시점 기준)
    ]
    for col_name, col_type in etf_fundamentals_columns:
        try:
            cursor.execute(f"ALTER TABLE etf_fundamentals ADD COLUMN {col_name} {col_type}")
            logger.info(f"Added {col_name} column to etf_fundamentals table")
        except Exception as e:
            if "duplicate column" not in str(e).lower() and "already exists" not in str(e).lower():
                logger.warning(f"Could not add {col_name} column to etf_fundamentals: {e}")

    # Create etf_rebalancing table for rebalancing history
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS etf_rebalancing (
            id {id_type},
            ticker {text_type} NOT NULL,
            rebalance_date DATE NOT NULL,
            action {text_type} NOT NULL,
            stock_code {text_type},
            stock_name {text_type},
            weight_before {real_type},
            weight_after {real_type},
            shares_change {integer_type},
            created_at TIMESTAMP {timestamp_default},
            FOREIGN KEY (ticker) REFERENCES etfs(ticker)
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_etf_rebalancing_ticker_date
        ON etf_rebalancing(ticker, rebalance_date DESC)
    """)

    # Create etf_distributions table for dividend/distribution history
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS etf_distributions (
            id {id_type},
            ticker {text_type} NOT NULL,
            record_date DATE NOT NULL,
            payment_date DATE,
            ex_date DATE,
            amount_per_share {real_type} NOT NULL,
            distribution_type {text_type},
            yield_pct {real_type},
            created_at TIMESTAMP {timestamp_default},
            FOREIGN KEY (ticker) REFERENCES etfs(ticker),
            UNIQUE(ticker, record_date)
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_etf_distributions_ticker_date
        ON etf_distributions(ticker, record_date DESC)
    """)

    # Create etf_holdings table for portfolio composition
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS etf_holdings (
            ticker {text_type} NOT NULL,
            date DATE NOT NULL,
            stock_code {text_type} NOT NULL,
            stock_name {text_type},
            weight {real_type},
            shares {integer_type},
            market_value {real_type},
            sector {text_type},
            created_at TIMESTAMP {timestamp_default},
            PRIMARY KEY (ticker, date, stock_code),
            FOREIGN KEY (ticker) REFERENCES etfs(ticker)
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_etf_holdings_ticker_date
        ON etf_holdings(ticker, date DESC)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_etf_holdings_weight
        ON etf_holdings(ticker, date, weight DESC)
    """)

    # Create stock_fundamentals table for stock financial metrics
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS stock_fundamentals (
            ticker {text_type} NOT NULL,
            date DATE NOT NULL,
            per {real_type},
            pbr {real_type},
            roe {real_type},
            roa {real_type},
            eps {real_type},
            bps {real_type},
            revenue {real_type},
            operating_profit {real_type},
            net_profit {real_type},
            operating_margin {real_type},
            net_margin {real_type},
            debt_ratio {real_type},
            current_ratio {real_type},
            dividend_yield {real_type},
            payout_ratio {real_type},
            created_at TIMESTAMP {timestamp_default},
            PRIMARY KEY (ticker, date),
            FOREIGN KEY (ticker) REFERENCES etfs(ticker)
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_stock_fundamentals_ticker_date
        ON stock_fundamentals(ticker, date DESC)
    """)

    # Create stock_distributions table for dividend history
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS stock_distributions (
            id {id_type},
            ticker {text_type} NOT NULL,
            record_date DATE NOT NULL,
            payment_date DATE,
            ex_date DATE,
            amount_per_share {real_type},
            distribution_type {text_type},
            yield_pct {real_type},
            created_at TIMESTAMP {timestamp_default},
            FOREIGN KEY (ticker) REFERENCES etfs(ticker),
            UNIQUE(ticker, record_date)
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_stock_distributions_ticker_date
        ON stock_distributions(ticker, record_date DESC)
    """)

    # Insert initial stock data from config (ETF 4개 + 주식 2개)
    stock_config = Config.get_stock_config()
    etfs_data = []

    for ticker, info in stock_config.items():
        # relevance_keywords를 JSON 문자열로 변환
        import json
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

    logger.info(f"Loading {len(etfs_data)} stocks from configuration")

    cursor.executemany(f"""
        INSERT {insert_ignore} INTO etfs (ticker, name, type, theme, purchase_date, purchase_price, quantity, search_keyword, relevance_keywords)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, etfs_data)

    conn.commit()
    conn.close()

    logger.info("Database initialized successfully")


def run_migrations():
    """
    SQLite 전용 빌드에서는 별도 마이그레이션 단계가 필요하지 않습니다.
    (스키마/컬럼 추가는 init_db()에서 처리)
    """
    return


def update_collection_status(ticker: str,
                            price_date: str = None,
                            trading_flow_date: str = None,
                            news_collected: bool = False,
                            success: bool = True):
    """
    종목의 데이터 수집 상태 업데이트

    Args:
        ticker: 종목 코드
        price_date: 마지막 수집한 가격 데이터 날짜
        trading_flow_date: 마지막 수집한 매매동향 데이터 날짜
        news_collected: 뉴스 수집 여부
        success: 수집 성공 여부
    """
    from datetime import datetime

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # 현재 상태 조회
        cursor.execute("""
            SELECT * FROM collection_status WHERE ticker = ?
        """, (ticker,))
        current = cursor.fetchone()

        now = datetime.now().isoformat()

        if current:
            # 기존 레코드 업데이트
            updates = []
            params = []

            if price_date:
                updates.append("last_price_date = ?")
                params.append(price_date)

            if trading_flow_date:
                updates.append("last_trading_flow_date = ?")
                params.append(trading_flow_date)

            if news_collected:
                updates.append("last_news_collected_at = ?")
                params.append(now)

            updates.append("last_collection_attempt = ?")
            params.append(now)

            if success:
                updates.append("last_successful_collection = ?")
                updates.append("consecutive_failures = 0")
                params.append(now)
            else:
                updates.append("consecutive_failures = consecutive_failures + 1")

            updates.append("updated_at = ?")
            params.append(now)

            params.append(ticker)

            cursor.execute(f"""
                UPDATE collection_status
                SET {', '.join(updates)}
                WHERE ticker = ?
            """, params)
        else:
            # 새 레코드 삽입
            cursor.execute("""
                INSERT INTO collection_status
                (ticker, last_price_date, last_trading_flow_date,
                 last_news_collected_at, last_collection_attempt,
                 last_successful_collection, consecutive_failures)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                ticker,
                price_date,
                trading_flow_date,
                now if news_collected else None,
                now,
                now if success else None,
                0 if success else 1
            ))

        conn.commit()


def get_collection_status(ticker: str = None):
    """
    데이터 수집 상태 조회

    Args:
        ticker: 종목 코드 (None이면 전체 조회)

    Returns:
        dict or list: 수집 상태 정보
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()

        if ticker:
            cursor.execute("""
                SELECT * FROM collection_status WHERE ticker = ?
            """, (ticker,))
            result = cursor.fetchone()
            return dict(result) if result else None
        else:
            cursor.execute("""
                SELECT * FROM collection_status ORDER BY ticker
            """)
            return [dict(row) for row in cursor.fetchall()]


def get_app_state(key: str):
    """app_state 키-값 조회. 없으면 None."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM app_state WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row["value"] if row else None


def set_app_state(key: str, value: str):
    """app_state 키-값 저장 (upsert)."""
    from datetime import datetime
    now = datetime.now().isoformat()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO app_state (key, value, updated_at) VALUES (?, ?, ?)",
            (key, value, now),
        )
        conn.commit()


if __name__ == "__main__":
    init_db()
