"""상승흐름 신호 판정 순수 함수 (docs/UPTREND_SIGNAL_DESIGN.md §2).

DB·네트워크 접근이 없는 순수 로직. 모든 판정은 `as_of_idx`까지의 데이터만
참조하도록 강제해 미래 데이터 누수(lookahead bias)를 구조적으로 차단한다.
DB 연동·소급 재생·알림 발신은 scan_all(Phase 2.3)이 담당한다.

용어·조건은 설계 §2-1~§2-4를 그대로 옮긴 것이며, 파라미터는 constants.py의
SIGNAL_* 상수를 참조한다.
"""
from dataclasses import dataclass
from datetime import date as date_type
from typing import Dict, List, Optional, Tuple

from app.constants import (
    SIGNAL_LOOKBACK_DAYS,
    SIGNAL_VOL_MULT,
    SIGNAL_CANDLE_POS_MIN,
    SIGNAL_OVERHEAT_5D,
    SIGNAL_MIN_DATA_DAYS,
    SIGNAL_CONFIRM_WINDOW,
    SIGNAL_RETEST_NEAR,
    SIGNAL_FAIL_FLOOR,
    SIGNAL_HOLD_DAYS,
)

# 과열 판정 기준일 수 (§2-2 B5: 당일 포함 최근 5거래일 수익률)
OVERHEAT_LOOKBACK = 5
# 수급 누적 판정 기간 (§2-2 B4 / §2-3 확정 재확인: 최근 3거래일)
FLOW_WINDOW_DAYS = 3


@dataclass
class PriceBar:
    """일봉 한 행. prices 테이블의 한 행에 대응."""
    date: date_type
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass
class BreakoutSignal:
    """LV1 돌파 포착 결과 (signal_events 컬럼과 1:1 대응)."""
    breakout_date: date_type
    breakout_level: float
    volume_ratio: float
    candle_pos: float
    flow_net_3d: int


def _candle_position(bar: PriceBar) -> float:
    """캔들 위치 (종가-저가)/(고가-저가). 고가=저가면 상단 마감으로 보고 1.0."""
    span = bar.high - bar.low
    if span <= 0:
        return 1.0
    return (bar.close - bar.low) / span


def _flow_sum_recent(
    prices: List[PriceBar],
    flows: Dict[date_type, int],
    idx: int,
    days: int = FLOW_WINDOW_DAYS,
) -> Tuple[int, bool]:
    """idx 포함 직전 `days` 거래일의 수급 순매수 합과 데이터 존재 여부.

    Returns:
        (합계, any_present). 해당 구간에 수급 데이터가 하나도 없으면 (0, False).
    """
    start = max(0, idx - days + 1)
    present = [
        flows[prices[j].date]
        for j in range(start, idx + 1)
        if prices[j].date in flows and flows[prices[j].date] is not None
    ]
    if not present:
        return 0, False
    return sum(present), True


def _breakout_supply_confirms(
    prices: List[PriceBar], flows: Dict[date_type, int], as_of_idx: int, net_3d: int
) -> bool:
    """B4: 당일 순매수 > 0 또는 최근 3거래일 누적 순매수 > 0."""
    today_net = flows.get(prices[as_of_idx].date)
    return (today_net is not None and today_net > 0) or net_3d > 0


def _is_overheated(prices: List[PriceBar], as_of_idx: int) -> bool:
    """B5: 당일 종가 ÷ 5거래일 전 종가 − 1 ≥ OVERHEAT_5D(%)면 과열."""
    prev_close = prices[as_of_idx - OVERHEAT_LOOKBACK].close
    if prev_close <= 0:
        return False
    return (prices[as_of_idx].close / prev_close - 1) * 100 >= SIGNAL_OVERHEAT_5D


def detect_breakout(
    prices: List[PriceBar],
    flows: Dict[date_type, int],
    as_of_idx: int,
) -> Optional[BreakoutSignal]:
    """`as_of_idx`일 종가 확정 기준으로 LV1 돌파(B1~B6)를 판정 (§2-2).

    Args:
        prices: 오래된→최신 순 정렬된 일봉 리스트
        flows: 날짜→수급 순매수(외국인+기관) 매핑
        as_of_idx: 판정 대상일 인덱스 (이 인덱스까지만 참조)

    Returns:
        모든 조건 충족 시 BreakoutSignal, 아니면 None.
    """
    # B6: 데이터 충분 — 룩백 20행 확보 + 최소 이력 일수
    if as_of_idx < SIGNAL_LOOKBACK_DAYS or (as_of_idx + 1) < SIGNAL_MIN_DATA_DAYS:
        return None

    today = prices[as_of_idx]
    lookback = prices[as_of_idx - SIGNAL_LOOKBACK_DAYS:as_of_idx]  # 당일 제외 직전 20행
    breakout_level = max(b.high for b in lookback)
    avg_vol = sum(b.volume for b in lookback) / len(lookback)
    volume_ratio = today.volume / avg_vol if avg_vol > 0 else 0.0
    candle_pos = _candle_position(today)
    net_3d, has_flow = _flow_sum_recent(prices, flows, as_of_idx)

    # B1 종가>돌파선, B2 거래량 배수, B3 캔들 위치, B4 수급(결측이면 보류), B5 과열 아님
    if today.close <= breakout_level:
        return None
    if volume_ratio < SIGNAL_VOL_MULT:
        return None
    if candle_pos < SIGNAL_CANDLE_POS_MIN:
        return None
    if not has_flow or not _breakout_supply_confirms(prices, flows, as_of_idx, net_3d):
        return None
    if _is_overheated(prices, as_of_idx):
        return None

    return BreakoutSignal(
        breakout_date=today.date,
        breakout_level=breakout_level,
        volume_ratio=volume_ratio,
        candle_pos=candle_pos,
        flow_net_3d=net_3d,
    )


