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
)

logger = logging.getLogger(__name__)

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


def _get_active_uptrend_rules() -> List[dict]:
    """활성 uptrend 알림 규칙 목록 (id, ticker)."""
    from app.database import get_db_connection, get_cursor

    with get_db_connection() as conn:
        cur = get_cursor(conn)
        cur.execute(
            "SELECT id, ticker FROM alert_rules WHERE alert_type = 'uptrend' AND is_active = 1"
        )
        return [{"id": r["id"], "ticker": r["ticker"]} for r in cur.fetchall()]


def _get_active_pending(ticker: str) -> Optional[dict]:
    """종목의 활성 pending 이벤트 1개 (최신 돌파일). 없으면 None."""
    from app.database import get_db_connection, get_cursor

    with get_db_connection() as conn:
        cur = get_cursor(conn)
        cur.execute(
            """SELECT id, breakout_date, breakout_level FROM signal_events
               WHERE ticker = ? AND status = 'pending'
               ORDER BY breakout_date DESC LIMIT 1""",
            (ticker,),
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


def _create_pending(rule_id: int, ticker: str, sig: BreakoutSignal) -> Optional[int]:
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
                candle_pos, flow_net_3d, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')""",
            (ticker, rule_id, sig.breakout_date.isoformat(), sig.breakout_level,
             sig.volume_ratio, sig.candle_pos, sig.flow_net_3d),
        )
        conn.commit()
        if cur.rowcount and cur.lastrowid:
            return cur.lastrowid
        # 이미 존재 — 여전히 pending이면 그 id 반환(재생 중 이어받기)
        cur.execute(
            "SELECT id, status FROM signal_events WHERE ticker = ? AND breakout_date = ?",
            (ticker, sig.breakout_date.isoformat()),
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


def _build_alert_message(name: str, path: Optional[str], level: float) -> str:
    """LV2 확정 알림 문구 (§3-3, 천 단위 콤마)."""
    if path == "retest":
        return f"[{name}] 상승흐름 확정 — 돌파선 {level:,.0f}원 재시험 성공"
    return f"[{name}] 상승흐름 확정 — 돌파 후 {SIGNAL_HOLD_DAYS}일 연속 유지"


def _emit_uptrend_alert(rule_id: int, ticker: str, name: str, level: float,
                        path: Optional[str], confirmed_date: date_type,
                        prices: List[PriceBar], confirm_idx: int) -> bool:
    """쿨다운 게이트 통과 시 alert_history 기록 + last_triggered_at 갱신 (§3-4).

    Returns:
        기록했으면 True, 쿨다운으로 억제됐으면 False.
    """
    from app.database import get_db_connection, get_cursor

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

        message = _build_alert_message(name, path, level)
        cur.execute(
            """INSERT INTO alert_history (rule_id, ticker, alert_type, message, triggered_at)
               VALUES (?, ?, 'uptrend', ?, ?)""",
            (rule_id, ticker, message, confirmed_date.isoformat()),
        )
        cur.execute(
            "UPDATE alert_rules SET last_triggered_at = ? WHERE id = ?",
            (confirmed_date.isoformat(), rule_id),
        )
        conn.commit()
    return True


def _step_day(rule_id: int, ticker: str, name: str, prices: List[PriceBar],
              flows: Dict[date_type, int], i: int, active: Optional[dict]) -> Optional[dict]:
    """하루치 상태 전이 처리. 갱신된 active(또는 None)를 반환한다."""
    bar = prices[i]

    # 1) 활성 pending 상태 갱신 (있으면)
    if active is not None:
        status, path = update_pending(active["signal"], prices, flows, i)
        if status != "pending":
            _resolve_event(active["id"], status, path, bar.date)
            if status == "confirmed":
                _emit_uptrend_alert(
                    rule_id, ticker, name, active["signal"].breakout_level,
                    path, bar.date, prices, i,
                )
            active = None

    # 2) pending 없으면 신규 돌파 탐지 (이중 pending 차단)
    if active is None:
        sig = detect_breakout(prices, flows, i)
        if sig is not None:
            new_id = _create_pending(rule_id, ticker, sig)
            if new_id is not None:
                active = {"id": new_id, "signal": sig}

    return active


def _scan_ticker(collector, rule_id: int, ticker: str,
                 since_date: Optional[date_type],
                 until_date: date_type) -> Optional[date_type]:
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

    active = _get_active_pending(ticker)
    last_processed: Optional[date_type] = None

    for i, bar in enumerate(prices):
        if since_date is not None and bar.date <= since_date:
            continue
        if bar.date > until_date:
            break
        active = _step_day(rule_id, ticker, name, prices, flows, i, active)
        last_processed = bar.date

    return last_processed


def scan_all(since=None, until=None) -> dict:
    """활성 uptrend 종목 전체를 소급 재생 스캔한다 (§3-1, 두 진입점 공용, 멱등).

    Args:
        since: 마지막 스캔일(이후만 재생). None이면 전체 이력 재생(초기 구축).
        until: 처리 상한 거래일(포함). None이면 오늘까지.

    Returns:
        {scanned, failed, marker} 요약. 전 종목 성공 시에만 마커를 갱신한다.
    """
    from app.services.data_collector import ETFDataCollector
    from app.database import set_app_state

    collector = ETFDataCollector()
    rules = _get_active_uptrend_rules()
    since_date = _as_date(since)
    until_date = _as_date(until) or date_type.today()

    all_success = True
    scanned = 0
    max_processed: Optional[date_type] = None

    for rule in rules:
        try:
            processed_to = _scan_ticker(
                collector, rule["id"], rule["ticker"], since_date, until_date
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
