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
            info.get("search_keyword"),
            relevance_keywords_json
        ))

    logger.info(f"Loading {len(etfs_data)} stocks from configuration")

    cursor.executemany("""
        INSERT OR IGNORE INTO etfs (ticker, name, type, theme, purchase_date, purchase_price, search_keyword, relevance_keywords)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, etfs_data)
    
    conn.commit()
    conn.close()
    
    logger.info("Database initialized successfully")

if __name__ == "__main__":
    init_db()
