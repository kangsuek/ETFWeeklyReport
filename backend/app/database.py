import sqlite3
from pathlib import Path
import logging
from app.config import Config

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
    
    # Insert initial stock data from config (ETF 4개 + 주식 2개)
    stock_config = Config.get_stock_config()
    etfs_data = []
    
    for ticker, info in stock_config.items():
        etfs_data.append((
            ticker,
            info.get("name"),
            info.get("type"),
            info.get("theme"),
            info.get("launch_date"),
            info.get("expense_ratio")
        ))
    
    logger.info(f"Loading {len(etfs_data)} stocks from configuration")
    
    cursor.executemany("""
        INSERT OR IGNORE INTO etfs (ticker, name, type, theme, launch_date, expense_ratio)
        VALUES (?, ?, ?, ?, ?, ?)
    """, etfs_data)
    
    conn.commit()
    conn.close()
    
    logger.info("Database initialized successfully")

if __name__ == "__main__":
    init_db()
