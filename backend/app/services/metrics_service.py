"""
지표 계산 서비스 (계산의 단일 정본)

가격/매매동향 데이터로부터 수익률·변동성·MDD·RSI·MACD 등을 계산한다.
프론트엔드는 이 결과를 표시만 하고 자체 계산하지 않는다
(산식 명세: docs/METRICS_SPEC.md).

입력 규약:
- prices_desc: 날짜 내림차순(최신 → 과거) PriceData 리스트 (API 기본 정렬)
- closes_asc: 날짜 오름차순 종가 리스트 (RSI/MACD 계산용)
"""
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# 연환산 기준 상수
TRADING_DAYS_PER_YEAR = 252  # 변동성 연환산(√252)
CALENDAR_DAYS_PER_YEAR = 365  # 수익률 연환산 지수(365/거래일수)
MIN_TRADING_DAYS_FOR_ANNUALIZATION = 60  # 약 3개월 미만은 연환산 표기 안 함


def _close(p: Any) -> float:
    """PriceData 객체 또는 dict에서 종가 추출"""
    return p.close_price if hasattr(p, "close_price") else p["close_price"]


# ---------------------------------------------------------------------------
# 기간 수익률
# ---------------------------------------------------------------------------

def period_return(prices_desc: List[Any]) -> float:
    """기간 수익률(%) — 조회 기간 시작 종가 → 종료 종가"""
    if not prices_desc or len(prices_desc) < 2:
        return 0.0
    first_price = _close(prices_desc[-1])  # 가장 오래된 종가
    last_price = _close(prices_desc[0])  # 최신 종가
    if not first_price:
        return 0.0
    return (last_price - first_price) / first_price * 100


def annualized_return(prices_desc: List[Any]) -> Dict[str, Any]:
    """
    연환산 수익률 — 복리 반영: ((1 + 기간수익률)^(365/거래일수) - 1) * 100

    거래일수(데이터 포인트 수)가 60일 미만이면 연환산하지 않고
    기간 수익률을 그대로 반환한다.

    Returns:
        {"value": float, "label": str, "show_annualized": bool, "note": str|None}
    """
    base = {"value": 0.0, "label": "기간 수익률", "show_annualized": False, "note": None}
    if not prices_desc or len(prices_desc) < 2:
        return base

    trading_days = len(prices_desc)
    first_price = _close(prices_desc[-1])
    last_price = _close(prices_desc[0])
    if not first_price:
        return base

    ret = (last_price - first_price) / first_price

    if trading_days < MIN_TRADING_DAYS_FOR_ANNUALIZATION:
        return {
            "value": ret * 100,
            "label": f"{trading_days}일 수익률",
            "show_annualized": False,
            "note": None,
        }

    annualized = ((1 + ret) ** (CALENDAR_DAYS_PER_YEAR / trading_days) - 1) * 100
    return {
        "value": annualized,
        "label": "연환산 수익률",
        "show_annualized": True,
        "note": "참고용",
    }


# ---------------------------------------------------------------------------
# 변동성 / MDD
# ---------------------------------------------------------------------------

def daily_volatility(prices_desc: List[Any]) -> Optional[float]:
    """일간 변동성(%) — 일간 수익률의 모표준편차"""
    if not prices_desc or len(prices_desc) < 2:
        return None

    daily_returns = []
    for i in range(len(prices_desc) - 1):
        today = _close(prices_desc[i])
        yesterday = _close(prices_desc[i + 1])
        if yesterday and yesterday > 0:
            daily_returns.append((today - yesterday) / yesterday)

    if not daily_returns:
        return None

    mean = sum(daily_returns) / len(daily_returns)
    variance = sum((r - mean) ** 2 for r in daily_returns) / len(daily_returns)
    return (variance ** 0.5) * 100


def annualized_volatility(prices_desc: List[Any]) -> Optional[float]:
    """연환산 변동성(%) — 일간 변동성 × √252"""
    daily = daily_volatility(prices_desc)
    if daily is None:
        return None
    return daily * (TRADING_DAYS_PER_YEAR ** 0.5)


def max_drawdown(prices_desc: List[Any]) -> Optional[Dict[str, float]]:
    """
    최대 낙폭(MDD) — 시간순으로 훑으며 (고점 - 현재가) / 고점 최대값

    Returns:
        {"value": MDD%, "peak": 고점가, "trough": 저점가} 또는 None
    """
    if not prices_desc or len(prices_desc) < 2:
        return None

    prices_asc = [_close(p) for p in reversed(prices_desc)]

    peak = prices_asc[0]
    mdd = 0.0
    peak_price = prices_asc[0]
    trough_price = prices_asc[0]

    for price in prices_asc:
        if price > peak:
            peak = price
        if peak > 0:
            drawdown = (peak - price) / peak * 100
            if drawdown > mdd:
                mdd = drawdown
                peak_price = peak
                trough_price = price

    return {"value": mdd, "peak": peak_price, "trough": trough_price}


# ---------------------------------------------------------------------------
# 기술지표 (RSI / MACD) — 프론트 차트 시리즈 계산과 동일 산식
# ---------------------------------------------------------------------------

def rsi_series(closes_asc: List[float], period: int = 14) -> List[Optional[float]]:
    """RSI (Wilder's smoothing). 입력은 종가 오름차순, 반환 길이 동일 (앞 period개는 None)."""
    n = len(closes_asc)
    if n < period + 1:
        return []

    gains, losses = [], []
    for i in range(1, n):
        change = closes_asc[i] - closes_asc[i - 1]
        gains.append(change if change > 0 else 0.0)
        losses.append(abs(change) if change < 0 else 0.0)

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    result: List[Optional[float]] = [None] * period
    first_rs = 100.0 if avg_loss == 0 else avg_gain / avg_loss
    result.append(100 - 100 / (1 + first_rs))

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        rs = 100.0 if avg_loss == 0 else avg_gain / avg_loss
        result.append(100 - 100 / (1 + rs))

    return result


def _ema_series(values: List[float], period: int) -> List[Optional[float]]:
    """EMA. 첫 EMA는 SMA, 이후 지수 평활. 앞 (period-1)개는 None."""
    n = len(values)
    ema: List[Optional[float]] = [None] * n
    if n < period:
        return ema

    ema[period - 1] = sum(values[:period]) / period
    multiplier = 2 / (period + 1)
    for i in range(period, n):
        ema[i] = (values[i] - ema[i - 1]) * multiplier + ema[i - 1]
    return ema


def macd_series(
    closes_asc: List[float],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> List[Dict[str, Optional[float]]]:
    """MACD(fast EMA - slow EMA)와 Signal(MACD의 EMA). 반환 길이는 입력과 동일."""
    n = len(closes_asc)
    if n < slow + signal:
        return []

    fast_ema = _ema_series(closes_asc, fast)
    slow_ema = _ema_series(closes_asc, slow)

    macd_line: List[Optional[float]] = [
        (fast_ema[i] - slow_ema[i]) if fast_ema[i] is not None and slow_ema[i] is not None else None
        for i in range(n)
    ]

    valid_macd = [v for v in macd_line if v is not None]
    signal_ema = _ema_series(valid_macd, signal)

    result = []
    valid_index = 0
    for i in range(n):
        if macd_line[i] is None:
            result.append({"macd": None, "signal": None, "histogram": None})
        else:
            sig = signal_ema[valid_index]
            histogram = macd_line[i] - sig if sig is not None else None
            result.append({"macd": macd_line[i], "signal": sig, "histogram": histogram})
            valid_index += 1

    return result


