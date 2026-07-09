"""상승흐름 신호 판정 순수 함수 (docs/UPTREND_SIGNAL_DESIGN.md §2).

DB·네트워크 접근이 없는 순수 로직. 모든 판정은 `as_of_idx`까지의 데이터만
참조하도록 강제해 미래 데이터 누수(lookahead bias)를 구조적으로 차단한다.
DB 연동·소급 재생·알림 발신은 scan_all(Phase 2.3)이 담당한다.

용어·조건은 설계 §2-1~§2-4를 그대로 옮긴 것이며, 파라미터는 constants.py의
SIGNAL_* 상수를 참조한다.
"""
import logging
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
    SIGNAL_COOLDOWN_DAYS,
    SIGNAL_ALERT_FRESH_DAYS,
    SIGNAL_BATCH_SCAN_MAX,
)

logger = logging.getLogger(__name__)

# 과열 판정 기준일 수 (§2-2 B5: 당일 포함 최근 5거래일 수익률)
OVERHEAT_LOOKBACK = 5
# 수급 누적 판정 기간 (§2-2 B4 / §2-3 확정 재확인: 최근 3거래일)
FLOW_WINDOW_DAYS = 3

# 신호 방향 — 상승흐름(up)과 그 거울상 하락흐름(down)을 같은 로직으로 판정.
UP = "up"
DOWN = "down"


def _sign(direction: str) -> int:
    """up→+1, down→-1. 부호로 상/하 비교를 대칭 처리한다."""
    return 1 if direction == UP else -1


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


def _effective_candle(bar: PriceBar, direction: str) -> float:
    """방향 기준 캔들 강도 — up은 상단 마감일수록, down은 하단 마감일수록 1에 가깝다.

    고가=저가(상한가·하한가 잠김 등 한 가격 마감)는 방향과 무관하게 가장 강한
    마감으로 간주해 1.0을 반환한다. 단순히 1-_candle_position을 쓰면 하한가
    잠김 봉(가장 강한 이탈)이 0이 되어 기각되는 비대칭이 생긴다.
    """
    if bar.high - bar.low <= 0:
        return 1.0
    pos = _candle_position(bar)
    return pos if direction == UP else 1 - pos


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
    prices: List[PriceBar], flows: Dict[date_type, int],
    as_of_idx: int, net_3d: int, s: int
) -> bool:
    """B4: 당일 또는 최근 3거래일 누적 수급이 방향과 일치(up→순매수, down→순매도)."""
    today_net = flows.get(prices[as_of_idx].date)
    return (today_net is not None and s * today_net > 0) or s * net_3d > 0


def _is_extreme_move(prices: List[PriceBar], as_of_idx: int, s: int) -> bool:
    """B5: 5거래일 방향 수익률이 임계(±OVERHEAT_5D%) 넘으면 과열/과매도 → 추격 제외."""
    prev_close = prices[as_of_idx - OVERHEAT_LOOKBACK].close
    if prev_close <= 0:
        return False
    return s * (prices[as_of_idx].close / prev_close - 1) * 100 >= SIGNAL_OVERHEAT_5D


