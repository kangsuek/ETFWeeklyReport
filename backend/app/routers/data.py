"""
데이터 수집 관련 API 라우터
"""

from fastapi import APIRouter, HTTPException, Query, Depends, Request
from app.services.data_collector import ETFDataCollector
from app.services.scheduler import get_scheduler
from app.exceptions import DatabaseException, ValidationException, ScraperException
from app.dependencies import verify_api_key_dependency
from app.middleware.rate_limit import limiter, RateLimitConfig
from app.utils.cache import get_cache, make_cache_key
from app.constants import (
    MAX_COLLECTION_DAYS,
    DEFAULT_COLLECTION_DAYS,
    DEFAULT_BACKFILL_DAYS,
    ERROR_DATABASE,
    ERROR_DATABASE_COLLECTION,
    ERROR_DATABASE_BACKFILL,
    ERROR_DATABASE_RESET,
    ERROR_VALIDATION_COLLECTION_PARAMS,
    ERROR_VALIDATION_BACKFILL_PARAMS,
    ERROR_SCRAPER,
    ERROR_INTERNAL_COLLECTION,
    ERROR_INTERNAL_BACKFILL,
    ERROR_INTERNAL_GET_STATUS,
    ERROR_INTERNAL_GET_SCHEDULER_STATUS,
    ERROR_INTERNAL_GET_STATS,
    ERROR_INTERNAL_RESET,
    CACHE_TTL_STATUS,
    CACHE_TTL_STATS,
)
import sqlite3
import logging
import os

router = APIRouter()
logger = logging.getLogger(__name__)

# 캐시 설정
CACHE_TTL_SECONDS = int(float(os.getenv("CACHE_TTL_MINUTES", "0.5")) * 60)
cache = get_cache(ttl_seconds=CACHE_TTL_SECONDS)

