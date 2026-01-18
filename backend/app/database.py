import sqlite3
from pathlib import Path
import logging
import os
from contextlib import contextmanager
from threading import Lock
from queue import Queue, Empty
from app.config import Config
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# DATABASE_URL 환경 변수 사용 (설정되지 않으면 기본값 사용)
DATABASE_URL = os.getenv("DATABASE_URL")
USE_POSTGRES = False
DB_PATH = None

if DATABASE_URL:
    parsed = urlparse(DATABASE_URL)
    if parsed.scheme == "postgresql" or parsed.scheme == "postgres":
        USE_POSTGRES = True
        logger.info(f"Using PostgreSQL database: {DATABASE_URL}")
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            from psycopg2.pool import ThreadedConnectionPool
        except ImportError:
            logger.error("psycopg2 is required for PostgreSQL. Install it with: pip install psycopg2-binary")
            raise
    elif parsed.scheme == "sqlite" or DATABASE_URL.startswith("sqlite:///"):
        # sqlite:///path/to/db.db 형식에서 경로 추출
        db_path_str = DATABASE_URL.replace("sqlite:///", "")
        DB_PATH = Path(db_path_str)
        logger.info(f"Using SQLite database: {DB_PATH}")
    else:
        logger.warning(f"Unsupported database URL scheme: {parsed.scheme}. Using default SQLite.")
        DB_PATH = Path(__file__).parent.parent / "data" / "etf_data.db"
else:
    # 기본값: SQLite
    DB_PATH = Path(__file__).parent.parent / "data" / "etf_data.db"
    logger.info(f"Using default SQLite database path: {DB_PATH}")

class ConnectionPool:
    """
    Connection pool for SQLite and PostgreSQL
    """
    def __init__(self, max_connections: int = 10):
        self.max_connections = max_connections
        self.use_postgres = USE_POSTGRES
        
        if self.use_postgres:
            # PostgreSQL connection pool
            try:
                import psycopg2
                from psycopg2.pool import ThreadedConnectionPool
                self.pg_pool = ThreadedConnectionPool(1, max_connections, DATABASE_URL)
                logger.info(f"PostgreSQL connection pool initialized with max_connections={max_connections}")
            except Exception as e:
                logger.error(f"Failed to initialize PostgreSQL connection pool: {e}")
                raise
        else:
            # SQLite connection pool
            self.pool = Queue(maxsize=max_connections)
            self.lock = Lock()
            self.current_connections = 0
            logger.info(f"SQLite connection pool initialized with max_connections={max_connections}")

    def get_connection(self):
        """Get a connection from the pool or create a new one"""
        if self.use_postgres:
            return self.pg_pool.getconn()
        else:
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
                    else:
                        # Wait for a connection to become available
                        logger.debug("Pool full, waiting for connection...")
                        conn = self.pool.get(block=True)
                        logger.debug("Got connection after waiting")
                        return conn

    def return_connection(self, conn):
        """Return a connection to the pool"""
        if self.use_postgres:
            self.pg_pool.putconn(conn)
        else:
            try:
                self.pool.put_nowait(conn)
                logger.debug("Returned connection to pool")
            except:
                # Pool is full, close the connection
                conn.close()
                with self.lock:
                    self.current_connections -= 1
                logger.debug("Pool full, closed connection")

    def close_all(self):
        """Close all connections in the pool"""
        if self.use_postgres:
            if hasattr(self, 'pg_pool'):
                self.pg_pool.closeall()
            logger.info("All PostgreSQL connections closed")
        else:
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