def detect_breakout(
    prices: List[PriceBar],
    flows: Dict[date_type, int],
    as_of_idx: int,
    direction: str = UP,
) -> Optional[BreakoutSignal]:
    """`as_of_idx`일 종가 확정 기준으로 LV1 돌파/이탈(B1~B6)을 판정 (§2-2).

    direction='up'이면 20일 고점 상향 돌파, 'down'이면 20일 저점 하향 이탈을
    같은 규칙의 거울상으로 판정한다.

    Returns:
        모든 조건 충족 시 BreakoutSignal, 아니면 None.
    """
    # B6: 데이터 충분 — 룩백 20행 확보 + 최소 이력 일수
    if as_of_idx < SIGNAL_LOOKBACK_DAYS or (as_of_idx + 1) < SIGNAL_MIN_DATA_DAYS:
        return None

    s = _sign(direction)
    today = prices[as_of_idx]
    lookback = prices[as_of_idx - SIGNAL_LOOKBACK_DAYS:as_of_idx]  # 당일 제외 직전 20행
    breakout_level = (
        max(b.high for b in lookback) if direction == UP
        else min(b.low for b in lookback)
    )
    avg_vol = sum(b.volume for b in lookback) / len(lookback)
    volume_ratio = today.volume / avg_vol if avg_vol > 0 else 0.0
    candle_pos = _candle_position(today)
    # up은 상단 마감(위치↑), down은 하단 마감(위치↓). 한 가격 마감(상·하한가)은 양쪽 모두 1.0
    eff_candle = _effective_candle(today, direction)
    net_3d, has_flow = _flow_sum_recent(prices, flows, as_of_idx)

    # B1 방향 돌파, B2 거래량 배수, B3 캔들 위치, B4 수급(결측이면 보류), B5 과열/과매도 아님
    if s * (today.close - breakout_level) <= 0:
        return None
    if volume_ratio < SIGNAL_VOL_MULT:
        return None
    if eff_candle < SIGNAL_CANDLE_POS_MIN:
        return None
    if not has_flow or not _breakout_supply_confirms(prices, flows, as_of_idx, net_3d, s):
        return None
    if _is_extreme_move(prices, as_of_idx, s):
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


def _supply_ok(prices: List[PriceBar], flows: Dict[date_type, int], idx: int, s: int) -> bool:
    """확정일 수급 재확인 — 최근 3거래일 누적 수급이 방향과 일치 (결측이면 False)."""
    net_3d, has_flow = _flow_sum_recent(prices, flows, idx)
    return has_flow and s * net_3d > 0


def _hold_confirms(
    prices: List[PriceBar], flows: Dict[date_type, int],
    b_idx: int, level: float, i: int, s: int
) -> bool:
    """C2: 돌파일 포함 HOLD_DAYS 연속 종가가 돌파선 반대편 유지 + 수급 확인 (§2-3)."""
    if i != b_idx + SIGNAL_HOLD_DAYS - 1:
        return False
    if not all(s * (prices[j].close - level) > 0 for j in range(b_idx, i + 1)):
        return False
    return _supply_ok(prices, flows, i, s)


def _retest_confirms(
    bar: PriceBar, level: float, retest_touched: bool, c1_broken: bool,
    prices: List[PriceBar], flows: Dict[date_type, int], i: int, s: int
) -> bool:
    """C1: 재시험 접근 이력 + 실패선 붕괴 없음 + 종가 재이탈 + 수급 확인 (§2-3)."""
    if not (retest_touched and not c1_broken and s * (bar.close - level) > 0):
        return False
    return _supply_ok(prices, flows, i, s)


