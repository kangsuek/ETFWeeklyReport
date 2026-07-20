"""
Tests for scanner YTD base-price caching (S2).

_fetch_supply_data가 저장된 올해 YTD 기준가가 있으면 1월까지 딥 페이징하지 않고
2페이지 이내로만 수집하는지, YTD 수익률을 캐시로 계산하는지 검증한다.
"""

from datetime import date
from unittest.mock import patch, MagicMock

from app.services.catalog_data_collector import CatalogDataCollector


def _make_page_html(rows):
    """frgn.naver 형태의 2번째 table.type2 페이지 HTML 생성.

    rows: [(date_str, close), ...] — 각 행은 cols[0]=날짜, cols[1]=종가,
    cols[5]=기관, cols[6]=외국인 (len>=7).
    """
    tr = []
    for d, close in rows:
        tr.append(
            f"<tr><td>{d}</td><td>{close:,}</td><td>0</td><td>0</td>"
            f"<td>0</td><td>100</td><td>200</td></tr>"
        )
    body = "".join(tr)
    # 첫 type2 테이블은 무시되고 두 번째가 데이터 테이블
    return (
        "<table class='type2'><tr><td>header</td></tr></table>"
        f"<table class='type2'>{body}</table>"
    )


def _resp(html):
    r = MagicMock()
    r.text = html
    r.raise_for_status = MagicMock()
    return r


def test_cached_ytd_stops_after_one_page():
    """올해 기준가 캐시가 있으면 20행(=1페이지) 확보 후 즉시 종료하고 캐시로 YTD 계산."""
    year = date.today().year
    # 페이지1: 20행 (전부 최근월, 1월 데이터 없음) — 캐시 경로는 여기서 종료
    page1 = [(f"{year}.07.{20 - i:02d}", 10000 - i * 10) for i in range(20)]
    pages = {1: _make_page_html(page1)}
    calls = []

    def fake_get(url, **kwargs):
        page = int(url.split("page=")[1])
        calls.append(page)
        return _resp(pages.get(page, _make_page_html([])))

    c = CatalogDataCollector()
    cached = {"date": f"{year}.01.02", "price": 9000.0}
    with patch("app.services.catalog_data_collector.requests.get", side_effect=fake_get):
        result = c._fetch_supply_data("005930", use_rate_limiter=False, cached_ytd_base=cached)

    assert calls == [1], f"캐시 경로는 1페이지만 수집해야 함, got {calls}"
    assert result is not None
    assert result["ytd_base_price"] == 9000.0
    assert result["ytd_base_date"] == f"{year}.01.02"
    # YTD = (현재가 10000 - 9000) / 9000 * 100
    assert result["ytd_return"] == round((10000 - 9000) / 9000 * 100, 2)


def test_no_cache_deep_paginates_to_january():
    """캐시가 없으면 1월 첫 거래일 도달까지 페이지를 더 수집하고 기준가를 산출한다."""
    year = date.today().year
    page1 = [(f"{year}.07.{20 - i:02d}", 10000 - i * 10) for i in range(20)]
    # 페이지2: 1월 데이터 포함 → _has_ytd_base 충족 → 종료
    page2 = [(f"{year}.01.{15 - i:02d}", 8000 + i * 5) for i in range(14)]
    pages = {1: _make_page_html(page1), 2: _make_page_html(page2)}
    calls = []

    def fake_get(url, **kwargs):
        page = int(url.split("page=")[1])
        calls.append(page)
        return _resp(pages.get(page, _make_page_html([])))

    c = CatalogDataCollector()
    with patch("app.services.catalog_data_collector.requests.get", side_effect=fake_get):
        result = c._fetch_supply_data("005930", use_rate_limiter=False, cached_ytd_base=None)

    assert calls == [1, 2], f"캐시 없으면 1월 도달까지 딥 페이징해야 함, got {calls}"
    assert result is not None
    # 1월 가장 오래된 행이 기준: page2 마지막 행 date=year.01.02, price=8000+13*5=8065
    assert result["ytd_base_date"] == f"{year}.01.02"
    assert result["ytd_base_price"] == 8065.0


def test_stale_year_cache_is_ignored():
    """작년 기준가 캐시는 무효 → 딥 페이징으로 올해 기준가 재확보."""
    year = date.today().year
    page1 = [(f"{year}.07.{20 - i:02d}", 10000 - i * 10) for i in range(20)]
    page2 = [(f"{year}.01.{15 - i:02d}", 8000 + i * 5) for i in range(14)]
    pages = {1: _make_page_html(page1), 2: _make_page_html(page2)}
    calls = []

    def fake_get(url, **kwargs):
        page = int(url.split("page=")[1])
        calls.append(page)
        return _resp(pages.get(page, _make_page_html([])))

    c = CatalogDataCollector()
    last_year_cache = {"date": f"{year - 1}.01.03", "price": 5000.0}
    with patch("app.services.catalog_data_collector.requests.get", side_effect=fake_get):
        result = c._fetch_supply_data("005930", use_rate_limiter=False, cached_ytd_base=last_year_cache)

    assert calls == [1, 2], "작년 캐시는 무시하고 딥 페이징해야 함"
    assert result["ytd_base_date"] == f"{year}.01.02"
    assert result["ytd_base_price"] != 5000.0
