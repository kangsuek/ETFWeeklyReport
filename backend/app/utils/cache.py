"""
메모리 기반 캐시 시스템

TTL(Time To Live) 기반의 스레드 안전한 메모리 캐시 구현
실시간 데이터 업데이트 최적화를 위해 사용
"""

import threading
import time
from typing import Any, Optional, Dict, Callable
from datetime import datetime, timedelta
import logging
import hashlib
import json

logger = logging.getLogger(__name__)


class MemoryCache:
    """
    TTL 기반 메모리 캐시

    Features:
    - TTL(Time To Live) 지원
    - 스레드 안전성 (threading.Lock)
    - 캐시 통계 제공
    - LRU eviction (최대 크기 제한)
    """

    def __init__(self, default_ttl_seconds: int = 30, max_size: int = 1000):
        """
        Args:
            default_ttl_seconds: 기본 TTL (초), 기본값 30초
            max_size: 최대 캐시 항목 수, 기본값 1000개
        """
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._default_ttl = default_ttl_seconds
        self._max_size = max_size

        # 통계
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "sets": 0,
        }

    def _is_expired(self, item: Dict[str, Any]) -> bool:
        """캐시 항목이 만료되었는지 확인"""
        return time.time() > item["expires_at"]

    def _evict_oldest(self):
        """가장 오래된 항목 제거 (LRU)"""
        if not self._cache:
            return

        oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k]["created_at"])
        del self._cache[oldest_key]
        self._stats["evictions"] += 1
        logger.debug(f"Evicted oldest cache entry: {oldest_key}")

    def _cleanup_expired(self):
        """만료된 항목 정리"""
        expired_keys = [
            key for key, item in self._cache.items()
            if self._is_expired(item)
        ]
        for key in expired_keys:
            del self._cache[key]
            logger.debug(f"Cleaned up expired cache entry: {key}")

    def get(self, key: str) -> Optional[Any]:
        """
        캐시에서 값 조회

        Args:
            key: 캐시 키

        Returns:
            캐시된 값 또는 None (만료/존재하지 않음)
        """
        with self._lock:
            if key not in self._cache:
                self._stats["misses"] += 1
                return None

            item = self._cache[key]

            if self._is_expired(item):
                del self._cache[key]
                self._stats["misses"] += 1
                logger.debug(f"Cache miss (expired): {key}")
                return None

            self._stats["hits"] += 1
            logger.debug(f"Cache hit: {key}")
            return item["value"]

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None):
        """
        캐시에 값 저장

        Args:
            key: 캐시 키
            value: 저장할 값
            ttl_seconds: TTL (초), None이면 기본값 사용
        """
        with self._lock:
            # 크기 제한 확인
            if len(self._cache) >= self._max_size:
                self._evict_oldest()

            ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl

            self._cache[key] = {
                "value": value,
                "created_at": time.time(),
                "expires_at": time.time() + ttl,
                "ttl": ttl,
            }

            self._stats["sets"] += 1
            logger.debug(f"Cache set: {key} (TTL: {ttl}s)")

    def delete(self, key: str) -> bool:
        """
        캐시에서 항목 삭제

        Args:
            key: 캐시 키

        Returns:
            삭제 성공 여부
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"Cache deleted: {key}")
                return True
            return False

    def clear(self):
        """모든 캐시 항목 삭제"""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            logger.info(f"Cache cleared: {count} items removed")

    def invalidate_pattern(self, pattern: str):
        """
        패턴에 매칭되는 모든 캐시 항목 무효화

        Args:
            pattern: 키에 포함되어야 하는 문자열
        """
        with self._lock:
            keys_to_delete = [key for key in self._cache.keys() if pattern in key]
            for key in keys_to_delete:
                del self._cache[key]
            logger.info(f"Invalidated {len(keys_to_delete)} cache entries matching pattern: {pattern}")

    def get_stats(self) -> Dict[str, Any]:
        """
        캐시 통계 조회

        Returns:
            캐시 통계 정보 (hits, misses, hit_rate, size 등)
        """
        with self._lock:
            # 만료된 항목 정리
            self._cleanup_expired()

            total_requests = self._stats["hits"] + self._stats["misses"]
            hit_rate = (
                (self._stats["hits"] / total_requests * 100)
                if total_requests > 0
                else 0
            )

            return {
                "hits": self._stats["hits"],
                "misses": self._stats["misses"],
                "hit_rate_pct": round(hit_rate, 2),
                "total_requests": total_requests,
                "evictions": self._stats["evictions"],
                "sets": self._stats["sets"],
                "current_size": len(self._cache),
                "max_size": self._max_size,
                "default_ttl_seconds": self._default_ttl,
            }

    def get_or_set(
        self,
        key: str,
        factory: Callable[[], Any],
        ttl_seconds: Optional[int] = None
    ) -> Any:
        """
        캐시에서 값을 가져오거나, 없으면 factory 함수를 호출하여 설정

        Args:
            key: 캐시 키
            factory: 캐시 미스 시 호출할 함수
            ttl_seconds: TTL (초)

        Returns:
            캐시된 값 또는 factory 함수 결과
        """
        value = self.get(key)
        if value is not None:
            return value

        # 캐시 미스: factory 함수 호출
        value = factory()
        self.set(key, value, ttl_seconds)
        return value


def make_cache_key(endpoint: str, **kwargs) -> str:
    """
    캐시 키 생성

    Args:
        endpoint: API 엔드포인트 (예: "etfs", "prices")
        **kwargs: 추가 파라미터 (ticker, date 등)

    Returns:
        생성된 캐시 키

    Example:
        make_cache_key("prices", ticker="487240", start_date="2025-11-01")
        # => "prices:487240:hash_of_params"
    """
    # 기본 키 생성
    key_parts = [endpoint]

    # ticker가 있으면 추가
    if "ticker" in kwargs:
        key_parts.append(str(kwargs.pop("ticker")))

    # 나머지 파라미터는 해시로 변환
    if kwargs:
        # 정렬하여 일관성 보장
        params_str = json.dumps(kwargs, sort_keys=True, default=str)
        params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
        key_parts.append(params_hash)

    return ":".join(key_parts)


# 전역 캐시 인스턴스 (싱글톤)
_global_cache: Optional[MemoryCache] = None
_cache_lock = threading.Lock()


def get_cache(ttl_seconds: int = 30, max_size: int = 1000) -> MemoryCache:
    """
    전역 캐시 인스턴스 가져오기 (싱글톤 패턴)

    Args:
        ttl_seconds: 기본 TTL (초)
        max_size: 최대 캐시 크기

    Returns:
        MemoryCache 인스턴스
    """
    global _global_cache

    if _global_cache is None:
        with _cache_lock:
            if _global_cache is None:
                _global_cache = MemoryCache(
                    default_ttl_seconds=ttl_seconds,
                    max_size=max_size
                )
                logger.info(f"Global cache initialized (TTL: {ttl_seconds}s, Max size: {max_size})")

    return _global_cache