def update_pending(
    event: BreakoutSignal,
    prices: List[PriceBar],
    flows: Dict[date_type, int],
    as_of_idx: int,
    direction: str = UP,
) -> Tuple[str, Optional[str]]:
    """pending 이벤트의 상태를 `as_of_idx` 기준으로 판정 (§2-3, §2-4).

    돌파일부터 as_of_idx(최대 CONFIRM_WINDOW)까지 시간순으로 재생하며 최초의
    종결 전이를 반환한다. direction으로 상승/하락을 대칭 처리한다.

    Returns:
        (status, path): status ∈ {pending, confirmed, failed, expired},
        path ∈ {'retest', 'hold', None}
    """
    b_idx = _find_index(prices, event.breakout_date)
    if b_idx is None or b_idx > as_of_idx:
        return ("pending", None)

    s = _sign(direction)
    level = event.breakout_level
    # 실패선: up→level×0.97(아래), down→level×1.03(위)
    fail_line = level * (1 - s * (1 - SIGNAL_FAIL_FLOOR))
    near_lo = level * (1 - SIGNAL_RETEST_NEAR)
    near_hi = level * (1 + SIGNAL_RETEST_NEAR)
    window_end = b_idx + SIGNAL_CONFIRM_WINDOW
    end = min(as_of_idx, window_end)

    retest_touched = False
    c1_broken = False

    for i in range(b_idx, end + 1):
        bar = prices[i]
        # 재시험 접근·붕괴 판정에 쓰는 극단가: up→저가, down→고가
        extreme = bar.low if direction == UP else bar.high

        # 실패: 돌파일 이후 종가가 실패선 반대편으로 마감 (§2-4)
        if i > b_idx and s * (bar.close - fail_line) < 0:
            return ("failed", None)
        # 극단가가 실패선 붕괴 → C1 자격 상실 (종가 회복 시 failed는 아님, §2-3 주석)
        if s * (extreme - fail_line) < 0:
            c1_broken = True
        # C2 연속 유지 확정
        if _hold_confirms(prices, flows, b_idx, level, i, s):
            return ("confirmed", "hold")
        # C1 재시험 접근(돌파일 이후 극단가가 ±RETEST_NEAR 밴드 진입)
        if i > b_idx and near_lo <= extreme <= near_hi:
            retest_touched = True
        # C1 재시험 확정 (접근·재마감 동일일 허용)
        if _retest_confirms(bar, level, retest_touched, c1_broken, prices, flows, i, s):
            return ("confirmed", "retest")
        # 만료: CONFIRM_WINDOW 경과 (§2-4)
        if i >= window_end:
            return ("expired", None)

    return ("pending", None)


# ─────────────────────────────────────────────────────────────────────────────
# DB 연동 · 소급 재생 · 알림 발신 (Phase 2.3, docs/UPTREND_SIGNAL_DESIGN.md §3)
#
# 위 순수 함수를 DB와 엮어, 놓친 거래일을 오래된 순서로 하루씩 재생(replay)한다.
# UNIQUE(ticker, breakout_date) + INSERT OR IGNORE로 멱등 재실행을 보장하고,
# LV2 확정 시에만 쿨다운 게이트를 통과한 건을 alert_history에 기록한다.
# ─────────────────────────────────────────────────────────────────────────────


def _as_date(value) -> Optional[date_type]:
    """date/문자열/None을 date 또는 None으로 정규화."""
    if value is None:
        return None
    if isinstance(value, date_type):
        return value
    return date_type.fromisoformat(str(value))


def _load_price_bars(ticker: str) -> List[PriceBar]:
    """prices 테이블을 오래된→최신 순 PriceBar 리스트로 로드 (결측 OHLC는 종가로 보정)."""
    from app.database import get_db_connection, get_cursor

    bars: List[PriceBar] = []
    with get_db_connection() as conn:
        cur = get_cursor(conn)
        cur.execute(
            """SELECT date, open_price, high_price, low_price, close_price, volume
               FROM prices WHERE ticker = ? ORDER BY date ASC""",
            (ticker,),
        )
        for r in cur.fetchall():
            close = r["close_price"]
            if close is None:
                continue
            d = _as_date(r["date"])
            bars.append(PriceBar(
                date=d,
                open=r["open_price"] if r["open_price"] is not None else close,
                high=r["high_price"] if r["high_price"] is not None else close,
                low=r["low_price"] if r["low_price"] is not None else close,
                close=close,
                volume=r["volume"] or 0,
            ))
    return bars


def _load_flows(ticker: str) -> Dict[date_type, int]:
    """trading_flow를 날짜→수급 순매수(외국인+기관) 매핑으로 로드."""
    from app.database import get_db_connection, get_cursor

    flows: Dict[date_type, int] = {}
    with get_db_connection() as conn:
        cur = get_cursor(conn)
        cur.execute(
            "SELECT date, foreign_net, institutional_net FROM trading_flow WHERE ticker = ?",
            (ticker,),
        )
        for r in cur.fetchall():
            fn, inn = r["foreign_net"], r["institutional_net"]
            if fn is None and inn is None:
                continue
            flows[_as_date(r["date"])] = (fn or 0) + (inn or 0)
    return flows


