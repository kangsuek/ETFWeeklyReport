"""
Date utility functions for the application
"""
from datetime import date, timedelta
from typing import Tuple, Optional


def get_default_date_range(days: int = 7) -> Tuple[date, date]:
    """
    기본 날짜 범위 반환

    Args:
        days: 과거 며칠까지 조회할지 (기본: 7일)

    Returns:
        (start_date, end_date) 튜플
        - start_date: 오늘로부터 N일 전
        - end_date: 오늘

    Example:
        >>> start_date, end_date = get_default_date_range(7)
        >>> # start_date는 7일 전, end_date는 오늘
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    return start_date, end_date


def apply_default_dates(
    start_date: Optional[date],
    end_date: Optional[date],
    default_days: int = 7
) -> Tuple[date, date]:
    """
    제공된 날짜에 기본값 적용

    Args:
        start_date: 시작 날짜 (None이면 기본값 적용)
        end_date: 종료 날짜 (None이면 오늘)
        default_days: start_date가 None일 때 사용할 기본 일수

    Returns:
        (start_date, end_date) 튜플

    Example:
        >>> start, end = apply_default_dates(None, None, 7)
        >>> # start는 7일 전, end는 오늘

        >>> from datetime import date
        >>> custom_start = date(2025, 11, 1)
        >>> start, end = apply_default_dates(custom_start, None)
        >>> # start는 2025-11-01, end는 오늘
    """
    if not start_date:
        start_date = date.today() - timedelta(days=default_days)
    if not end_date:
        end_date = date.today()
    return start_date, end_date
