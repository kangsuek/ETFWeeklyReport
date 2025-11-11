"""
Settings router for stock/ETF management

This router provides CRUD operations for managing stocks/ETFs
via the stocks.json configuration file.
"""

from fastapi import APIRouter, HTTPException, Path as PathParam
from typing import Dict, Any
import logging
from app.models import StockCreate, StockUpdate, StockDeleteResponse
from app.utils import stocks_manager

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/stocks", status_code=201)
async def create_stock(
    stock_data: StockCreate
) -> Dict[str, Any]:
    """
    Create a new stock/ETF entry

    **Request Body:**
    - ticker: Stock ticker code (e.g., "005930")
    - name: Stock name (required)
    - type: "ETF" or "STOCK" (required)
    - theme: Theme/sector (required)
    - launch_date: Launch date in YYYY-MM-DD format (required for ETF, null for STOCK)
    - expense_ratio: Expense ratio as decimal (required for ETF, null for STOCK)
    - search_keyword: Keyword for news search (optional)
    - relevance_keywords: List of relevant keywords (optional)

    **Example Request:**
    ```json
    {
      "ticker": "005930",
      "name": "삼성전자",
      "type": "STOCK",
      "theme": "반도체/전자",
      "launch_date": null,
      "expense_ratio": null,
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
    stock_data: StockUpdate = None
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
    - launch_date: Launch date in YYYY-MM-DD format (optional)
    - expense_ratio: Expense ratio as decimal (optional)
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
        update_dict = stock_data.model_dump(exclude_unset=True)
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
    ticker: str = PathParam(..., description="Stock ticker code")
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

    This endpoint will be implemented in Task 1.3 (ticker_scraper.py)

    **Path Parameters:**
    - ticker: Stock ticker code (e.g., "005930")

    **Example Response:**
    ```json
    {
      "ticker": "005930",
      "name": "삼성전자",
      "type": "STOCK",
      "theme": "반도체/전자",
      "launch_date": null,
      "expense_ratio": null,
      "search_keyword": "삼성전자",
      "relevance_keywords": ["삼성전자", "반도체", "전자"]
    }
    ```

    **Status Codes:**
    - 200: Ticker is valid
    - 404: Ticker not found on Naver Finance
    - 500: Scraping error

    **Notes:**
    - This is a placeholder for Task 1.3
    - Will scrape data from Naver Finance
    - Returns data in stocks.json format
    """
    # Placeholder for Task 1.3
    raise HTTPException(
        status_code=501,
        detail="Ticker validation not yet implemented. See Task 1.3."
    )
