"""
Tests for sise_market_sum crawl sharing between collectors (D1/S4).

종목목록 수집(_collect_sise_stocks)과 스캐너 Phase4가 동일 메서드를 호출하므로,
프로세스 레벨 TTL 캐시로 190페이지 중복 크롤을 제거한다.
"""

from unittest.mock import patch, MagicMock

import pytest

import app.services.ticker_catalog_collector as tc_mod
from app.services.ticker_catalog_collector import TickerCatalogCollector


@pytest.fixture(autouse=True)
def clear_sise_cache():
    tc_mod._sise_cache.clear()
    yield
    tc_mod._sise_cache.clear()


def _sise_page_html(rows):
    """sise_market_sum 페이지 HTML (table.type_2, 행당 >=10 td + item 링크)."""
    tr = []
    for ticker, name, close in rows:
        tds = (
            f"<td>1</td>"
            f"<td><a href='/item/main.naver?code={ticker}'>{name}</a></td>"
            f"<td>{close:,}</td>"
            + "".join(f"<td>{i}</td>" for i in range(8))
        )
        tr.append(f"<tr>{tds}</tr>")
    return f"<table class='type_2'>{''.join(tr)}</table>"


def _resp(html):
    r = MagicMock()
    r.text = html
    r.raise_for_status = MagicMock()
    return r


def _make_fake_get(calls):
    page1 = _sise_page_html([("005930", "삼성전자", 70000), ("000660", "SK하이닉스", 190000)])
    empty = _sise_page_html([])

    def fake_get(url, **kwargs):
        page = int(url.split("page=")[1].split("&")[0])
        calls.append(page)
        return _resp(page1 if page == 1 else empty)

    return fake_get


def test_fresh_crawl_populates_cache_and_use_cache_reuses():
    c = TickerCatalogCollector()
    calls = []
    with patch("app.services.ticker_catalog_collector.requests.get", side_effect=_make_fake_get(calls)):
        # 1) 종목목록 수집 경로: use_cache=False → 실제 크롤 + 캐시 저장
        first = c._collect_sise_stocks(sosok=0, market="KOSPI", max_pages=5)
        crawl_calls = len(calls)
        # 2) 스캐너 Phase4 경로: use_cache=True → 재크롤 없이 캐시 재사용
        second = c._collect_sise_stocks(sosok=0, market="KOSPI", max_pages=5, use_cache=True)
        assert len(calls) == crawl_calls, "캐시 재사용 시 추가 크롤이 없어야 함"

    assert len(first) == 2 and first[0]["ticker"] == "005930"
    assert [s["ticker"] for s in second] == [s["ticker"] for s in first]


def test_use_cache_miss_crawls():
    c = TickerCatalogCollector()
    calls = []
    with patch("app.services.ticker_catalog_collector.requests.get", side_effect=_make_fake_get(calls)):
        # 캐시 비어 있음 → use_cache=True여도 크롤 발생
        result = c._collect_sise_stocks(sosok=1, market="KOSDAQ", max_pages=5, use_cache=True)
    assert len(calls) > 0
    assert len(result) == 2


def test_cache_reuse_returns_isolated_copy():
    c = TickerCatalogCollector()
    calls = []
    with patch("app.services.ticker_catalog_collector.requests.get", side_effect=_make_fake_get(calls)):
        c._collect_sise_stocks(sosok=0, market="KOSPI", max_pages=5)
        reused = c._collect_sise_stocks(sosok=0, market="KOSPI", max_pages=5, use_cache=True)
    # 재사용본을 변형해도 캐시 원본에 영향 없어야 함
    reused[0]["close_price"] = -1
    again = c._collect_sise_stocks(sosok=0, market="KOSPI", max_pages=5, use_cache=True)
    assert again[0]["close_price"] == 70000


def test_expired_cache_recrawls():
    from datetime import datetime, timedelta
    c = TickerCatalogCollector()
    calls = []
    with patch("app.services.ticker_catalog_collector.requests.get", side_effect=_make_fake_get(calls)):
        c._collect_sise_stocks(sosok=0, market="KOSPI", max_pages=5)
        # 캐시 타임스탬프를 TTL 밖으로 이동
        ts, data = tc_mod._sise_cache[(0, "KOSPI")]
        tc_mod._sise_cache[(0, "KOSPI")] = (datetime.now() - timedelta(minutes=999), data)
        before = len(calls)
        c._collect_sise_stocks(sosok=0, market="KOSPI", max_pages=5, use_cache=True)
        assert len(calls) > before, "만료된 캐시는 재크롤해야 함"
