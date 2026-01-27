from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import date

class ETF(BaseModel):
    ticker: str
    name: str
    type: str  # "ETF" or "STOCK"
    theme: Optional[str] = None
    purchase_date: Optional[date] = None  # 구매일
    purchase_price: Optional[float] = None  # 매입 평균 금액
    quantity: Optional[int] = None  # 보유 수량
    search_keyword: Optional[str] = None
    relevance_keywords: Optional[List[str]] = None

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
    max_drawdown: Optional[float] = None  # 최대 낙폭 (%)
    sharpe_ratio: Optional[float] = None  # 샤프 비율

class ETFDetailResponse(BaseModel):
    etf: ETF
    prices: List[PriceData]
    trading_flow: List[TradingFlow]
    news: List[News]
    metrics: ETFMetrics

# Settings API Models
class StockCreate(BaseModel):
    """종목 추가 요청"""
    ticker: str  # Stock ticker code (e.g., "005930")
    name: str
    type: str  # "ETF" or "STOCK"
    theme: Optional[str] = None  # Theme/sector (optional)
    purchase_date: Optional[str] = None  # YYYY-MM-DD format, 구매일 (선택)
    purchase_price: Optional[float] = None  # 매입 평균 금액 (선택)
    quantity: Optional[int] = None  # 보유 수량 (선택)
    search_keyword: Optional[str] = None
    relevance_keywords: Optional[List[str]] = None

class StockUpdate(BaseModel):
    """종목 수정 요청 (부분 업데이트 지원)"""
    name: Optional[str] = None
    type: Optional[str] = None
    theme: Optional[str] = None
    purchase_date: Optional[str] = None  # 구매일
    purchase_price: Optional[float] = None  # 매입 평균 금액
    quantity: Optional[int] = None  # 보유 수량
    search_keyword: Optional[str] = None
    relevance_keywords: Optional[List[str]] = None

class StockDeleteResponse(BaseModel):
    """종목 삭제 응답"""
    ticker: str
    deleted: dict  # {"prices": 150, "news": 20, "trading_flow": 30}

# Batch API Models
class ETFCardSummary(BaseModel):
    """대시보드 카드에 표시할 종목별 요약 데이터"""
    ticker: str
    latest_price: Optional[PriceData] = None  # 최신 가격 (5일치 중 첫번째)
    prices: List[PriceData] = []  # 최근 5일 가격 (차트용)
    weekly_return: Optional[float] = None  # 주간 수익률
    latest_trading_flow: Optional[TradingFlow] = None  # 최근 1일 매매동향
    latest_news: List[News] = []  # 최근 5개 뉴스

class BatchSummaryRequest(BaseModel):
    """배치 요약 요청"""
    tickers: List[str] = Field(..., max_length=50)  # 종목 코드 리스트 (최대 50개)
    price_days: int = Field(default=5, ge=1, le=365)  # 가격 데이터 일수 (1-365일)
    news_limit: int = Field(default=5, ge=1, le=100)  # 뉴스 개수 (1-100개)

    @field_validator('tickers')
    @classmethod
    def validate_tickers_length(cls, v):
        if len(v) > 50:
            raise ValueError('한 번에 최대 50개의 종목만 요청할 수 있습니다')
        if len(v) == 0:
            raise ValueError('최소 1개의 종목을 지정해야 합니다')
        return v

class BatchSummaryResponse(BaseModel):
    """배치 요약 응답"""
    data: dict  # {ticker: ETFCardSummary}

# Insights API Models
class StrategyInsights(BaseModel):
    """투자 전략 인사이트"""
    short_term: str  # 단기 전략: "비중확대", "보유", "관망", "비중축소"
    medium_term: str  # 중기 전략
    long_term: str  # 장기 전략
    recommendation: str  # 종합 추천
    comment: str  # 코멘트

class ETFInsights(BaseModel):
    """종목 인사이트"""
    strategy: StrategyInsights
    key_points: List[str]  # 핵심 포인트 (최대 3개)
    risks: List[str]  # 리스크 요약 (최대 3개)
