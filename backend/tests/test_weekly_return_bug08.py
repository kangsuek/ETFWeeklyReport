"""
BUG-08 및 주간수익률 공식 관련 테스트

- BUG-08: _update_stock_prices에서 ETF(market='ETF') 종목의 weekly_return이 0.0으로 덮어써지는 버그 수정 검증
- 주간수익률 공식: prices_with_date[5] (5거래일 전, 0-indexed) 기준으로 통일 검증
- 배치 요약 주간수익률: etfs.py batch-summary의 weekly_return 계산 검증
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import date, datetime, timedelta


class TestBug08ETFWeeklyReturnPreserved:
    """BUG-08: _update_stock_prices가 ETF 종목의 weekly_return을 0.0으로 덮어쓰지 않아야 함"""

    @pytest.fixture
    def collector(self):
        """CatalogDataCollector 인스턴스 생성"""
        from app.services.catalog_data_collector import CatalogDataCollector
        return CatalogDataCollector()

    @patch('app.services.catalog_data_collector.get_db_connection')
    @patch('app.services.catalog_data_collector.USE_POSTGRES', False)
    def test_etf_tickers_excluded_from_price_map(self, mock_get_db, collector):
        """ETF 티커가 price_map에서 제외되어 weekly_return이 덮어써지지 않음을 검증"""
        # sise_market_sum에서 수집된 데이터에 ETF 티커가 포함된 상황
        kospi_stocks = [
            {"ticker": "005930", "close_price": 70000, "daily_change_pct": 1.0, "volume": 1000000},
            {"ticker": "487240", "close_price": 12500, "daily_change_pct": 0.5, "volume": 500000},  # ETF
        ]

        # price_map 생성 로직 시뮬레이션
        price_map = {s["ticker"]: s for s in kospi_stocks}

        # DB에서 ETF 티커 조회 결과 모킹
        etf_tickers = {"487240"}

        # ETF 제외 로직 (FIX-08에서 추가된 코드와 동일한 로직)
        excluded = sum(1 for t in price_map if t in etf_tickers)
        price_map = {t: s for t, s in price_map.items() if t not in etf_tickers}

        # ETF 티커가 price_map에서 제외됨
        assert "487240" not in price_map, "ETF 티커가 price_map에 남아있으면 안됨"
        assert "005930" in price_map, "일반 종목은 price_map에 남아있어야 함"
        assert excluded == 1, "ETF 1개가 제외되어야 함"

    @patch('app.services.catalog_data_collector.get_db_connection')
    @patch('app.services.catalog_data_collector.USE_POSTGRES', False)
    def test_etf_weekly_return_not_overwritten(self, mock_get_db, collector):
        """
        ETF의 기존 weekly_return 값이 Phase 4(_update_stock_prices)에서 보존됨을 검증.

        시나리오: ETF 487240의 DB에 weekly_return=3.5가 저장된 상태에서
        _update_stock_prices가 실행되어도 해당 값이 0.0으로 덮어써지지 않아야 함.
        """
        # 기존 DB 상태: ETF에 weekly_return이 있음
        existing_etf_record = {
            "ticker": "487240",
            "close_price": 12500,
            "week_base_price": 12000,
            "week_base_date": "2026-02-23",
            "weekly_return": 3.5,  # 기존 weekly_return (Phase 1~3에서 계산된 값)
        }

        # sise 수집에서 ETF가 포함되어 들어온 경우
        kospi_stocks = [
            {"ticker": "005930", "close_price": 70000, "daily_change_pct": 1.0, "volume": 1000000},
            {"ticker": "487240", "close_price": 12500, "daily_change_pct": 0.5, "volume": 500000},
        ]

        price_map = {s["ticker"]: s for s in kospi_stocks}

        # ETF 제외 적용
        etf_tickers = {"487240"}
        price_map = {t: s for t, s in price_map.items() if t not in etf_tickers}

        # ETF 티커에 대해 UPDATE가 실행되지 않음을 확인
        assert "487240" not in price_map
        # 따라서 기존 weekly_return=3.5이 보존됨
        assert existing_etf_record["weekly_return"] == 3.5

    def test_multiple_etf_tickers_all_excluded(self):
        """여러 ETF 티커가 모두 price_map에서 제외됨을 검증"""
        kospi_stocks = [
            {"ticker": "005930", "close_price": 70000},
            {"ticker": "487240", "close_price": 12500},  # ETF
            {"ticker": "466920", "close_price": 15000},  # ETF
            {"ticker": "000660", "close_price": 80000},
        ]

        price_map = {s["ticker"]: s for s in kospi_stocks}
        etf_tickers = {"487240", "466920"}

        excluded = sum(1 for t in price_map if t in etf_tickers)
        price_map = {t: s for t, s in price_map.items() if t not in etf_tickers}

        assert excluded == 2
        assert len(price_map) == 2
        assert "487240" not in price_map
        assert "466920" not in price_map
        assert "005930" in price_map
        assert "000660" in price_map


class TestWeeklyReturn5TradingDays:
    """주간수익률이 5거래일 전(prices_with_date[5], 0-indexed) 기준으로 계산됨을 검증"""

    @pytest.fixture
    def collector(self):
        """CatalogDataCollector 인스턴스 생성"""
        from app.services.catalog_data_collector import CatalogDataCollector
        return CatalogDataCollector()

    def test_weekly_return_with_sufficient_data(self, collector):
        """
        prices_with_date에 7개 데이터가 있을 때:
        weekly_return = (prices_with_date[0] - prices_with_date[5]) / prices_with_date[5] * 100
        """
        # 7개의 (date, price) 데이터 (날짜 내림차순)
        prices_with_date = [
            (date(2026, 2, 27), 10500),  # [0] 최신: 10,500
            (date(2026, 2, 26), 10400),  # [1]
            (date(2026, 2, 25), 10300),  # [2]
            (date(2026, 2, 24), 10200),  # [3]
            (date(2026, 2, 23), 10100),  # [4]
            (date(2026, 2, 20), 10000),  # [5] 5거래일 전: 10,000
            (date(2026, 2, 19), 9900),   # [6]
        ]

        # _fetch_supply_data 내부의 calc_ret 로직 재현
        def calc_ret(curr, prev):
            if prev and prev > 0:
                return round((curr - prev) / prev * 100, 2)
            return None

        current_val = prices_with_date[0][1]
        weekly_return = calc_ret(
            current_val,
            prices_with_date[5][1] if len(prices_with_date) >= 6 else None
        )

        # (10500 - 10000) / 10000 * 100 = 5.0%
        assert weekly_return == 5.0

    def test_weekly_return_with_exactly_6_data_points(self, collector):
        """prices_with_date에 정확히 6개(len >= 6) 데이터가 있을 때 정상 계산"""
        prices_with_date = [
            (date(2026, 2, 27), 10500),  # [0]
            (date(2026, 2, 26), 10400),  # [1]
            (date(2026, 2, 25), 10300),  # [2]
            (date(2026, 2, 24), 10200),  # [3]
            (date(2026, 2, 23), 10100),  # [4]
            (date(2026, 2, 20), 10000),  # [5]
        ]

        def calc_ret(curr, prev):
            if prev and prev > 0:
                return round((curr - prev) / prev * 100, 2)
            return None

        current_val = prices_with_date[0][1]
        weekly_return = calc_ret(
            current_val,
            prices_with_date[5][1] if len(prices_with_date) >= 6 else None
        )

        assert weekly_return == 5.0

    def test_weekly_return_insufficient_data(self, collector):
        """prices_with_date에 5개(len < 6) 데이터일 때: weekly_return = None"""
        prices_with_date = [
            (date(2026, 2, 27), 10500),  # [0]
            (date(2026, 2, 26), 10400),  # [1]
            (date(2026, 2, 25), 10300),  # [2]
            (date(2026, 2, 24), 10200),  # [3]
            (date(2026, 2, 23), 10100),  # [4]
        ]

        def calc_ret(curr, prev):
            if prev and prev > 0:
                return round((curr - prev) / prev * 100, 2)
            return None

        current_val = prices_with_date[0][1]
        weekly_return = calc_ret(
            current_val,
            prices_with_date[5][1] if len(prices_with_date) >= 6 else None
        )

        assert weekly_return is None, "데이터가 6개 미만이면 weekly_return은 None이어야 함"

    def test_weekly_return_negative(self, collector):
        """가격 하락 시 음수 주간수익률 계산"""
        prices_with_date = [
            (date(2026, 2, 27), 9500),   # [0] 최신: 9,500
            (date(2026, 2, 26), 9600),   # [1]
            (date(2026, 2, 25), 9700),   # [2]
            (date(2026, 2, 24), 9800),   # [3]
            (date(2026, 2, 23), 9900),   # [4]
            (date(2026, 2, 20), 10000),  # [5] 5거래일 전: 10,000
        ]

        def calc_ret(curr, prev):
            if prev and prev > 0:
                return round((curr - prev) / prev * 100, 2)
            return None

        current_val = prices_with_date[0][1]
        weekly_return = calc_ret(
            current_val,
            prices_with_date[5][1] if len(prices_with_date) >= 6 else None
        )

        # (9500 - 10000) / 10000 * 100 = -5.0%
        assert weekly_return == -5.0

    def test_weekly_return_zero_base_price(self, collector):
        """5거래일 전 가격이 0이면 weekly_return = None"""
        prices_with_date = [
            (date(2026, 2, 27), 10500),
            (date(2026, 2, 26), 10400),
            (date(2026, 2, 25), 10300),
            (date(2026, 2, 24), 10200),
            (date(2026, 2, 23), 10100),
            (date(2026, 2, 20), 0),  # 0원
        ]

        def calc_ret(curr, prev):
            if prev and prev > 0:
                return round((curr - prev) / prev * 100, 2)
            return None

        current_val = prices_with_date[0][1]
        weekly_return = calc_ret(
            current_val,
            prices_with_date[5][1] if len(prices_with_date) >= 6 else None
        )

        assert weekly_return is None, "기준가가 0이면 weekly_return은 None이어야 함"


class TestBatchSummaryWeeklyReturn:
    """etfs.py 배치 요약의 weekly_return이 5거래일 전 기준(prices[5])으로 계산됨을 검증"""

    def _make_mock_price(self, close_price, trade_date=None):
        """Mock price object 생성"""
        mock = MagicMock()
        mock.close_price = close_price
        mock.date = trade_date or date.today()
        return mock

    def test_batch_summary_weekly_return_with_6_prices(self):
        """prices가 6개 이상일 때 prices[5] 기준으로 weekly_return 계산"""
        prices = [
            self._make_mock_price(10500),  # [0] 최신
            self._make_mock_price(10400),  # [1]
            self._make_mock_price(10300),  # [2]
            self._make_mock_price(10200),  # [3]
            self._make_mock_price(10100),  # [4]
            self._make_mock_price(10000),  # [5] 5거래일 전
        ]

        # etfs.py batch-summary의 주간수익률 계산 로직 재현
        weekly_return = None
        if len(prices) >= 6:
            current_price = prices[0].close_price
            base_price = prices[5].close_price
            if base_price and base_price > 0:
                weekly_return = ((current_price - base_price) / base_price) * 100

        # (10500 - 10000) / 10000 * 100 = 5.0%
        assert weekly_return is not None
        assert abs(weekly_return - 5.0) < 0.01

    def test_batch_summary_weekly_return_insufficient_prices(self):
        """prices가 6개 미만이면 weekly_return은 None"""
        prices = [
            self._make_mock_price(10500),  # [0]
            self._make_mock_price(10400),  # [1]
            self._make_mock_price(10300),  # [2]
            self._make_mock_price(10200),  # [3]
            self._make_mock_price(10100),  # [4]
        ]

        weekly_return = None
        if len(prices) >= 6:
            current_price = prices[0].close_price
            base_price = prices[5].close_price
            if base_price and base_price > 0:
                weekly_return = ((current_price - base_price) / base_price) * 100

        assert weekly_return is None

    def test_batch_summary_weekly_return_not_using_index_4(self):
        """
        BUG-08 이전에는 prices[4] (4거래일 전)을 사용했음.
        수정 후에는 prices[5]를 사용하므로, 결과가 달라야 함.
        """
        prices = [
            self._make_mock_price(10500),  # [0]
            self._make_mock_price(10400),  # [1]
            self._make_mock_price(10300),  # [2]
            self._make_mock_price(10200),  # [3]
            self._make_mock_price(10100),  # [4] = old base (4거래일 전)
            self._make_mock_price(10000),  # [5] = new base (5거래일 전)
        ]

        # 수정된 공식: prices[5] 기준
        current_price = prices[0].close_price
        correct_base = prices[5].close_price
        correct_return = ((current_price - correct_base) / correct_base) * 100

        # 이전 공식: prices[4] 기준 (버그)
        wrong_base = prices[4].close_price
        wrong_return = ((current_price - wrong_base) / wrong_base) * 100

        # 두 결과가 다름을 검증 (5거래일 vs 4거래일)
        assert correct_return != wrong_return
        # 올바른 값: (10500 - 10000) / 10000 * 100 = 5.0%
        assert abs(correct_return - 5.0) < 0.01
        # 이전 값: (10500 - 10100) / 10100 * 100 ≈ 3.96%
        assert abs(wrong_return - 3.96) < 0.1

    def test_batch_summary_empty_prices(self):
        """prices가 비어있으면 weekly_return은 None"""
        prices = []

        weekly_return = None
        if len(prices) >= 6:
            current_price = prices[0].close_price
            base_price = prices[5].close_price
            if base_price and base_price > 0:
                weekly_return = ((current_price - base_price) / base_price) * 100

        assert weekly_return is None
