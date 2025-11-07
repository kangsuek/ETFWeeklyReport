import sqlite3
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent / "data" / "etf_data.db"

def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

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
            launch_date DATE,
            expense_ratio REAL
        )
    """)
    
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
    
    # Insert initial stock data (ETF 4개 + 주식 2개)
    etfs_data = [
        # ETF 4개
        ("487240", "삼성 KODEX AI전력핵심설비 ETF", "ETF", "AI/전력", "2024-03-15", 0.0045),
        ("466920", "신한 SOL 조선TOP3플러스 ETF", "ETF", "조선", "2023-08-10", 0.0050),
        ("0020H0", "KoAct 글로벌양자컴퓨팅액티브 ETF", "ETF", "양자컴퓨팅", "2024-05-20", 0.0070),
        ("442320", "KB RISE 글로벌원자력 iSelect ETF", "ETF", "원자력", "2024-01-25", 0.0055),
        # 주식 2개
        ("042660", "한화오션", "STOCK", "조선/방산", None, None),
        ("034020", "두산에너빌리티", "STOCK", "에너지/전력", None, None)
    ]
    
    cursor.executemany("""
        INSERT OR IGNORE INTO etfs (ticker, name, type, theme, launch_date, expense_ratio)
        VALUES (?, ?, ?, ?, ?, ?)
    """, etfs_data)
    
    conn.commit()
    conn.close()
    
    logger.info("Database initialized successfully")

if __name__ == "__main__":
    init_db()
