from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import date, timedelta
from app.models import News
from app.services.news_scraper import NewsScraper
import logging

router = APIRouter()
logger = logging.getLogger(__name__)
scraper = NewsScraper()

@router.get("/{ticker}", response_model=List[News])
async def get_news(
    ticker: str,
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None)
):
    """Get news related to ETF theme"""
    if not start_date:
        start_date = date.today() - timedelta(days=7)
    if not end_date:
        end_date = date.today()
    
    try:
        return scraper.get_news_for_ticker(ticker, start_date, end_date)
    except Exception as e:
        logger.error(f"Error fetching news for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
