"""
Rate Limiter 유틸리티

API 요청 빈도를 제어하여 서버 부하를 방지합니다.
"""

import logging
import time
from typing import Optional
from datetime import datetime, timedelta
from threading import Lock

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Rate Limiter 클래스
    
    요청 간 최소 대기 시간을 보장하고, 동시 요청 수를 제한합니다.
    
    Example:
        limiter = RateLimiter(min_interval=0.5)
        
        for ticker in tickers:
            with limiter:
                data = fetch_data(ticker)
    """
    
    def __init__(
        self,
        min_interval: float = 0.5,
        max_concurrent: Optional[int] = None
    ):
        """
        Rate Limiter 초기화
        
        Args:
            min_interval: 요청 간 최소 대기 시간 (초, 기본: 0.5초)
            max_concurrent: 최대 동시 요청 수 (None이면 제한 없음)
        """
        self.min_interval = min_interval
        self.max_concurrent = max_concurrent
        self._last_request_time: Optional[float] = None
        self._lock = Lock()
        self._concurrent_count = 0
        self._total_requests = 0
        self._total_wait_time = 0.0
        
        logger.debug(
            f"RateLimiter 초기화: min_interval={min_interval}초, "
            f"max_concurrent={max_concurrent}"
        )
    
    def __enter__(self):
        """Context Manager 진입"""
        self.wait_if_needed()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context Manager 종료"""
        with self._lock:
            if self.max_concurrent is not None:
                self._concurrent_count -= 1
        return False
    
    def wait_if_needed(self):
        """
        필요한 경우 대기

        마지막 요청으로부터 min_interval이 경과하지 않았으면 대기합니다.
        Lock 밖에서 sleep하여 다른 스레드가 동시에 대기할 수 있도록 합니다.
        """
        wait_time = 0

        # 동시 요청 수 제한 확인 (Lock 밖에서 polling)
        if self.max_concurrent is not None:
            while True:
                with self._lock:
                    if self._concurrent_count < self.max_concurrent:
                        self._concurrent_count += 1
                        break
                time.sleep(0.05)

        # 시간 슬롯 예약 (Lock 내에서 계산만, sleep은 밖에서)
        with self._lock:
            current_time = time.time()

            if self._last_request_time is not None:
                # 예약된 마지막 시점 기준으로 대기 시간 계산
                wait_time = self._last_request_time + self.min_interval - current_time
                if wait_time < 0:
                    wait_time = 0

            # 이 스레드의 요청 시점을 예약
            scheduled_time = current_time + wait_time
            self._last_request_time = scheduled_time
            self._total_requests += 1
            if wait_time > 0:
                self._total_wait_time += wait_time

        # Lock 밖에서 대기 → 다른 스레드도 동시에 슬롯 예약 가능
        if wait_time > 0:
            logger.debug(f"Rate limit: {wait_time:.2f}초 대기")
            time.sleep(wait_time)
    
    def get_stats(self) -> dict:
        """
        Rate Limiter 통계 조회
        
        Returns:
            통계 딕셔너리
        """
        with self._lock:
            return {
                'total_requests': self._total_requests,
                'total_wait_time': round(self._total_wait_time, 2),
                'avg_wait_time': (
                    round(self._total_wait_time / self._total_requests, 2)
                    if self._total_requests > 0 else 0.0
                ),
                'current_concurrent': self._concurrent_count
            }
    
    def reset_stats(self):
        """통계 초기화"""
        with self._lock:
            self._total_requests = 0
            self._total_wait_time = 0.0
            logger.info("RateLimiter 통계 초기화")


# 전역 Rate Limiter 인스턴스
_rate_limiter_instance: Optional[RateLimiter] = None


def get_rate_limiter(
    min_interval: float = 0.5,
    max_concurrent: Optional[int] = None
) -> RateLimiter:
    """
    Rate Limiter 인스턴스 조회 (싱글톤 패턴)
    
    Args:
        min_interval: 요청 간 최소 대기 시간 (초)
        max_concurrent: 최대 동시 요청 수
    
    Returns:
        RateLimiter 인스턴스
    """
    global _rate_limiter_instance
    
    if _rate_limiter_instance is None:
        _rate_limiter_instance = RateLimiter(
            min_interval=min_interval,
            max_concurrent=max_concurrent
        )
    
    return _rate_limiter_instance

