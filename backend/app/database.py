import sqlite3
from pathlib import Path
import logging
import os
from contextlib import contextmanager
from threading import Lock
from queue import Queue, Empty
from app.config import Config

logger = logging.getLogger(__name__)

# DATABASE_URL 환경 변수 사용 (설정되지 않으면 기본값 사용)
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    # PostgreSQL 등 다른 DB URL이 제공된 경우
    # 현재는 SQLite만 지원하므로 경고 로깅
    if not DATABASE_URL.startswith("sqlite"):
        logger.warning(f"Only SQLite is currently supported. Ignoring DATABASE_URL: {DATABASE_URL}")
        DB_PATH = Path(__file__).parent.parent / "data" / "etf_data.db"
    else:
        # sqlite:///path/to/db.db 형식에서 경로 추출
        db_path_str = DATABASE_URL.replace("sqlite:///", "")
        DB_PATH = Path(db_path_str)
        logger.info(f"Using DATABASE_URL: {DATABASE_URL}")
else:
    # 기본값: SQLite
    DB_PATH = Path(__file__).parent.parent / "data" / "etf_data.db"
    logger.info(f"Using default database path: {DB_PATH}")

class ConnectionPool:
    """
    Simple connection pool for SQLite

    Note: SQLite has limited benefit from connection pooling compared to
    client-server databases like PostgreSQL. This implementation is
    primarily for future PostgreSQL migration and preventing too many
    concurrent connection creations.
    """
    def __init__(self, max_connections: int = 10):
        self.max_connections = max_connections
        self.pool = Queue(maxsize=max_connections)
        self.lock = Lock()
        self.current_connections = 0
        logger.info(f"Connection pool initialized with max_connections={max_connections}")

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
                else:
                    # Wait for a connection to become available
                    logger.debug("Pool full, waiting for connection...")
                    conn = self.pool.get(block=True)
                    logger.debug("Got connection after waiting")
                    return conn

    def return_connection(self, conn):
        """Return a connection to the pool"""
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
        while not self.pool.empty():
            try:
                conn = self.pool.get_nowait()
                conn.close()
            except Empty:
                break
        self.current_connections = 0
        logger.info("All connections closed")

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
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM etfs")
            rows = cursor.fetchall()
    """
    pool = get_connection_pool()
    conn = pool.get_connection()
    try:
        yield conn
    finally:
        pool.return_connection(conn)

def init_db():
    """Initialize database with schema"""
    DB_PATH.parent.mkdir(exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS etfs (
            ticker TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            theme TEXT,
            purchase_date DATE,
            purchase_price REAL,
            quantity INTEGER,
            search_keyword TEXT,
            relevance_keywords TEXT
        )
    """)
    
    # quantity 컬럼이 없으면 추가 (마이그레이션)
    try:
        cursor.execute("ALTER TABLE etfs ADD COLUMN quantity INTEGER")
        logger.info("Added quantity column to etfs table")
    except sqlite3.OperationalError:
        # 컬럼이 이미 존재하는 경우 무시
        pass
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            date DATE NOT NULL,
            open_price REAL,
            high_price REAL,
            low_price REAL,
            close_price REAL,
            volume INTEGER,
            daily_change_pct REAL,
            FOREIGN KEY (ticker) REFERENCES etfs(ticker),
            UNIQUE(ticker, date)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trading_flow (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            date DATE NOT NULL,
            individual_net INTEGER,
            institutional_net INTEGER,
            foreign_net INTEGER,
            FOREIGN KEY (ticker) REFERENCES etfs(ticker),
            UNIQUE(ticker, date)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            date DATE NOT NULL,
            title TEXT,
            url TEXT,
            source TEXT,
            relevance_score REAL,
            FOREIGN KEY (ticker) REFERENCES etfs(ticker)
        )
    """)
    
    # Create stock_catalog table for ticker catalog
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stock_catalog (
            ticker TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            market TEXT,
            sector TEXT,
            listed_date DATE,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active INTEGER DEFAULT 1
        )
    """)

    # Create collection_status table for tracking data collection
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS collection_status (
            ticker TEXT PRIMARY KEY,
            last_price_date DATE,
            last_trading_flow_date DATE,
            last_news_collected_at TIMESTAMP,
            price_records_count INTEGER DEFAULT 0,
            trading_flow_records_count INTEGER DEFAULT 0,
            news_records_count INTEGER DEFAULT 0,
            last_collection_attempt TIMESTAMP,
            last_successful_collection TIMESTAMP,
            consecutive_failures INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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

    cursor.executemany("""
        INSERT OR IGNORE INTO etfs (ticker, name, type, theme, purchase_date, purchase_price, quantity, search_keyword, relevance_keywords)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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

if __name__ == "__main__":
    init_db()
