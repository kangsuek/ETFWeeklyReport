"""
데이터 수집 유틸리티 함수

자동 데이터 수집 로직을 재사용 가능한 함수로 제공합니다.
"""

import logging
from datetime import date
from typing import Callable, Optional, Dict, Any, List

logger = logging.getLogger(__name__)


def auto_collect_if_needed(
    ticker: str,
    start_date: date,
    end_date: date,
    get_data_fn: Callable[[str, date, date], List[Any]],
    get_data_range_fn: Callable[[str], Optional[Dict[str, date]]],
    collect_fn: Callable,
    data_type: str = "data",
    pass_dates_to_collect: bool = False
) -> List[Any]:
    """
    데이터가 부족한 경우 자동으로 수집하는 공통 로직

    Args:
        ticker: 종목 코드
        start_date: 조회 시작 날짜
        end_date: 조회 종료 날짜
        get_data_fn: 데이터 조회 함수 (ticker, start_date, end_date) -> List
        get_data_range_fn: 데이터 범위 조회 함수 (ticker) -> Dict or None
        collect_fn: 데이터 수집 함수
            - pass_dates_to_collect=False: (ticker, days) -> count
            - pass_dates_to_collect=True: (ticker, days, start_date, end_date) -> count
        data_type: 데이터 타입 (로깅용, 예: "price", "trading flow")
        pass_dates_to_collect: collect_fn에 start_date, end_date를 전달할지 여부

    Returns:
        데이터 리스트 (자동 수집 후 재조회된 결과 포함)

    Raises:
        ScraperException: 데이터 수집 실패
        DatabaseException: DB 오류
    """
    # 1. DB 데이터 조회
    data = get_data_fn(ticker, start_date, end_date)

    # 2. 데이터 범위 확인
    data_range = get_data_range_fn(ticker)

    # 3. 데이터가 없거나 범위가 부족한 경우 자동 수집
    should_collect = False
    collection_days = 0

    if not data_range:
        # DB에 데이터가 전혀 없음
        logger.info(f"No {data_type} data in DB for {ticker}, collecting {(end_date - start_date).days + 1} days")
        should_collect = True
        collection_days = (end_date - start_date).days + 1
    elif data_range['min_date'] > start_date or data_range['max_date'] < end_date:
        # 요청 범위가 DB 범위를 벗어남
        logger.info(
            f"Requested {data_type} range ({start_date} to {end_date}) exceeds "
            f"DB range ({data_range['min_date']} to {data_range['max_date']})"
        )
        should_collect = True

        # 부족한 기간 계산
        if data_range['min_date'] > start_date:
            collection_days = max(collection_days, (data_range['min_date'] - start_date).days)
        if data_range['max_date'] < end_date:
            collection_days = max(collection_days, (end_date - data_range['max_date']).days)

        # 전체 범위로 다시 수집
        collection_days = (end_date - start_date).days + 1

    if should_collect:
        logger.info(f"Auto-collecting {collection_days} days of {data_type} data for {ticker}")

        # 수집 함수 호출 (날짜 전달 여부에 따라 다르게 호출)
        if pass_dates_to_collect:
            collected_count = collect_fn(ticker, collection_days, start_date, end_date)
        else:
            collected_count = collect_fn(ticker, collection_days)

        logger.info(f"Auto-collected {collected_count} {data_type} records for {ticker}")

        # 다시 조회
        data = get_data_fn(ticker, start_date, end_date)

    return data
