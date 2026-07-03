"""
metrics_service 단위 테스트

지표 계산의 단일 정본(metrics_service) 산식 검증.
산식 명세: docs/METRICS_SPEC.md
"""
from app.services import metrics_service


class FakePrice:
    """PriceData 대역 (필요 필드만)"""

    def __init__(self, date, close, chg=0.0):
        self.date = date
        self.close_price = close
        self.daily_change_pct = chg


def desc_prices(closes_desc):
    """최신 → 과거 순 종가 리스트로 FakePrice 목록 생성"""
    return [FakePrice(f"2026-01-{len(closes_desc) - i:02d}", c) for i, c in enumerate(closes_desc)]


class TestPeriodReturn:
    """기간 수익률"""

    def test_basic_return(self):
        # Given: 100 → 110 (desc: [110, 100])
        prices = desc_prices([110, 100])
        # When / Then: (110-100)/100*100 = 10%
        assert metrics_service.period_return(prices) == 10.0

    def test_insufficient_data_returns_zero(self):
        assert metrics_service.period_return(desc_prices([100])) == 0.0
        assert metrics_service.period_return([]) == 0.0


class TestAnnualizedReturn:
    """연환산 수익률 (60거래일 미만은 연환산하지 않음)"""

    def test_short_period_not_annualized(self):
        result = metrics_service.annualized_return(desc_prices([110, 105, 100]))
        assert result["show_annualized"] is False
        assert result["label"] == "3일 수익률"
        assert round(result["value"], 4) == 10.0

    def test_long_period_annualized_compound(self):
        # Given: 100거래일 동안 10% 수익
        closes = [110.0] + [100.0] * 99  # desc: 최신 110, 나머지 100
        result = metrics_service.annualized_return(desc_prices(closes))
        # Then: (1.1)^(365/100) - 1
        expected = ((1.1) ** (365 / 100) - 1) * 100
        assert result["show_annualized"] is True
        assert result["label"] == "연환산 수익률"
        assert abs(result["value"] - expected) < 1e-9


class TestVolatility:
    """변동성 (일간 표준편차, 연환산 ×√252)"""

    def test_constant_price_zero_volatility(self):
        assert metrics_service.daily_volatility(desc_prices([100, 100, 100])) == 0.0

    def test_annualized_is_sqrt252_times_daily(self):
        prices = desc_prices([110, 100, 105, 95])
        daily = metrics_service.daily_volatility(prices)
        annual = metrics_service.annualized_volatility(prices)
        assert abs(annual - daily * (252 ** 0.5)) < 1e-9

    def test_insufficient_data_returns_none(self):
        assert metrics_service.daily_volatility(desc_prices([100])) is None


class TestMaxDrawdown:
    """최대 낙폭 (고점 대비 하락률 최대값)"""

    def test_basic_mdd(self):
        # Given(시간순): 80 → 100 → 120 → 90, desc로 뒤집어 입력
        prices = desc_prices([90, 120, 100, 80])
        mdd = metrics_service.max_drawdown(prices)
        # Then: (120-90)/120 = 25%
        assert mdd["value"] == 25.0
        assert mdd["peak"] == 120
        assert mdd["trough"] == 90

    def test_monotonic_rise_zero_mdd(self):
        mdd = metrics_service.max_drawdown(desc_prices([120, 110, 100]))
        assert mdd["value"] == 0.0


class TestRsiMacd:
    """RSI(Wilder) / MACD(12,26,9)"""

    def test_rsi_all_gains_near_100(self):
        closes = [float(c) for c in range(1, 31)]
        rsi = metrics_service.rsi_series(closes, 14)
        assert len(rsi) == len(closes)
        assert rsi[13] is None  # 앞 period개는 None
        assert rsi[-1] > 95

    def test_rsi_insufficient_data(self):
        assert metrics_service.rsi_series([1.0, 2.0], 14) == []

    def test_macd_structure(self):
        closes = [float(c) for c in range(1, 41)]
        macd = metrics_service.macd_series(closes)
        assert len(macd) == len(closes)
        last = macd[-1]
        assert last["macd"] is not None
        assert last["signal"] is not None
        # 등차수열은 EMA 차이가 수렴 → histogram ≈ 0
        assert abs(last["histogram"]) < 0.5

    def test_macd_insufficient_data(self):
        assert metrics_service.macd_series([1.0] * 10) == []


class TestInsightPoints:
    """InsightsService typed 포인트 생성 (구 frontend insights.js 이식 검증)"""

    def _make_flow(self, foreign, institutional):
        return {"foreign_net": foreign, "institutional_net": institutional}

    def test_consecutive_foreign_buying_point(self):
        from app.services.insights_service import InsightsService
        service = InsightsService()

        flow = [self._make_flow(100, 0) for _ in range(4)]
        points = service._generate_trading_points(flow)
        texts = [p["text"] for p in points]
        assert any("외국인 순매수 4일 연속" in t for t in texts)

    def test_combined_selling_risk(self):
        from app.services.insights_service import InsightsService
        service = InsightsService()

        flow = [self._make_flow(-100, -100) for _ in range(3)]
        risks = service._generate_point_risks([], flow)
        assert "외국인+기관 동반 순매도 3일 연속" in risks

    def test_volatility_point_includes_period(self):
        from app.services.insights_service import InsightsService
        service = InsightsService()

        # 변동성이 큰 가격 시계열 (일간 표준편차 > 3%)
        prices = desc_prices([100, 95, 105, 92, 108, 90, 110])
        points = service._generate_price_points(prices)
        vol_points = [p for p in points if p.get("category") == "volatility"]
        assert vol_points, "변동성 포인트가 생성되어야 함"
        # 표본 기간이 텍스트에 명시되어야 함 (과거 라벨 불일치 사건 방지)
        assert f"최근 {len(prices)}일" in vol_points[0]["text"]

    def test_points_capped_at_four(self):
        from app.services.insights_service import InsightsService
        service = InsightsService()

        prices = desc_prices([100 + (i % 7) * 3 for i in range(50)])
        flow = [self._make_flow(2_000_000_000, 2_000_000_000) for _ in range(5)]
        points = service._generate_points(prices, flow)
        assert len(points) <= 4
        assert all({"type", "category", "text"} <= set(p.keys()) for p in points)
