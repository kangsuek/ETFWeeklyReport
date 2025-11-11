from pydantic import BaseModel
from typing import Optional, List
from datetime import date

class ETF(BaseModel):
    ticker: str
    name: str
    type: str  # "ETF" or "STOCK"
    theme: Optional[str] = None
    launch_date: Optional[date] = None
    expense_ratio: Optional[float] = None

class PriceData(BaseModel):
    date: date
    open_price: Optional[float] = None
    high_price: Optional[float] = None
    low_price: Optional[float] = None
    close_price: float
    volume: int
    daily_change_pct: Optional[float] = None

class TradingFlow(BaseModel):
    date: date
    individual_net: int
    institutional_net: int
    foreign_net: int

class News(BaseModel):
    date: date
    title: str
    url: str
    source: str
    relevance_score: Optional[float] = None

class ETFMetrics(BaseModel):
    ticker: str
    aum: Optional[float] = None  # in billions KRW
    returns: dict  # {"1w": 0.023, "1m": 0.085, "ytd": 0.153}
    volatility: Optional[float] = None

class ETFDetailResponse(BaseModel):
    etf: ETF
    prices: List[PriceData]
    trading_flow: List[TradingFlow]
    news: List[News]
    metrics: ETFMetrics

# Stock Management Models (for Settings API)
class StockCreate(BaseModel):
    """Model for creating a new stock/ETF"""
    ticker: str  # Stock ticker code (e.g., "005930")
    name: str
    type: str  # "ETF" or "STOCK"
    theme: str
    launch_date: Optional[str] = None  # YYYY-MM-DD format, required for ETF
    expense_ratio: Optional[float] = None  # Required for ETF
    search_keyword: Optional[str] = None
    relevance_keywords: Optional[List[str]] = None

class StockUpdate(BaseModel):
    """Model for updating an existing stock/ETF (partial update)"""
    name: Optional[str] = None
    type: Optional[str] = None
    theme: Optional[str] = None
    launch_date: Optional[str] = None
    expense_ratio: Optional[float] = None
    search_keyword: Optional[str] = None
    relevance_keywords: Optional[List[str]] = None

class StockDeleteResponse(BaseModel):
    """Response model for stock deletion"""
    ticker: str
    deleted: dict  # {"prices": 150, "news": 20, "trading_flow": 30}
