"""
투자 시뮬레이션 API 라우터

일시 투자, 적립식(DCA), 포트폴리오 시뮬레이션 엔드포인트
"""

from fastapi import APIRouter, HTTPException
from app.models import (
    LumpSumRequest, LumpSumResponse,
    DCARequest, DCAResponse,
    PortfolioSimulationRequest, PortfolioSimulationResponse,
)
from app.services.data_collector import ETFDataCollector
from app.services.simulation_service import SimulationService
from app.utils.cache import make_cache_key, get_cache
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

CACHE_TTL = 300  # 5분


def _get_service() -> SimulationService:
    return SimulationService(ETFDataCollector())


@router.post("/lump-sum", response_model=LumpSumResponse)
async def simulation_lump_sum(req: LumpSumRequest):
    """일시 투자 시뮬레이션"""
    cache = get_cache()
    cache_key = make_cache_key(
        "simulation_lump_sum",
        ticker=req.ticker,
        buy_date=str(req.buy_date),
        amount=req.amount,
    )

    cached = cache.get(cache_key)
    if cached:
        return cached

    try:
        service = _get_service()
        result = service.run_lump_sum(req)
        cache.set(cache_key, result.model_dump(), CACHE_TTL)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Lump-sum simulation failed: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail=f"시뮬레이션 실행 실패: {str(e)}")


@router.post("/dca", response_model=DCAResponse)
async def simulation_dca(req: DCARequest):
    """적립식 투자 시뮬레이션"""
    # 유효성 검사
    if req.start_date >= req.end_date:
        raise HTTPException(status_code=400, detail="시작일은 종료일보다 이전이어야 합니다")
    if req.buy_day < 1 or req.buy_day > 28:
        raise HTTPException(status_code=400, detail="매수일은 1~28 사이여야 합니다")

    cache = get_cache()
    cache_key = make_cache_key(
        "simulation_dca",
        ticker=req.ticker,
        monthly_amount=req.monthly_amount,
        start_date=str(req.start_date),
        end_date=str(req.end_date),
        buy_day=req.buy_day,
    )

    cached = cache.get(cache_key)
    if cached:
        return cached

    try:
        service = _get_service()
        result = service.run_dca(req)
        cache.set(cache_key, result.model_dump(), CACHE_TTL)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"DCA simulation failed: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail=f"시뮬레이션 실행 실패: {str(e)}")


@router.post("/portfolio", response_model=PortfolioSimulationResponse)
async def simulation_portfolio(req: PortfolioSimulationRequest):
    """포트폴리오 시뮬레이션"""
    if req.start_date >= req.end_date:
        raise HTTPException(status_code=400, detail="시작일은 종료일보다 이전이어야 합니다")
    if not req.holdings:
        raise HTTPException(status_code=400, detail="최소 1개 이상의 종목이 필요합니다")
    tickers = [h.ticker for h in req.holdings]
    if len(tickers) != len(set(tickers)):
        raise HTTPException(status_code=400, detail="동일 종목이 중복 입력되었습니다")

    cache = get_cache()
    tickers_str = ",".join(f"{h.ticker}:{h.weight}" for h in req.holdings)
    cache_key = make_cache_key(
        "simulation_portfolio",
        holdings=tickers_str,
        amount=req.amount,
        start_date=str(req.start_date),
        end_date=str(req.end_date),
    )

    cached = cache.get(cache_key)
    if cached:
        return cached

    try:
        service = _get_service()
        result = service.run_portfolio(req)
        cache.set(cache_key, result.model_dump(), CACHE_TTL)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Portfolio simulation failed: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail=f"시뮬레이션 실행 실패: {str(e)}")
