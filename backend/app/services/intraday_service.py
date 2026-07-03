"""
분봉(시간별 체결) 조회 오케스트레이션 서비스

DB 조회 → 마지막 거래일 폴백 → 장중 신선도 판단 → 백그라운드 재수집 트리거를
담당한다. (구 routers/etfs.py GET /{ticker}/intraday 인라인 로직)
실제 스크레이핑·저장은 intraday_collector가 수행한다.
"""
import asyncio
import logging
from datetime import date, datetime, time as dtime
from typing import Optional

from app.utils.cache import get_cache, make_cache_key

logger = logging.getLogger(__name__)

# 분봉 백그라운드 수집 중인 티커 (중복 수집 방지)
_intraday_collecting = set()

# 장중 캐시 TTL (초) — 장중에는 데이터가 빠르게 갱신되므로 짧게 유지
MARKET_HOURS_CACHE_TTL = 15


def _run_intraday_collect(ticker: str, incremental: bool) -> None:
    """백그라운드 스레드에서 분봉 수집 후 캐시 무효화"""
    try:
        from app.services.intraday_collector import IntradayDataCollector
        collector = IntradayDataCollector()
        if incremental:
            collector.incremental_collect_and_save(ticker)
        else:
            collector.collect_and_save_intraday(ticker, pages=40)
    finally:
        get_cache().invalidate_pattern(f"intraday:{ticker}")
        _intraday_collecting.discard(ticker)


