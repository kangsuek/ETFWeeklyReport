"""
Settings API Router

종목 관리 CRUD API (stocks.json 기반)
"""
from fastapi import APIRouter, HTTPException, status
from typing import Dict, Any
import logging

from app.models import (
    StockCreateRequest,
    StockUpdateRequest,
    StockDeleteResponse,
    StockValidateResponse
)
from app.utils.stocks_manager import (
    load_stocks,
    save_stocks,
    validate_stock_data,
    sync_stocks_to_db,
    delete_stock_from_db
)
from app.services.ticker_scraper import get_ticker_scraper
from app.config import Config
from app.exceptions import ValidationException, ScraperException

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/stocks", status_code=status.HTTP_201_CREATED)
async def create_stock(request: StockCreateRequest) -> Dict[str, Any]:
    """
    새 종목 추가

    stocks.json 파일에 종목을 추가하고 데이터베이스에 동기화합니다.

    **Request Body:**
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

    **Response:**
    ```json
    {
      "ticker": "005930",
      "name": "삼성전자",
      "message": "Stock created successfully"
    }
    ```

    **Status Codes:**
    - 201: 생성 성공
    - 400: 잘못된 요청 (필수 필드 누락, 중복 티커 등)
    - 500: 서버 오류
    """
    try:
        # 1. 기존 종목 로드
        stocks = load_stocks()

        # 2. 중복 티커 체크
        if request.ticker in stocks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Stock with ticker {request.ticker} already exists"
            )

        # 3. 종목 데이터 생성
        stock_data = {
            "name": request.name,
            "type": request.type,
            "theme": request.theme,
            "launch_date": request.launch_date,
            "expense_ratio": request.expense_ratio,
            "search_keyword": request.search_keyword or request.name,
            "relevance_keywords": request.relevance_keywords or [request.name]
        }

        # 4. 데이터 검증
        validate_stock_data(stock_data, request.ticker)

        # 5. stocks.json 파일에 추가
        stocks[request.ticker] = stock_data
        save_stocks(stocks)

        # 6. DB 동기화
        sync_stocks_to_db()

        # 7. Config 캐시 갱신
        Config.reload_stock_config()

        logger.info(f"Successfully created stock: {request.ticker}")
        return {
            "ticker": request.ticker,
            "name": request.name,
            "message": "Stock created successfully"
        }

    except ValidationException as e:
        logger.error(f"Validation error creating stock {request.ticker}: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error creating stock {request.ticker}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create stock. Please try again."
        )


@router.put("/stocks/{ticker}")
async def update_stock(ticker: str, request: StockUpdateRequest) -> Dict[str, Any]:
    """
    종목 정보 수정 (부분 업데이트)

    stocks.json 파일의 종목 정보를 수정하고 데이터베이스에 동기화합니다.

    **Path Parameters:**
    - ticker: 종목 코드 (예: 005930)

    **Request Body (부분 업데이트):**
    ```json
    {
      "name": "삼성전자 (수정)",
      "theme": "반도체/IT/전자"
    }
    ```

    **Response:**
    ```json
    {
      "ticker": "005930",
      "message": "Stock updated successfully"
    }
    ```

    **Status Codes:**
    - 200: 수정 성공
    - 404: 종목을 찾을 수 없음
    - 400: 잘못된 요청
    - 500: 서버 오류
    """
    try:
        # 1. 기존 종목 로드
        stocks = load_stocks()

        # 2. 종목 존재 여부 확인
        if ticker not in stocks:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stock with ticker {ticker} not found"
            )

        # 3. 부분 업데이트 (제공된 필드만 수정)
        stock_data = stocks[ticker]
        update_data = request.dict(exclude_unset=True)  # None이 아닌 필드만

        for key, value in update_data.items():
            stock_data[key] = value

        # 4. 데이터 검증
        validate_stock_data(stock_data, ticker)

        # 5. stocks.json 파일 저장
        stocks[ticker] = stock_data
        save_stocks(stocks)

        # 6. DB 동기화
        sync_stocks_to_db()

        # 7. Config 캐시 갱신
        Config.reload_stock_config()

        logger.info(f"Successfully updated stock: {ticker}")
        return {
            "ticker": ticker,
            "message": "Stock updated successfully"
        }

    except ValidationException as e:
        logger.error(f"Validation error updating stock {ticker}: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error updating stock {ticker}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update stock. Please try again."
        )


@router.delete("/stocks/{ticker}", response_model=StockDeleteResponse)
async def delete_stock(ticker: str) -> StockDeleteResponse:
    """
    종목 삭제 (CASCADE)

    stocks.json 파일에서 종목을 제거하고 관련 데이터를 데이터베이스에서 삭제합니다.

    **Path Parameters:**
    - ticker: 종목 코드 (예: 005930)

    **Response:**
    ```json
    {
      "ticker": "005930",
      "deleted": {
        "prices": 150,
        "news": 20,
        "trading_flow": 30
      }
    }
    ```

    **Status Codes:**
    - 200: 삭제 성공
    - 404: 종목을 찾을 수 없음
    - 500: 서버 오류
    """
    try:
        # 1. 기존 종목 로드
        stocks = load_stocks()

        # 2. 종목 존재 여부 확인
        if ticker not in stocks:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stock with ticker {ticker} not found"
            )

        # 3. stocks.json 파일에서 제거
        del stocks[ticker]
        save_stocks(stocks)

        # 4. DB CASCADE 삭제
        deleted_counts = delete_stock_from_db(ticker)

        # 5. Config 캐시 갱신
        Config.reload_stock_config()

        logger.info(f"Successfully deleted stock: {ticker}, deleted counts: {deleted_counts}")
        return StockDeleteResponse(
            ticker=ticker,
            deleted=deleted_counts
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error deleting stock {ticker}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete stock. Please try again."
        )


@router.get("/stocks/{ticker}/validate", response_model=StockValidateResponse)
async def validate_ticker(ticker: str) -> StockValidateResponse:
    """
    종목 코드 유효성 검증 (네이버 금융 스크래핑)

    네이버 금융에서 종목 정보를 자동으로 수집하여 stocks.json 형식으로 반환합니다.
    프론트엔드에서 "네이버에서 자동 입력" 기능에 사용됩니다.

    **Path Parameters:**
    - ticker: 종목 코드 (예: 005930, 487240)

    **Response:**
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
    - 200: 성공 (종목 정보 반환)
    - 404: 종목을 찾을 수 없음 (네이버 금융에 없음)
    - 500: 스크래핑 실패 (네트워크 에러, 파싱 실패 등)

    **Notes:**
    - 이 API는 검증만 수행하며 stocks.json에 저장하지 않습니다
    - 프론트엔드에서 사용자가 확인/수정 후 POST /api/settings/stocks로 저장
    """
    try:
        scraper = get_ticker_scraper()
        stock_info = scraper.scrape_ticker_info(ticker)

        logger.info(f"Successfully validated ticker: {ticker}")
        return StockValidateResponse(**stock_info)

    except ScraperException as e:
        logger.error(f"Scraper error validating ticker {ticker}: {e}")
        # 404 또는 500으로 구분
        if "찾을 수 없습니다" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
    except Exception as e:
        logger.error(f"Unexpected error validating ticker {ticker}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate ticker. Please try again."
        )
