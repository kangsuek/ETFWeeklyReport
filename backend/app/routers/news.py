from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional, Dict
from datetime import date, timedelta
from app.models import News, ETF
from app.services.news_scraper import NewsScraper
from app.services.data_collector import ETFDataCollector
from app.exceptions import DatabaseException, ValidationException, ScraperException
from app.utils.date_utils import apply_default_dates
from app.dependencies import get_etf_or_404, get_collector
import sqlite3
import logging

router = APIRouter()
logger = logging.getLogger(__name__)
scraper = NewsScraper()

@router.get("/{ticker}", response_model=List[News])
async def get_news(
    etf: ETF = Depends(get_etf_or_404),
    start_date: Optional[date] = Query(default=None, description="조회 시작 날짜 (기본: 7일 전)"),
    end_date: Optional[date] = Query(default=None, description="조회 종료 날짜 (기본: 오늘)")
):
    """
    종목별 뉴스 조회

    - **etf**: 종목 정보 (자동 주입, 검증됨)
    - **start_date**: 시작 날짜 (선택, 기본: 7일 전)
    - **end_date**: 종료 날짜 (선택, 기본: 오늘)

    Returns:
        뉴스 리스트 (날짜, 제목, URL, 출처, 관련도 점수)
    """
    # 날짜 기본값 설정
    start_date, end_date = apply_default_dates(start_date, end_date, default_days=7)

    try:
        news_list = scraper.get_news_for_ticker(etf.ticker, start_date, end_date)

        if not news_list:
            logger.warning(f"No news found for {etf.ticker} between {start_date} and {end_date}")

        logger.info(f"Retrieved {len(news_list)} news articles for {etf.ticker}")
        return news_list

    except sqlite3.Error as e:
        logger.error(f"Database error fetching news for {etf.ticker}: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred")
    except ValidationException as e:
        logger.error(f"Validation error fetching news for {etf.ticker}: {e}")
        raise HTTPException(status_code=400, detail="Invalid date range or ticker")
    except Exception as e:
        logger.error(f"Unexpected error fetching news for {etf.ticker}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve news. Please try again later.")

@router.post("/{ticker}/collect")
async def collect_news(
    etf: ETF = Depends(get_etf_or_404),
    days: int = Query(7, ge=1, le=30, description="수집할 일수 (1-30일)")
) -> Dict:
    """
    종목별 뉴스 수집

    - **etf**: 종목 정보 (자동 주입, 검증됨)
    - **days**: 수집할 일수 (1-30일, 기본: 7일)

    Returns:
        수집 결과 및 저장된 레코드 수
    """
    try:
        logger.info(f"Starting news collection for {etf.ticker}, days={days}")
        result = scraper.collect_and_save_news(etf.ticker, days)

        result['name'] = etf.name
        return result

    except sqlite3.Error as e:
        logger.error(f"Database error collecting news for {etf.ticker}: {e}")
        raise HTTPException(status_code=500, detail="Database error during news collection")
    except ScraperException as e:
        logger.error(f"Scraper error collecting news for {etf.ticker}: {e}")
        raise HTTPException(status_code=503, detail="News source temporarily unavailable")
    except ValidationException as e:
        logger.error(f"Validation error collecting news for {etf.ticker}: {e}")
        raise HTTPException(status_code=400, detail="Invalid collection parameters")
    except Exception as e:
        logger.error(f"Unexpected error collecting news for {etf.ticker}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="News collection failed. Please try again later.")
