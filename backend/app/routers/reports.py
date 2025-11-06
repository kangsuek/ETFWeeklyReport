from fastapi import APIRouter, HTTPException
from typing import List
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/generate")
async def generate_report(tickers: List[str], format: str = "markdown"):
    """Generate report for selected ETFs"""
    # TODO: Implement report generation
    return {
        "message": "Report generation not yet implemented",
        "tickers": tickers,
        "format": format
    }
