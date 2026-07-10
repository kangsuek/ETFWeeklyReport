"""
종목 발굴(Scanner) 가격 수집 관련 테스트

- sise_market_sum 파싱: 헤더 기반 컬럼 매핑으로 현재가/등락률/거래량이
  올바른 컬럼에서 추출되는지 검증 (거래량이 상장주식수로 잘못 파싱되던 버그)
- _resolve_week_base: 비상위권 종목의 주간수익률 rolling window 계산 검증
  (기준일 5일 미만일 때 매일 리셋되어 항상 0%가 되던 버그)
"""
from datetime import date
from bs4 import BeautifulSoup

from app.services.ticker_catalog_collector import TickerCatalogCollector
from app.services.catalog_data_collector import CatalogDataCollector


# 네이버 sise_market_sum 기본 레이아웃 재현 (13컬럼)
NAVER_SISE_HTML = """
<table class="type_2">
  <thead>
    <tr>
      <th>N</th><th>종목명</th><th>현재가</th><th>전일비</th><th>등락률</th>
      <th>액면가</th><th>시가총액</th><th>상장주식수</th><th>외국인비율</th>
      <th>거래량</th><th>PER</th><th>ROE</th><th>토론실</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td class="no">1</td>
      <td><a href="/item/main.naver?code=005930">삼성전자</a></td>
      <td class="number">71,200</td>
      <td class="number">1,200</td>
      <td class="number"><span class="red01">+1.71%</span></td>
      <td class="number">100</td>
      <td class="number">4,250,000</td>
      <td class="number">5,969,782,550</td>
      <td class="number">51.31</td>
      <td class="number">12,345,678</td>
      <td class="number">13.11</td>
      <td class="number">6.63</td>
      <td class="center"><a href="/item/board.naver?code=005930">토론실</a></td>
    </tr>
  </tbody>
</table>
"""

# 컬럼 구성이 바뀐 레이아웃 (거래량이 앞쪽으로 이동)
NAVER_SISE_HTML_REORDERED = """
<table class="type_2">
  <thead>
    <tr>
      <th>N</th><th>종목명</th><th>현재가</th><th>전일비</th><th>등락률</th>
      <th>거래량</th><th>시가총액</th><th>PER</th><th>토론실</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td class="no">1</td>
      <td><a href="/item/main.naver?code=000660">SK하이닉스</a></td>
      <td class="number">180,500</td>
      <td class="number">2,500</td>
      <td class="number"><span class="blue01">-1.37%</span></td>
      <td class="number">3,456,789</td>
      <td class="number">1,314,000</td>
      <td class="number">8.42</td>
      <td class="center"><a href="/item/board.naver?code=000660">토론실</a></td>
    </tr>
  </tbody>
</table>
"""


def _get_table_and_cols(html):
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table', {'class': 'type_2'})
    data_row = table.find('tbody').find_all('tr')[0]
    return table, data_row.find_all('td')


class TestSisePriceRowParsing:
    """_parse_sise_price_row 헤더 기반 컬럼 매핑 검증"""

    def test_default_layout_parses_correct_columns(self):
        """기본 레이아웃에서 현재가/등락률/거래량이 올바른 컬럼에서 추출됨"""
        table, cols = _get_table_and_cols(NAVER_SISE_HTML)
        col_map = TickerCatalogCollector._build_sise_col_map(table)
        result = TickerCatalogCollector._parse_sise_price_row(cols, col_map)

        assert result["close_price"] == 71200.0
        assert result["daily_change_pct"] == 1.71
        # 거래량(12,345,678)이어야 하며 상장주식수(5,969,782,550)가 아님
        assert result["volume"] == 12345678

    def test_volume_not_shares_outstanding(self):
        """거래량이 상장주식수 컬럼([7])에서 잘못 파싱되지 않음 (기존 버그)"""
        table, cols = _get_table_and_cols(NAVER_SISE_HTML)
        col_map = TickerCatalogCollector._build_sise_col_map(table)
        result = TickerCatalogCollector._parse_sise_price_row(cols, col_map)

        assert result["volume"] != 5969782550

    def test_reordered_layout_still_correct(self):
        """네이버가 컬럼 구성을 바꿔도 헤더 매핑으로 올바르게 파싱됨"""
        table, cols = _get_table_and_cols(NAVER_SISE_HTML_REORDERED)
        col_map = TickerCatalogCollector._build_sise_col_map(table)
        result = TickerCatalogCollector._parse_sise_price_row(cols, col_map)

        assert result["close_price"] == 180500.0
        assert result["daily_change_pct"] == -1.37
        assert result["volume"] == 3456789

    def test_fallback_without_header(self):
        """헤더 매핑이 없으면 기본 레이아웃 인덱스로 fallback"""
        _, cols = _get_table_and_cols(NAVER_SISE_HTML)
        result = TickerCatalogCollector._parse_sise_price_row(cols, None)

        assert result["close_price"] == 71200.0
        assert result["daily_change_pct"] == 1.71
        assert result["volume"] == 12345678

    def test_zero_price_treated_as_missing(self):
        """현재가 0은 유효하지 않은 값으로 처리 (None)"""
        html = NAVER_SISE_HTML.replace('71,200', '0')
        table, cols = _get_table_and_cols(html)
        col_map = TickerCatalogCollector._build_sise_col_map(table)
        result = TickerCatalogCollector._parse_sise_price_row(cols, col_map)

        assert result["close_price"] is None

    def test_build_col_map(self):
        """헤더 텍스트 → 인덱스 매핑 생성"""
        table, _ = _get_table_and_cols(NAVER_SISE_HTML)
        col_map = TickerCatalogCollector._build_sise_col_map(table)

        assert col_map["현재가"] == 2
        assert col_map["등락률"] == 4
        assert col_map["거래량"] == 9
        assert col_map["상장주식수"] == 7