async def get_intraday_snapshot(
    ticker: str,
    target_date: Optional[date],
    auto_collect: bool,
    force_refresh: bool,
    cache,
    default_cache_ttl: int,
) -> dict:
    """
    분봉 데이터 스냅샷 조회 (필요 시 백그라운드 수집 트리거)

    Args:
        ticker: 종목 코드
        target_date: 조회할 날짜 (None이면 오늘, 없으면 마지막 거래일 폴백)
        auto_collect: 데이터 없거나 오래됐을 때 자동 수집 여부
        force_refresh: 캐시 무시 및 재수집 트리거
        cache: 라우터가 사용하는 캐시 인스턴스
        default_cache_ttl: 장외 시간 캐시 TTL (초)

    Returns:
        분봉 응답 dict (ticker/date/data/count/first_time/last_time [+플래그])
    """
    from app.services.intraday_collector import IntradayDataCollector

    intraday_collector = IntradayDataCollector()

    # 실제 조회할 날짜 결정
    actual_date = target_date or date.today()

    # 캐시 확인 (실제 날짜 기준, force_refresh 시 캐시 무시)
    cache_key = make_cache_key("intraday", ticker=ticker, date=actual_date)
    if force_refresh:
        cache.invalidate_pattern(f"intraday:{ticker}")
        logger.info(f"Force refresh: cache invalidated for intraday:{ticker}")
    else:
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            logger.debug(f"Cache hit for {cache_key}")
            return cached_result

    # DB에서 데이터 조회
    intraday_data = intraday_collector.get_intraday_data(ticker, actual_date)

    # 오늘 데이터가 없으면 마지막 거래일 데이터 확인
    if not intraday_data and target_date is None:
        last_trading_date = intraday_collector.get_last_trading_date(ticker)
        if last_trading_date and last_trading_date != date.today():
            logger.debug(f"No intraday data for today, checking last trading date: {last_trading_date}")
            actual_date = last_trading_date
            intraday_data = intraday_collector.get_intraday_data(ticker, last_trading_date)

    # 장중 여부 판단 (09:00 ~ 15:30 KST, 평일)
    now = datetime.now()
    is_market_hours = (
        now.weekday() < 5  # 월~금
        and dtime(9, 0) <= now.time() <= dtime(15, 30)
        and actual_date == date.today()
    )

    # force_refresh 또는 장중에 마지막 체결 시간이 3분 이상 지났으면 재수집
    need_recollect = force_refresh  # force_refresh 시 무조건 재수집
    if intraday_data and is_market_hours and auto_collect and not need_recollect:
        last_dt_str = intraday_data[-1].get('datetime')
        if last_dt_str:
            try:
                if isinstance(last_dt_str, str):
                    last_dt = datetime.fromisoformat(last_dt_str.replace(' ', 'T'))
                else:
                    last_dt = last_dt_str
                elapsed = (now - last_dt).total_seconds()
                if elapsed > 180:  # 3분
                    need_recollect = True
                    logger.info(f"Intraday data for {ticker} is {int(elapsed)}s old, triggering re-collection")
            except Exception as e:
                logger.warning(f"Could not parse last intraday datetime: {e}")

    # 데이터가 없거나, 재수집이 필요할 때 백그라운드 수집 시작
    bg_collect_triggered = False
    if (not intraday_data or need_recollect) and auto_collect:
        if ticker not in _intraday_collecting:
            _intraday_collecting.add(ticker)
            bg_collect_triggered = True
            # 기존 데이터가 있으면 증분 수집 (빠름), 없으면 전체 수집
            use_incremental = bool(intraday_data)
            log_msg = "incremental re-collect" if use_incremental else "full collect (no data)"
            logger.debug(f"Intraday {log_msg} for {ticker}, starting background collection")

            loop = asyncio.get_running_loop()
            loop.run_in_executor(None, _run_intraday_collect, ticker, use_incremental)
        else:
            # 이미 수집 중이면 그 사실을 알림
            bg_collect_triggered = True

        # 데이터가 아예 없으면 수집 중 응답 반환
        if not intraday_data:
            return {
                "ticker": ticker,
                "date": actual_date.isoformat(),
                "data": [],
                "count": 0,
                "first_time": None,
                "last_time": None,
                "background_collect_started": True,
                "message": "분봉 데이터 수집 중입니다. 잠시 후 자동으로 갱신됩니다.",
            }
        # 기존 데이터가 있으면 아래에서 데이터와 함께 background_collect_started 플래그 포함

    if not intraday_data:
        # 빈 결과는 캐시하지 않음. 다음 요청(프론트 새로고침 등)에서 auto_collect가 다시 시도되도록 함
        return {
            "ticker": ticker,
            "date": actual_date.isoformat(),
            "data": [],
            "count": 0,
            "first_time": None,
            "last_time": None,
            "message": "데이터 없음 (장 마감 또는 휴장일)"
        }

    # datetime을 ISO 문자열로 변환하고 시간 추출
    for item in intraday_data:
        dt_value = item['datetime']
        if isinstance(dt_value, str):
            # 문자열인 경우 ISO 형식으로 변환 (공백 -> T)
            item['datetime'] = dt_value.replace(' ', 'T')
        else:
            item['datetime'] = dt_value.isoformat()

    # 시간 추출 (HH:MM 형식)
    first_dt = intraday_data[0]['datetime']
    last_dt = intraday_data[-1]['datetime']
    first_time = first_dt.split('T')[1][:5] if 'T' in first_dt else first_dt.split(' ')[1][:5]
    last_time = last_dt.split('T')[1][:5] if 'T' in last_dt else last_dt.split(' ')[1][:5]

    response = {
        "ticker": ticker,
        "date": actual_date.isoformat(),
        "data": intraday_data,
        "count": len(intraday_data),
        "first_time": first_time,
        "last_time": last_time
    }

    # 백그라운드 수집이 진행 중이면 플래그 추가 (프론트엔드가 3초 간격 polling)
    if bg_collect_triggered:
        response["background_collect_started"] = True
        # 수집 중에는 캐시하지 않음 (다음 요청에서 새 데이터 반영)
    else:
        # 장중에는 캐시 TTL을 짧게(15초), 장 외에는 기본값 사용
        intraday_cache_ttl = MARKET_HOURS_CACHE_TTL if is_market_hours else default_cache_ttl
        cache.set(cache_key, response, ttl_seconds=intraday_cache_ttl)
    return response