def _find_index(prices: List[PriceBar], target: date_type) -> Optional[int]:
    """target 날짜의 인덱스. 없으면 None."""
    for i, bar in enumerate(prices):
        if bar.date == target:
            return i
    return None


def _supply_ok(prices: List[PriceBar], flows: Dict[date_type, int], idx: int) -> bool:
    """확정일 수급 재확인 — 최근 3거래일 누적 순매수 > 0 (결측이면 보수적으로 False)."""
    net_3d, has_flow = _flow_sum_recent(prices, flows, idx)
    return has_flow and net_3d > 0


def _hold_confirms(
    prices: List[PriceBar], flows: Dict[date_type, int], b_idx: int, level: float, i: int
) -> bool:
    """C2: 돌파일 포함 HOLD_DAYS 연속 종가 > 돌파선 + 수급 확인 (§2-3)."""
    if i != b_idx + SIGNAL_HOLD_DAYS - 1:
        return False
    if not all(prices[j].close > level for j in range(b_idx, i + 1)):
        return False
    return _supply_ok(prices, flows, i)


def _retest_confirms(
    bar: PriceBar, level: float, retest_touched: bool, c1_broken: bool,
    prices: List[PriceBar], flows: Dict[date_type, int], i: int
) -> bool:
    """C1: 재시험 접근 이력 + 저가 붕괴 없음 + 종가 > 돌파선 + 수급 확인 (§2-3)."""
    if not (retest_touched and not c1_broken and bar.close > level):
        return False
    return _supply_ok(prices, flows, i)


def update_pending(
    event: BreakoutSignal,
    prices: List[PriceBar],
    flows: Dict[date_type, int],
    as_of_idx: int,
) -> Tuple[str, Optional[str]]:
    """pending 이벤트의 상태를 `as_of_idx` 기준으로 판정 (§2-3, §2-4).

    돌파일부터 as_of_idx(최대 CONFIRM_WINDOW)까지 시간순으로 재생하며 최초의
    종결 전이를 반환한다. 종결 전이가 없으면 ('pending', None).

    Returns:
        (status, path): status ∈ {pending, confirmed, failed, expired},
        path ∈ {'retest', 'hold', None}
    """
    b_idx = _find_index(prices, event.breakout_date)
    if b_idx is None or b_idx > as_of_idx:
        return ("pending", None)

    level = event.breakout_level
    fail_line = level * SIGNAL_FAIL_FLOOR
    near_lo = level * (1 - SIGNAL_RETEST_NEAR)
    near_hi = level * (1 + SIGNAL_RETEST_NEAR)
    window_end = b_idx + SIGNAL_CONFIRM_WINDOW
    end = min(as_of_idx, window_end)

    retest_touched = False
    c1_broken = False

    for i in range(b_idx, end + 1):
        bar = prices[i]

        # 실패: 돌파일 이후 종가가 실패선(돌파선×0.97) 미만 마감 (§2-4)
        if i > b_idx and bar.close < fail_line:
            return ("failed", None)
        # 저가가 실패선 붕괴 → C1 자격 상실 (종가 회복 시 failed는 아님, §2-3 주석)
        if bar.low < fail_line:
            c1_broken = True
        # C2 연속 유지 확정
        if _hold_confirms(prices, flows, b_idx, level, i):
            return ("confirmed", "hold")
        # C1 재시험 접근(돌파일 이후 저가가 ±RETEST_NEAR 밴드 진입)
        if i > b_idx and near_lo <= bar.low <= near_hi:
            retest_touched = True
        # C1 재시험 확정 (접근·재마감 동일일 허용)
        if _retest_confirms(bar, level, retest_touched, c1_broken, prices, flows, i):
            return ("confirmed", "retest")
        # 만료: CONFIRM_WINDOW 경과 (§2-4)
        if i >= window_end:
            return ("expired", None)

    return ("pending", None)
