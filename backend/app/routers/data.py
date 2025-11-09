"""
데이터 수집 관련 API 라우터
"""

from fastapi import APIRouter, HTTPException, Query
from app.services.data_collector import ETFDataCollector
from app.services.scheduler import get_scheduler
from app.exceptions import DatabaseException, ValidationException, ScraperException
import sqlite3
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/collect-all")
async def collect_all_data(
    days: int = Query(1, ge=1, le=365, description="수집할 일수 (기본: 1일)")
):
    """
    모든 종목의 가격 데이터를 일괄 수집
    
    - **days**: 수집할 일수 (1-365)
    
    Returns:
        수집 결과 및 종목별 상세 정보
    """
    try:
        collector = ETFDataCollector()
        result = collector.collect_all_tickers(days=days)

        return {
            "message": f"Data collection completed for {result['total_tickers']} tickers",
            "result": result
        }
    except sqlite3.Error as e:
        logger.error(f"Database error during batch collection: {e}")
        raise HTTPException(status_code=500, detail="Database error during batch collection")
    except ScraperException as e:
        logger.error(f"Scraper error during batch collection: {e}")
        raise HTTPException(status_code=503, detail="Data source temporarily unavailable")
    except ValidationException as e:
        logger.error(f"Validation error during batch collection: {e}")
        raise HTTPException(status_code=400, detail="Invalid collection parameters")
    except Exception as e:
        logger.error(f"Unexpected error during batch collection: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Batch collection failed. Please try again later.")


@router.post("/backfill")
async def backfill_data(
    days: int = Query(90, ge=1, le=365, description="백필할 일수 (기본: 90일)")
):
    """
    모든 종목의 히스토리 데이터를 백필
    
    - **days**: 백필할 일수 (1-365일, 기본: 90일)
    
    Returns:
        백필 결과 및 종목별 상세 정보
    """
    try:
        collector = ETFDataCollector()
        result = collector.backfill_all_tickers(days=days)

        return {
            "message": f"Backfill completed for {result['total_tickers']} tickers ({days} days)",
            "result": result
        }
    except sqlite3.Error as e:
        logger.error(f"Database error during backfill: {e}")
        raise HTTPException(status_code=500, detail="Database error during backfill")
    except ScraperException as e:
        logger.error(f"Scraper error during backfill: {e}")
        raise HTTPException(status_code=503, detail="Data source temporarily unavailable")
    except ValidationException as e:
        logger.error(f"Validation error during backfill: {e}")
        raise HTTPException(status_code=400, detail="Invalid backfill parameters")
    except Exception as e:
        logger.error(f"Unexpected error during backfill: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Backfill failed. Please try again later.")


@router.get("/status")
async def get_collection_status():
    """
    데이터 수집 상태 조회

    Returns:
        각 종목별 데이터 수집 현황
    """
    try:
        collector = ETFDataCollector()
        all_etfs = collector.get_all_etfs()

        status_list = []
        for etf in all_etfs:
            # 최근 30일 데이터 조회
            from datetime import date, timedelta
            end_date = date.today()
            start_date = end_date - timedelta(days=30)

            prices = collector.get_price_data(etf.ticker, start_date, end_date)

            status_list.append({
                "ticker": etf.ticker,
                "name": etf.name,
                "type": etf.type,
                "recent_data_count": len(prices),
                "latest_date": prices[0].date if prices else None
            })

        return {
            "total_tickers": len(all_etfs),
            "status": status_list
        }
    except sqlite3.Error as e:
        logger.error(f"Database error getting collection status: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred")
    except Exception as e:
        logger.error(f"Unexpected error getting collection status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get status. Please try again later.")


@router.get("/scheduler-status")
async def get_scheduler_status():
    """
    스케줄러 상태 조회

    Returns:
        스케줄러 실행 상태 및 마지막 수집 시간
    """
    try:
        scheduler = get_scheduler()
        status = scheduler.get_status()

        return {
            "scheduler": status,
            "message": "Scheduler status retrieved successfully"
        }
    except sqlite3.Error as e:
        logger.error(f"Database error getting scheduler status: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred")
    except Exception as e:
        logger.error(f"Unexpected error getting scheduler status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get scheduler status. Please try again later.")

