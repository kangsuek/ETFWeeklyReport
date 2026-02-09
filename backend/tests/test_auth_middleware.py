"""
API 인증 미들웨어 테스트
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app

client = TestClient(app)


class TestAPIKeyAuth:
    """API Key 인증 테스트"""

    def test_public_endpoint_no_auth(self):
        """공개 엔드포인트는 인증 불필요"""
        response = client.get("/api/health")
        assert response.status_code == 200

    def test_get_etfs_no_auth(self):
        """GET /api/etfs는 공개 (인증 불필요)"""
        response = client.get("/api/etfs")
        assert response.status_code == 200

    def test_get_etf_detail_no_auth(self):
        """GET /api/etfs/{ticker}는 공개 (인증 불필요)"""
        response = client.get("/api/etfs/487240")
        assert response.status_code in [200, 404]  # 티커가 있으면 200, 없으면 404

    @patch("app.middleware.auth.Config.API_KEY", "test-api-key-12345")
    def test_protected_endpoint_without_api_key(self):
        """보호된 엔드포인트는 API Key 없으면 401"""
        response = client.delete("/api/data/reset")
        assert response.status_code == 401
        assert "API Key" in response.json()["detail"]

    @patch("app.middleware.auth.Config.API_KEY", "test-api-key-12345")
    def test_protected_endpoint_with_invalid_api_key(self):
        """잘못된 API Key로는 접근 불가"""
        headers = {"X-API-Key": "wrong-api-key"}
        response = client.delete("/api/data/reset", headers=headers)
        assert response.status_code == 401
        assert "잘못된 API Key" in response.json()["detail"]

    @patch("app.middleware.auth.Config.API_KEY", "test-api-key-12345")
    def test_protected_endpoint_with_valid_api_key(self):
        """올바른 API Key로는 접근 가능"""
        headers = {"X-API-Key": "test-api-key-12345"}
        response = client.delete("/api/data/reset", headers=headers)
        # 인증은 통과, DB 처리 결과는 상관없음 (200 또는 500)
        assert response.status_code in [200, 500]

    @patch("app.middleware.auth.Config.API_KEY", "test-api-key-12345")
    def test_post_collect_all_without_api_key(self):
        """POST /api/data/collect-all은 API Key 필요"""
        response = client.post("/api/data/collect-all")
        assert response.status_code == 401

    @patch("app.middleware.auth.Config.API_KEY", "test-api-key-12345")
    def test_post_collect_all_with_valid_api_key(self):
        """올바른 API Key로 데이터 수집 가능"""
        headers = {"X-API-Key": "test-api-key-12345"}
        response = client.post("/api/data/collect-all", headers=headers)
        assert response.status_code in [200, 500]  # 인증 통과

    @patch("app.middleware.auth.Config.API_KEY", "test-api-key-12345")
    def test_post_backfill_without_api_key(self):
        """POST /api/data/backfill은 API Key 필요"""
        response = client.post("/api/data/backfill")
        assert response.status_code == 401

    @patch("app.middleware.auth.Config.API_KEY", "test-api-key-12345")
    def test_post_stock_create_without_api_key(self):
        """POST /api/settings/stocks는 API Key 필요"""
        stock_data = {
            "ticker": "005930",
            "name": "삼성전자",
            "type": "STOCK",
            "theme": "반도체"
        }
        response = client.post("/api/settings/stocks", json=stock_data)
        assert response.status_code == 401

    @patch("app.middleware.auth.Config.API_KEY", "test-api-key-12345")
    def test_put_stock_update_without_api_key(self):
        """PUT /api/settings/stocks/{ticker}는 API Key 필요"""
        update_data = {"name": "삼성전자 업데이트"}
        response = client.put("/api/settings/stocks/005930", json=update_data)
        assert response.status_code == 401

    @patch("app.middleware.auth.Config.API_KEY", "test-api-key-12345")
    def test_delete_stock_without_api_key(self):
        """DELETE /api/settings/stocks/{ticker}는 API Key 필요"""
        response = client.delete("/api/settings/stocks/005930")
        assert response.status_code == 401

    @patch("app.middleware.auth.Config.API_KEY", None)
    def test_no_api_key_configured_allows_all(self):
        """API_KEY 미설정 시 모든 요청 허용 (개발 모드)"""
        # API Key가 설정되지 않으면 모든 요청 허용
        response = client.delete("/api/data/reset")
        assert response.status_code in [200, 500]  # 인증 통과 (DB 처리만)

    @patch("app.middleware.auth.Config.API_KEY", "test-api-key-12345")
    def test_post_ticker_catalog_collect_without_api_key(self):
        """POST /api/settings/ticker-catalog/collect는 API Key 필요"""
        response = client.post("/api/settings/ticker-catalog/collect")
        assert response.status_code == 401

    @patch("app.middleware.auth.Config.API_KEY", "test-api-key-12345")
    def test_post_etf_collect_without_api_key(self):
        """POST /api/etfs/{ticker}/collect는 API Key 필요"""
        response = client.post("/api/etfs/487240/collect")
        assert response.status_code == 401

    @patch("app.middleware.auth.Config.API_KEY", "test-api-key-12345")
    def test_post_trading_flow_collect_without_api_key(self):
        """POST /api/etfs/{ticker}/collect-trading-flow는 API Key 필요"""
        response = client.post("/api/etfs/487240/collect-trading-flow")
        assert response.status_code == 401

    @patch("app.middleware.auth.Config.API_KEY", "test-api-key-12345")
    def test_post_news_collect_without_api_key(self):
        """POST /api/news/{ticker}/collect는 API Key 필요"""
        response = client.post("/api/news/487240/collect")
        assert response.status_code == 401


class TestAuthMiddleware:
    """인증 미들웨어 동작 테스트"""

    def test_is_public_endpoint(self):
        """공개 엔드포인트 판별"""
        from app.middleware.auth import APIKeyAuth

        # 정확히 일치하는 공개 엔드포인트
        assert APIKeyAuth.is_public_endpoint("/", "GET") is True
        assert APIKeyAuth.is_public_endpoint("/api/health", "GET") is True
        assert APIKeyAuth.is_public_endpoint("/docs", "GET") is True

        # GET 요청은 대부분 공개
        assert APIKeyAuth.is_public_endpoint("/api/etfs", "GET") is True
        assert APIKeyAuth.is_public_endpoint("/api/etfs/487240", "GET") is True
        assert APIKeyAuth.is_public_endpoint("/api/news/487240", "GET") is True

        # POST/DELETE는 보호
        assert APIKeyAuth.is_public_endpoint("/api/data/reset", "DELETE") is False
        assert APIKeyAuth.is_public_endpoint("/api/data/collect-all", "POST") is False
        assert APIKeyAuth.is_public_endpoint("/api/settings/stocks", "POST") is False

    def test_verify_api_key(self):
        """API Key 검증 로직"""
        from app.middleware.auth import APIKeyAuth

        with patch("app.middleware.auth.Config.API_KEY", "test-key-123"):
            # 올바른 API Key
            assert APIKeyAuth.verify_api_key("test-key-123") is True

            # 잘못된 API Key
            assert APIKeyAuth.verify_api_key("wrong-key") is False
            assert APIKeyAuth.verify_api_key(None) is False
            assert APIKeyAuth.verify_api_key("") is False

        # API_KEY 미설정 시 보안 강화로 모든 요청 거부 (verify_api_key 기준)
        with patch("app.middleware.auth.Config.API_KEY", None):
            assert APIKeyAuth.verify_api_key("any-key") is False
            assert APIKeyAuth.verify_api_key(None) is False
