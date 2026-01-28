from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
from datetime import date, timedelta
from app.models import (
    ETF, PriceData, TradingFlow, ETFDetailResponse, ETFMetrics,
    ETFCardSummary, BatchSummaryRequest, BatchSummaryResponse,
    ETFInsights, BenchmarkComparison
)
from app.services.data_collector import ETFDataCollector
from app.services.comparison_service import ComparisonService
from app.exceptions import DatabaseException, ValidationException, ScraperException
from app.utils.date_utils import apply_default_dates
from app.utils.data_collection import auto_collect_if_needed
from app.utils.cache import get_cache, make_cache_key
from app.dependencies import get_etf_or_404, get_collector, verify_api_key_dependency
from app.constants import (
    ERROR_DATABASE,
    ERROR_DATABASE_COLLECTION,
    ERROR_VALIDATION,
    ERROR_VALIDATION_TICKER,
    ERROR_VALIDATION_DATE_RANGE,
    ERROR_VALIDATION_COLLECTION_PARAMS,
    ERROR_SCRAPER,
    ERROR_SCRAPER_COLLECTION,
    ERROR_INTERNAL,
    ERROR_INTERNAL_FETCH_PRICES,
    ERROR_INTERNAL_FETCH_TRADING_FLOW,
    ERROR_INTERNAL_FETCH_METRICS,
    ERROR_INTERNAL_COMPARE,
    ERROR_INTERNAL_COLLECTION,
    CACHE_TTL_STATIC,
    CACHE_TTL_FAST_CHANGING,
    CACHE_TTL_SLOW_CHANGING,
)
import sqlite3
import logging
import os

router = APIRouter()
logger = logging.getLogger(__name__)

# 캐시 설정 (환경 변수에서 TTL 가져오기, 기본값 30초)
CACHE_TTL_SECONDS = int(float(os.getenv("CACHE_TTL_MINUTES", "0.5")) * 60)  # 분을 초로 변환
cache = get_cache(ttl_seconds=CACHE_TTL_SECONDS)

