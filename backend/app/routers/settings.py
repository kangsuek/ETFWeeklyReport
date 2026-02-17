"""
Settings router for stock/ETF management

This router provides CRUD operations for managing stocks/ETFs
via the stocks.json configuration file.
"""

from fastapi import APIRouter, HTTPException, Path as PathParam, Query, Depends, Request
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging
import json
import os
from app.models import StockCreate, StockUpdate, StockDeleteResponse
from app.utils import stocks_manager
from app.dependencies import verify_api_key_dependency
from app.middleware.rate_limit import limiter, RateLimitConfig
from app.services.ticker_scraper import TickerScraper
from app.services.ticker_catalog_collector import TickerCatalogCollector
from app.exceptions import ScraperException
from app.config import Config

router = APIRouter()
logger = logging.getLogger(__name__)


# ─── API Keys 관리 ─────────────────────────────────────────────────────
def _get_api_keys_path() -> str:
    """API 키 설정 파일 경로"""
    config_dir = str(Path(Config.STOCK_CONFIG_PATH).parent)
    return os.path.join(config_dir, "api-keys.json")


def _load_api_keys() -> Dict[str, str]:
    """api-keys.json에서 API 키 로드"""
    keys_path = _get_api_keys_path()
    if not os.path.exists(keys_path):
        return {}
    try:
        with open(keys_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load api-keys.json: {e}")
        return {}


def _save_api_keys(keys: Dict[str, str]):
    """api-keys.json에 API 키 저장"""
    keys_path = _get_api_keys_path()
    config_dir = os.path.dirname(keys_path)
    if not os.path.exists(config_dir):
        os.makedirs(config_dir, exist_ok=True)
    with open(keys_path, "w", encoding="utf-8") as f:
        json.dump(keys, f, indent=2, ensure_ascii=False)


def load_api_keys_to_env():
    """저장된 API 키를 os.environ에 로드 (서버 시작 시 호출)"""
    keys = _load_api_keys()
    count = 0
    for key, value in keys.items():
        if value and not value.startswith("your_"):
            os.environ[key] = value
            count += 1
    if count > 0:
        logger.info(f"Loaded {count} API keys from api-keys.json")
        # Config 클래스 속성도 업데이트
        if "NAVER_CLIENT_ID" in keys:
            Config.NAVER_CLIENT_ID = keys["NAVER_CLIENT_ID"]
        if "NAVER_CLIENT_SECRET" in keys:
            Config.NAVER_CLIENT_SECRET = keys["NAVER_CLIENT_SECRET"]
        # PERPLEXITY_API_KEY는 os.environ으로만 관리 (Config 속성 불필요)

# Initialize ticker scraper
ticker_scraper = TickerScraper()
ticker_catalog_collector = TickerCatalogCollector()


@router.get("/stocks")
async def get_stocks() -> List[Dict[str, Any]]:
    """
    Get all stocks/ETFs from configuration

    Returns all stocks currently configured in stocks.json as an array

    **Example Response:**
    ```json
    [
      {
        "ticker": "005930",
        "name": "삼성전자",
        "type": "STOCK",
        "theme": "반도체/전자",
        "purchase_date": "2024-01-15",
        "search_keyword": "삼성전자",
        "relevance_keywords": ["삼성전자", "반도체", "전자"]
      },
      ...
    ]
    ```

    **Status Codes:**
    - 200: Success
    - 500: Server error
    """
    try:
        # 캐시를 무효화하고 파일에서 직접 읽기 (파일 직접 수정 반영)
        Config.reload_stock_config()
        stocks_dict = stocks_manager.load_stocks()
        # Convert dict to array with ticker included
        # purchase_date가 None인 경우 null로 변환하여 JSON 직렬화 가능하도록 처리
        stocks_array = []
        for ticker, data in stocks_dict.items():
            stock_item = {"ticker": ticker, **data}
            # purchase_date가 None이거나 빈 문자열인 경우 None으로 명시적 설정
            if stock_item.get("purchase_date") is None or stock_item.get("purchase_date") == "":
                stock_item["purchase_date"] = None
            stocks_array.append(stock_item)
        logger.debug(f"Loaded {len(stocks_array)} stocks")
        return stocks_array
    except Exception as e:
        logger.error(f"Failed to load stocks: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to load stocks")


@router.post("/stocks", status_code=201)
@limiter.limit(RateLimitConfig.DEFAULT)
async def create_stock(
    request: Request,
    stock_data: StockCreate,
    api_key: str = Depends(verify_api_key_dependency)
) -> Dict[str, Any]:
    """
    Create a new stock/ETF entry

    **Request Body:**
    - ticker: Stock ticker code (e.g., "005930")
    - name: Stock name (required)
    - type: "ETF" or "STOCK" (required)
    - theme: Theme/sector (required)
    - purchase_date: Purchase date in YYYY-MM-DD format (optional)
    - search_keyword: Keyword for news search (optional)
    - relevance_keywords: List of relevant keywords (optional)

    **Example Request:**
    ```json
    {
      "ticker": "005930",
      "name": "삼성전자",
      "type": "STOCK",
      "theme": "반도체/전자",
      "purchase_date": "2024-01-15",
      "search_keyword": "삼성전자",
      "relevance_keywords": ["삼성전자", "반도체", "전자"]
    }
    ```

    **Status Codes:**
    - 201: Successfully created
    - 400: Invalid data or duplicate ticker
    - 500: Server error

    **Notes:**
    - Automatically syncs to database
    - Reloads configuration cache
    """
    try:
        ticker = stock_data.ticker
        logger.info(f"Creating new stock: {ticker}")

        # Convert Pydantic model to dict and remove ticker (will be used as key)
        stock_dict = stock_data.model_dump(exclude={"ticker"})

        # Add the stock
        stocks_manager.add_stock(ticker, stock_dict)

        # 캐시 무효화 (ETF 목록 캐시 무효화하여 대시보드에 즉시 반영)
        from app.utils.cache import get_cache
        cache = get_cache()
        cache.invalidate_pattern("etfs")
        logger.info(f"Cache invalidated for etfs after creating stock {ticker}")

        # Return created stock
        return {
            "ticker": ticker,
            **stock_dict,
            "message": "Stock created successfully"
        }

    except ValueError as e:
        logger.error(f"Validation error creating stock: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error creating stock: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create stock")


@router.put("/stocks/{ticker}")
async def update_stock(
    ticker: str = PathParam(..., description="Stock ticker code"),
    stock_data: StockUpdate = None,
    api_key: str = Depends(verify_api_key_dependency)
) -> Dict[str, Any]:
    """
    Update an existing stock/ETF entry

    Supports partial updates - only provided fields will be updated.

    **Path Parameters:**
    - ticker: Stock ticker code (e.g., "487240")

    **Request Body:**
    - name: Stock name (optional)
    - type: "ETF" or "STOCK" (optional)
    - theme: Theme/sector (optional)
    - purchase_date: Purchase date in YYYY-MM-DD format (optional)
    - purchase_price: Purchase average price (optional)
    - quantity: Holding quantity (optional)
    - search_keyword: Keyword for news search (optional)
    - relevance_keywords: List of relevant keywords (optional)

    **Example Request:**
    ```json
    {
      "theme": "AI/전력/인프라",
      "relevance_keywords": ["AI", "전력", "데이터센터", "인프라"]
    }
    ```

    **Status Codes:**
    - 200: Successfully updated
    - 400: Invalid data
    - 404: Stock not found
    - 500: Server error

    **Notes:**
    - Only updates provided fields (partial update)
    - Automatically syncs to database
    """
    try:
        logger.info(f"Updating stock: {ticker}")

        # Load current stock data
        stocks = stocks_manager.load_stocks()

        if ticker not in stocks:
            raise HTTPException(status_code=404, detail=f"Stock {ticker} not found")

        # Merge with existing data (partial update)
        current_data = stocks[ticker]
        # exclude_unset=True는 설정되지 않은 필드만 제외
        # purchase_date, purchase_price, quantity가 None으로 명시적으로 전달된 경우도 포함되도록 처리
        update_dict = stock_data.model_dump(exclude_unset=True)
        # purchase_date가 명시적으로 설정된 경우 (None 포함) 처리
        if hasattr(stock_data, 'model_fields_set') and 'purchase_date' in stock_data.model_fields_set:
            update_dict['purchase_date'] = stock_data.purchase_date
        # purchase_price가 명시적으로 설정된 경우 (None 포함) 처리
        if hasattr(stock_data, 'model_fields_set') and 'purchase_price' in stock_data.model_fields_set:
            update_dict['purchase_price'] = stock_data.purchase_price
        # quantity가 명시적으로 설정된 경우 (None 포함) 처리
        if hasattr(stock_data, 'model_fields_set') and 'quantity' in stock_data.model_fields_set:
            update_dict['quantity'] = stock_data.quantity
        merged_data = {**current_data, **update_dict}

        # Update the stock
        stocks_manager.update_stock(ticker, merged_data)

        # 캐시 무효화 (ETF 상세 정보 캐시도 무효화)
        from app.utils.cache import get_cache
        cache = get_cache()
        cache.invalidate_pattern("etfs")
        cache.invalidate_pattern(f"etf:{ticker}")

        # Return updated stock
        return {
            "ticker": ticker,
            **merged_data,
            "message": "Stock updated successfully"
        }

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error updating stock {ticker}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error updating stock {ticker}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update stock")


@router.delete("/stocks/{ticker}", response_model=StockDeleteResponse)
async def delete_stock(
    ticker: str = PathParam(..., description="Stock ticker code"),
    api_key: str = Depends(verify_api_key_dependency)
) -> StockDeleteResponse:
    """
    Delete a stock/ETF entry and all related data

    **Path Parameters:**
    - ticker: Stock ticker code (e.g., "487240")

    **Cascade Deletion:**
    This endpoint will delete:
    - Stock entry from stocks.json
    - Stock entry from database (etfs table)
    - All related price data
    - All related news data
    - All related trading flow data

    **Example Response:**
    ```json
    {
      "ticker": "487240",
      "deleted": {
        "prices": 150,
        "news": 20,
        "trading_flow": 30
      }
    }
    ```

    **Status Codes:**
    - 200: Successfully deleted
    - 404: Stock not found
    - 500: Server error

    **Notes:**
    - CASCADE deletes all related data (prices, news, trading_flow)
    - Cannot be undone
    - Reloads configuration cache
    """
    try:
        logger.info(f"Deleting stock: {ticker}")

        # Delete the stock (cascade)
        deleted_counts = stocks_manager.delete_stock(ticker)

        # 캐시 무효화 (ETF 목록 및 해당 종목 캐시 무효화)
        from app.utils.cache import get_cache
        cache = get_cache()
        cache.invalidate_pattern("etfs")
        cache.invalidate_pattern(f"etf:{ticker}")
        logger.info(f"Cache invalidated for etfs after deleting stock {ticker}")

        logger.info(f"Successfully deleted stock {ticker}: {deleted_counts}")

        return StockDeleteResponse(
            ticker=ticker,
            deleted=deleted_counts
        )

    except ValueError as e:
        logger.error(f"Stock {ticker} not found: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error deleting stock {ticker}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete stock")


@router.get("/stocks/{ticker}/validate")
async def validate_ticker(
    ticker: str = PathParam(..., description="Stock ticker code to validate")
) -> Dict[str, Any]:
    """
    Validate a ticker code and fetch basic information from Naver Finance

    **Path Parameters:**
    - ticker: Stock ticker code (e.g., "005930")

    **Example Response:**
    ```json
    {
      "ticker": "005930",
      "name": "삼성전자",
      "type": "STOCK",
      "theme": "반도체/전자",
      "purchase_date": null,
      "search_keyword": "삼성전자",
      "relevance_keywords": ["삼성전자", "반도체", "전자"]
    }
    ```

    **Status Codes:**
    - 200: Ticker is valid
    - 404: Ticker not found on Naver Finance
    - 500: Scraping error

    **Notes:**
    - Scrapes data from Naver Finance
    - Returns data in stocks.json format ready for use
    """
    try:
        logger.info(f"Validating ticker: {ticker}")

        # Scrape ticker info from Naver Finance
        stock_info = ticker_scraper.scrape_ticker_info(ticker)

        logger.info(f"Successfully validated ticker {ticker}: {stock_info.get('name')}")
        return stock_info

    except ScraperException as e:
        logger.error(f"Failed to validate ticker {ticker}: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error validating ticker {ticker}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to validate ticker")


@router.get("/ticker-catalog/collect-progress")
async def get_ticker_catalog_progress(request: Request):
    """
    종목 목록 수집 진행률 조회

    Returns:
        현재 수집 진행 상태 (idle, in_progress, completed)
    """
    from app.services.progress import get_progress
    progress = get_progress("ticker-catalog")
    return progress or {"status": "idle"}


@router.post("/ticker-catalog/collect")
@limiter.limit(RateLimitConfig.DANGEROUS)
async def collect_ticker_catalog(request: Request, api_key: str = Depends(verify_api_key_dependency)) -> Dict[str, Any]:
    """
    종목 목록 수집 트리거 (관리자용)

    네이버 금융에서 전체 종목 목록(코스피, 코스닥, ETF)을 수집하여
    stock_catalog 테이블에 저장합니다.

    **Example Response:**
    ```json
    {
      "total_collected": 2500,
      "kospi_count": 800,
      "kosdaq_count": 1400,
      "etf_count": 300,
      "saved_count": 2500,
      "timestamp": "2025-01-15T10:30:00"
    }
    ```

    **Status Codes:**
    - 200: Successfully collected
    - 500: Collection error

    **Notes:**
    - 수집에는 시간이 걸릴 수 있습니다 (약 5-10분)
    - 기존 데이터는 업데이트됩니다
    """
    import asyncio

    logger.info(f"[종목목록수집] 요청 수신: {request.method} {request.url.path}")
    logger.info(f"[종목목록수집] 클라이언트: {request.client.host if request.client else 'unknown'}")

    try:
        logger.info("[종목목록수집] 종목 목록 수집 시작...")

        result = await asyncio.to_thread(ticker_catalog_collector.collect_all_stocks)

        logger.info(f"[종목목록수집] 종목 목록 수집 완료: {result}")
        return result

    except ScraperException as e:
        logger.error(f"[종목목록수집] 수집 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"[종목목록수집] 예상치 못한 에러: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to collect ticker catalog")


@router.get("/stocks/search")
@limiter.limit(RateLimitConfig.SEARCH)
async def search_stocks(
    request: Request,
    q: str = Query(..., description="검색어 (티커 코드 또는 종목명)"),
    type: Optional[str] = Query(None, description="종목 타입 필터 (STOCK, ETF, ALL 또는 null=전체)")
) -> List[Dict[str, Any]]:
    """
    종목 목록 검색 (자동완성용)
    
    stock_catalog 테이블에서 티커 코드 또는 종목명으로 검색합니다.
    
    **Query Parameters:**
    - q: 검색어 (최소 2자 이상)
    - type: 종목 타입 필터 (선택사항, STOCK 또는 ETF)
    
    **Example Request:**
    ```
    GET /api/settings/stocks/search?q=삼성&type=STOCK
    ```
    
    **Example Response:**
    ```json
    [
      {
        "ticker": "005930",
        "name": "삼성전자",
        "type": "STOCK",
        "market": "KOSPI",
        "sector": null
      },
      {
        "ticker": "005935",
        "name": "삼성전자우",
        "type": "STOCK",
        "market": "KOSPI",
        "sector": null
      }
    ]
    ```
    
    **Status Codes:**
    - 200: Success
    - 400: Invalid query (too short)
    - 500: Server error
    
    **Notes:**
    - 최대 20개 결과 반환
    - 정확한 티커 코드 매칭이 우선순위가 높습니다
    """
    try:
        if len(q) < 2:
            raise HTTPException(status_code=400, detail="검색어는 최소 2자 이상이어야 합니다")
        
        # 'ALL'이면 None으로 변환하여 모든 타입 검색
        stock_type = None if type == 'ALL' or type is None else type
        results = ticker_catalog_collector.search_stocks(q, stock_type=stock_type, limit=20)
        
        logger.debug(f"Search query '{q}' (type={stock_type}) returned {len(results)} results")
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error searching stocks: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to search stocks")


@router.post("/stocks/reorder")
@limiter.limit(RateLimitConfig.DEFAULT)
async def reorder_stocks(
    request: Request,
    tickers: List[str],
    api_key: str = Depends(verify_api_key_dependency)
) -> Dict[str, Any]:
    """
    종목 순서 변경
    
    stocks.json에 저장된 종목들의 순서를 변경합니다.
    
    **Request Body:**
    - tickers: 새로운 순서대로 정렬된 티커 코드 배열
    
    **Example Request:**
    ```json
    ["487240", "466920", "0020H0", "442320", "395270"]
    ```
    
    **Status Codes:**
    - 200: Successfully reordered
    - 400: Invalid ticker list
    - 500: Server error
    
    **Notes:**
    - 모든 기존 종목이 포함되어야 합니다
    - 순서만 변경되며 데이터는 변경되지 않습니다
    """
    try:
        logger.info(f"Reordering stocks: {tickers}")
        
        # 현재 종목 목록 로드
        stocks = stocks_manager.load_stocks()
        
        # 티커 검증: stocks.json에 있는 종목만 사용, 없는 종목은 무시
        current_tickers = set(stocks.keys())
        
        # 새로운 순서로 재정렬 (stocks.json에 존재하는 종목만)
        reordered_stocks = {}
        for ticker in tickers:
            if ticker in stocks:
                reordered_stocks[ticker] = stocks[ticker]
            else:
                logger.debug(f"Skipping ticker not in stocks.json: {ticker}")
        
        # stocks.json에는 있지만 요청에 빠진 종목은 맨 뒤에 추가
        for ticker in stocks:
            if ticker not in reordered_stocks:
                reordered_stocks[ticker] = stocks[ticker]
                logger.debug(f"Appending missing ticker to end: {ticker}")
        
        # 저장
        stocks_manager.save_stocks(reordered_stocks)
        
        # 데이터베이스 캐시 갱신 (필요 시)
        # Config 캐시 강제 갱신
        Config._stock_config_cache = None
        
        # ETF 캐시 무효화 (순서가 변경되었으므로)
        from app.utils.cache import get_cache
        cache = get_cache()
        cache.invalidate_pattern("etfs")
        
        logger.info(f"Successfully reordered {len(tickers)} stocks")
        
        return {
            "message": "Successfully reordered stocks",
            "count": len(tickers),
            "order": tickers
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error reordering stocks: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to reorder stocks")


# ─── API Keys Endpoints ──────────────────────────────────────────────────


class ApiKeysUpdate(BaseModel):
    """API 키 업데이트 요청 모델"""
    NAVER_CLIENT_ID: Optional[str] = None
    NAVER_CLIENT_SECRET: Optional[str] = None
    PERPLEXITY_API_KEY: Optional[str] = None


@router.get("/api-keys")
async def get_api_keys(raw: bool = False) -> Dict[str, Any]:
    """
    저장된 API 키 조회

    **Query Parameters:**
    - raw: true면 원본 값 반환, false면 마스킹 처리 (기본: false)

    **Status Codes:**
    - 200: Success
    """
    keys = _load_api_keys()

    result = {}
    for key in ["NAVER_CLIENT_ID", "NAVER_CLIENT_SECRET"]:
        value = keys.get(key, "") or os.getenv(key, "")
        if value and not value.startswith("your_"):
            result[key] = value if raw else value[:4] + "*" * max(0, len(value) - 4)
        else:
            result[key] = ""

    has_naver = bool(result["NAVER_CLIENT_ID"] and result["NAVER_CLIENT_SECRET"])

    return {
        "keys": result,
        "configured": {
            "naver": has_naver,
        }
    }


@router.put("/api-keys")
async def update_api_keys(
    data: ApiKeysUpdate,
    api_key: str = Depends(verify_api_key_dependency)
) -> Dict[str, Any]:
    """
    API 키 저장 및 즉시 적용

    **Request Body:**
    - NAVER_CLIENT_ID: 네이버 API Client ID
    - NAVER_CLIENT_SECRET: 네이버 API Client Secret
    - PERPLEXITY_API_KEY: Perplexity AI API Key

    **Status Codes:**
    - 200: Successfully saved
    - 500: Server error
    """
    try:
        # 현재 저장된 키 로드
        current_keys = _load_api_keys()

        # 업데이트할 키만 갱신 (None이면 기존 값 유지)
        update_dict = data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            if value is not None:
                current_keys[key] = value

        # 파일에 저장
        _save_api_keys(current_keys)

        # os.environ에 즉시 반영 (실행 중인 서비스가 바로 사용할 수 있도록)
        for key, value in current_keys.items():
            if value and not value.startswith("your_"):
                os.environ[key] = value
                logger.info(f"Updated env: {key}={value[:4]}****")

        # Config 클래스 속성 업데이트
        if "NAVER_CLIENT_ID" in current_keys:
            Config.NAVER_CLIENT_ID = current_keys["NAVER_CLIENT_ID"]
        if "NAVER_CLIENT_SECRET" in current_keys:
            Config.NAVER_CLIENT_SECRET = current_keys["NAVER_CLIENT_SECRET"]

        logger.info("API keys saved and applied successfully")
        return {"message": "API 키가 저장되었습니다", "updated": list(update_dict.keys())}

    except Exception as e:
        logger.error(f"Failed to save API keys: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to save API keys")
