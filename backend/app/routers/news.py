from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional, Dict
from datetime import date
from app.models import News, ETF
from app.services.news_scraper import NewsScraper
from app.services.data_collector import ETFDataCollector
from app.exceptions import ValidationException, ScraperException
from app.utils.date_utils import apply_default_dates
from app.utils.cache import get_cache, make_cache_key
from app.dependencies import get_etf_or_404, get_collector, verify_api_key_dependency
from app.constants import (
    ERROR_DATABASE,
    ERROR_VALIDATION_DATE_RANGE,
    ERROR_SCRAPER_NEWS,
    ERROR_VALIDATION_COLLECTION_PARAMS,
    ERROR_INTERNAL_FETCH_NEWS,
    ERROR_INTERNAL_COLLECTION,
    CACHE_TTL_SLOW_CHANGING,
)
import sqlite3
import logging
import os

router = APIRouter()
logger = logging.getLogger(__name__)
scraper = NewsScraper()

# 캐시 설정
CACHE_TTL_SECONDS = int(float(os.getenv("CACHE_TTL_MINUTES", "0.5")) * 60)
cache = get_cache(ttl_seconds=CACHE_TTL_SECONDS)

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

    # 캐시 확인
    cache_key = make_cache_key("news", ticker=etf.ticker, start_date=start_date, end_date=end_date)
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        logger.debug(f"Cache hit for {cache_key}")
        return cached_result

    try:
        news_list = scraper.get_news_for_ticker(etf.ticker, start_date, end_date)

        if not news_list:
            logger.info(
                "No cached news for %s (%s ~ %s). Triggering on-demand collection.",
                etf.ticker,
                start_date,
                end_date,
            )
            days_requested = (end_date - start_date).days + 1
            days_to_collect = max(1, min(30, days_requested if days_requested > 0 else 7))
            try:
                collect_result = scraper.collect_and_save_news(etf.ticker, days=days_to_collect)
                logger.info(
                    "On-demand news collection completed for %s: %s",
                    etf.ticker,
                    collect_result,
                )
            except ScraperException as e:
                logger.error("On-demand news collection failed for %s: %s", etf.ticker, e)
                # continue to return empty result below
            except Exception as e:
                logger.error(
                    "Unexpected error during on-demand news collection for %s: %s",
                    etf.ticker,
                    e,
                    exc_info=True,
                )

            news_list = scraper.get_news_for_ticker(etf.ticker, start_date, end_date)

        if not news_list:
            logger.warning(f"No news found for {etf.ticker} between {start_date} and {end_date}")
            cache.set(cache_key, [], ttl_seconds=CACHE_TTL_SLOW_CHANGING)  # 1분 캐싱 (빈 결과도 캐싱)
            return []

        logger.info(f"Retrieved {len(news_list)} news articles for {etf.ticker}")
        cache.set(cache_key, news_list, ttl_seconds=CACHE_TTL_SLOW_CHANGING)  # 1분 캐싱 (뉴스)
        return news_list

    except sqlite3.Error as e:
        logger.error(f"Database error fetching news for {etf.ticker}: {e}")
        raise HTTPException(status_code=500, detail=ERROR_DATABASE)
    except ValidationException as e:
        logger.error(f"Validation error fetching news for {etf.ticker}: {e}")
        raise HTTPException(status_code=400, detail=ERROR_VALIDATION_DATE_RANGE)
    except Exception as e:
        logger.error(f"Unexpected error fetching news for {etf.ticker}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=ERROR_INTERNAL_FETCH_NEWS)

@router.post("/{ticker}/collect")
async def collect_news(
    etf: ETF = Depends(get_etf_or_404),
    days: int = Query(7, ge=1, le=30, description="수집할 일수 (1-30일)"),
    api_key: str = Depends(verify_api_key_dependency)
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

        # 수집 후 해당 티커의 뉴스 캐시 무효화
        cache.invalidate_pattern(f"news:{etf.ticker}")

        result['name'] = etf.name
        return result

    except sqlite3.Error as e:
        logger.error(f"Database error collecting news for {etf.ticker}: {e}")
        raise HTTPException(status_code=500, detail=ERROR_DATABASE_COLLECTION)
    except ScraperException as e:
        logger.error(f"Scraper error collecting news for {etf.ticker}: {e}")
        raise HTTPException(status_code=503, detail=ERROR_SCRAPER_NEWS)
    except ValidationException as e:
        logger.error(f"Validation error collecting news for {etf.ticker}: {e}")
        raise HTTPException(status_code=400, detail=ERROR_VALIDATION_COLLECTION_PARAMS)
    except Exception as e:
        logger.error(f"Unexpected error collecting news for {etf.ticker}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=ERROR_INTERNAL_COLLECTION)
