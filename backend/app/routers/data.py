"""
데이터 수집 관련 API 라우터
"""

from fastapi import APIRouter, HTTPException, Query
from app.services.data_collector import ETFDataCollector
from app.services.scheduler import get_scheduler
from app.exceptions import DatabaseException, ValidationException, ScraperException
from app.constants import MAX_COLLECTION_DAYS, DEFAULT_COLLECTION_DAYS, DEFAULT_BACKFILL_DAYS
import sqlite3
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/collect-all")
async def collect_all_data(
    days: int = Query(DEFAULT_COLLECTION_DAYS, ge=1, le=MAX_COLLECTION_DAYS, description=f"수집할 일수 (기본: {DEFAULT_COLLECTION_DAYS}일)")
):
    """
    전체 종목 데이터 일괄 수집

    등록된 모든 종목(6개)의 가격 데이터와 매매동향을 일괄 수집합니다.

    **Query Parameters:**
    - days: 수집할 일수 (기본: 1일, 최대: 365일)

    **Example Request:**
    ```
    # 당일 데이터만 수집 (기본)
    POST /api/data/collect-all

    # 최근 10일 데이터 수집
    POST /api/data/collect-all?days=10
    ```

    **Example Response:**
    ```json
    {
      "message": "Data collection completed for 6 tickers",
      "result": {
        "total_tickers": 6,
        "success_count": 6,
        "fail_count": 0,
        "total_price_records": 6,
        "total_trading_flow_records": 6,
        "total_news_records": 0,
        "details": {
          "487240": {
            "name": "삼성 KODEX AI전력핵심설비 ETF",
            "success": true,
            "price_records": 1,
            "trading_flow_records": 1,
            "news_records": 0
          }
        }
      }
    }
    ```

    **Status Codes:**
    - 200: 성공
    - 400: 잘못된 파라미터
    - 503: 데이터 소스 일시적 오류
    - 500: 서버 오류

    **Notes:**
    - 일반적으로 스케줄러가 자동으로 실행하므로 수동 호출은 불필요
    - 데이터 갱신이 필요한 경우에만 사용
    - 대량 수집 시 시간이 오래 걸릴 수 있음 (약 6초/종목)
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
    days: int = Query(DEFAULT_BACKFILL_DAYS, ge=1, le=MAX_COLLECTION_DAYS, description=f"백필할 일수 (기본: {DEFAULT_BACKFILL_DAYS}일)")
):
    """
    모든 종목의 히스토리 데이터를 백필

    - **days**: 백필할 일수 (1-{MAX_COLLECTION_DAYS}일, 기본: {DEFAULT_BACKFILL_DAYS}일)
    
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


@router.get("/stats")
async def get_data_stats():
    """
    데이터베이스 통계 조회

    각 테이블의 레코드 수와 마지막 수집 시간을 반환합니다.

    **Example Response:**
    ```json
    {
      "etfs": 6,
      "prices": 1500,
      "news": 250,
      "trading_flow": 180,
      "last_collection": "2025-11-12T10:30:00",
      "database_size_mb": 2.5
    }
    ```

    **Status Codes:**
    - 200: 성공
    - 500: 서버 오류
    """
    try:
        from app.database import get_db_connection, DB_PATH
        import os

        with get_db_connection() as conn:
            cursor = conn.cursor()

            # 각 테이블의 레코드 수 조회
            cursor.execute("SELECT COUNT(*) FROM etfs")
            etfs_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM prices")
            prices_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM news")
            news_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM trading_flow")
            trading_flow_count = cursor.fetchone()[0]

            # 마지막 수집 시간 (스케줄러 상태에서 가져옴)
            scheduler = get_scheduler()
            status = scheduler.get_status()
            last_collection = status.get("last_run")

            # 데이터베이스 파일 크기 (MB)
            db_size_bytes = os.path.getsize(DB_PATH) if DB_PATH.exists() else 0
            db_size_mb = round(db_size_bytes / (1024 * 1024), 2)

            return {
                "etfs": etfs_count,
                "prices": prices_count,
                "news": news_count,
                "trading_flow": trading_flow_count,
                "last_collection": last_collection,
                "database_size_mb": db_size_mb
            }
    except sqlite3.Error as e:
        logger.error(f"Database error getting stats: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred")
    except Exception as e:
        logger.error(f"Unexpected error getting stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get stats. Please try again later.")


@router.delete("/reset")
async def reset_database():
    """
    데이터베이스 초기화 (위험!)

    prices, news, trading_flow 테이블의 모든 데이터를 삭제합니다.
    etfs 테이블은 유지됩니다.

    **⚠️ 경고: 이 작업은 되돌릴 수 없습니다!**

    **Example Response:**
    ```json
    {
      "message": "Database reset successfully",
      "deleted": {
        "prices": 1500,
        "news": 250,
        "trading_flow": 180
      }
    }
    ```

    **Status Codes:**
    - 200: 성공
    - 500: 서버 오류
    """
    try:
        from app.database import get_db_connection

        with get_db_connection() as conn:
            cursor = conn.cursor()

            # 삭제 전 레코드 수 확인
            cursor.execute("SELECT COUNT(*) FROM prices")
            prices_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM news")
            news_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM trading_flow")
            trading_flow_count = cursor.fetchone()[0]

            # 테이블 데이터 삭제 (etfs 제외)
            cursor.execute("DELETE FROM prices")
            cursor.execute("DELETE FROM news")
            cursor.execute("DELETE FROM trading_flow")

            conn.commit()

            logger.warning(f"Database reset: deleted {prices_count} prices, {news_count} news, {trading_flow_count} trading_flow records")

            return {
                "message": "Database reset successfully",
                "deleted": {
                    "prices": prices_count,
                    "news": news_count,
                    "trading_flow": trading_flow_count
                }
            }
    except sqlite3.Error as e:
        logger.error(f"Database error during reset: {e}")
        raise HTTPException(status_code=500, detail="Database error during reset")
    except Exception as e:
        logger.error(f"Unexpected error during reset: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to reset database. Please try again later.")