class TestResolveWeekBase:
    """_resolve_week_base: 5거래일 rolling window 기준가/수익률 결정 검증"""

    def test_no_base_resets_and_preserves_return(self):
        """기준 없음 → 오늘 종가로 기준 설정, 수익률은 None(기존 값 보존)"""
        today = date(2026, 7, 10)
        wr, base_price, base_date = CatalogDataCollector._resolve_week_base(
            10000, None, None, today
        )
        assert wr is None
        assert base_price == 10000
        assert base_date == "2026-07-10"

    def test_young_base_kept_and_return_preserved(self):
        """기준일이 5일 미만 → 기준 유지 + 기존 수익률 보존 (매일 리셋 버그 수정)"""
        today = date(2026, 7, 10)
        wr, base_price, base_date = CatalogDataCollector._resolve_week_base(
            10500, 10000, "2026-07-08", today  # 2일 전
        )
        assert wr is None, "5일 미만이면 수익률을 덮어쓰지 않아야 함"
        assert base_price == 10000, "기준가가 리셋되면 안 됨"
        assert base_date == "2026-07-08", "기준일이 리셋되면 안 됨"

    def test_valid_window_computes_return(self):
        """기준일이 5~9일 전 → 수익률 계산, 기준 유지"""
        today = date(2026, 7, 10)
        wr, base_price, base_date = CatalogDataCollector._resolve_week_base(
            10500, 10000, "2026-07-03", today  # 7일 전
        )
        assert wr == 5.0
        assert base_price == 10000
        assert base_date == "2026-07-03"

    def test_negative_return(self):
        """하락 시 음수 수익률"""
        today = date(2026, 7, 10)
        wr, _, _ = CatalogDataCollector._resolve_week_base(
            9500, 10000, "2026-07-03", today
        )
        assert wr == -5.0

    def test_stale_base_resets(self):
        """기준일이 9일 초과 → 오늘 종가로 기준 재설정, 수익률 보존"""
        today = date(2026, 7, 10)
        wr, base_price, base_date = CatalogDataCollector._resolve_week_base(
            10500, 10000, "2026-06-25", today  # 15일 전
        )
        assert wr is None
        assert base_price == 10500
        assert base_date == "2026-07-10"

    def test_malformed_base_date_resets(self):
        """기준일이 손상된 문자열 → 오늘 종가로 기준 재설정"""
        today = date(2026, 7, 10)
        wr, base_price, base_date = CatalogDataCollector._resolve_week_base(
            10500, 10000, "not-a-date", today
        )
        assert wr is None
        assert base_price == 10500
        assert base_date == "2026-07-10"

    def test_zero_base_price_resets(self):
        """기준가 0 → 오늘 종가로 기준 재설정 (0으로 나누기 방지)"""
        today = date(2026, 7, 10)
        wr, base_price, base_date = CatalogDataCollector._resolve_week_base(
            10500, 0, "2026-07-03", today
        )
        assert wr is None
        assert base_price == 10500
        assert base_date == "2026-07-10"

    def test_daily_collection_reaches_valid_window(self):
        """매일 수집해도 기준일이 유지되어 5일 후 수익률이 계산됨 (버그 수정 검증)"""
        base_price, base_date = None, None
        prices = {0: 10000, 1: 10050, 2: 10100, 3: 10150, 4: 10200, 5: 10500}
        start = date(2026, 7, 6)
        computed = None

        for day_offset, price in prices.items():
            today = date(2026, 7, 6 + day_offset)
            wr, base_price, base_date = CatalogDataCollector._resolve_week_base(
                price, base_price, base_date, today
            )
            if wr is not None:
                computed = wr

        # day 0에 기준 설정(10000) → day 5에 (10500-10000)/10000 = 5.0% 계산
        assert base_date == start.isoformat(), "기준일이 매일 리셋되면 안 됨"
        assert computed == 5.0
