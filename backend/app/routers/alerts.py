"""
알림 규칙 CRUD API + 알림 트리거 기록
- buy / sell: 목표가 도달 알림
- price_change: 급등/급락 알림 (target_price = 임계 %)
- trading_signal: 외국인·기관 동시 매수/매도 시그널
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List
from pydantic import BaseModel
from app.models import AlertRuleCreate, AlertRuleUpdate, AlertRuleResponse
from app.database import get_db_connection, get_cursor, USE_POSTGRES
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

PP = "%s" if USE_POSTGRES else "?"

# 허용되는 alert_type / direction 조합
VALID_ALERT_TYPES = {"buy", "sell", "price_change", "trading_signal"}
VALID_DIRECTIONS = {"above", "below", "both"}


def _validate_rule(alert_type: str, direction: str, target_price: float):
    """공통 유효성 검사"""
    if alert_type not in VALID_ALERT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"alert_type은 {VALID_ALERT_TYPES} 중 하나여야 합니다",
        )
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
            if USE_POSTGRES:
                cursor = conn_or_cursor
                conn = cursor.connection
            else:
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


# ──────────────────────────── CRUD ────────────────────────────


@router.post("/", response_model=AlertRuleResponse)
async def create_alert_rule(rule: AlertRuleCreate):
    """알림 규칙 생성"""
    _validate_rule(rule.alert_type, rule.direction, rule.target_price)

    try:
        with get_db_connection() as conn_or_cursor:
            if USE_POSTGRES:
                cursor = conn_or_cursor
                conn = cursor.connection
            else:
                conn = conn_or_cursor
                cursor = conn.cursor()

            cursor.execute(
                f"""INSERT INTO alert_rules (ticker, alert_type, direction, target_price, memo)
                    VALUES ({PP}, {PP}, {PP}, {PP}, {PP})""",
                (rule.ticker, rule.alert_type, rule.direction, rule.target_price, rule.memo),
            )
            conn.commit()

            if USE_POSTGRES:
                cursor.execute("SELECT lastval()")
                new_id = cursor.fetchone()["lastval"]
            else:
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
                cursor.execute(
                    f"SELECT * FROM alert_rules WHERE ticker = {PP} AND is_active = 1 ORDER BY created_at DESC",
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
            if USE_POSTGRES:
                cursor = conn_or_cursor
                conn = cursor.connection
            else:
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
            if USE_POSTGRES:
                cursor = conn_or_cursor
                conn = cursor.connection
            else:
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
