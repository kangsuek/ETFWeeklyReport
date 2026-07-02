"""
주식 펀더멘털 데이터 수집기

네이버 모바일 JSON API에서 재무제표를 수집하여 stock_fundamentals DB에 저장합니다.
- /stock/{code}/finance/annual  : 연간 실적 (최근 3~4개년)
- /stock/{code}/finance/quarter : 분기 실적 (최근 5~6개 분기)
- /stock/{code}/integration     : 현재 배당수익률 (totalInfos.dividendYieldRatio)

구형 main.naver HTML '기업실적분석' 표 파싱(최신 연간 1개 열만, date=수집일) 대비:
- 결산기 말일을 date로 하는 다년치/분기 행을 모두 저장 → 재무 추세 조회 가능
- 추정치(isConsensus=Y) 열은 미래 날짜 행이 '최신'으로 노출되는 것을 막기 위해 제외
- 배당성향은 주당배당금/EPS로 계산 (JSON에 시가배당률·배당성향 행이 없음)

단위: 매출/이익 → 억원, 비율 → %
"""

import calendar
import logging
from datetime import date
from typing import Optional, Dict, Any, List

from app.database import get_db_connection
from app.services.naver_stock_api import MOBILE_API_BASE, get_json, parse_number

logger = logging.getLogger(__name__)

# finance rowList 행 제목 → DB 컬럼 매핑
_ROW_MAP = {
    '매출액': 'revenue',
    '영업이익': 'operating_profit',
    '당기순이익': 'net_profit',
    '영업이익률': 'operating_margin',
    '순이익률': 'net_margin',
    'ROE': 'roe',
    '부채비율': 'debt_ratio',
    '당좌비율': 'current_ratio',
    'EPS': 'eps',
    'PER': 'per',
    'BPS': 'bps',
    'PBR': 'pbr',
}

# 주당배당금은 stock_distributions에 별도 저장 + 배당성향 계산에 사용
_DIVIDEND_ROW = '주당배당금'


def _period_key_to_date(key: str) -> Optional[date]:
    """'202512' / '202603' (YYYYMM) → 해당 월 말일 date."""
    try:
        year, month = int(key[:4]), int(key[4:6])
        return date(year, month, calendar.monthrange(year, month)[1])
    except (ValueError, IndexError, TypeError):
        return None


def _fetch_finance(ticker: str, period_type: str) -> Optional[Dict[str, Any]]:
    """finance/annual 또는 finance/quarter JSON 조회."""
    url = f"{MOBILE_API_BASE}/stock/{ticker}/finance/{period_type}"
    data = get_json(url)
    if not isinstance(data, dict):
        return None
    return data.get('financeInfo')


def _fetch_current_dividend_yield(ticker: str) -> Optional[float]:
    """integration.totalInfos에서 현재 배당수익률(%) 조회."""
    data = get_json(f"{MOBILE_API_BASE}/stock/{ticker}/integration")
    if not isinstance(data, dict):
        return None
    for info in data.get('totalInfos') or []:
        if info.get('code') == 'dividendYieldRatio':
            return parse_number(info.get('value'))
    return None


def _extract_period_rows(finance_info: dict) -> List[Dict[str, Any]]:
    """
    financeInfo → 결산기별 지표 dict 목록 (실적 확정분만, 오름차순).

    Returns:
        [{'date': date, 'revenue': ..., 'per': ..., 'dividend_per_share': ...}, ...]
    """
    if not finance_info:
        return []

    # 실적 확정(isConsensus=N) 기간만 취한다.
    periods = [
        t['key'] for t in (finance_info.get('trTitleList') or [])
        if t.get('isConsensus') == 'N' and t.get('key')
    ]
    if not periods:
        return []

    # 행 제목 → {기간키: 값} 테이블 구성
    row_values: Dict[str, Dict[str, Optional[float]]] = {}
    for row in finance_info.get('rowList') or []:
        title = row.get('title')
        columns = row.get('columns') or {}
        row_values[title] = {
            key: parse_number((columns.get(key) or {}).get('value'))
            for key in periods
        }

    results = []
    for key in periods:
        period_date = _period_key_to_date(key)
        if not period_date:
            continue

        record: Dict[str, Any] = {'date': period_date}
        for title, column in _ROW_MAP.items():
            record[column] = row_values.get(title, {}).get(key)
        record['dividend_per_share'] = row_values.get(_DIVIDEND_ROW, {}).get(key)

        # 배당성향(%) = 주당배당금 / EPS × 100 (둘 다 있을 때만)
        dps, eps = record['dividend_per_share'], record.get('eps')
        record['payout_ratio'] = round(dps / eps * 100, 2) if dps and eps else None

        # 유효 지표가 하나도 없는 기간은 제외
        if any(record.get(c) is not None for c in _ROW_MAP.values()):
            results.append(record)

    results.sort(key=lambda r: r['date'])
    return results


