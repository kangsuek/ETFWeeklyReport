from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict
from datetime import date, timedelta
from app.models import News
from app.services.news_scraper import NewsScraper
from app.services.data_collector import ETFDataCollector
from app.exceptions import DatabaseException, ValidationException, ScraperException
import sqlite3
import logging

router = APIRouter()
logger = logging.getLogger(__name__)
scraper = NewsScraper()
collector = ETFDataCollector()

@router.get("/{ticker}", response_model=List[News])
async def get_news(
    ticker: str,
    start_date: Optional[date] = Query(default=None, description="조회 시작 날짜 (기본: 7일 전)"),
    end_date: Optional[date] = Query(default=None, description="조회 종료 날짜 (기본: 오늘)")
):
    """
    종목별 뉴스 조회
    
    - **ticker**: 종목 코드
    - **start_date**: 시작 날짜 (선택, 기본: 7일 전)
    - **end_date**: 종료 날짜 (선택, 기본: 오늘)
    
    Returns:
        뉴스 리스트 (날짜, 제목, URL, 출처, 관련도 점수)
    """
    # ETF/Stock 존재 확인
    etf_info = collector.get_etf_info(ticker)
    if not etf_info:
        raise HTTPException(status_code=404, detail=f"ETF/Stock not found: {ticker}")
    
    if not start_date:
        start_date = date.today() - timedelta(days=7)
    if not end_date:
        end_date = date.today()
    
    try:
        news_list = scraper.get_news_for_ticker(ticker, start_date, end_date)

        if not news_list:
            logger.warning(f"No news found for {ticker} between {start_date} and {end_date}")

        logger.info(f"Retrieved {len(news_list)} news articles for {ticker}")
        return news_list

    except sqlite3.Error as e:
        logger.error(f"Database error fetching news for {ticker}: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred")
    except ValidationException as e:
        logger.error(f"Validation error fetching news for {ticker}: {e}")
        raise HTTPException(status_code=400, detail="Invalid date range or ticker")
    except Exception as e:
        logger.error(f"Unexpected error fetching news for {ticker}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve news. Please try again later.")

@router.post("/{ticker}/collect")
async def collect_news(
    ticker: str,
    days: int = Query(7, ge=1, le=30, description="수집할 일수 (1-30일)")
) -> Dict:
    """
    종목별 뉴스 수집
    
    - **ticker**: 종목 코드
    - **days**: 수집할 일수 (1-30일, 기본: 7일)
    
    Returns:
        수집 결과 및 저장된 레코드 수
    """
    # ETF/Stock 존재 확인
    etf_info = collector.get_etf_info(ticker)
    if not etf_info:
        raise HTTPException(status_code=404, detail=f"ETF/Stock not found: {ticker}")
    
    try:
        logger.info(f"Starting news collection for {ticker}, days={days}")
        result = scraper.collect_and_save_news(ticker, days)

        result['name'] = etf_info.name
        return result

    except sqlite3.Error as e:
        logger.error(f"Database error collecting news for {ticker}: {e}")
        raise HTTPException(status_code=500, detail="Database error during news collection")
    except ScraperException as e:
        logger.error(f"Scraper error collecting news for {ticker}: {e}")
        raise HTTPException(status_code=503, detail="News source temporarily unavailable")
    except ValidationException as e:
        logger.error(f"Validation error collecting news for {ticker}: {e}")
        raise HTTPException(status_code=400, detail="Invalid collection parameters")
    except Exception as e:
        logger.error(f"Unexpected error collecting news for {ticker}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="News collection failed. Please try again later.")
