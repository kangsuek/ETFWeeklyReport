from typing import List, Optional
from datetime import date
from app.models import ETF, PriceData, TradingFlow, ETFMetrics
from app.database import get_db_connection
import logging

logger = logging.getLogger(__name__)

class ETFDataCollector:
    """Service for collecting ETF data from various sources"""
    
    def get_all_etfs(self) -> List[ETF]:
        """Get list of all ETFs from database"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM etfs")
        rows = cursor.fetchall()
        conn.close()
        
        return [ETF(**dict(row)) for row in rows]
    
    def get_etf_info(self, ticker: str) -> Optional[ETF]:
        """Get basic info for specific ETF"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM etfs WHERE ticker = ?", (ticker,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return ETF(**dict(row))
        return None
    
    def get_price_data(self, ticker: str, start_date: date, end_date: date) -> List[PriceData]:
        """Get price data for date range"""
        # TODO: Implement actual data collection from Naver Finance or other sources
        # For now, return empty list
        logger.info(f"Fetching prices for {ticker} from {start_date} to {end_date}")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT date, close_price, volume, daily_change_pct
            FROM prices
            WHERE ticker = ? AND date BETWEEN ? AND ?
            ORDER BY date DESC
        """, (ticker, start_date, end_date))
        rows = cursor.fetchall()
        conn.close()
        
        return [PriceData(**dict(row)) for row in rows]
    
    def get_trading_flow(self, ticker: str, start_date: date, end_date: date) -> List[TradingFlow]:
        """Get trading flow data"""
        logger.info(f"Fetching trading flow for {ticker} from {start_date} to {end_date}")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT date, individual_net, institutional_net, foreign_net
            FROM trading_flow
            WHERE ticker = ? AND date BETWEEN ? AND ?
            ORDER BY date DESC
        """, (ticker, start_date, end_date))
        rows = cursor.fetchall()
        conn.close()
        
        return [TradingFlow(**dict(row)) for row in rows]
    
    def get_etf_metrics(self, ticker: str) -> ETFMetrics:
        """Calculate key metrics for ETF"""
        # TODO: Implement metrics calculation
        logger.info(f"Calculating metrics for {ticker}")
        
        return ETFMetrics(
            ticker=ticker,
            aum=None,
            returns={"1w": 0.0, "1m": 0.0, "ytd": 0.0},
            volatility=None
        )
