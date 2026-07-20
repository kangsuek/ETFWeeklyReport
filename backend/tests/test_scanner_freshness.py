"""
Tests for scanner (catalog data) collection freshness guard (S1).

Covers:
- CatalogDataCollector._last_market_close / _parse_db_timestamp helpers
- CatalogDataCollector.check_freshness (market-hours TTL vs after-close close-guard)
- POST /api/scanner/collect-data force / fresh-skip behavior
"""

from datetime import datetime
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import init_db
from app.services.catalog_data_collector import CatalogDataCollector

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    init_db()
    yield


class TestLastMarketClose:
    """가장 최근 장 마감(확정) 시각 계산 (기준 15:40)."""

    def test_weekday_after_close_returns_today(self):
        # 월요일 16:00 → 오늘 15:40
        assert CatalogDataCollector._last_market_close(
            datetime(2026, 7, 20, 16, 0)
        ) == datetime(2026, 7, 20, 15, 40)

    def test_weekday_during_market_returns_prev_trading_day(self):
        # 월요일 11:00 → 직전 거래일 금요일(7/17) 15:40
        assert CatalogDataCollector._last_market_close(
            datetime(2026, 7, 20, 11, 0)
        ) == datetime(2026, 7, 17, 15, 40)

    def test_sunday_returns_friday(self):
        assert CatalogDataCollector._last_market_close(
            datetime(2026, 7, 19, 12, 0)
        ) == datetime(2026, 7, 17, 15, 40)

    def test_saturday_returns_friday(self):
        assert CatalogDataCollector._last_market_close(
            datetime(2026, 7, 18, 12, 0)
        ) == datetime(2026, 7, 17, 15, 40)


class TestParseDbTimestamp:
    def test_parses_sqlite_string(self):
        assert CatalogDataCollector._parse_db_timestamp(
            "2026-07-20 16:10:00"
        ) == datetime(2026, 7, 20, 16, 10, 0)

    def test_passthrough_datetime(self):
        dt = datetime(2026, 7, 20, 16, 10)
        assert CatalogDataCollector._parse_db_timestamp(dt) == dt

    def test_none_returns_none(self):
        assert CatalogDataCollector._parse_db_timestamp(None) is None


def _patch_max_timestamp(value):
    """check_freshness가 읽는 MAX(catalog_updated_at) 반환값을 목킹."""
    cursor = MagicMock()
    cursor.fetchone.return_value = (value,)
    cursor.cursor.return_value = cursor  # SQLite 경로: conn.cursor()
    ctx = MagicMock()
    ctx.__enter__.return_value = cursor
    ctx.__exit__.return_value = False
    return patch(
        "app.services.catalog_data_collector.get_db_connection",
        return_value=ctx,
    )


class TestCheckFreshness:
    def test_null_is_stale(self):
        c = CatalogDataCollector()
        with _patch_max_timestamp(None):
            result = c.check_freshness()
        assert result == {"fresh": False, "last_updated": None}

    def test_after_close_with_todays_data_is_fresh(self):
        c = CatalogDataCollector()
        # now: 월 17:00(마감후), last_updated: 월 16:10 → 오늘 마감분 확보 → fresh
        with _patch_max_timestamp("2026-07-20 16:10:00"):
            result = c.check_freshness(now=datetime(2026, 7, 20, 17, 0))
        assert result["fresh"] is True

    def test_after_close_with_stale_data_is_stale(self):
        c = CatalogDataCollector()
        # now: 월 17:00, last_updated: 일 18:55(월 마감 이전) → stale
        with _patch_max_timestamp("2026-07-19 18:55:00"):
            result = c.check_freshness(now=datetime(2026, 7, 20, 17, 0))
        assert result["fresh"] is False

    def test_market_hours_within_ttl_is_fresh(self):
        c = CatalogDataCollector()
        # now: 월 11:00(장중), last_updated: 월 10:30(30분 전, TTL 6h 이내) → fresh
        with _patch_max_timestamp("2026-07-20 10:30:00"):
            result = c.check_freshness(now=datetime(2026, 7, 20, 11, 0))
        assert result["fresh"] is True

    def test_market_hours_beyond_ttl_is_stale(self):
        c = CatalogDataCollector()
        # now: 월 15:00(장중), last_updated: 월 03:00(12h 전, TTL 6h 초과) → stale
        with _patch_max_timestamp("2026-07-20 03:00:00"):
            result = c.check_freshness(now=datetime(2026, 7, 20, 15, 0))
        assert result["fresh"] is False


class TestCollectDataEndpoint:
    """POST /api/scanner/collect-data force / fresh-skip."""

    @patch("app.services.catalog_data_collector.CatalogDataCollector.check_freshness")
    def test_fresh_skips_without_background_task(self, mock_fresh):
        mock_fresh.return_value = {"fresh": True, "last_updated": "2026-07-20T16:10:00"}
        response = client.post("/api/scanner/collect-data")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "fresh"
        assert data["skipped"] is True
        assert data["last_updated"] == "2026-07-20T16:10:00"

    @patch("app.services.catalog_data_collector.CatalogDataCollector.collect_all")
    @patch("app.services.catalog_data_collector.CatalogDataCollector.check_freshness")
    def test_force_bypasses_freshness(self, mock_fresh, mock_collect):
        response = client.post("/api/scanner/collect-data?force=true")
        assert response.status_code == 200
        assert response.json()["status"] == "started"
        # force=true면 freshness 확인 자체를 건너뛴다
        mock_fresh.assert_not_called()

    @patch("app.services.catalog_data_collector.CatalogDataCollector.collect_all")
    @patch("app.services.catalog_data_collector.CatalogDataCollector.check_freshness")
    def test_stale_starts_collection(self, mock_fresh, mock_collect):
        mock_fresh.return_value = {"fresh": False, "last_updated": None}
        response = client.post("/api/scanner/collect-data")
        assert response.status_code == 200
        assert response.json()["status"] == "started"
