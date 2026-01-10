"""
Settings router for stock/ETF management

This router provides CRUD operations for managing stocks/ETFs
via the stocks.json configuration file.
"""

from fastapi import APIRouter, HTTPException, Path as PathParam, Query, Depends, Request
from typing import Dict, Any, List, Optional
import logging
from app.models import StockCreate, StockUpdate, StockDeleteResponse
from app.utils import stocks_manager
from app.dependencies import verify_api_key_dependency
from app.middleware.rate_limit import limiter, RateLimitConfig
from app.services.ticker_scraper import TickerScraper
from app.services.ticker_catalog_collector import TickerCatalogCollector
from app.exceptions import ScraperException

router = APIRouter()
logger = logging.getLogger(__name__)

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
    - Creates backup of stocks.json before modification
    - Reloads configuration cache
    """
    try:
        ticker = stock_data.ticker
        logger.info(f"Creating new stock: {ticker}")

        # Convert Pydantic model to dict and remove ticker (will be used as key)
        stock_dict = stock_data.model_dump(exclude={"ticker"})

        # Add the stock
        stocks_manager.add_stock(ticker, stock_dict)

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
    - Creates backup before modification
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
        # purchase_date가 None으로 명시적으로 전달된 경우도 포함되도록 처리
        update_dict = stock_data.model_dump(exclude_unset=True)
        # purchase_date가 명시적으로 설정된 경우 (None 포함) 처리
        if hasattr(stock_data, 'model_fields_set') and 'purchase_date' in stock_data.model_fields_set:
            update_dict['purchase_date'] = stock_data.purchase_date
        merged_data = {**current_data, **update_dict}

        # Update the stock
        stocks_manager.update_stock(ticker, merged_data)

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
    - Creates backup of stocks.json before deletion
    - Cannot be undone (use backup to restore)
    - Reloads configuration cache
    """
    try:
        logger.info(f"Deleting stock: {ticker}")

        # Delete the stock (cascade)
        deleted_counts = stocks_manager.delete_stock(ticker)

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
    try:
        logger.info("Starting ticker catalog collection")
        
        result = ticker_catalog_collector.collect_all_stocks()
        
        logger.info(f"Ticker catalog collection completed: {result}")
        return result
        
    except ScraperException as e:
        logger.error(f"Failed to collect ticker catalog: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error collecting ticker catalog: {e}", exc_info=True)
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