@contextmanager
def get_db_connection():
    """
    Get database connection as a context manager.
    Uses connection pooling for improved performance.
    Ensures connection is properly closed even if an exception occurs.

    Usage:
        with get_db_connection() as conn_or_cursor:
            # PostgreSQL: get_db_connection()이 이미 cursor를 반환
            # SQLite: get_db_connection()이 connection을 반환
            if USE_POSTGRES:
                cursor = conn_or_cursor
            else:
                cursor = conn_or_cursor.cursor()
            cursor.execute("SELECT * FROM etfs")
            rows = cursor.fetchall()
    """
    pool = get_connection_pool()
    conn = pool.get_connection()
    try:
        if USE_POSTGRES:
            # PostgreSQL: Use RealDictCursor for dict-like row access
            from psycopg2.extras import RealDictCursor
            yield conn.cursor(cursor_factory=RealDictCursor)
        else:
            # SQLite: Already has row_factory set to sqlite3.Row
            yield conn
    finally:
        pool.return_connection(conn)

def get_cursor(conn_or_cursor):
    """
    Get cursor from connection or return cursor if already a cursor.
    Helper function to handle both PostgreSQL and SQLite.
    
    Args:
        conn_or_cursor: Connection (SQLite) or Cursor (PostgreSQL) from get_db_connection()
    
    Returns:
        cursor: Database cursor
    """
    if USE_POSTGRES:
        # PostgreSQL: get_db_connection()이 이미 cursor를 반환
        return conn_or_cursor
    else:
        # SQLite: get_db_connection()이 connection을 반환
        return conn_or_cursor.cursor()

