"""
재시도 로직 유틸리티

Exponential Backoff를 사용한 재시도 데코레이터를 제공합니다.
"""

import logging
import time
from functools import wraps
from typing import Callable, Type, Tuple

logger = logging.getLogger(__name__)


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 10.0,
    exponential_base: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """
    Exponential Backoff를 사용한 재시도 데코레이터
    
    Args:
        max_retries: 최대 재시도 횟수 (기본: 3회)
        base_delay: 기본 대기 시간 (초, 기본: 1.0초)
        max_delay: 최대 대기 시간 (초, 기본: 10.0초)
        exponential_base: 지수 베이스 (기본: 2.0)
        exceptions: 재시도할 예외 타입 튜플 (기본: 모든 Exception)
    
    Example:
        @retry_with_backoff(max_retries=3, base_delay=1.0)
        def fetch_data():
            # 네트워크 요청
            pass
    
    재시도 패턴:
        - 1번째 실패: 1초 대기 후 재시도
        - 2번째 실패: 2초 대기 후 재시도
        - 3번째 실패: 4초 대기 후 재시도
        - 4번째 실패: 예외 발생
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            retry_count = 0
            
            while retry_count <= max_retries:
                try:
                    return func(*args, **kwargs)
                    
                except exceptions as e:
                    retry_count += 1
                    
                    if retry_count > max_retries:
                        logger.error(
                            f"[재시도 실패] {func.__name__}: "
                            f"{max_retries}회 재시도 후 실패 - {type(e).__name__}: {e}"
                        )
                        raise
                    
                    # Exponential Backoff 계산
                    delay = min(
                        base_delay * (exponential_base ** (retry_count - 1)),
                        max_delay
                    )
                    
                    logger.warning(
                        f"[재시도 {retry_count}/{max_retries}] {func.__name__}: "
                        f"{type(e).__name__}: {e} - {delay:.1f}초 후 재시도"
                    )
                    
                    time.sleep(delay)
            
            # 이 코드에는 도달하지 않아야 함 (while 루프에서 return 또는 raise)
            raise RuntimeError(f"Unexpected retry loop exit in {func.__name__}")
        
        return wrapper
    return decorator