def collect_stock_fundamentals(ticker: str) -> dict:
    """
    주식 종목의 펀더멘털 지표를 수집하여 DB에 저장합니다.

    연간+분기 실적을 결산기 말일 기준 행으로 저장하며,
    기존 행(과거 수집일 기준 포함)은 전량 교체합니다.

    Args:
        ticker: 주식 종목 코드 (etfs 테이블의 type=STOCK 종목)

    Returns:
        {
            'success': bool,
            'ticker': str,
            'date': str,          # 수집 기준일 (오늘)
            'saved': bool,        # DB 저장 성공 여부
            'dividend_saved': bool,  # 배당 이력 저장 여부
            'error': str | None,
        }
    """
    result = {
        'success': False,
        'ticker': ticker,
        'date': str(date.today()),
        'saved': False,
        'dividend_saved': False,
        'error': None,
    }

    # 1. 연간 + 분기 실적 수집 (같은 결산기는 연간 값이 우선하도록 분기를 먼저 넣는다)
    annual = _extract_period_rows(_fetch_finance(ticker, 'annual'))
    quarter = _extract_period_rows(_fetch_finance(ticker, 'quarter'))

    if not annual and not quarter:
        result['error'] = 'No fundamental data from finance API'
        logger.warning(f"[stock_fundamentals] No data for {ticker}")
        return result

    merged: Dict[date, Dict[str, Any]] = {}
    for record in quarter + annual:
        merged[record['date']] = record
    records = sorted(merged.values(), key=lambda r: r['date'])

    # 2. 최신 실적 행에 현재 배당수익률 반영 (finance API에는 시가배당률 행이 없음)
    current_yield = _fetch_current_dividend_yield(ticker)
    for record in records:
        record['dividend_yield'] = None
    if current_yield is not None and records:
        records[-1]['dividend_yield'] = current_yield

    # 3. DB 저장 — 기존 행 전량 교체 (과거 수집일(date=오늘) 기준 행 정리 포함)
    try:
        with get_db_connection() as conn_or_cursor:
            conn = conn_or_cursor
            cursor = conn.cursor()

            cursor.execute("DELETE FROM stock_fundamentals WHERE ticker = ?", (ticker,))
            cursor.execute(
                "DELETE FROM stock_distributions WHERE ticker = ? AND distribution_type = ?",
                (ticker, '현금배당'),
            )

            for record in records:
                cursor.execute("""
                    INSERT OR REPLACE INTO stock_fundamentals
                        (ticker, date, per, pbr, roe, roa, eps, bps,
                         revenue, operating_profit, net_profit,
                         operating_margin, net_margin,
                         debt_ratio, current_ratio,
                         dividend_yield, payout_ratio)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    ticker, record['date'],
                    record.get('per'), record.get('pbr'),
                    record.get('roe'), None,
                    record.get('eps'), record.get('bps'),
                    record.get('revenue'), record.get('operating_profit'),
                    record.get('net_profit'), record.get('operating_margin'),
                    record.get('net_margin'), record.get('debt_ratio'),
                    record.get('current_ratio'), record.get('dividend_yield'),
                    record.get('payout_ratio'),
                ))

                # 배당 이력 저장 (연간 결산기의 주당배당금이 있을 때)
                if record.get('dividend_per_share'):
                    cursor.execute("""
                        INSERT OR REPLACE INTO stock_distributions
                            (ticker, record_date, amount_per_share, distribution_type, yield_pct)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        ticker, record['date'], record['dividend_per_share'],
                        '현금배당', record.get('dividend_yield'),
                    ))
                    result['dividend_saved'] = True

            conn.commit()
            result['saved'] = True
            logger.info(
                f"[stock_fundamentals] Saved {len(records)} period rows for {ticker} "
                f"({records[0]['date']} ~ {records[-1]['date']})"
            )

        result['success'] = True

    except Exception as e:
        logger.error(f"[stock_fundamentals] DB error for {ticker}: {e}")
        result['error'] = str(e)

    return result