def init_db():
    """Initialize database with schema"""
    if USE_POSTGRES:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
    else:
        DB_PATH.parent.mkdir(exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
    
    # SQL 문법 차이 처리
    if USE_POSTGRES:
        id_type = "SERIAL PRIMARY KEY"
        text_type = "TEXT"
        real_type = "REAL"
        integer_type = "INTEGER"
        timestamp_default = "DEFAULT CURRENT_TIMESTAMP"
        auto_increment = ""  # SERIAL already handles this
        insert_ignore = "ON CONFLICT (ticker) DO NOTHING"
        param_placeholder = "%s"
    else:
        id_type = "INTEGER PRIMARY KEY AUTOINCREMENT"
        text_type = "TEXT"
        real_type = "REAL"
        integer_type = "INTEGER"
        timestamp_default = "DEFAULT CURRENT_TIMESTAMP"
        auto_increment = "AUTOINCREMENT"
        insert_ignore = "OR IGNORE"
        param_placeholder = "?"
    
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
    
    # quantity 컬럼이 없으면 추가 (마이그레이션)
    # PostgreSQL에서는 컬럼 존재 여부를 먼저 확인 (트랜잭션 오류 방지)
    if USE_POSTGRES:
        try:
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='etfs' AND column_name='quantity'
            """)
            if not cursor.fetchone():
                cursor.execute(f"ALTER TABLE etfs ADD COLUMN quantity {integer_type}")
                logger.info("Added quantity column to etfs table")
            else:
                logger.debug("quantity column already exists")
        except Exception as e:
            logger.warning(f"Could not check/add quantity column: {e}")
            # PostgreSQL에서 오류 발생 시 트랜잭션 롤백 후 재시도
            conn.rollback()
            # 롤백 후 다시 시도하지 않고 계속 진행 (컬럼이 이미 존재할 수 있음)
    else:
        # SQLite는 기존 방식 유지
        try:
            cursor.execute(f"ALTER TABLE etfs ADD COLUMN quantity {integer_type}")
            logger.info("Added quantity column to etfs table")
        except Exception as e:
            # 컬럼이 이미 존재하는 경우 무시
            if "duplicate column" not in str(e).lower() and "already exists" not in str(e).lower():
                logger.warning(f"Could not add quantity column: {e}")
    
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
    
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS news (
            id {id_type},
            ticker {text_type} NOT NULL,
            date DATE NOT NULL,
            title {text_type},
            url {text_type},
            source {text_type},
            relevance_score {real_type},
            FOREIGN KEY (ticker) REFERENCES etfs(ticker)
        )
    """)
    
    # Create stock_catalog table for ticker catalog
    if USE_POSTGRES:
        is_active_type = "BOOLEAN DEFAULT TRUE"
    else:
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

    # Create indexes for collection_status
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_collection_status_last_dates
        ON collection_status(last_price_date, last_trading_flow_date)
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

    if USE_POSTGRES:
        cursor.executemany(f"""
            INSERT INTO etfs (ticker, name, type, theme, purchase_date, purchase_price, quantity, search_keyword, relevance_keywords)
            VALUES ({param_placeholder}, {param_placeholder}, {param_placeholder}, {param_placeholder}, {param_placeholder}, {param_placeholder}, {param_placeholder}, {param_placeholder}, {param_placeholder})
            {insert_ignore}
        """, etfs_data)
    else:
        cursor.executemany(f"""
            INSERT {insert_ignore} INTO etfs (ticker, name, type, theme, purchase_date, purchase_price, quantity, search_keyword, relevance_keywords)
            VALUES ({param_placeholder}, {param_placeholder}, {param_placeholder}, {param_placeholder}, {param_placeholder}, {param_placeholder}, {param_placeholder}, {param_placeholder}, {param_placeholder})
        """, etfs_data)
    
    conn.commit()
    conn.close()
    
    logger.info("Database initialized successfully")

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

    param_placeholder = "%s" if USE_POSTGRES else "?"

    with get_db_connection() as cursor_or_conn:
        if USE_POSTGRES:
            cursor = cursor_or_conn
            conn = cursor.connection
        else:
            conn = cursor_or_conn
            cursor = conn.cursor()

        # 현재 상태 조회
        cursor.execute(f"""
            SELECT * FROM collection_status WHERE ticker = {param_placeholder}
        """, (ticker,))
        current = cursor.fetchone()

        now = datetime.now().isoformat()

        if current:
            # 기존 레코드 업데이트
            updates = []
            params = []

            if price_date:
                updates.append(f"last_price_date = {param_placeholder}")
                params.append(price_date)

            if trading_flow_date:
                updates.append(f"last_trading_flow_date = {param_placeholder}")
                params.append(trading_flow_date)

            if news_collected:
                updates.append(f"last_news_collected_at = {param_placeholder}")
                params.append(now)

            updates.append(f"last_collection_attempt = {param_placeholder}")
            params.append(now)

            if success:
                updates.append(f"last_successful_collection = {param_placeholder}")
                updates.append("consecutive_failures = 0")
                params.append(now)
            else:
                updates.append("consecutive_failures = consecutive_failures + 1")

            updates.append(f"updated_at = {param_placeholder}")
            params.append(now)

            params.append(ticker)

            cursor.execute(f"""
                UPDATE collection_status
                SET {', '.join(updates)}
                WHERE ticker = {param_placeholder}
            """, params)
        else:
            # 새 레코드 삽입
            cursor.execute(f"""
                INSERT INTO collection_status
                (ticker, last_price_date, last_trading_flow_date,
                 last_news_collected_at, last_collection_attempt,
                 last_successful_collection, consecutive_failures)
                VALUES ({param_placeholder}, {param_placeholder}, {param_placeholder}, {param_placeholder}, {param_placeholder}, {param_placeholder}, {param_placeholder})
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
    param_placeholder = "%s" if USE_POSTGRES else "?"
    
    with get_db_connection() as cursor_or_conn:
        if USE_POSTGRES:
            cursor = cursor_or_conn
        else:
            conn = cursor_or_conn
            cursor = conn.cursor()

        if ticker:
            cursor.execute(f"""
                SELECT * FROM collection_status WHERE ticker = {param_placeholder}
            """, (ticker,))
            result = cursor.fetchone()
            return dict(result) if result else None
        else:
            cursor.execute("""
                SELECT * FROM collection_status ORDER BY ticker
            """)
            return [dict(row) for row in cursor.fetchall()]

if __name__ == "__main__":
    init_db()
