"""상승흐름 신호 판정 순수 함수 테스트 (signal_detector, Phase 2.2)

합성 가격/수급 시리즈로 detect_breakout(B1~B6)과 update_pending(C1/C2/
failed/expired)의 각 분기를 경계값 포함해 검증한다. Given-When-Then.
"""
from datetime import date, timedelta

import pytest

from app.services.signal_detector import (
    PriceBar,
    BreakoutSignal,
    detect_breakout,
    update_pending,
)

BASE = date(2026, 1, 5)


def _bar(i, o, h, low, c, v):
    return PriceBar(date=BASE + timedelta(days=i), open=o, high=h, low=low, close=c, volume=v)


def _base_flat(n=30, price=100.0, vol=1000):
    """price 고정·거래량 vol 고정의 평탄한 n일 (고가=저가=종가=price)."""
    return [
        PriceBar(date=BASE + timedelta(days=i), open=price, high=price,
                 low=price, close=price, volume=vol)
        for i in range(n)
    ]


def _pos_flows(prices, net=500):
    """모든 날짜에 양(+)의 수급을 부여."""
    return {b.date: net for b in prices}


class TestDetectBreakout:
    """LV1 돌파 포착 (§2-2 B1~B6)"""

    def test_valid_breakout(self):
        """Given 모든 조건 충족 When 판정 Then BreakoutSignal 반환"""
        prices = _base_flat(30) + [_bar(30, 101, 105, 101, 104.5, 2500)]
        flows = _pos_flows(prices)

        sig = detect_breakout(prices, flows, 30)

        assert sig is not None
        assert sig.breakout_level == pytest.approx(100.0)
        assert sig.volume_ratio == pytest.approx(2.5)
        assert sig.candle_pos == pytest.approx(0.875)
        assert sig.flow_net_3d == 1500  # 3일 × 500
        assert sig.breakout_date == prices[30].date

    def test_b1_close_not_above_level(self):
        """Given 종가가 돌파선 이하 When 판정 Then None"""
        prices = _base_flat(30) + [_bar(30, 100, 100, 100, 100, 2500)]
        assert detect_breakout(prices, _pos_flows(prices), 30) is None

    def test_b2_volume_below_multiple(self):
        """Given 거래량 배수 < 2.0 When 판정 Then None"""
        prices = _base_flat(30) + [_bar(30, 101, 105, 101, 104.5, 1500)]
        assert detect_breakout(prices, _pos_flows(prices), 30) is None

    def test_b2_volume_boundary_ok(self):
        """Given 거래량 배수 정확히 2.0 When 판정 Then 통과(경계 포함)"""
        prices = _base_flat(30) + [_bar(30, 101, 105, 101, 104.5, 2000)]
        assert detect_breakout(prices, _pos_flows(prices), 30) is not None

    def test_b3_weak_candle_upper_wick(self):
        """Given 위꼬리 긴 약한 캔들(위치<0.6) When 판정 Then None"""
        # candle_pos = (101-100)/(110-100) = 0.1
        prices = _base_flat(30) + [_bar(30, 100, 110, 100, 101, 2500)]
        assert detect_breakout(prices, _pos_flows(prices), 30) is None

    def test_b4_negative_supply(self):
        """Given 당일·3일 누적 수급 모두 음수 When 판정 Then None"""
        prices = _base_flat(30) + [_bar(30, 101, 105, 101, 104.5, 2500)]
        flows = {b.date: -300 for b in prices}
        assert detect_breakout(prices, flows, 30) is None

    def test_b4_missing_supply_holds(self):
        """Given 최근 3일 수급 데이터 결측 When 판정 Then None(판정 보류)"""
        prices = _base_flat(30) + [_bar(30, 101, 105, 101, 104.5, 2500)]
        # 최근 3일(28,29,30) 수급 제거
        flows = {b.date: 500 for b in prices[:28]}
        assert detect_breakout(prices, flows, 30) is None

    def test_b4_today_negative_but_3d_positive(self):
        """Given 당일 수급 음수지만 3일 누적 양수 When 판정 Then 통과"""
        prices = _base_flat(30) + [_bar(30, 101, 105, 101, 104.5, 2500)]
        flows = {b.date: 500 for b in prices}
        flows[prices[30].date] = -100  # 당일 음수, 3일 누적 = 500+500-100 = 900 > 0
        assert detect_breakout(prices, flows, 30) is not None

    def test_b5_overheat_excluded(self):
        """Given 5일 수익률 ≥ 25% When 판정 Then None(과열)"""
        # prices[25].close=100, today close=130 → +30%
        prices = _base_flat(30) + [_bar(30, 126, 131, 126, 130, 2500)]
        assert detect_breakout(prices, _pos_flows(prices), 30) is None

    def test_b5_below_overheat_ok(self):
        """Given 5일 수익률 < 25% When 판정 Then 통과"""
        # today close=120 → +20%
        prices = _base_flat(30) + [_bar(30, 116, 121, 116, 120, 2500)]
        assert detect_breakout(prices, _pos_flows(prices), 30) is not None

    def test_b6_insufficient_history(self):
        """Given 이력 < MIN_DATA_DAYS(30) When 판정 Then None"""
        prices = _base_flat(24) + [_bar(24, 101, 105, 101, 104.5, 2500)]
        assert detect_breakout(prices, _pos_flows(prices), 24) is None

    def test_b6_insufficient_lookback(self):
        """Given 룩백 20행 미확보(as_of_idx<20) When 판정 Then None"""
        prices = _base_flat(15) + [_bar(15, 101, 105, 101, 104.5, 2500)]
        assert detect_breakout(prices, _pos_flows(prices), 15) is None


