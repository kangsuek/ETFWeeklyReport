"""
Retry 유틸리티 테스트

retry_with_backoff 데코레이터의 동작을 검증합니다.
"""

import pytest
import time
from unittest.mock import Mock, patch
from app.utils.retry import retry_with_backoff


class TestRetryWithBackoff:
    """retry_with_backoff 데코레이터 테스트"""
    
    def test_success_on_first_try(self):
        """첫 번째 시도에서 성공하는 경우"""
        mock_func = Mock(return_value="success")
        
        @retry_with_backoff(max_retries=3, base_delay=0.1)
        def test_func():
            return mock_func()
        
        result = test_func()
        
        assert result == "success"
        assert mock_func.call_count == 1
    
    def test_success_after_retries(self):
        """재시도 후 성공하는 경우"""
        mock_func = Mock(side_effect=[
            Exception("1st failure"),
            Exception("2nd failure"),
            "success"
        ])
        
        @retry_with_backoff(max_retries=3, base_delay=0.1)
        def test_func():
            result = mock_func()
            if isinstance(result, str):
                return result
            raise result
        
        start_time = time.time()
        result = test_func()
        duration = time.time() - start_time
        
        assert result == "success"
        assert mock_func.call_count == 3
        # 0.1초 + 0.2초 = 0.3초 이상 대기
        assert duration >= 0.3
    
    def test_failure_after_max_retries(self):
        """최대 재시도 횟수 초과 시 예외 발생"""
        mock_func = Mock(side_effect=Exception("persistent failure"))
        
        @retry_with_backoff(max_retries=2, base_delay=0.1)
        def test_func():
            return mock_func()
        
        with pytest.raises(Exception, match="persistent failure"):
            test_func()
        
        # 최초 시도 + 2회 재시도 = 3회 호출
        assert mock_func.call_count == 3
    
    def test_exponential_backoff_timing(self):
        """Exponential Backoff 대기 시간 검증"""
        call_times = []
        
        def record_time():
            call_times.append(time.time())
            raise Exception("test error")
        
        @retry_with_backoff(max_retries=3, base_delay=0.1, exponential_base=2.0)
        def test_func():
            record_time()
        
        with pytest.raises(Exception, match="test error"):
            test_func()
        
        # 호출 간격 검증
        assert len(call_times) == 4  # 최초 + 3회 재시도
        
        # 1번째 재시도: 약 0.1초 대기
        interval1 = call_times[1] - call_times[0]
        assert 0.08 <= interval1 <= 0.15
        
        # 2번째 재시도: 약 0.2초 대기
        interval2 = call_times[2] - call_times[1]
        assert 0.18 <= interval2 <= 0.25
        
        # 3번째 재시도: 약 0.4초 대기
        interval3 = call_times[3] - call_times[2]
        assert 0.38 <= interval3 <= 0.45
    
    def test_max_delay_limit(self):
        """최대 대기 시간 제한 검증"""
        call_times = []
        
        def record_time():
            call_times.append(time.time())
            raise Exception("test error")
        
        @retry_with_backoff(
            max_retries=5,
            base_delay=1.0,
            max_delay=2.0,  # 최대 2초로 제한
            exponential_base=2.0
        )
        def test_func():
            record_time()
        
        with pytest.raises(Exception, match="test error"):
            test_func()
        
        # 3번째 재시도부터 max_delay(2초)가 적용되어야 함
        # 1초, 2초, 2초, 2초, 2초
        assert len(call_times) == 6  # 최초 + 5회 재시도
        
        # 마지막 재시도는 max_delay(2초) 적용
        interval_last = call_times[-1] - call_times[-2]
        assert 1.9 <= interval_last <= 2.2
    
    def test_specific_exceptions_only(self):
        """특정 예외만 재시도하는 경우"""
        call_count = 0
        
        def func_with_value_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("value error")
        
        # ValueError만 재시도
        @retry_with_backoff(
            max_retries=3,
            base_delay=0.1,
            exceptions=(ValueError,)
        )
        def test_func_value_error():
            func_with_value_error()
        
        with pytest.raises(ValueError):
            test_func_value_error()
        
        # 재시도됨 (최초 + 3회 = 4회)
        assert call_count == 4
        
        # RuntimeError는 재시도하지 않음
        call_count = 0
        
        @retry_with_backoff(
            max_retries=3,
            base_delay=0.1,
            exceptions=(ValueError,)
        )
        def test_func_runtime_error():
            nonlocal call_count
            call_count += 1
            raise RuntimeError("runtime error")
        
        with pytest.raises(RuntimeError):
            test_func_runtime_error()
        
        # 재시도 안됨 (최초 1회만)
        assert call_count == 1
    
    def test_return_value_preserved(self):
        """반환값이 올바르게 전달되는지 검증"""
        @retry_with_backoff(max_retries=3, base_delay=0.1)
        def get_number():
            return 42
        
        @retry_with_backoff(max_retries=3, base_delay=0.1)
        def get_dict():
            return {"key": "value"}
        
        assert get_number() == 42
        assert get_dict() == {"key": "value"}
    
    def test_function_with_arguments(self):
        """인자를 받는 함수에 적용"""
        mock_func = Mock(return_value="result")
        
        @retry_with_backoff(max_retries=3, base_delay=0.1)
        def func_with_args(a, b, c=None):
            return mock_func(a, b, c=c)
        
        result = func_with_args(1, 2, c=3)
        
        assert result == "result"
        mock_func.assert_called_once_with(1, 2, c=3)
    
    def test_logging_on_retry(self, caplog):
        """재시도 시 로그 기록 확인"""
        import logging
        
        call_count = 0
        
        @retry_with_backoff(max_retries=2, base_delay=0.1)
        def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError(f"failure #{call_count}")
            return "success"
        
        with caplog.at_level(logging.WARNING):
            result = failing_func()
        
        assert result == "success"
        
        # 재시도 로그 확인
        assert "재시도 1/2" in caplog.text
        assert "재시도 2/2" in caplog.text
        assert "ConnectionError" in caplog.text
    
    def test_logging_on_final_failure(self, caplog):
        """최종 실패 시 에러 로그 확인"""
        import logging
        
        @retry_with_backoff(max_retries=1, base_delay=0.1)
        def always_fail():
            raise TimeoutError("timeout")
        
        with caplog.at_level(logging.ERROR):
            with pytest.raises(TimeoutError):
                always_fail()
        
        # 최종 실패 로그 확인
        assert "재시도 실패" in caplog.text
        assert "1회 재시도 후 실패" in caplog.text
        assert "TimeoutError" in caplog.text


class TestRetryIntegration:
    """실제 네트워크 요청 시나리오 테스트 (Mock 사용)"""
    
    @patch('requests.get')
    def test_network_request_with_retry(self, mock_get):
        """네트워크 요청 실패 후 재시도 성공"""
        import requests
        
        # 처음 2번 실패, 3번째 성공
        mock_get.side_effect = [
            requests.exceptions.Timeout("timeout"),
            requests.exceptions.ConnectionError("connection error"),
            Mock(status_code=200, json=lambda: {"data": "success"})
        ]
        
        @retry_with_backoff(
            max_retries=3,
            base_delay=0.1,
            exceptions=(requests.exceptions.RequestException,)
        )
        def fetch_data():
            response = mock_get("https://api.example.com/data")
            return response.json()
        
        result = fetch_data()
        
        assert result == {"data": "success"}
        assert mock_get.call_count == 3