ALERT_TYPE_BY_DIRECTION = {UP: "uptrend", DOWN: "downtrend"}
DIRECTION_BY_ALERT_TYPE = {"uptrend": UP, "downtrend": DOWN}


def _get_active_signal_rules() -> List[dict]:
    """활성 상승/하락 신호 규칙 목록 (id, ticker, alert_type, direction)."""
    from app.database import get_db_connection, get_cursor

    with get_db_connection() as conn:
        cur = get_cursor(conn)
        cur.execute(
            """SELECT id, ticker, alert_type FROM alert_rules
               WHERE alert_type IN ('uptrend', 'downtrend') AND is_active = 1"""
        )
        return [{
            "id": r["id"], "ticker": r["ticker"], "alert_type": r["alert_type"],
            "direction": DIRECTION_BY_ALERT_TYPE[r["alert_type"]],
        } for r in cur.fetchall()]


def _get_active_pending(ticker: str, direction: str = UP) -> Optional[dict]:
    """종목·방향의 활성 pending 이벤트 1개 (최신 돌파일). 없으면 None."""
    from app.database import get_db_connection, get_cursor

    with get_db_connection() as conn:
        cur = get_cursor(conn)
        cur.execute(
            """SELECT id, breakout_date, breakout_level FROM signal_events
               WHERE ticker = ? AND direction = ? AND status = 'pending'
               ORDER BY breakout_date DESC LIMIT 1""",
            (ticker, direction),
        )
        r = cur.fetchone()
        if not r:
            return None
        sig = BreakoutSignal(
            breakout_date=_as_date(r["breakout_date"]),
            breakout_level=r["breakout_level"],
            volume_ratio=0.0, candle_pos=0.0, flow_net_3d=0,
        )
        return {"id": r["id"], "signal": sig}


def _create_pending(rule_id: int, ticker: str, sig: BreakoutSignal,
                    direction: str = UP) -> Optional[int]:
    """pending 이벤트 생성 (멱등: 동일 (ticker, breakout_date) 있으면 무시).

    Returns:
        새로 만든 event id, 또는 기존 행이 여전히 pending이면 그 id, 아니면 None.
    """
    from app.database import get_db_connection, get_cursor

    with get_db_connection() as conn:
        cur = get_cursor(conn)
        cur.execute(
            """INSERT OR IGNORE INTO signal_events
               (ticker, rule_id, breakout_date, breakout_level, volume_ratio,
                candle_pos, flow_net_3d, status, direction)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?)""",
            (ticker, rule_id, sig.breakout_date.isoformat(), sig.breakout_level,
             sig.volume_ratio, sig.candle_pos, sig.flow_net_3d, direction),
        )
        conn.commit()
        if cur.rowcount and cur.lastrowid:
            return cur.lastrowid
        # 이미 존재 — 여전히 pending이면 그 id 반환(재생 중 이어받기)
        cur.execute(
            """SELECT id, status FROM signal_events
               WHERE ticker = ? AND breakout_date = ? AND direction = ?""",
            (ticker, sig.breakout_date.isoformat(), direction),
        )
        row = cur.fetchone()
        if row and row["status"] == "pending":
            return row["id"]
        return None


def _resolve_event(event_id: int, status: str, path: Optional[str],
                   confirmed_date: date_type) -> None:
    """이벤트를 종결 상태로 전이 (confirmed면 확정일·경로 기록)."""
    from app.database import get_db_connection, get_cursor

    with get_db_connection() as conn:
        cur = get_cursor(conn)
        if status == "confirmed":
            cur.execute(
                """UPDATE signal_events
                   SET status = ?, confirmed_date = ?, confirm_path = ?,
                       updated_at = CURRENT_TIMESTAMP
                   WHERE id = ?""",
                (status, confirmed_date.isoformat(), path, event_id),
            )
        else:
            cur.execute(
                "UPDATE signal_events SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, event_id),
            )
        conn.commit()


