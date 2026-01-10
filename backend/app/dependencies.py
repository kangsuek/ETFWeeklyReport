"""
FastAPI dependency injection functions
"""
from fastapi import HTTPException, Depends
from app.models import ETF
from app.services.data_collector import ETFDataCollector
from app.middleware.auth import verify_api_key_dependency
import logging

logger = logging.getLogger(__name__)

# Global collector instance for dependency injection
_collector = ETFDataCollector()


def get_collector() -> ETFDataCollector:
    """
    Get ETFDataCollector instance

    Returns:
        ETFDataCollector instance
    """
    return _collector


def get_etf_or_404(ticker: str, collector: ETFDataCollector = Depends(get_collector)) -> ETF:
    """
    ETF 존재 확인 의존성

    Args:
        ticker: Stock/ETF ticker code
        collector: ETFDataCollector instance (injected)

    Returns:
        ETF model instance

    Raises:
        HTTPException: 404 if ETF/Stock not found

    Example:
        ```python
        @router.get("/{ticker}/data")
        async def get_data(etf: ETF = Depends(get_etf_or_404)):
            # etf는 이미 검증되었고, 존재함이 보장됨
            return {"name": etf.name}
        ```
    """
    try:
        etf = collector.get_etf_info(ticker)
        if not etf:
            logger.warning(f"Stock/ETF {ticker} not found")
            raise HTTPException(status_code=404, detail=f"Stock/ETF {ticker} not found")
        return etf
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching ETF {ticker}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
