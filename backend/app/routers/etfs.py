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
    end_date: Optional[date] = Query(default=None)
):
    """Get price data for ETF within date range"""
    if not start_date:
        start_date = date.today() - timedelta(days=7)
    if not end_date:
        end_date = date.today()
    
    try:
        return collector.get_price_data(ticker, start_date, end_date)
    except Exception as e:
        logger.error(f"Error fetching prices for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{ticker}/trading-flow", response_model=List[TradingFlow])
async def get_trading_flow(
    ticker: str,
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None)
):
    """Get investor trading flow data"""
    if not start_date:
        start_date = date.today() - timedelta(days=7)
    if not end_date:
        end_date = date.today()
    
    try:
        return collector.get_trading_flow(ticker, start_date, end_date)
    except Exception as e:
        logger.error(f"Error fetching trading flow for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{ticker}/metrics", response_model=ETFMetrics)
async def get_metrics(ticker: str):
    """Get key metrics for ETF"""
    try:
        return collector.get_etf_metrics(ticker)
    except Exception as e:
        logger.error(f"Error fetching metrics for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
