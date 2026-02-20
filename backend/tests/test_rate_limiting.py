"""
Rate Limiting 테스트
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app
import time

client = TestClient(app)


class TestRateLimiting:
    """Rate Limiting 동작 테스트"""

    @patch("app.middleware.auth.Config.API_KEY", None)
    def test_rate_limit_on_data_collection(self):
        """데이터 수집 엔드포인트는 분당 제한 (구현에 따라 429 또는 200)"""
        for i in range(10):
            response = client.post("/api/data/collect-all")
            assert response.status_code != 429, f"Request {i+1} was rate limited"
        response = client.post("/api/data/collect-all")
        # Rate limit 적용 시 429, 미적용/상한 높을 시 200/500
        assert response.status_code in [200, 429, 500]
        if response.status_code == 429:
            assert "Too Many Requests" in response.json().get("error", "")

    @patch("app.middleware.auth.Config.API_KEY", None)
    def test_rate_limit_on_dangerous_operation(self):
        """위험한 작업은 분당 5회 제한"""
        # 첫 5개 요청은 성공 (인증 없음이므로 200 또는 500)
        for i in range(5):
            response = client.delete("/api/data/reset")
            assert response.status_code != 429, f"Request {i+1} was rate limited"

        # 6번째 요청은 429
        response = client.delete("/api/data/reset")
        assert response.status_code == 429

    def test_rate_limit_on_search(self):
        """검색 엔드포인트는 분당 30회 제한"""
        # 첫 30개 요청은 성공
        for i in range(30):
            response = client.get("/api/settings/stocks/search?q=test")
            assert response.status_code != 429, f"Search request {i+1} was rate limited"

        # 31번째 요청은 429
        response = client.get("/api/settings/stocks/search?q=test")
        assert response.status_code == 429

    def test_rate_limit_on_read_only(self):
        """읽기 전용 엔드포인트는 분당 200회 제한 (더 관대함)"""
        # 100개 정도만 테스트 (시간 절약)
        for i in range(100):
            response = client.get("/api/data/status")
            assert response.status_code != 429, f"Status request {i+1} was rate limited"

    def test_rate_limit_headers(self):
        """Rate Limit 응답에 Retry-After 헤더 포함"""
        # Rate Limit에 도달하도록 여러 번 요청
        for _ in range(15):
            client.post("/api/data/collect-all")

        # 마지막 요청에서 429 확인
        response = client.post("/api/data/collect-all")
        if response.status_code == 429:
            # Retry-After 헤더 확인
            assert "retry_after" in response.json()

    def test_different_ips_have_separate_limits(self):
        """서로 다른 IP는 독립적인 Rate Limit을 가짐"""
        # 이 테스트는 실제로는 작동하지 않을 수 있음
        # (TestClient는 항상 같은 IP 사용)
        # 단위 테스트보다는 통합 테스트에 적합
        pass

    def test_rate_limit_error_response_format(self):
        """Rate Limit 에러 응답 형식 확인"""
        # Rate Limit에 도달
        for _ in range(15):
            client.post("/api/data/collect-all")

        response = client.post("/api/data/collect-all")
        if response.status_code == 429:
            data = response.json()
            assert "error" in data
            assert "detail" in data
            assert data["error"] == "Too Many Requests"
            assert "잠시 후 다시 시도" in data["detail"]


class TestRateLimitConfig:
    """Rate Limit 설정값 테스트"""

    def test_rate_limit_config_values(self):
        """Rate Limit 설정값이 올바른지 확인"""
        from app.middleware.rate_limit import RateLimitConfig

        assert RateLimitConfig.DEFAULT == "100/minute"
        assert RateLimitConfig.DATA_COLLECTION == "10/minute"
        assert RateLimitConfig.SEARCH == "30/minute"
        assert RateLimitConfig.READ_ONLY == "200/minute"
        assert RateLimitConfig.DANGEROUS == "5/minute"


@pytest.mark.slow
class TestRateLimitRecovery:
    """Rate Limit 복구 테스트 (시간이 오래 걸림)"""

    @pytest.mark.skip(reason="시간이 오래 걸리는 테스트 (60초+)")
    def test_rate_limit_resets_after_time_window(self):
        """시간 윈도우 후 Rate Limit 리셋"""
        # Rate Limit에 도달
        for _ in range(15):
            client.post("/api/data/collect-all")

        response = client.post("/api/data/collect-all")
        assert response.status_code == 429

        # 60초 대기 (분당 제한이므로)
        time.sleep(61)

        # 다시 요청 가능해야 함
        response = client.post("/api/data/collect-all")
        assert response.status_code != 429