@router.get("/", response_model=List[ETF])
async def get_etfs(collector: ETFDataCollector = Depends(get_collector)):
    """
    전체 종목 목록 조회

    등록된 모든 ETF 및 주식 종목의 기본 정보를 반환합니다.

    **Returns:**
    종목 목록 (ETF 4개 + 주식 2개 = 총 6개)

    **Example Request:**
    ```
    GET /api/etfs/
    ```

    **Example Response:**
    ```json
    [
      {
        "ticker": "487240",
        "name": "삼성 KODEX AI전력핵심설비 ETF",
        "type": "ETF",
        "theme": "AI/전력",
        "launch_date": "2024-03-15",
        "expense_ratio": 0.0045
      },
      {
        "ticker": "042660",
        "name": "한화오션",
        "type": "STOCK",
        "theme": "조선/방산",
        "launch_date": null,
        "expense_ratio": null
      }
    ]
    ```

    **Status Codes:**
    - 200: 성공
    - 500: 서버 오류
    """
    # 캐시 확인
    cache_key = make_cache_key("etfs")
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        logger.debug(f"Cache hit for {cache_key}")
        return cached_result

    try:
        result = collector.get_all_etfs()
        cache.set(cache_key, result, ttl_seconds=CACHE_TTL_STATIC)  # 5분 캐싱 (정적 데이터)
        return result
    except sqlite3.Error as e:
        logger.error(f"Database error fetching ETFs: {e}")
        raise HTTPException(status_code=500, detail=ERROR_DATABASE)
    except ValidationException as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=ERROR_VALIDATION)
    except Exception as e:
        logger.error(f"Unexpected error fetching ETFs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=ERROR_INTERNAL)


@router.get("/compare")
async def compare_etfs(
    tickers: str = Query(..., description="Comma-separated ticker codes (2-6 tickers)"),
    start_date: Optional[date] = Query(default=None, description="Start date (default: 30 days ago)"),
    end_date: Optional[date] = Query(default=None, description="End date (default: today)"),
    collector: ETFDataCollector = Depends(get_collector)
):
    """
    종목 비교 분석

    여러 종목의 가격 변화를 비교하고 통계 지표를 제공합니다.

    **Query Parameters:**
    - tickers: 쉼표로 구분된 종목 코드 (2-6개, 예: "487240,466920,042660")
    - start_date: 조회 시작 날짜 (선택, 기본값: 30일 전)
    - end_date: 조회 종료 날짜 (선택, 기본값: 오늘)

    **Example Request:**
    ```
    GET /api/etfs/compare?tickers=487240,466920,042660&start_date=2025-10-01&end_date=2025-11-13
    ```

    **Example Response:**
    ```json
    {
      "normalized_prices": {
        "dates": ["2025-10-01", "2025-10-02", ...],
        "data": {
          "487240": [100, 102.5, 98.3, ...],
          "466920": [100, 101.2, 99.8, ...],
          "042660": [100, 103.1, 105.2, ...]
        }
      },
      "statistics": {
        "487240": {
          "period_return": 12.5,
          "annualized_return": 45.2,
          "volatility": 25.3,
          "max_drawdown": -8.2,
          "sharpe_ratio": 1.67,
          "data_points": 30
        },
        ...
      },
      "correlation_matrix": {
        "tickers": ["487240", "466920", "042660"],
        "matrix": [
          [1.0, 0.85, 0.72],
          [0.85, 1.0, 0.68],
          [0.72, 0.68, 1.0]
        ]
      }
    }
    ```

    **Response Fields:**
    - normalized_prices: 정규화된 가격 (시작일 = 100)
      - dates: 날짜 배열
      - data: 종목별 정규화 가격 배열
    - statistics: 종목별 통계
      - period_return: 기간 수익률 (%)
      - annualized_return: 연환산 수익률 (%)
      - volatility: 연환산 변동성 (%)
      - max_drawdown: 최대 낙폭 (%)
      - sharpe_ratio: 샤프 비율
      - data_points: 데이터 개수
    - correlation_matrix: 상관관계 행렬
      - tickers: 종목 코드 배열
      - matrix: 상관계수 행렬 (2차원 배열)

    **Status Codes:**
    - 200: 성공
    - 400: 잘못된 요청 (티커 개수, 날짜 범위 등)
    - 500: 서버 오류

    **Notes:**
    - 최소 2개, 최대 6개 종목 비교 가능
    - 최대 조회 기간: 1년 (365일)
    - 데이터가 없는 종목은 결과에서 제외
    - 상관관계는 일일 수익률 기준으로 계산
    """
    # 티커 파싱 (쉼표로 구분)
    ticker_list = [t.strip() for t in tickers.split(',') if t.strip()]

    # 날짜 기본값 설정
    start_date, end_date = apply_default_dates(start_date, end_date, default_days=30)

    # 캐시 확인
    cache_key = make_cache_key("compare", tickers=",".join(sorted(ticker_list)), start_date=start_date, end_date=end_date)
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        logger.debug(f"Cache hit for {cache_key}")
        return cached_result

    try:
        logger.info(f"Comparing tickers: {ticker_list}, date range: {start_date} to {end_date}")

        # 각 종목에 대해 자동 수집 수행 (데이터가 없는 경우)
        # auto_collect_if_needed를 사용하여 데이터 수집 및 재조회
        for ticker in ticker_list:
            try:
                logger.info(f"Checking and auto-collecting price data for {ticker} if needed")
                auto_collect_if_needed(
                    ticker=ticker,
                    start_date=start_date,
                    end_date=end_date,
                    get_data_fn=collector.get_price_data,
                    get_data_range_fn=collector.get_price_data_range,
                    collect_fn=collector.collect_and_save_prices,
                    data_type="price",
                    pass_dates_to_collect=False
                )
                logger.info(f"Price data ready for {ticker}")
            except ScraperException as e:
                # 스크래퍼 오류는 로그만 남기고 계속 진행 (다른 종목은 비교 가능)
                logger.warning(f"Failed to auto-collect price data for {ticker}: {e}")
            except Exception as e:
                # 기타 오류도 로그만 남기고 계속 진행
                logger.warning(f"Unexpected error while auto-collecting for {ticker}: {e}")

        # 비교 서비스 생성 및 실행
        comparison_service = ComparisonService()
        result = comparison_service.get_comparison_data(ticker_list, start_date, end_date)

        logger.info(f"Comparison completed for {len(ticker_list)} tickers")
        cache.set(cache_key, result, ttl_seconds=CACHE_TTL_SLOW_CHANGING)  # 1분 캐싱 (복잡한 연산)
        return result

    except ValidationException as e:
        logger.error(f"Validation error in compare_etfs: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except sqlite3.Error as e:
        logger.error(f"Database error in compare_etfs: {e}")
        raise HTTPException(status_code=500, detail=ERROR_DATABASE)
    except Exception as e:
        logger.error(f"Unexpected error in compare_etfs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=ERROR_INTERNAL_COMPARE)


@router.get("/{ticker}", response_model=ETF)
async def get_etf(etf: ETF = Depends(get_etf_or_404)):
    """
    특정 종목 상세 정보 조회

    종목 코드(ticker)로 특정 ETF 또는 주식의 상세 정보를 조회합니다.

    **Path Parameters:**
    - ticker: 종목 코드 (예: 487240, 042660)

    **Example Request:**
    ```
    GET /api/etfs/487240
    ```

    **Example Response:**
    ```json
    {
      "ticker": "487240",
      "name": "삼성 KODEX AI전력핵심설비 ETF",
      "type": "ETF",
      "theme": "AI/전력",
      "launch_date": "2024-03-15",
      "expense_ratio": 0.0045
    }
    ```

    **Status Codes:**
    - 200: 성공
    - 404: 종목을 찾을 수 없음
    - 500: 서버 오류
    """
    # 캐시 확인
    cache_key = make_cache_key("etf", ticker=etf.ticker)
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        logger.debug(f"Cache hit for {cache_key}")
        return cached_result

    try:
        cache.set(cache_key, etf, ttl_seconds=CACHE_TTL_STATIC)  # 5분 캐싱 (정적 데이터)
        return etf
    except HTTPException:
        raise
    except sqlite3.Error as e:
        logger.error(f"Database error fetching ETF {etf.ticker}: {e}")
        raise HTTPException(status_code=500, detail=ERROR_DATABASE)
    except ValidationException as e:
        logger.error(f"Validation error for ticker {etf.ticker}: {e}")
        raise HTTPException(status_code=400, detail=ERROR_VALIDATION_TICKER)
    except Exception as e:
        logger.error(f"Unexpected error fetching ETF {etf.ticker}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=ERROR_INTERNAL)

@router.get("/{ticker}/prices", response_model=List[PriceData])
async def get_prices(
    etf: ETF = Depends(get_etf_or_404),
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None),
    days: Optional[int] = Query(default=None, description="Number of days to fetch (alternative to date range)"),
    collector: ETFDataCollector = Depends(get_collector)
):
    """
    종목 가격 데이터 조회 (자동 수집 지원)

    지정한 기간 동안의 가격 데이터(시가, 고가, 저가, 종가, 거래량, 등락률)를 조회합니다.
    요청한 기간의 데이터가 DB에 없으면 자동으로 수집합니다.

    **Path Parameters:**
    - ticker: 종목 코드 (예: 487240)

    **Query Parameters:**
    - start_date: 조회 시작 날짜 (선택, 기본값: 7일 전)
    - end_date: 조회 종료 날짜 (선택, 기본값: 오늘)
    - days: 조회 일수 (선택, date range 대신 사용 가능)

    **Example Requests:**
    ```
    # 기본 (최근 7일)
    GET /api/etfs/487240/prices

    # 날짜 범위 지정
    GET /api/etfs/487240/prices?start_date=2025-11-01&end_date=2025-11-09

    # 최근 N일
    GET /api/etfs/487240/prices?days=30
    ```

    **Example Response:**
    ```json
    [
      {
        "date": "2025-11-09",
        "open_price": 12400.0,
        "high_price": 12600.0,
        "low_price": 12300.0,
        "close_price": 12500.0,
        "volume": 1000000,
        "daily_change_pct": 2.5
      },
      {
        "date": "2025-11-08",
        "open_price": 12200.0,
        "high_price": 12450.0,
        "low_price": 12150.0,
        "close_price": 12400.0,
        "volume": 850000,
        "daily_change_pct": 1.2
      }
    ]
    ```

    **Response Fields:**
    - date: 거래 날짜
    - open_price: 시가
    - high_price: 고가
    - low_price: 저가
    - close_price: 종가
    - volume: 거래량
    - daily_change_pct: 전일 대비 등락률 (%)

    **Status Codes:**
    - 200: 성공
    - 404: 종목을 찾을 수 없음
    - 400: 잘못된 날짜 범위
    - 500: 서버 오류

    **Notes:**
    - 데이터는 최신순(날짜 내림차순)으로 정렬됨
    - 주말/공휴일 데이터는 포함되지 않음
    - 최대 조회 가능 기간: 1년 (365일)
    - 데이터 부족 시 자동 수집 (최대 30초 소요)
    """
    logger.info(f"Fetching prices for {etf.ticker}")

    # 날짜 범위 설정
    start_date, end_date = apply_default_dates(start_date, end_date, default_days=7)

    # 캐시 확인
    cache_key = make_cache_key("prices", ticker=etf.ticker, start_date=start_date, end_date=end_date)
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        logger.debug(f"Cache hit for {cache_key}")
        return cached_result

    try:
        # 자동 수집 로직을 포함한 데이터 조회
        prices = auto_collect_if_needed(
            ticker=etf.ticker,
            start_date=start_date,
            end_date=end_date,
            get_data_fn=collector.get_price_data,
            get_data_range_fn=collector.get_price_data_range,
            collect_fn=collector.collect_and_save_prices,
            data_type="price",
            pass_dates_to_collect=False
        )

        logger.info(f"Successfully fetched {len(prices)} price records for {etf.ticker}")
        cache.set(cache_key, prices, ttl_seconds=CACHE_TTL_FAST_CHANGING)  # 30초 캐싱 (가격 데이터)
        return prices

    except sqlite3.Error as e:
        logger.error(f"Database error fetching prices for {etf.ticker}: {e}")
        raise HTTPException(status_code=500, detail=ERROR_DATABASE)
    except ValidationException as e:
        logger.error(f"Validation error fetching prices for {etf.ticker}: {e}")
        raise HTTPException(status_code=400, detail=ERROR_VALIDATION_DATE_RANGE)
    except ScraperException as e:
        logger.error(f"Scraper error auto-collecting prices for {etf.ticker}: {e}")
        raise HTTPException(status_code=503, detail=ERROR_SCRAPER_COLLECTION)
    except Exception as e:
        logger.error(f"Unexpected error fetching prices for {etf.ticker}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=ERROR_INTERNAL_FETCH_PRICES)

@router.post("/{ticker}/collect")
async def collect_prices(
    etf: ETF = Depends(get_etf_or_404),
    days: int = Query(default=10, description="Number of days to collect"),
    collector: ETFDataCollector = Depends(get_collector),
    api_key: str = Depends(verify_api_key_dependency)
):
    """
    Trigger data collection from Naver Finance for a specific stock/ETF

    Args:
        etf: ETF/Stock model (injected, validated)
        days: Number of days to collect (default: 10)
        collector: Data collector instance (injected)

    Returns:
        Collection result with count

    Raises:
        404: ETF/Stock not found
        500: Collection failed
    """
    logger.info(f"Starting data collection for {etf.ticker} (days={days})")

    try:
        saved_count = collector.collect_and_save_prices(etf.ticker, days=days)

        # 수집 후 해당 티커의 캐시 무효화
        cache.invalidate_pattern(f"prices:{etf.ticker}")
        cache.invalidate_pattern(f"etf:{etf.ticker}")
        cache.invalidate_pattern(f"metrics:{etf.ticker}")

        if saved_count == 0:
            logger.warning(f"No data collected for {etf.ticker}")
            return {
                "ticker": etf.ticker,
                "collected": 0,
                "message": "No data collected. Check if the ticker is valid or data is available."
            }

        logger.info(f"Successfully collected {saved_count} records for {etf.ticker}")
        return {
            "ticker": etf.ticker,
            "collected": saved_count,
            "message": f"Successfully collected {saved_count} price records"
        }
    except sqlite3.Error as e:
        logger.error(f"Database error collecting data for {etf.ticker}: {e}")
        raise HTTPException(status_code=500, detail=ERROR_DATABASE_COLLECTION)
    except ScraperException as e:
        logger.error(f"Scraper error collecting data for {etf.ticker}: {e}")
        raise HTTPException(status_code=503, detail=ERROR_SCRAPER)
    except ValidationException as e:
        logger.error(f"Validation error collecting data for {etf.ticker}: {e}")
        raise HTTPException(status_code=400, detail=ERROR_VALIDATION_COLLECTION_PARAMS)
    except Exception as e:
        logger.error(f"Unexpected error collecting data for {etf.ticker}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=ERROR_INTERNAL_COLLECTION)

@router.get("/{ticker}/trading-flow")
async def get_trading_flow(
    etf: ETF = Depends(get_etf_or_404),
    start_date: Optional[date] = Query(default=None, description="조회 시작 날짜 (기본: 7일 전)"),
    end_date: Optional[date] = Query(default=None, description="조회 종료 날짜 (기본: 오늘)"),
    collector: ETFDataCollector = Depends(get_collector)
):
    """
    투자자별 매매동향 데이터 조회 (자동 수집 지원)

    - **etf**: 종목 정보 (자동 주입, 검증됨)
    - **start_date**: 시작 날짜 (선택, 기본: 7일 전)
    - **end_date**: 종료 날짜 (선택, 기본: 오늘)

    Returns:
        매매동향 데이터 리스트 (개인, 기관, 외국인 순매수)

    Notes:
        - 데이터 부족 시 자동 수집 (최대 30초 소요)
    """
    # 날짜 기본값 설정
    start_date, end_date = apply_default_dates(start_date, end_date, default_days=7)

    # 캐시 확인
    cache_key = make_cache_key("trading_flow", ticker=etf.ticker, start_date=start_date, end_date=end_date)
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        logger.debug(f"Cache hit for {cache_key}")
        return cached_result

    try:
        # 자동 수집 로직을 포함한 데이터 조회
        trading_data = auto_collect_if_needed(
            ticker=etf.ticker,
            start_date=start_date,
            end_date=end_date,
            get_data_fn=collector.get_trading_flow_data,
            get_data_range_fn=collector.get_trading_flow_data_range,
            collect_fn=collector.collect_and_save_trading_flow,
            data_type="trading flow",
            pass_dates_to_collect=True
        )

        if not trading_data:
            logger.warning(f"No trading flow data found for {etf.ticker} between {start_date} and {end_date}")
            cache.set(cache_key, [], ttl_seconds=CACHE_TTL_FAST_CHANGING)  # 30초 캐싱 (빈 결과도 캐싱)
            return []

        logger.info(f"Retrieved {len(trading_data)} trading flow records for {etf.ticker}")
        cache.set(cache_key, trading_data, ttl_seconds=CACHE_TTL_FAST_CHANGING)  # 30초 캐싱 (매매동향)
        return trading_data

    except sqlite3.Error as e:
        logger.error(f"Database error fetching trading flow for {etf.ticker}: {e}")
        raise HTTPException(status_code=500, detail=ERROR_DATABASE)
    except ValidationException as e:
        logger.error(f"Validation error fetching trading flow for {etf.ticker}: {e}")
        raise HTTPException(status_code=400, detail=ERROR_VALIDATION_DATE_RANGE)
    except ScraperException as e:
        logger.error(f"Scraper error auto-collecting trading flow for {etf.ticker}: {e}")
        raise HTTPException(status_code=503, detail=ERROR_SCRAPER_COLLECTION)
    except Exception as e:
        logger.error(f"Unexpected error fetching trading flow for {etf.ticker}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=ERROR_INTERNAL_FETCH_TRADING_FLOW)


@router.post("/{ticker}/collect-trading-flow")
async def collect_trading_flow(
    etf: ETF = Depends(get_etf_or_404),
    days: int = Query(10, ge=1, le=90, description="수집할 일수 (1-90일)"),
    collector: ETFDataCollector = Depends(get_collector),
    api_key: str = Depends(verify_api_key_dependency)
):
    """
    투자자별 매매동향 데이터 수집

    - **etf**: 종목 정보 (자동 주입, 검증됨)
    - **days**: 수집할 일수 (1-90일, 기본: 10일)

    Returns:
        수집 결과 및 저장된 레코드 수
    """
    try:
        logger.info(f"Starting trading flow collection for {etf.ticker}, days={days}")
        saved_count = collector.collect_and_save_trading_flow(etf.ticker, days)

        # 수집 후 해당 티커의 캐시 무효화
        cache.invalidate_pattern(f"trading_flow:{etf.ticker}")

        return {
            "ticker": etf.ticker,
            "name": etf.name,
            "collected": saved_count,
            "days": days,
            "message": f"Successfully collected {saved_count} trading flow records"
        }

    except sqlite3.Error as e:
        logger.error(f"Database error collecting trading flow for {etf.ticker}: {e}")
        raise HTTPException(status_code=500, detail=ERROR_DATABASE_COLLECTION)
    except ScraperException as e:
        logger.error(f"Scraper error collecting trading flow for {etf.ticker}: {e}")
        raise HTTPException(status_code=503, detail=ERROR_SCRAPER)
    except ValidationException as e:
        logger.error(f"Validation error collecting trading flow for {etf.ticker}: {e}")
        raise HTTPException(status_code=400, detail=ERROR_VALIDATION_COLLECTION_PARAMS)
    except Exception as e:
        logger.error(f"Unexpected error collecting trading flow for {etf.ticker}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=ERROR_INTERNAL_COLLECTION)

@router.get("/{ticker}/metrics", response_model=ETFMetrics)
async def get_metrics(
    etf: ETF = Depends(get_etf_or_404),
    collector: ETFDataCollector = Depends(get_collector)
):
    """
    종목 주요 지표 조회

    종목의 수익률, 변동성 등 주요 투자 지표를 계산하여 반환합니다.

    **Path Parameters:**
    - ticker: 종목 코드 (예: 487240)

    **Example Request:**
    ```
    GET /api/etfs/487240/metrics
    ```

    **Example Response:**
    ```json
    {
      "ticker": "487240",
      "aum": null,
      "returns": {
        "1w": 5.2,
        "1m": 12.5,
        "ytd": 18.3
      },
      "volatility": 25.4
    }
    ```

    **Response Fields:**
    - ticker: 종목 코드
    - aum: 순자산총액 (AUM, 현재 미제공)
    - returns: 수익률 (%)
      - 1w: 1주일 수익률
      - 1m: 1개월 수익률
      - ytd: 연초 대비 수익률 (Year-to-Date)
    - volatility: 연환산 변동성 (%)

    **Calculation Methods:**
    - 수익률: (현재가 - 과거가) / 과거가 × 100
    - 변동성: 일간 변동성 표준편차 × √252 (연환산)

    **Status Codes:**
    - 200: 성공
    - 404: 종목을 찾을 수 없음
    - 500: 서버 오류

    **Notes:**
    - 데이터가 부족한 경우 null 반환
    - 최소 7일 데이터 필요 (1주 수익률)
    - 최소 30일 데이터 필요 (1개월 수익률)
    - 변동성 계산에는 최소 10일 데이터 필요
    """
    # 캐시 확인
    cache_key = make_cache_key("metrics", ticker=etf.ticker)
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        logger.debug(f"Cache hit for {cache_key}")
        return cached_result

    try:
        result = collector.get_etf_metrics(etf.ticker)
        cache.set(cache_key, result, ttl_seconds=CACHE_TTL_SLOW_CHANGING)  # 1분 캐싱 (지표)
        return result
    except sqlite3.Error as e:
        logger.error(f"Database error fetching metrics for {etf.ticker}: {e}")
        raise HTTPException(status_code=500, detail=ERROR_DATABASE)
    except ValidationException as e:
        logger.error(f"Validation error fetching metrics for {etf.ticker}: {e}")
        raise HTTPException(status_code=400, detail=ERROR_VALIDATION_TICKER)
    except Exception as e:
        logger.error(f"Unexpected error fetching metrics for {etf.ticker}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=ERROR_INTERNAL_FETCH_METRICS)


@router.get("/{ticker}/insights", response_model=ETFInsights)
async def get_insights(
    etf: ETF = Depends(get_etf_or_404),
    period: str = Query(default="1m", description="분석 기간: 1w, 1m, 3m, 6m, 1y"),
    collector: ETFDataCollector = Depends(get_collector)
):
    """
    종목 인사이트 조회
    
    종목의 투자 전략, 핵심 포인트, 리스크를 분석하여 제공합니다.
    
    **Path Parameters:**
    - ticker: 종목 코드 (예: 487240)
    
    **Query Parameters:**
    - period: 분석 기간 (기본값: "1m")
      - "1w": 1주
      - "1m": 1개월
      - "3m": 3개월
      - "6m": 6개월
      - "1y": 1년
    
    **Example Request:**
    ```
    GET /api/etfs/487240/insights?period=1m
    ```
    
    **Example Response:**
    ```json
    {
      "strategy": {
        "short_term": "비중확대",
        "medium_term": "보유",
        "long_term": "보유",
        "recommendation": "보유",
        "comment": "단기 급등 구간, 변동성 확대 예상"
      },
      "key_points": [
        "1개월 수익률 12.5%로 강세 지속",
        "변동성 확대 구간, 리스크 관리 필요",
        "외국인 대규모 순매수 지속"
      ],
      "risks": [
        "높은 변동성으로 인한 가격 급등락 리스크",
        "규제 리스크: 정부 규제 강화 가능성"
      ]
    }
    ```
    
    **Status Codes:**
    - 200: 성공
    - 404: 종목을 찾을 수 없음
    - 500: 서버 오류
    """
    # 캐시 확인
    cache_key = make_cache_key("insights", ticker=etf.ticker, period=period)
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        logger.debug(f"Cache hit for {cache_key}")
        return cached_result
    
    try:
        from app.services.insights_service import InsightsService
        insights_service = InsightsService()
        result = insights_service.get_insights(etf.ticker, period)
        cache.set(cache_key, result, ttl_seconds=CACHE_TTL_SLOW_CHANGING)  # 1분 캐싱
        return result
    except sqlite3.Error as e:
        logger.error(f"Database error fetching insights for {etf.ticker}: {e}")
        raise HTTPException(status_code=500, detail=ERROR_DATABASE)
    except Exception as e:
        logger.error(f"Unexpected error fetching insights for {etf.ticker}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=ERROR_INTERNAL)


@router.get("/{ticker}/benchmark-comparison", response_model=BenchmarkComparison)
async def get_benchmark_comparison(
    etf: ETF = Depends(get_etf_or_404),
    benchmark: str = Query("KOSPI", description="벤치마크 지수: KOSPI, KOSDAQ, KOSPI200"),
    period: str = Query("1m", description="분석 기간: 1w, 1m, 3m, 6m, 1y")
):
    """
    벤치마크 대비 성과 비교

    종목의 수익률을 벤치마크 지수와 비교하여 초과수익률(Alpha)과 상관계수를 계산합니다.

    **Path Parameters:**
    - ticker: 종목 코드 (예: 487240)

    **Query Parameters:**
    - benchmark: 벤치마크 지수 (기본값: KOSPI)
      - KOSPI: 코스피 지수
      - KOSDAQ: 코스닥 지수
      - KOSPI200: 코스피200 지수
    - period: 분석 기간 (기본값: 1m)
      - 1w: 1주
      - 1m: 1개월
      - 3m: 3개월
      - 6m: 6개월
      - 1y: 1년

    **Example Request:**
    ```
    GET /api/etfs/487240/benchmark-comparison?benchmark=KOSPI&period=1m
    ```

    **Example Response:**
    ```json
    {
      "ticker": "487240",
      "benchmark": "KOSPI",
      "period": "1m",
      "etf_return": 12.5,
      "benchmark_return": 8.3,
      "alpha": 4.2,
      "correlation": 0.85,
      "start_date": "2024-12-27",
      "end_date": "2025-01-27",
      "data_points": 20
    }
    ```

    **Response Fields:**
    - ticker: 종목 코드
    - benchmark: 벤치마크 지수 이름
    - period: 분석 기간
    - etf_return: ETF 수익률 (%)
    - benchmark_return: 벤치마크 수익률 (%)
    - alpha: 초과수익률 (ETF 수익률 - 벤치마크 수익률, %)
    - correlation: 상관계수 (-1 ~ 1)
    - start_date: 분석 시작 날짜
    - end_date: 분석 종료 날짜
    - data_points: 공통 데이터 포인트 수
    - error: 에러 메시지 (데이터 부족 시)

    **Status Codes:**
    - 200: 성공
    - 404: 종목을 찾을 수 없음
    - 500: 서버 오류

    **Notes:**
    - FinanceDataReader를 사용하여 벤치마크 데이터를 가져옵니다
    - 데이터가 부족한 경우 null 값 반환
    - 상관계수는 일간 수익률 기준으로 계산됩니다
    """
    # 캐시 확인
    cache_key = make_cache_key("benchmark", ticker=etf.ticker, benchmark=benchmark, period=period)
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        logger.debug(f"Cache hit for {cache_key}")
        return cached_result

    try:
        from app.services.benchmark_service import BenchmarkService
        benchmark_service = BenchmarkService()
        result = benchmark_service.compare_with_benchmark(etf.ticker, benchmark, period)
        cache.set(cache_key, result, ttl_seconds=CACHE_TTL_SLOW_CHANGING)  # 1분 캐싱
        return result
    except sqlite3.Error as e:
        logger.error(f"Database error fetching benchmark comparison for {etf.ticker}: {e}")
        raise HTTPException(status_code=500, detail=ERROR_DATABASE)
    except Exception as e:
        logger.error(f"Unexpected error fetching benchmark comparison for {etf.ticker}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=ERROR_INTERNAL)


@router.post("/batch-summary", response_model=BatchSummaryResponse)
async def get_batch_summary(
    request: BatchSummaryRequest,
    collector: ETFDataCollector = Depends(get_collector)
):
    """
    여러 종목의 요약 데이터 일괄 조회 (N+1 쿼리 최적화)

    대시보드에서 여러 종목의 카드 데이터를 한 번에 조회합니다.
    각 종목별로 최신 가격, 차트용 가격 데이터, 매매동향, 뉴스를 반환합니다.

    **Request Body:**
    - tickers: 종목 코드 리스트 (예: ["487240", "466920", "042660"])
    - price_days: 가격 데이터 조회 일수 (기본: 5일)
    - news_limit: 뉴스 개수 제한 (기본: 5개)

    **Example Request:**
    ```json
    {
      "tickers": ["487240", "466920", "042660"],
      "price_days": 5,
      "news_limit": 5
    }
    ```

    **Example Response:**
    ```json
    {
      "data": {
        "487240": {
          "ticker": "487240",
          "latest_price": {
            "date": "2025-11-18",
            "open_price": 12400.0,
            "high_price": 12600.0,
            "low_price": 12300.0,
            "close_price": 12500.0,
            "volume": 1000000,
            "daily_change_pct": 2.5
          },
          "prices": [...],
          "weekly_return": 5.2,
          "latest_trading_flow": {...},
          "latest_news": [...]
        },
        ...
      }
    }
    ```

    **Status Codes:**
    - 200: 성공
    - 400: 잘못된 요청
    - 500: 서버 오류

    **Notes:**
    - 여러 종목을 한 번의 API 호출로 조회하여 성능 최적화
    - 데이터가 없는 종목도 빈 객체로 반환 (에러 없음)
    - 캐시 적용으로 반복 요청 시 빠른 응답
    """
    # 캐시 확인
    cache_key = make_cache_key(
        "batch_summary",
        tickers=",".join(sorted(request.tickers)),
        price_days=request.price_days,
        news_limit=request.news_limit
    )
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        logger.debug(f"Cache hit for {cache_key}")
        return cached_result

    try:
        logger.info(f"Fetching batch summary for {len(request.tickers)} tickers")

        result_data = {}

        # 날짜 계산
        end_date = date.today()
        start_date = end_date - timedelta(days=request.price_days)
        logger.info(f"Date range: {start_date} to {end_date}")

        # 배치 쿼리로 모든 종목의 데이터를 한 번에 조회 (IN 절 활용)
        try:
            # 1. 가격 데이터 배치 조회
            prices_batch = collector.get_price_data_batch(request.tickers, start_date, end_date)
            logger.info(f"Batch fetched prices for {len(prices_batch)} tickers")

            # 2. 매매동향 배치 조회
            trading_flow_batch = collector.get_trading_flow_batch(request.tickers, start_date, end_date)
            logger.info(f"Batch fetched trading flow for {len(trading_flow_batch)} tickers")

            # 3. 뉴스는 ticker별로 조회 (뉴스는 IN 절 최적화 필요 없음 - 데이터 적음)
            from app.services.news_scraper import NewsScraper
            news_scraper = NewsScraper()

        except Exception as e:
            logger.error(f"Error in batch queries: {e}", exc_info=True)
            # 배치 쿼리 실패 시 빈 결과로 처리
            prices_batch = {ticker: [] for ticker in request.tickers}
            trading_flow_batch = {ticker: [] for ticker in request.tickers}

        # 종목별로 데이터 조합
        for ticker in request.tickers:
            try:
                summary = ETFCardSummary(ticker=ticker)

                # 1. 가격 데이터 설정
                prices = prices_batch.get(ticker, [])
                if prices:
                    summary.prices = prices
                    summary.latest_price = prices[0] if prices else None

                    # 주간 수익률 계산 (첫 가격과 마지막 가격 비교)
                    if len(prices) >= 2:
                        first_price = prices[0].close_price
                        last_price = prices[-1].close_price
                        summary.weekly_return = ((first_price - last_price) / last_price) * 100
                else:
                    logger.debug(f"[{ticker}] No price data found")

                # 2. 매매동향 설정
                trading_flow = trading_flow_batch.get(ticker, [])
                if trading_flow:
                    # Dict를 TradingFlow로 변환
                    from app.models import TradingFlow
                    summary.latest_trading_flow = TradingFlow(**trading_flow[0])

                # 3. 뉴스 조회 (ticker별로 - 최적화 불필요)
                try:
                    news = news_scraper.get_news_for_ticker(ticker, start_date, end_date)
                    if news:
                        summary.latest_news = news[:request.news_limit]
                except Exception as e:
                    logger.warning(f"Error fetching news for {ticker}: {e}")

                result_data[ticker] = summary

            except Exception as e:
                logger.warning(f"Error processing summary for {ticker}: {e}")
                # 개별 종목 에러는 빈 객체로 처리
                result_data[ticker] = ETFCardSummary(ticker=ticker)

        response = BatchSummaryResponse(data=result_data)
        cache.set(cache_key, response, ttl_seconds=CACHE_TTL_FAST_CHANGING)  # 30초 캐싱 (배치 요약)

        logger.info(f"Successfully fetched batch summary for {len(result_data)} tickers")
        return response

    except Exception as e:
        logger.error(f"Unexpected error in batch summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=ERROR_INTERNAL)


@router.get("/{ticker}/intraday")
async def get_intraday_prices(
    etf: ETF = Depends(get_etf_or_404),
    target_date: Optional[date] = Query(default=None, description="조회할 날짜 (기본: 오늘)"),
    auto_collect: bool = Query(default=True, description="데이터 없을 시 자동 수집 여부")
):
    """
    분봉(시간별 체결) 데이터 조회

    해당 종목의 당일 시간별 체결 데이터를 조회합니다.
    장중에는 실시간으로 업데이트되며, 장 마감 후에는 당일 전체 데이터를 반환합니다.

    **Path Parameters:**
    - ticker: 종목 코드 (예: 487240)

    **Query Parameters:**
    - target_date: 조회할 날짜 (선택, 기본값: 오늘)
    - auto_collect: 데이터가 없을 때 자동 수집 여부 (기본: true)

    **Example Request:**
    ```
    GET /api/etfs/487240/intraday
    GET /api/etfs/487240/intraday?target_date=2025-01-24
    ```

    **Example Response:**
    ```json
    {
      "ticker": "487240",
      "date": "2025-01-24",
      "data": [
        {
          "datetime": "2025-01-24T09:00:00",
          "price": 12500.0,
          "change_amount": 100.0,
          "volume": 1500,
          "bid_volume": 800,
          "ask_volume": 700
        },
        ...
      ],
      "count": 390,
      "first_time": "09:00",
      "last_time": "15:30"
    }
    ```

    **Status Codes:**
    - 200: 성공
    - 404: 종목을 찾을 수 없음
    - 500: 서버 오류

    **Notes:**
    - 데이터는 시간순(오래된 시간 → 최신 시간)으로 정렬됨
    - 장중에는 약 1분 간격으로 데이터 제공
    - 주말/공휴일은 데이터 없음
    """
    from app.services.intraday_collector import IntradayDataCollector

    try:
        intraday_collector = IntradayDataCollector()

        # 실제 조회할 날짜 결정
        actual_date = target_date or date.today()

        # 캐시 확인 (실제 날짜 기준)
        cache_key = make_cache_key("intraday", ticker=etf.ticker, date=actual_date)
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            logger.debug(f"Cache hit for {cache_key}")
            return cached_result

        # DB에서 데이터 조회
        intraday_data = intraday_collector.get_intraday_data(etf.ticker, actual_date)

        # 오늘 데이터가 없으면 마지막 거래일 데이터 확인
        if not intraday_data and target_date is None:
            last_trading_date = intraday_collector.get_last_trading_date(etf.ticker)
            if last_trading_date and last_trading_date != date.today():
                logger.info(f"No intraday data for today, checking last trading date: {last_trading_date}")
                actual_date = last_trading_date
                intraday_data = intraday_collector.get_intraday_data(etf.ticker, last_trading_date)

        # 데이터가 없고 자동 수집이 켜져 있으면 수집 시도
        if not intraday_data and auto_collect:
            logger.info(f"No intraday data for {etf.ticker}, attempting auto-collection")
            result = intraday_collector.collect_and_save_intraday(etf.ticker, pages=20)

            if result['collected'] > 0:
                # 수집된 날짜로 다시 조회
                actual_date = date.fromisoformat(result.get('date', date.today().isoformat()))
                intraday_data = intraday_collector.get_intraday_data(etf.ticker, actual_date)

        if not intraday_data:
            response = {
                "ticker": etf.ticker,
                "date": actual_date.isoformat(),
                "data": [],
                "count": 0,
                "first_time": None,
                "last_time": None,
                "message": "데이터 없음 (장 마감 또는 휴장일)"
            }
            cache.set(cache_key, response, ttl_seconds=60)  # 1분 캐싱 (빈 결과)
            return response

        # datetime을 ISO 문자열로 변환하고 시간 추출
        first_time = None
        last_time = None

        for item in intraday_data:
            dt_value = item['datetime']
            if isinstance(dt_value, str):
                # 문자열인 경우 ISO 형식으로 변환 (공백 -> T)
                item['datetime'] = dt_value.replace(' ', 'T')
            else:
                item['datetime'] = dt_value.isoformat()

        if intraday_data:
            # 시간 추출 (HH:MM 형식)
            first_dt = intraday_data[0]['datetime']
            last_dt = intraday_data[-1]['datetime']
            first_time = first_dt.split('T')[1][:5] if 'T' in first_dt else first_dt.split(' ')[1][:5]
            last_time = last_dt.split('T')[1][:5] if 'T' in last_dt else last_dt.split(' ')[1][:5]

        response = {
            "ticker": etf.ticker,
            "date": actual_date.isoformat(),
            "data": intraday_data,
            "count": len(intraday_data),
            "first_time": first_time,
            "last_time": last_time
        }

        cache.set(cache_key, response, ttl_seconds=CACHE_TTL_FAST_CHANGING)  # 30초 캐싱
        return response

    except Exception as e:
        logger.error(f"Error fetching intraday data for {etf.ticker}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"분봉 데이터 조회 실패: {str(e)}")


@router.post("/{ticker}/collect-intraday")
async def collect_intraday_prices(
    etf: ETF = Depends(get_etf_or_404),
    pages: int = Query(default=20, ge=1, le=50, description="수집할 페이지 수 (1-50)"),
    api_key: str = Depends(verify_api_key_dependency)
):
    """
    분봉(시간별 체결) 데이터 수집

    네이버 금융에서 해당 종목의 시간별 체결 데이터를 수집합니다.

    **Path Parameters:**
    - ticker: 종목 코드 (예: 487240)

    **Query Parameters:**
    - pages: 수집할 페이지 수 (1-50, 기본: 20, 페이지당 약 10건)

    **Example Request:**
    ```
    POST /api/etfs/487240/collect-intraday?pages=30
    ```

    **Example Response:**
    ```json
    {
      "ticker": "487240",
      "collected": 285,
      "first_time": "09:01",
      "last_time": "15:29",
      "message": "285건 수집 완료"
    }
    ```

    **Status Codes:**
    - 200: 성공
    - 404: 종목을 찾을 수 없음
    - 500: 서버 오류

    **Notes:**
    - 장중에 호출 시 실시간 데이터 수집
    - 장 마감 후에는 당일 전체 데이터 수집
    - 오래된 데이터는 7일 후 자동 삭제
    """
    from app.services.intraday_collector import IntradayDataCollector

    try:
        logger.info(f"Starting intraday collection for {etf.ticker}, pages={pages}")

        intraday_collector = IntradayDataCollector()
        result = intraday_collector.collect_and_save_intraday(etf.ticker, pages=pages)

        # 수집 후 캐시 무효화
        cache.invalidate_pattern(f"intraday:{etf.ticker}")

        return result

    except Exception as e:
        logger.error(f"Error collecting intraday data for {etf.ticker}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"분봉 데이터 수집 실패: {str(e)}")
