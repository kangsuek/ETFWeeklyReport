from fastapi import APIRouter, HTTPException
from typing import List
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/generate", deprecated=True)
async def generate_report(tickers: List[str], format: str = "markdown"):
    """
    Generate report for selected ETFs

    ⚠️ **Status: Coming Soon**

    This endpoint is currently under development and will be available in a future release.

    **Planned Features:**
    - Comprehensive analysis report generation
    - Multiple output formats (Markdown, PDF, HTML)
    - Custom date range selection
    - Performance metrics and charts

    **Current Status:** Not implemented

    Args:
        tickers: List of stock/ETF ticker codes
        format: Output format (default: "markdown")

    Returns:
        Placeholder response indicating feature is not yet available
    """
    logger.warning(f"Report generation endpoint called but not implemented: tickers={tickers}, format={format}")
    raise HTTPException(
        status_code=501,
        detail="Report generation feature is coming soon. This endpoint is currently not implemented."
    )
