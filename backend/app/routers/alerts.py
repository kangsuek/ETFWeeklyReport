"""
알림 규칙 CRUD API + 알림 트리거 기록
- buy / sell: 목표가 도달 알림
- price_change: 급등/급락 알림 (target_price = 임계 %)
- trading_signal: 외국인·기관 동시 매수/매도 시그널
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel
from app.models import AlertRuleCreate, AlertRuleUpdate, AlertRuleResponse
from app.database import get_db_connection, get_cursor, get_app_state, set_app_state
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

PP = "?"

# 허용되는 alert_type / direction 조합
# uptrend/downtrend: 상승·하락 흐름 확정 신호 — 방향·목표가를 쓰지 않고 감지기가 판정
SIGNAL_ALERT_TYPES = {"uptrend", "downtrend"}
VALID_ALERT_TYPES = {"buy", "sell", "price_change", "trading_signal"} | SIGNAL_ALERT_TYPES
VALID_DIRECTIONS = {"above", "below", "both"}


def _validate_rule(alert_type: str, direction: str, target_price: float):
    """공통 유효성 검사"""
    if alert_type not in VALID_ALERT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"alert_type은 {VALID_ALERT_TYPES} 중 하나여야 합니다",
        )
    if alert_type in SIGNAL_ALERT_TYPES:
        # 상승/하락 흐름 규칙은 켜기/끄기만 의미 — 방향·목표가 검사 면제
        return
    if direction not in VALID_DIRECTIONS:
        raise HTTPException(
            status_code=400,
            detail=f"direction은 {VALID_DIRECTIONS} 중 하나여야 합니다",
        )
    if alert_type in ("buy", "sell") and target_price <= 0:
        raise HTTPException(status_code=400, detail="목표가는 0보다 커야 합니다")
    if alert_type == "price_change" and (target_price <= 0 or target_price > 100):
        raise HTTPException(status_code=400, detail="등락률 임계값은 0~100 사이여야 합니다")


# ──────────────────────── 알림 트리거 기록 ────────────────────────
# 고정 경로를 매개변수 경로(/{ticker}, /{rule_id}) 앞에 배치


class AlertTriggerRequest(BaseModel):
    """알림 트리거 기록 요청"""
    rule_id: int
    ticker: str
    alert_type: str
    message: str


@router.post("/trigger")
async def record_alert_trigger(req: AlertTriggerRequest):
    """프론트엔드에서 감지한 알림 트리거를 히스토리에 기록"""
    try:
        with get_db_connection() as conn_or_cursor:
            conn = conn_or_cursor
            cursor = conn.cursor()

            cursor.execute(
                f"""INSERT INTO alert_history (rule_id, ticker, alert_type, message)
                    VALUES ({PP}, {PP}, {PP}, {PP})""",
                (req.rule_id, req.ticker, req.alert_type, req.message),
            )

            # alert_rules의 last_triggered_at 업데이트
            cursor.execute(
                f"UPDATE alert_rules SET last_triggered_at = CURRENT_TIMESTAMP WHERE id = {PP}",
                (req.rule_id,),
            )
            conn.commit()

            return {"recorded": True}
    except Exception as e:
        logger.error(f"Failed to record alert trigger: {e}")
        raise HTTPException(status_code=500, detail="알림 기록 실패")


@router.get("/history/{ticker}")
async def get_alert_history(
    ticker: str,
    limit: int = Query(20, ge=1, le=100),
):
    """종목별 알림 이력 조회"""
    try:
        with get_db_connection() as conn_or_cursor:
            cursor = get_cursor(conn_or_cursor)
            cursor.execute(
                f"SELECT * FROM alert_history WHERE ticker = {PP} ORDER BY triggered_at DESC LIMIT {PP}",
                (ticker, limit),
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Failed to fetch alert history for {ticker}: {e}")
        raise HTTPException(status_code=500, detail="알림 이력 조회 실패")


@router.get("/signals/{ticker}")
async def get_signal_events(
    ticker: str,
    limit: int = Query(50, ge=1, le=200),
):
    """종목별 상승흐름 신호 이벤트 조회 (상세 페이지 배지·상태 표시용)"""
    try:
        with get_db_connection() as conn_or_cursor:
            cursor = get_cursor(conn_or_cursor)
            cursor.execute(
                f"""SELECT * FROM signal_events WHERE ticker = {PP}
                    ORDER BY breakout_date DESC LIMIT {PP}""",
                (ticker, limit),
            )
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Failed to fetch signal events for {ticker}: {e}")
        raise HTTPException(status_code=500, detail="신호 이벤트 조회 실패")


@router.post("/signals/{ticker}/scan")
async def scan_ticker_now(ticker: str):
    """단일 종목 즉시 스캔 (B — 토글 ON 직후 결과 바로 확인).

    해당 종목에 활성 uptrend 규칙이 있어야 하며, signal_events·alert_history를
    기록한다. 블로킹 수집을 스레드로 오프로드.
    """
    import asyncio
    from app.services.signal_detector import scan_ticker
    try:
        result = await asyncio.to_thread(scan_ticker, ticker)
        return result
    except Exception as e:
        logger.error(f"Failed to scan ticker {ticker}: {e}")
        raise HTTPException(status_code=500, detail="종목 스캔 실패")


# ─── 상승/하락 흐름 신호 알림 이력·읽음 (마커 방식, 방향별 분리) ───
# ⚠️ 아래 고정 경로들은 반드시 매개변수 경로(/{ticker}, /{rule_id})보다 먼저 등록.
# 흐름 신호만 서버 이력·미읽음 관리(기존 3종 상태성 알림과 분리 — 설계 §3-5).

READ_KEY = {"uptrend": "uptrend_last_read_at", "downtrend": "downtrend_last_read_at"}


async def _watchlist(direction: str):
    """방향별 관심종목 일괄 점검 (읽기 전용 — signal_events/alert_history 미변경)."""
    import asyncio
    from app.services.signal_detector import evaluate_watchlist
    try:
        items = await asyncio.to_thread(evaluate_watchlist, direction)
        return {"items": items}
    except Exception as e:
        logger.error(f"Failed to scan watchlist ({direction}): {e}")
        raise HTTPException(status_code=500, detail="관심종목 점검 실패")


def _signal_history(alert_type: str, limit: int, offset: int):
    """방향별 확정 알림 이력 + 미읽음(triggered_at > 마커; 마커 부재 시 전체 미읽음)."""
    marker = get_app_state(READ_KEY[alert_type])
    with get_db_connection() as conn_or_cursor:
        cursor = get_cursor(conn_or_cursor)
        cursor.execute(
            f"""SELECT * FROM alert_history WHERE alert_type = {PP}
                ORDER BY triggered_at DESC LIMIT {PP} OFFSET {PP}""",
            (alert_type, limit, offset),
        )
        items = [dict(row) for row in cursor.fetchall()]
        if marker:
            cursor.execute(
                f"""SELECT COUNT(*) AS c FROM alert_history
                    WHERE alert_type = {PP} AND triggered_at > {PP}""",
                (alert_type, marker),
            )
        else:
            cursor.execute(
                f"SELECT COUNT(*) AS c FROM alert_history WHERE alert_type = {PP}",
                (alert_type,),
            )
        unread = cursor.fetchone()["c"]
    return {"items": items, "unread_count": unread}


def _clear_signal_history(alert_type: str, before: Optional[str]):
    with get_db_connection() as conn_or_cursor:
        conn = conn_or_cursor
        cursor = conn.cursor()
        if before:
            cursor.execute(
                f"""DELETE FROM alert_history
                    WHERE alert_type = {PP} AND triggered_at < {PP}""",
                (alert_type, before),
            )
        else:
            cursor.execute(
                f"DELETE FROM alert_history WHERE alert_type = {PP}", (alert_type,)
            )
        conn.commit()
        return {"deleted": cursor.rowcount}


def _delete_signal_alert(alert_type: str, alert_id: int):
    with get_db_connection() as conn_or_cursor:
        conn = conn_or_cursor
        cursor = conn.cursor()
        cursor.execute(
            f"DELETE FROM alert_history WHERE id = {PP} AND alert_type = {PP}",
            (alert_id, alert_type),
        )
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="알림을 찾을 수 없습니다")
        return {"deleted": True}


# ── 상승흐름(uptrend) ──
@router.get("/uptrend/watchlist")
async def scan_watchlist_up():
    """관심종목 상승흐름 일괄 점검 (읽기 전용)."""
    return await _watchlist("up")


@router.get("/uptrend")
async def get_uptrend_alerts(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
    """상승흐름 확정 알림 이력 + 미읽음 카운트."""
    try:
        return _signal_history("uptrend", limit, offset)
    except Exception as e:
        logger.error(f"Failed to fetch uptrend alerts: {e}")
        raise HTTPException(status_code=500, detail="상승흐름 알림 조회 실패")


@router.post("/uptrend/read")
async def mark_uptrend_read():
    """상승흐름 알림 읽음 처리."""
    from datetime import datetime
    try:
        set_app_state(READ_KEY["uptrend"], datetime.now().isoformat())
        return {"read": True}
    except Exception as e:
        logger.error(f"Failed to mark uptrend read: {e}")
        raise HTTPException(status_code=500, detail="읽음 처리 실패")


@router.delete("/uptrend")
async def clear_uptrend_alerts(before: Optional[str] = Query(None)):
    """상승흐름 알림 이력 정리."""
    try:
        return _clear_signal_history("uptrend", before)
    except Exception as e:
        logger.error(f"Failed to clear uptrend alerts: {e}")
        raise HTTPException(status_code=500, detail="상승흐름 알림 삭제 실패")


@router.delete("/uptrend/{alert_id}")
async def delete_uptrend_alert(alert_id: int):
    """상승흐름 알림 이력 1건 삭제."""
    try:
        return _delete_signal_alert("uptrend", alert_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete uptrend alert {alert_id}: {e}")
        raise HTTPException(status_code=500, detail="상승흐름 알림 삭제 실패")


# ── 하락흐름(downtrend) ──
@router.get("/downtrend/watchlist")
async def scan_watchlist_down():
    """관심종목 하락흐름 일괄 점검 (읽기 전용)."""
    return await _watchlist("down")


@router.get("/downtrend")
async def get_downtrend_alerts(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
    """하락흐름 확정 알림 이력 + 미읽음 카운트."""
    try:
        return _signal_history("downtrend", limit, offset)
    except Exception as e:
        logger.error(f"Failed to fetch downtrend alerts: {e}")
        raise HTTPException(status_code=500, detail="하락흐름 알림 조회 실패")


@router.post("/downtrend/read")
async def mark_downtrend_read():
    """하락흐름 알림 읽음 처리."""
    from datetime import datetime
    try:
        set_app_state(READ_KEY["downtrend"], datetime.now().isoformat())
        return {"read": True}
    except Exception as e:
        logger.error(f"Failed to mark downtrend read: {e}")
        raise HTTPException(status_code=500, detail="읽음 처리 실패")


@router.delete("/downtrend")
async def clear_downtrend_alerts(before: Optional[str] = Query(None)):
    """하락흐름 알림 이력 정리."""
    try:
        return _clear_signal_history("downtrend", before)
    except Exception as e:
        logger.error(f"Failed to clear downtrend alerts: {e}")
        raise HTTPException(status_code=500, detail="하락흐름 알림 삭제 실패")


@router.delete("/downtrend/{alert_id}")
async def delete_downtrend_alert(alert_id: int):
    """하락흐름 알림 이력 1건 삭제."""
    try:
        return _delete_signal_alert("downtrend", alert_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete downtrend alert {alert_id}: {e}")
        raise HTTPException(status_code=500, detail="하락흐름 알림 삭제 실패")


# ──────────────────────────── CRUD ────────────────────────────


@router.post("/", response_model=AlertRuleResponse)
async def create_alert_rule(rule: AlertRuleCreate):
    """알림 규칙 생성"""
    _validate_rule(rule.alert_type, rule.direction, rule.target_price)

    try:
        with get_db_connection() as conn_or_cursor:
            conn = conn_or_cursor
            cursor = conn.cursor()

            cursor.execute(
                f"""INSERT INTO alert_rules (ticker, alert_type, direction, target_price, memo)
                    VALUES ({PP}, {PP}, {PP}, {PP}, {PP})""",
                (rule.ticker, rule.alert_type, rule.direction, rule.target_price, rule.memo),
            )
            conn.commit()

            new_id = cursor.lastrowid

            cursor.execute(f"SELECT * FROM alert_rules WHERE id = {PP}", (new_id,))
            row = cursor.fetchone()
            return dict(row)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create alert rule: {e}")
        raise HTTPException(status_code=500, detail="알림 규칙 생성 실패")


@router.get("/{ticker}", response_model=List[AlertRuleResponse])
async def get_alert_rules(
    ticker: str,
    active_only: bool = Query(True, description="활성 규칙만 조회"),
):
    """종목별 알림 규칙 목록 조회"""
    try:
        with get_db_connection() as conn_or_cursor:
            cursor = get_cursor(conn_or_cursor)

            if active_only:
                is_active_cmp = "is_active = 1"
                cursor.execute(
                    f"SELECT * FROM alert_rules WHERE ticker = {PP} AND {is_active_cmp} ORDER BY created_at DESC",
                    (ticker,),
                )
            else:
                cursor.execute(
                    f"SELECT * FROM alert_rules WHERE ticker = {PP} ORDER BY created_at DESC",
                    (ticker,),
                )

            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Failed to fetch alert rules for {ticker}: {e}")
        raise HTTPException(status_code=500, detail="알림 규칙 조회 실패")


@router.put("/{rule_id}", response_model=AlertRuleResponse)
async def update_alert_rule(rule_id: int, rule: AlertRuleUpdate):
    """알림 규칙 수정"""
    try:
        with get_db_connection() as conn_or_cursor:
            conn = conn_or_cursor
            cursor = conn.cursor()

            cursor.execute(f"SELECT * FROM alert_rules WHERE id = {PP}", (rule_id,))
            existing = cursor.fetchone()
            if not existing:
                raise HTTPException(status_code=404, detail="알림 규칙을 찾을 수 없습니다")

            updates = []
            params = []

            if rule.alert_type is not None:
                if rule.alert_type not in VALID_ALERT_TYPES:
                    raise HTTPException(status_code=400, detail=f"alert_type은 {VALID_ALERT_TYPES} 중 하나여야 합니다")
                updates.append(f"alert_type = {PP}")
                params.append(rule.alert_type)

            if rule.direction is not None:
                if rule.direction not in VALID_DIRECTIONS:
                    raise HTTPException(status_code=400, detail=f"direction은 {VALID_DIRECTIONS} 중 하나여야 합니다")
                updates.append(f"direction = {PP}")
                params.append(rule.direction)

            if rule.target_price is not None:
                updates.append(f"target_price = {PP}")
                params.append(rule.target_price)

            if rule.memo is not None:
                updates.append(f"memo = {PP}")
                params.append(rule.memo)

            if rule.is_active is not None:
                updates.append(f"is_active = {PP}")
                params.append(rule.is_active)

            if not updates:
                raise HTTPException(status_code=400, detail="수정할 필드가 없습니다")

            params.append(rule_id)
            cursor.execute(
                f"UPDATE alert_rules SET {', '.join(updates)} WHERE id = {PP}",
                params,
            )
            conn.commit()

            cursor.execute(f"SELECT * FROM alert_rules WHERE id = {PP}", (rule_id,))
            row = cursor.fetchone()
            return dict(row)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update alert rule {rule_id}: {e}")
        raise HTTPException(status_code=500, detail="알림 규칙 수정 실패")


@router.delete("/{rule_id}")
async def delete_alert_rule(rule_id: int):
    """알림 규칙 삭제"""
    try:
        with get_db_connection() as conn_or_cursor:
            conn = conn_or_cursor
            cursor = conn.cursor()

            cursor.execute(f"SELECT id FROM alert_rules WHERE id = {PP}", (rule_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="알림 규칙을 찾을 수 없습니다")

            cursor.execute(f"DELETE FROM alert_history WHERE rule_id = {PP}", (rule_id,))
            cursor.execute(f"DELETE FROM alert_rules WHERE id = {PP}", (rule_id,))
            conn.commit()

            return {"deleted": True, "id": rule_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete alert rule {rule_id}: {e}")
        raise HTTPException(status_code=500, detail="알림 규칙 삭제 실패")