@router.post("/collect-all")
@limiter.limit(RateLimitConfig.DATA_COLLECTION)
async def collect_all_data(
    request: Request,
    days: int = Query(DEFAULT_COLLECTION_DAYS, ge=1, le=MAX_COLLECTION_DAYS, description=f"수집할 일수 (기본: {DEFAULT_COLLECTION_DAYS}일)"),
    api_key: str = Depends(verify_api_key_dependency)
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
        from datetime import datetime
        import pytz
        
        collector = ETFDataCollector()
        result = collector.collect_all_tickers(days=days)
        
        # 수집 완료 후 스케줄러의 마지막 수집 시간 업데이트
        try:
            scheduler = get_scheduler()
            KST = pytz.timezone('Asia/Seoul')
            scheduler.last_collection_time = datetime.now(KST)
            logger.info(f"스케줄러 마지막 수집 시간 업데이트: {scheduler.last_collection_time}")
        except Exception as e:
            logger.warning(f"스케줄러 마지막 수집 시간 업데이트 실패 (무시): {e}")

        # 수집 후 모든 캐시 무효화 (전체 데이터 갱신)
        cache.clear()
        logger.info("Cache cleared after data collection")

        return {
            "message": f"Data collection completed for {result['total_tickers']} tickers",
            "result": result
        }
    except sqlite3.Error as e:
        logger.error(f"Database error during batch collection: {e}")
        raise HTTPException(status_code=500, detail=ERROR_DATABASE_COLLECTION)
    except ScraperException as e:
        logger.error(f"Scraper error during batch collection: {e}")
        raise HTTPException(status_code=503, detail=ERROR_SCRAPER)
    except ValidationException as e:
        logger.error(f"Validation error during batch collection: {e}")
        raise HTTPException(status_code=400, detail=ERROR_VALIDATION_COLLECTION_PARAMS)
    except Exception as e:
        logger.error(f"Unexpected error during batch collection: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=ERROR_INTERNAL_COLLECTION)


@router.post("/backfill")
@limiter.limit(RateLimitConfig.DATA_COLLECTION)
async def backfill_data(
    request: Request,
    days: int = Query(DEFAULT_BACKFILL_DAYS, ge=1, le=MAX_COLLECTION_DAYS, description=f"백필할 일수 (기본: {DEFAULT_BACKFILL_DAYS}일)"),
    api_key: str = Depends(verify_api_key_dependency)
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

        # 백필 후 모든 캐시 무효화 (히스토리 데이터 갱신)
        cache.clear()
        logger.info("Cache cleared after backfill")

        return {
            "message": f"Backfill completed for {result['total_tickers']} tickers ({days} days)",
            "result": result
        }
    except sqlite3.Error as e:
        logger.error(f"Database error during backfill: {e}")
        raise HTTPException(status_code=500, detail=ERROR_DATABASE_BACKFILL)
    except ScraperException as e:
        logger.error(f"Scraper error during backfill: {e}")
        raise HTTPException(status_code=503, detail=ERROR_SCRAPER)
    except ValidationException as e:
        logger.error(f"Validation error during backfill: {e}")
        raise HTTPException(status_code=400, detail=ERROR_VALIDATION_BACKFILL_PARAMS)
    except Exception as e:
        logger.error(f"Unexpected error during backfill: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=ERROR_INTERNAL_BACKFILL)


@router.get("/status")
@limiter.limit(RateLimitConfig.READ_ONLY)
async def get_collection_status(request: Request):
    """
    데이터 수집 상태 조회

    Returns:
        각 종목별 데이터 수집 현황
    """
    # 캐시 확인
    cache_key = make_cache_key("status")
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        logger.debug(f"Cache hit for {cache_key}")
        return cached_result

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

        result = {
            "total_tickers": len(all_etfs),
            "status": status_list
        }
        cache.set(cache_key, result, ttl_seconds=CACHE_TTL_STATUS)  # 10초 캐싱 (상태 정보)
        return result
    except sqlite3.Error as e:
        logger.error(f"Database error getting collection status: {e}")
        raise HTTPException(status_code=500, detail=ERROR_DATABASE)
    except Exception as e:
        logger.error(f"Unexpected error getting collection status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=ERROR_INTERNAL_GET_STATUS)


@router.get("/scheduler-status")
@limiter.limit(RateLimitConfig.READ_ONLY)
async def get_scheduler_status(request: Request):
    """
    스케줄러 상태 조회

    Returns:
        스케줄러 실행 상태 및 마지막 수집 시간
    """
    # 캐시 확인
    cache_key = make_cache_key("scheduler_status")
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        logger.debug(f"Cache hit for {cache_key}")
        return cached_result

    try:
        scheduler = get_scheduler()
        status = scheduler.get_status()

        result = {
            "scheduler": status,
            "message": "Scheduler status retrieved successfully"
        }
        cache.set(cache_key, result, ttl_seconds=CACHE_TTL_STATUS)  # 10초 캐싱 (상태 정보)
        return result
    except sqlite3.Error as e:
        logger.error(f"Database error getting scheduler status: {e}")
        raise HTTPException(status_code=500, detail=ERROR_DATABASE)
    except Exception as e:
        logger.error(f"Unexpected error getting scheduler status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=ERROR_INTERNAL_GET_SCHEDULER_STATUS)


@router.get("/stats")
@limiter.limit(RateLimitConfig.READ_ONLY)
async def get_data_stats(request: Request):
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
    # 캐시 확인
    cache_key = make_cache_key("stats")
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        logger.debug(f"Cache hit for {cache_key}")
        return cached_result

    try:
        from app.database import get_db_connection, DB_PATH

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

            # 마지막 수집 시간 (가장 최근 가격 데이터 날짜 또는 스케줄러 상태)
            last_collection = None

            # 방법 1: 데이터베이스에서 가장 최근 데이터 날짜 조회
            cursor.execute("""
                SELECT MAX(date) as last_date
                FROM prices
            """)
            last_price_date = cursor.fetchone()[0]

            if last_price_date:
                # 날짜를 datetime으로 변환
                from datetime import datetime
                try:
                    last_collection = datetime.fromisoformat(last_price_date).isoformat()
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse last_price_date: {last_price_date}, error: {e}")
                    last_collection = last_price_date
            else:
                # 방법 2: 데이터가 없으면 스케줄러 상태에서 확인
                try:
                    scheduler = get_scheduler()
                    status = scheduler.get_status()
                    scheduler_time = status.get("last_collection_time")
                    # 스케줄러에서 가져온 값이 None이거나 없으면 None 유지
                    last_collection = scheduler_time if scheduler_time else None
                except (AttributeError, KeyError, Exception) as e:
                    logger.warning(f"Failed to get scheduler status: {e}")
                    last_collection = None

            # 데이터베이스 파일 크기 (MB)
            db_size_bytes = os.path.getsize(DB_PATH) if DB_PATH.exists() else 0
            db_size_mb = round(db_size_bytes / (1024 * 1024), 2)

            result = {
                "etfs": etfs_count,
                "prices": prices_count,
                "news": news_count,
                "trading_flow": trading_flow_count,
                "last_collection": last_collection,
                "database_size_mb": db_size_mb
            }
            cache.set(cache_key, result, ttl_seconds=CACHE_TTL_STATS)  # 1분 캐싱 (통계 정보)
            return result
    except sqlite3.Error as e:
        logger.error(f"Database error getting stats: {e}")
        raise HTTPException(status_code=500, detail=ERROR_DATABASE)
    except Exception as e:
        logger.error(f"Unexpected error getting stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=ERROR_INTERNAL_GET_STATS)


@router.get("/cache/stats")
@limiter.limit(RateLimitConfig.READ_ONLY)
async def get_cache_stats(request: Request):
    """
    캐시 통계 조회

    캐시 히트율, 미스율, 크기 등의 통계 정보를 반환합니다.

    **Example Response:**
    ```json
    {
      "hits": 150,
      "misses": 50,
      "hit_rate_pct": 75.0,
      "total_requests": 200,
      "evictions": 5,
      "sets": 55,
      "current_size": 50,
      "max_size": 1000,
      "default_ttl_seconds": 30
    }
    ```

    **Status Codes:**
    - 200: 성공
    """
    try:
        stats = cache.get_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get cache statistics")


@router.delete("/cache/clear")
@limiter.limit(RateLimitConfig.DANGEROUS)
async def clear_cache(request: Request, api_key: str = Depends(verify_api_key_dependency)):
    """
    캐시 전체 삭제

    모든 캐시 데이터를 삭제합니다.

    **Status Codes:**
    - 200: 성공
    """
    try:
        cache.clear()
        logger.info("Cache manually cleared via API")
        return {
            "message": "Cache cleared successfully"
        }
    except Exception as e:
        logger.error(f"Error clearing cache: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to clear cache")


@router.delete("/reset")
@limiter.limit(RateLimitConfig.DANGEROUS)
async def reset_database(request: Request, api_key: str = Depends(verify_api_key_dependency)):
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

            # 데이터베이스 초기화 후 모든 캐시 무효화
            cache.clear()
            logger.info("Cache cleared after database reset")

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
        raise HTTPException(status_code=500, detail=ERROR_DATABASE_RESET)
    except Exception as e:
        logger.error(f"Unexpected error during reset: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=ERROR_INTERNAL_RESET)