class TestUpdatePending:
    """LV2 확정/실패/만료 상태 전이 (§2-3, §2-4)"""

    def _event(self, prices, level=100.0):
        return BreakoutSignal(
            breakout_date=prices[30].date, breakout_level=level,
            volume_ratio=2.5, candle_pos=0.9, flow_net_3d=1500,
        )

    def _with_forward(self, forward_bars):
        """돌파일(idx30, close 104) + 이후 봉들로 구성된 시리즈·flows 생성."""
        prices = _base_flat(30) + [_bar(30, 101, 105, 101, 104.0, 2500)]
        prices += forward_bars
        return prices, _pos_flows(prices)

    # 저가를 재시험 밴드(±2%=98~102) 밖으로 두어 C1이 아닌 C2(연속 유지) 경로를 격리
    _HOLD_FWD = [_bar(31, 103, 104, 102.5, 103.0, 1200),
                 _bar(32, 103, 104, 102.5, 103.0, 1200)]

    def test_c2_hold_confirmed(self):
        """Given 돌파일 포함 3일 연속 종가>돌파선(밴드 밖) When 판정 Then confirmed/hold"""
        prices, flows = self._with_forward(list(self._HOLD_FWD))
        status, path = update_pending(self._event(prices), prices, flows, 32)
        assert (status, path) == ("confirmed", "hold")

    def test_c2_not_confirmed_before_hold_completes(self):
        """Given 아직 HOLD_DAYS 미완 When as_of_idx=31 판정 Then pending(미래 미참조)"""
        prices, flows = self._with_forward(list(self._HOLD_FWD))
        assert update_pending(self._event(prices), prices, flows, 31) == ("pending", None)

    def test_c1_retest_confirmed(self):
        """Given 되돌림 접근 후 재마감>돌파선 When 판정 Then confirmed/retest"""
        # day31 밴드 접근(low98.5) 종가99(<level), day32 종가101 재마감
        fwd = [_bar(31, 100, 100.5, 98.5, 99.0, 1000),
               _bar(32, 99, 101.5, 99, 101.0, 1300)]
        prices, flows = self._with_forward(fwd)
        status, path = update_pending(self._event(prices), prices, flows, 32)
        assert (status, path) == ("confirmed", "retest")

    def test_c1_same_day_touch_and_reclose(self):
        """Given 접근과 재마감이 같은 날 When 판정 Then confirmed/retest"""
        fwd = [_bar(31, 99, 101.5, 98.0, 101.0, 1300)]
        prices, flows = self._with_forward(fwd)
        status, path = update_pending(self._event(prices), prices, flows, 31)
        assert (status, path) == ("confirmed", "retest")

    def test_c1_disqualified_by_low_break(self):
        """Given 재시험 중 저가가 실패선 붕괴 When 판정 Then C1 무효(종가회복=failed아님)"""
        # day31 low96(<97)·close98(회복, failed아님) → c1_broken
        # day32 밴드 접근·종가101 이지만 C1 자격 상실 → 아직 pending
        fwd = [_bar(31, 99, 99.5, 96.0, 98.0, 1000),
               _bar(32, 99, 101.5, 98.5, 101.0, 1300)]
        prices, flows = self._with_forward(fwd)
        assert update_pending(self._event(prices), prices, flows, 32) == ("pending", None)

    def test_failed_on_close_breakdown(self):
        """Given 돌파일 이후 종가가 실패선 미만 When 판정 Then failed"""
        fwd = [_bar(31, 99, 100, 95, 96.0, 1000)]  # close 96 < 97
        prices, flows = self._with_forward(fwd)
        assert update_pending(self._event(prices), prices, flows, 31) == ("failed", None)

    def test_expired_after_window(self):
        """Given 확정도 실패도 없이 CONFIRM_WINDOW 경과 When 판정 Then expired"""
        # 저가 97.5(밴드 밖·실패선 위), 종가 98(연속유지 깨고 실패도 아님)
        fwd = [_bar(30 + k, 98, 99, 97.5, 98.0, 1000) for k in range(1, 16)]
        prices, flows = self._with_forward(fwd)
        # window_end = 30 + 15 = 45
        assert update_pending(self._event(prices), prices, flows, 45) == ("expired", None)

    def test_pending_within_window(self):
        """Given 창 내 미종결 When 판정 Then pending"""
        fwd = [_bar(30 + k, 98, 99, 97.5, 98.0, 1000) for k in range(1, 6)]
        prices, flows = self._with_forward(fwd)
        assert update_pending(self._event(prices), prices, flows, 35) == ("pending", None)

    def test_confirm_blocked_when_supply_missing(self):
        """Given 확정 조건이나 확정일 수급 결측 When 판정 Then 확정 보류(pending)"""
        # 밴드 밖 연속 유지(C2)로 격리 + 돌파일 이후 3일 수급 전부 제거
        prices = _base_flat(30) + [_bar(30, 101, 105, 101, 104.0, 2500)] + list(self._HOLD_FWD)
        flows = {b.date: 500 for b in prices if b.date < prices[30].date}
        assert update_pending(self._event(prices), prices, flows, 32) == ("pending", None)