def _index_on_or_before(prices: List[PriceBar], target: date_type) -> Optional[int]:
    """target 날짜 이하인 마지막 인덱스 (쿨다운 거래일 거리 계산용)."""
    result = None
    for i, bar in enumerate(prices):
        if bar.date <= target:
            result = i
        else:
            break
    return result


def _build_alert_message(name: str, path: Optional[str], level: float,
                         direction: str = UP) -> str:
    """LV2 확정 알림 문구 (§3-3, 천 단위 콤마)."""
    if direction == UP:
        if path == "retest":
            return f"[{name}] 상승흐름 확정 — 돌파선 {level:,.0f}원 재시험 성공"
        return f"[{name}] 상승흐름 확정 — 돌파 후 {SIGNAL_HOLD_DAYS}일 연속 유지"
    if path == "retest":
        return f"[{name}] 하락흐름 확정 — 이탈선 {level:,.0f}원 재이탈"
    return f"[{name}] 하락흐름 확정 — 이탈 후 {SIGNAL_HOLD_DAYS}일 연속 유지"


def _emit_signal_alert(rule_id: int, ticker: str, name: str, level: float,
                       path: Optional[str], confirmed_date: date_type,
                       prices: List[PriceBar], confirm_idx: int,
                       direction: str = UP) -> bool:
    """신선도·쿨다운 게이트 통과 시 alert_history 기록 + last_triggered_at 갱신 (§3-4).

    Returns:
        기록했으면 True, 신선도/쿨다운으로 억제됐으면 False.
    """
    from app.database import get_db_connection, get_cursor

    # 신선도 가드: 확정일이 최신 데이터로부터 너무 오래됐으면 상태만 두고 알림 억제.
    # 최초 스캔·장기 미기동 따라잡기의 소급 재생이 오래된 확정을 새 알림처럼 띄우는 것 방지.
    if (len(prices) - 1 - confirm_idx) > SIGNAL_ALERT_FRESH_DAYS:
        return False

    with get_db_connection() as conn:
        cur = get_cursor(conn)
        # 쿨다운: 직전 LV2(last_triggered_at)로부터 COOLDOWN_DAYS 거래일 이내면 억제
        cur.execute("SELECT last_triggered_at FROM alert_rules WHERE id = ?", (rule_id,))
        row = cur.fetchone()
        last = row["last_triggered_at"] if row else None
        if last:
            prev_idx = _index_on_or_before(prices, _as_date(str(last)[:10]))
            if prev_idx is not None and (confirm_idx - prev_idx) < SIGNAL_COOLDOWN_DAYS:
                return False

        message = _build_alert_message(name, path, level, direction)
        cur.execute(
            """INSERT INTO alert_history (rule_id, ticker, alert_type, message, triggered_at)
               VALUES (?, ?, ?, ?, ?)""",
            (rule_id, ticker, ALERT_TYPE_BY_DIRECTION[direction], message,
             confirmed_date.isoformat()),
        )
        cur.execute(
            "UPDATE alert_rules SET last_triggered_at = ? WHERE id = ?",
            (confirmed_date.isoformat(), rule_id),
        )
        conn.commit()
    return True


def _step_day(rule_id: int, ticker: str, name: str, prices: List[PriceBar],
              flows: Dict[date_type, int], i: int, active: Optional[dict],
              direction: str = UP) -> Optional[dict]:
    """하루치 상태 전이 처리. 갱신된 active(또는 None)를 반환한다."""
    bar = prices[i]

    # 1) 활성 pending 상태 갱신 (있으면)
    if active is not None:
        status, path = update_pending(active["signal"], prices, flows, i, direction)
        if status != "pending":
            _resolve_event(active["id"], status, path, bar.date)
            if status == "confirmed":
                _emit_signal_alert(
                    rule_id, ticker, name, active["signal"].breakout_level,
                    path, bar.date, prices, i, direction,
                )
            active = None

    # 2) pending 없으면 신규 돌파 탐지 (이중 pending 차단)
    if active is None:
        sig = detect_breakout(prices, flows, i, direction)
        if sig is not None:
            new_id = _create_pending(rule_id, ticker, sig, direction)
            if new_id is not None:
                active = {"id": new_id, "signal": sig}

    return active


