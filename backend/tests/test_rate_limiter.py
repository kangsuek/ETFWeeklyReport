"""
Rate Limiter 유틸리티 테스트

RateLimiter 클래스의 동작을 검증합니다.
"""

import pytest
import time
from app.utils.rate_limiter import RateLimiter, get_rate_limiter


class TestRateLimiter:
    """RateLimiter 클래스 테스트"""
    
    def test_initialization(self):
        """초기화 테스트"""
        limiter = RateLimiter(min_interval=0.5, max_concurrent=5)
        
        assert limiter.min_interval == 0.5
        assert limiter.max_concurrent == 5
        assert limiter._last_request_time is None
        assert limiter._concurrent_count == 0
    
    def test_first_request_no_wait(self):
        """첫 번째 요청은 대기 없이 즉시 실행"""
        limiter = RateLimiter(min_interval=0.5)
        
        start_time = time.time()
        with limiter:
            pass
        duration = time.time() - start_time
        
        # 첫 요청은 대기 없음
        assert duration < 0.1
    
    def test_min_interval_enforced(self):
        """최소 간격이 보장되는지 검증"""
        limiter = RateLimiter(min_interval=0.3)
        
        # 첫 번째 요청
        start_time = time.time()
        with limiter:
            pass
        
        # 두 번째 요청 (0.3초 대기해야 함)
        with limiter:
            pass
        duration = time.time() - start_time
        
        # 최소 0.3초 대기
        assert duration >= 0.3
        assert duration < 0.4  # 너무 오래 대기하지 않음
    
    def test_multiple_requests_timing(self):
        """여러 요청의 타이밍 검증"""
        limiter = RateLimiter(min_interval=0.2)
        request_times = []
        
        for i in range(3):
            with limiter:
                request_times.append(time.time())
        
        # 첫 번째 요청: 즉시
        # 두 번째 요청: +0.2초
        interval1 = request_times[1] - request_times[0]
        assert 0.18 <= interval1 <= 0.25
        
        # 세 번째 요청: +0.2초
        interval2 = request_times[2] - request_times[1]
        assert 0.18 <= interval2 <= 0.25
    
    def test_max_concurrent_limit(self):
        """동시 요청 수 제한 테스트 (기본 케이스)"""
        # 멀티스레딩 테스트는 복잡하므로 기본 기능만 확인
        limiter = RateLimiter(min_interval=0.1, max_concurrent=2)
        
        # 초기값 확인
        assert limiter._concurrent_count == 0
        
        # 단일 진입 테스트
        with limiter:
            assert limiter._concurrent_count == 1
        
        assert limiter._concurrent_count == 0
    
    def test_get_stats(self):
        """통계 조회 테스트"""
        limiter = RateLimiter(min_interval=0.1)
        
        # 초기 통계
        stats = limiter.get_stats()
        assert stats['total_requests'] == 0
        assert stats['total_wait_time'] == 0.0
        assert stats['avg_wait_time'] == 0.0
        
        # 3번 요청 후 통계
        for _ in range(3):
            with limiter:
                time.sleep(0.01)
        
        stats = limiter.get_stats()
        assert stats['total_requests'] == 3
        assert stats['total_wait_time'] > 0.0  # 2번 대기 (첫 요청 제외)
        assert stats['avg_wait_time'] > 0.0
    
    def test_reset_stats(self):
        """통계 초기화 테스트"""
        limiter = RateLimiter(min_interval=0.1)
        
        # 요청 후 통계 확인
        for _ in range(2):
            with limiter:
                pass
        
        stats_before = limiter.get_stats()
        assert stats_before['total_requests'] == 2
        
        # 통계 초기화
        limiter.reset_stats()
        
        stats_after = limiter.get_stats()
        assert stats_after['total_requests'] == 0
        assert stats_after['total_wait_time'] == 0.0
    
    def test_context_manager_exception_handling(self):
        """Context Manager에서 예외 발생 시에도 정리 작업 수행"""
        limiter = RateLimiter(min_interval=0.1, max_concurrent=1)
        
        try:
            with limiter:
                # concurrent_count 증가
                assert limiter._concurrent_count == 1
                raise ValueError("test error")
        except ValueError:
            pass
        
        # 예외 후에도 concurrent_count 감소
        assert limiter._concurrent_count == 0
    
    def test_no_max_concurrent_limit(self):
        """max_concurrent가 None이면 동시 요청 수 제한 없음"""
        limiter = RateLimiter(min_interval=0.05, max_concurrent=None)
        
        # max_concurrent가 None일 때 정상 동작 확인
        with limiter:
            assert limiter.max_concurrent is None
            # concurrent_count는 증가하지 않음
        
        # 여러 요청 가능
        for _ in range(3):
            with limiter:
                pass


class TestRateLimiterSingleton:
    """get_rate_limiter 싱글톤 패턴 테스트"""
    
    def test_singleton_pattern(self):
        """동일한 인스턴스 반환 확인"""
        # 전역 인스턴스 초기화
        import app.utils.rate_limiter
        app.utils.rate_limiter._rate_limiter_instance = None
        
        limiter1 = get_rate_limiter(min_interval=0.5)
        limiter2 = get_rate_limiter(min_interval=0.5)
        
        assert limiter1 is limiter2
        
        # 통계 공유 확인
        with limiter1:
            pass
        
        stats1 = limiter1.get_stats()
        stats2 = limiter2.get_stats()
        
        assert stats1['total_requests'] == 1
        assert stats2['total_requests'] == 1


class TestRateLimiterIntegration:
    """실제 시나리오 통합 테스트"""
    
    def test_api_request_simulation(self):
        """API 요청 시뮬레이션"""
        limiter = RateLimiter(min_interval=0.2)
        
        results = []
        start_time = time.time()
        
        # 5개 API 요청 시뮬레이션
        for i in range(5):
            with limiter:
                # API 호출 (Mock)
                results.append(f"response_{i}")
        
        duration = time.time() - start_time
        
        # 최소 0.8초 소요 (4 * 0.2초)
        assert duration >= 0.8
        assert len(results) == 5
        
        # 통계 확인
        stats = limiter.get_stats()
        assert stats['total_requests'] == 5
        assert stats['total_wait_time'] >= 0.8
    
    def test_sequential_requests_with_rate_limit(self):
        """순차적 요청에 Rate Limit 적용"""
        limiter = RateLimiter(min_interval=0.1)
        
        results = []
        
        # 5개 요청 순차 처리
        start_time = time.time()
        for i in range(5):
            with limiter:
                results.append(f"request_{i}")
        duration = time.time() - start_time
        
        # 총 5개 요청
        assert len(results) == 5
        
        # 최소 0.4초 소요 (4번의 0.1초 대기)
        assert duration >= 0.4
        
        # 통계 확인
        stats = limiter.get_stats()
        assert stats['total_requests'] == 5

