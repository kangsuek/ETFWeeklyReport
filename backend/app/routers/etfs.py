from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import date, timedelta
from app.models import ETF, PriceData, TradingFlow, ETFDetailResponse, ETFMetrics
from app.services.data_collector import ETFDataCollector
import logging

router = APIRouter()
logger = logging.getLogger(__name__)
collector = ETFDataCollector()

@router.get("/", response_model=List[ETF])
async def get_etfs():
    """Get list of all ETFs"""
    try:
        return collector.get_all_etfs()
    except Exception as e:
        logger.error(f"Error fetching ETFs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{ticker}", response_model=ETF)
async def get_etf(ticker: str):
    """Get basic info for specific ETF"""
    try:
        etf = collector.get_etf_info(ticker)
        if not etf:
            raise HTTPException(status_code=404, detail="ETF not found")
        return etf
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching ETF {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{ticker}/prices", response_model=List[PriceData])
async def get_prices(
    ticker: str,
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None),
    days: Optional[int] = Query(default=None, description="Number of days to fetch (alternative to date range)")
):
    """
    Get price data for ETF/Stock within date range
    
    Args:
        ticker: Stock/ETF ticker code
        start_date: Start date (optional, defaults to 7 days ago)
        end_date: End date (optional, defaults to today)
        days: Number of days to fetch (alternative to date range)
    
    Returns:
        List of price data
    
    Raises:
        404: ETF/Stock not found
        500: Internal server error
    """
    logger.info(f"Fetching prices for {ticker}")
    
    # ETF/Stock 존재 확인
    etf = collector.get_etf_info(ticker)
    if not etf:
        logger.warning(f"Stock/ETF {ticker} not found")
        raise HTTPException(status_code=404, detail=f"Stock/ETF {ticker} not found")
    
    # 날짜 범위 설정
    if not start_date:
        start_date = date.today() - timedelta(days=7)
    if not end_date:
        end_date = date.today()
    
    try:
        prices = collector.get_price_data(ticker, start_date, end_date)
        logger.info(f"Successfully fetched {len(prices)} price records for {ticker}")
        return prices
    except Exception as e:
        logger.error(f"Error fetching prices for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch prices: {str(e)}")

@router.post("/{ticker}/collect")
async def collect_prices(
    ticker: str,
    days: int = Query(default=10, description="Number of days to collect")
):
    """
    Trigger data collection from Naver Finance for a specific stock/ETF
    
    Args:
        ticker: Stock/ETF ticker code
        days: Number of days to collect (default: 10)
    
    Returns:
        Collection result with count
    
    Raises:
        404: ETF/Stock not found
        500: Collection failed
    """
    logger.info(f"Starting data collection for {ticker} (days={days})")
    
    # ETF/Stock 존재 확인
    etf = collector.get_etf_info(ticker)
    if not etf:
        logger.warning(f"Stock/ETF {ticker} not found")
        raise HTTPException(status_code=404, detail=f"Stock/ETF {ticker} not found")
    
    try:
        saved_count = collector.collect_and_save_prices(ticker, days=days)
        
        if saved_count == 0:
            logger.warning(f"No data collected for {ticker}")
            return {
                "ticker": ticker,
                "collected": 0,
                "message": "No data collected. Check if the ticker is valid or data is available."
            }
        
        logger.info(f"Successfully collected {saved_count} records for {ticker}")
        return {
            "ticker": ticker,
            "collected": saved_count,
            "message": f"Successfully collected {saved_count} price records"
        }
    except Exception as e:
        logger.error(f"Error collecting data for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=f"Data collection failed: {str(e)}")

@router.get("/{ticker}/trading-flow")
async def get_trading_flow(
    ticker: str,
    start_date: Optional[date] = Query(default=None, description="조회 시작 날짜 (기본: 7일 전)"),
    end_date: Optional[date] = Query(default=None, description="조회 종료 날짜 (기본: 오늘)")
):
    """
    투자자별 매매동향 데이터 조회
    
    - **ticker**: 종목 코드
    - **start_date**: 시작 날짜 (선택, 기본: 7일 전)
    - **end_date**: 종료 날짜 (선택, 기본: 오늘)
    
    Returns:
        매매동향 데이터 리스트 (개인, 기관, 외국인 순매수)
    """
    # 날짜 기본값 설정
    if not start_date:
        start_date = date.today() - timedelta(days=7)
    if not end_date:
        end_date = date.today()
    
    # ETF 존재 확인
    etf_info = collector.get_etf_info(ticker)
    if not etf_info:
        raise HTTPException(status_code=404, detail=f"ETF/Stock not found: {ticker}")
    
    try:
        trading_data = collector.get_trading_flow_data(ticker, start_date, end_date)
        
        if not trading_data:
            logger.warning(f"No trading flow data found for {ticker} between {start_date} and {end_date}")
            return []
        
        logger.info(f"Retrieved {len(trading_data)} trading flow records for {ticker}")
        return trading_data
        
    except Exception as e:
        logger.error(f"Error fetching trading flow for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve trading flow: {str(e)}")


@router.post("/{ticker}/collect-trading-flow")
async def collect_trading_flow(
    ticker: str,
    days: int = Query(10, ge=1, le=90, description="수집할 일수 (1-90일)")
):
    """
    투자자별 매매동향 데이터 수집
    
    - **ticker**: 종목 코드
    - **days**: 수집할 일수 (1-90일, 기본: 10일)
    
    Returns:
        수집 결과 및 저장된 레코드 수
    """
    # ETF 존재 확인
    etf_info = collector.get_etf_info(ticker)
    if not etf_info:
        raise HTTPException(status_code=404, detail=f"ETF/Stock not found: {ticker}")
    
    try:
        logger.info(f"Starting trading flow collection for {ticker}, days={days}")
        saved_count = collector.collect_and_save_trading_flow(ticker, days)
        
        return {
            "ticker": ticker,
            "name": etf_info.name,
            "collected": saved_count,
            "days": days,
            "message": f"Successfully collected {saved_count} trading flow records"
        }
        
    except Exception as e:
        logger.error(f"Error collecting trading flow for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=f"Trading flow collection failed: {str(e)}")

@router.get("/{ticker}/metrics", response_model=ETFMetrics)
async def get_metrics(ticker: str):
    """Get key metrics for ETF"""
    try:
        return collector.get_etf_metrics(ticker)
    except Exception as e:
        logger.error(f"Error fetching metrics for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