def _scan_ticker(collector, rule_id: int, ticker: str,
                 since_date: Optional[date_type],
                 until_date: date_type, direction: str = UP) -> Optional[date_type]:
    """단일 종목의 놓친 거래일을 재생하며 상태 전이·알림을 처리한다.

    Returns:
        마지막으로 처리한 거래일 (마커 갱신용), 처리분 없으면 None.
    """
    collector.ensure_recent_history(ticker)
    prices = _load_price_bars(ticker)
    if len(prices) < SIGNAL_MIN_DATA_DAYS:
        logger.info(f"[신호] {ticker}: 데이터 부족({len(prices)}행) → 판정 보류")
        return None
    flows = _load_flows(ticker)
    etf = collector.get_etf_info(ticker)
    name = etf.name if etf else ticker

    active = _get_active_pending(ticker, direction)
    last_processed: Optional[date_type] = None

    for i, bar in enumerate(prices):
        if since_date is not None and bar.date <= since_date:
            continue
        if bar.date > until_date:
            break
        active = _step_day(rule_id, ticker, name, prices, flows, i, active, direction)
        last_processed = bar.date

    return last_processed


def scan_all(since=None, until=None) -> dict:
    """활성 상승/하락 신호 종목 전체를 소급 재생 스캔한다 (§3-1, 멱등).

    Args:
        since: 마지막 스캔일(이후만 재생). None이면 전체 이력 재생(초기 구축).
        until: 처리 상한 거래일(포함). None이면 오늘까지.

    Returns:
        {scanned, failed, marker} 요약. 전 규칙 성공 시에만 마커를 갱신한다.
    """
    from app.services.data_collector import ETFDataCollector
    from app.database import set_app_state

    collector = ETFDataCollector()
    rules = _get_active_signal_rules()
    since_date = _as_date(since)
    until_date = _as_date(until) or date_type.today()

    all_success = True
    scanned = 0
    max_processed: Optional[date_type] = None

    for rule in rules:
        try:
            processed_to = _scan_ticker(
                collector, rule["id"], rule["ticker"], since_date, until_date,
                rule["direction"],
            )
            scanned += 1
            if processed_to and (max_processed is None or processed_to > max_processed):
                max_processed = processed_to
        except Exception as e:
            logger.error(f"[신호] {rule['ticker']} 스캔 실패: {e}", exc_info=True)
            all_success = False

    marker = None
    # 전 종목 성공 시에만 마커 갱신 (부분 실패 시 다음 기동에 다시 따라잡도록)
    if all_success and rules:
        marker = (max_processed or until_date).isoformat()
        set_app_state("last_signal_scan_date", marker)

    logger.info(
        f"[신호] 스캔 완료: {scanned}/{len(rules)} 종목, "
        f"마커={marker or '미갱신'}"
    )
    return {
        "scanned": scanned,
        "failed": len(rules) - scanned,
        "marker": marker,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 관심종목 일괄 점검(읽기 전용) · 단일 종목 즉시 스캔
#
# A. evaluate_watchlist: 등록 종목 전체를 저장된 데이터로 순수 재생해 현재 상태를
#    리포트한다. signal_events/alert_history를 건드리지 않는다(부작용 없음).
# B. scan_ticker: 단일 종목만 DB 기록·알림 발신 스캔(토글 ON 직후 즉시 확인용).
# ─────────────────────────────────────────────────────────────────────────────


def _event_dict(sig: BreakoutSignal, status: str, path: Optional[str],
                resolved_date: Optional[date_type]) -> dict:
    """재생 이벤트를 직렬화 가능한 dict로."""
    return {
        "breakout_date": sig.breakout_date.isoformat(),
        "breakout_level": sig.breakout_level,
        "volume_ratio": round(sig.volume_ratio, 2),
        "status": status,
        "confirm_path": path,
        "confirmed_date": (
            resolved_date.isoformat()
            if (status == "confirmed" and resolved_date) else None
        ),
    }


def replay_events(prices: List[PriceBar], flows: Dict[date_type, int],
                  start_idx: int = 0, direction: str = UP) -> List[dict]:
    """DB 없이 순수하게 재생해 신호 이벤트 목록을 시간순으로 반환한다.

    scan_all과 동일한 상태 전이 규칙을 쓰되 DB에 기록하지 않는다. 종목당 활성
    pending은 1개(이중 pending 차단)라는 불변식도 동일하게 유지된다.
    """
    events: List[dict] = []
    active: Optional[BreakoutSignal] = None

    for i in range(start_idx, len(prices)):
        if active is not None:
            status, path = update_pending(active, prices, flows, i, direction)
            if status != "pending":
                events.append(_event_dict(active, status, path, prices[i].date))
                active = None
        if active is None:
            sig = detect_breakout(prices, flows, i, direction)
            if sig is not None:
                active = sig

    if active is not None:  # 끝까지 미종결 → 대기 상태로 보고
        events.append(_event_dict(active, "pending", None, None))
    return events


def evaluate_watchlist(direction: str = UP) -> List[dict]:
    """등록 종목 전체의 현재 상승/하락 흐름 상태를 리포트한다 (읽기 전용, DB 미변경).

    저장된 가격·수급으로 재생하며, 각 종목의 **가장 최근 신호 이벤트**를 요약한다.
    데이터 부족 종목은 status='insufficient_data'로 표시한다.
    """
    from app.services.data_collector import ETFDataCollector

    collector = ETFDataCollector()
    results: List[dict] = []
    for etf in collector.get_all_etfs():
        prices = _load_price_bars(etf.ticker)
        if len(prices) < SIGNAL_MIN_DATA_DAYS:
            results.append({
                "ticker": etf.ticker, "name": etf.name,
                "status": "insufficient_data", "latest": None,
            })
            continue
        flows = _load_flows(etf.ticker)
        events = replay_events(prices, flows, direction=direction)
        latest = events[-1] if events else None
        results.append({
            "ticker": etf.ticker, "name": etf.name,
            "status": _current_status(latest, prices),
            "latest": latest,
        })
    return results


def _current_status(latest: Optional[dict], prices: List[PriceBar]) -> str:
    """'지금'의 상태로 환산 — 오래된 확정(신선도 초과)은 'none'으로 강등.

    확정 이벤트는 시점 신호라 시간이 지나면 '현재 상승흐름'이 아니다. pending은
    확정 창(≤15거래일) 내라 본질적으로 최근이므로 그대로 둔다.
    """
    if latest is None:
        return "none"
    if latest["status"] != "confirmed":
        return latest["status"]
    idx = _find_index(prices, _as_date(latest["confirmed_date"]))
    if idx is None or (len(prices) - 1 - idx) > SIGNAL_ALERT_FRESH_DAYS:
        return "none"
    return "confirmed"


def scan_ticker(ticker: str, since=None, direction: Optional[str] = None) -> dict:
    """단일 종목만 스캔한다 (DB 기록·알림 발신). 토글 ON 직후 즉시 확인용.

    direction=None이면 해당 종목의 활성 규칙(상승·하락) 전부를 스캔한다.
    전역 마커(last_signal_scan_date)는 건드리지 않는다 — 전체 스캔 전용이다.
    """
    from app.services.data_collector import ETFDataCollector

    rules = [
        r for r in _get_active_signal_rules()
        if r["ticker"] == ticker and (direction is None or r["direction"] == direction)
    ]
    if not rules:
        return {"scanned": False, "reason": "no_active_rule"}

    collector = ETFDataCollector()
    try:
        for rule in rules:
            _scan_ticker(collector, rule["id"], ticker, _as_date(since),
                         date_type.today(), rule["direction"])
        return {"scanned": True}
    except Exception as e:
        logger.error(f"[신호] {ticker} 단일 스캔 실패: {e}", exc_info=True)
        return {"scanned": False, "reason": str(e)}


# ─────────────────────────────────────────────────────────────────────────────
# 배치 점검 — 조건검색 결과 등 임의 종목 목록을 즉시 수집 후 판정
#
# evaluate_watchlist는 "이미 이력이 있는 등록 종목"만 본다. 카탈로그 종목은
# prices/trading_flow 이력이 없으므로, 판정 전에 종목별로 이력을 수집해야 한다.
# signal_events/alert_history는 건드리지 않는다(판정은 읽기 전용, 이력만 저장).
# ─────────────────────────────────────────────────────────────────────────────


def _lookup_names(tickers: List[str]) -> Dict[str, str]:
    """종목명 조회 — 등록 종목(etfs)을 우선하고, 없으면 카탈로그(stock_catalog)."""
    from app.database import get_db_connection, get_cursor

    if not tickers:
        return {}
    placeholders = ",".join("?" * len(tickers))
    names: Dict[str, str] = {}
    with get_db_connection() as conn:
        cur = get_cursor(conn)
        cur.execute(
            f"SELECT ticker, name FROM stock_catalog WHERE ticker IN ({placeholders})",
            tuple(tickers),
        )
        for r in cur.fetchall():
            names[r["ticker"]] = r["name"]
        cur.execute(
            f"SELECT ticker, name FROM etfs WHERE ticker IN ({placeholders})",
            tuple(tickers),
        )
        for r in cur.fetchall():
            names[r["ticker"]] = r["name"]
    return names


def evaluate_tickers(tickers: List[str], direction: str = UP,
                     limit: int = 30) -> List[dict]:
    """지정 종목들의 이력을 즉시 수집한 뒤 현재 흐름 상태를 리포트한다.

    가격·수급 이력은 DB에 저장되지만(ensure_recent_history), 신호 상태
    (signal_events)와 알림(alert_history)은 변경하지 않는다 — 판정은 순수 재생.

    Args:
        tickers: 대상 종목 코드 (중복 제거 후 앞에서부터 limit개만)
        direction: 'up' | 'down'
        limit: 상한 (1 ~ SIGNAL_BATCH_SCAN_MAX)
    """
    from app.services.data_collector import ETFDataCollector

    capped = max(1, min(limit, SIGNAL_BATCH_SCAN_MAX))
    targets = list(dict.fromkeys(tickers))[:capped]
    names = _lookup_names(targets)
    collector = ETFDataCollector()

    results: List[dict] = []
    for ticker in targets:
        name = names.get(ticker, ticker)
        try:
            collector.ensure_recent_history(ticker)
        except Exception as e:
            logger.warning(f"[신호 배치] {ticker} 이력 수집 실패: {e}")
            results.append({"ticker": ticker, "name": name,
                            "status": "error", "latest": None})
            continue

        prices = _load_price_bars(ticker)
        if len(prices) < SIGNAL_MIN_DATA_DAYS:
            results.append({"ticker": ticker, "name": name,
                            "status": "insufficient_data", "latest": None})
            continue

        flows = _load_flows(ticker)
        events = replay_events(prices, flows, direction=direction)
        latest = events[-1] if events else None
        results.append({
            "ticker": ticker, "name": name,
            "status": _current_status(latest, prices),
            "latest": latest,
        })

    logger.info(f"[신호 배치] {direction} {len(results)}종목 점검 완료")
    return results
