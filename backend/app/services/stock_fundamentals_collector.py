"""
주식 펀더멘털 데이터 수집기

네이버 금융 종목 메인 페이지의 '기업실적분석' 테이블에서
주요 재무지표를 수집하여 stock_fundamentals DB에 저장합니다.

수집 항목:
- PER, PBR, ROE, EPS, BPS
- 매출액, 영업이익, 당기순이익, 영업이익률, 순이익률
- 부채비율, 당좌비율
- 시가배당률, 배당성향

데이터 기준: 최신 실제 연간 실적 (추정치 제외)
단위: 매출/이익 → 억원, 비율 → %
"""

import logging
import re
from datetime import date
from typing import Optional

from app.database import get_db_connection, USE_POSTGRES
from app.services.naver_finance_scraper import fetch_main_page

logger = logging.getLogger(__name__)

# 기업실적분석 테이블 행 이름 → DB 컬럼 매핑
_ROW_MAP = {
    '매출액':       'revenue',
    '영업이익':     'operating_profit',
    '당기순이익':   'net_profit',
    '영업이익률':   'operating_margin',
    '순이익률':     'net_margin',
    'ROE(지배주주)': 'roe',
    '부채비율':     'debt_ratio',
    '당좌비율':     'current_ratio',
    'EPS(원)':      'eps',
    'PER(배)':      'per',
    'BPS(원)':      'bps',
    'PBR(배)':      'pbr',
    '시가배당률(%)': 'dividend_yield',
    '배당성향(%)':  'payout_ratio',
}

# 주당배당금은 stock_distributions에 별도 저장
_DIVIDEND_ROW = '주당배당금(원)'


def _parse_number(text: str) -> Optional[float]:
    """쉼표·공백 제거 후 float 변환. 변환 불가이거나 '-'이면 None."""
    if not text:
        return None
    cleaned = text.replace(',', '').strip()
    if cleaned in ('', '-', 'N/A'):
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _find_fundamentals_table(soup):
    """
    기업실적분석 테이블을 찾아 반환합니다.
    IFRS / US GAAP / IFRS 별도 등 다양한 클래스에 대응합니다.
    """
    # 1순위: 클래스명으로 찾기 (IFRS)
    for class_name in ('tb_type1_ifrs', 'tb_type1_us', 'tb_type1_k-gaap'):
        table = soup.find('table', {'class': re.compile(class_name)})
        if table:
            return table

    # 2순위: summary 속성으로 찾기
    for table in soup.find_all('table'):
        summary = table.get('summary', '')
        if '기업실적분석' in summary:
            return table

    return None


def _get_latest_annual_idx(table) -> Optional[int]:
    """
    헤더에서 '최근 연간 실적' 열 수를 파악하고,
    (E) 추정치를 제외한 가장 최신 연간 실적 열 인덱스를 반환합니다.
    """
    thead = table.find('thead')
    if not thead:
        return None

    rows = thead.find_all('tr')
    if len(rows) < 2:
        return None

    # 1행: "최근 연간 실적" th의 colspan으로 연간 열 수 확인
    annual_count = 4  # 기본값
    for th in rows[0].find_all('th'):
        if '연간' in th.get_text():
            try:
                annual_count = int(th.get('colspan', 4))
            except (ValueError, TypeError):
                annual_count = 4
            break

    # 2행: 날짜 레이블 파싱
    date_ths = rows[1].find_all('th')
    date_labels = [th.get_text(strip=True) for th in date_ths]

    # 연간 열 중 추정치 없는 가장 최신 열 선택
    for i in range(annual_count - 1, -1, -1):
        if i < len(date_labels) and '(E)' not in date_labels[i]:
            logger.debug(f"Latest actual annual column: idx={i}, label={date_labels[i]}")
            return i

    return None


def collect_stock_fundamentals(ticker: str) -> dict:
    """
    주식 종목의 펀더멘털 지표를 수집하여 DB에 저장합니다.

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

    # 1. 네이버 메인 페이지 수집
    soup = fetch_main_page(ticker)
    if not soup:
        result['error'] = 'Failed to fetch main page'
        return result

    # 2. 기업실적분석 테이블 찾기
    table = _find_fundamentals_table(soup)
    if not table:
        result['error'] = 'Fundamentals table not found'
        logger.warning(f"[stock_fundamentals] Table not found for {ticker}")
        return result

    # 3. 최신 연간 실적 열 인덱스 결정
    col_idx = _get_latest_annual_idx(table)
    if col_idx is None:
        result['error'] = 'Could not determine annual column index'
        return result

    # 4. 데이터 행 파싱
    fundamentals = {}
    dividend_amount = None

    tbody = table.find('tbody')
    if not tbody:
        result['error'] = 'tbody not found'
        return result

    for row in tbody.find_all('tr'):
        th = row.find('th')
        if not th:
            continue

        row_name = th.get_text(strip=True)
        tds = row.find_all('td')

        if col_idx >= len(tds):
            continue

        value = _parse_number(tds[col_idx].get_text(strip=True))

        if row_name in _ROW_MAP:
            fundamentals[_ROW_MAP[row_name]] = value
        elif row_name == _DIVIDEND_ROW:
            dividend_amount = value

    if not fundamentals:
        result['error'] = 'No fundamental data parsed'
        return result

    # 5. stock_fundamentals DB 저장
    today = date.today()

    try:
        with get_db_connection() as conn_or_cursor:
            if USE_POSTGRES:
                cursor = conn_or_cursor
                conn = cursor.connection
            else:
                conn = conn_or_cursor
                cursor = conn.cursor()

            if USE_POSTGRES:
                cursor.execute("""
                    INSERT INTO stock_fundamentals
                        (ticker, date, per, pbr, roe, roa, eps, bps,
                         revenue, operating_profit, net_profit,
                         operating_margin, net_margin,
                         debt_ratio, current_ratio,
                         dividend_yield, payout_ratio)
                    VALUES
                        (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (ticker, date) DO UPDATE SET
                        per=EXCLUDED.per, pbr=EXCLUDED.pbr, roe=EXCLUDED.roe,
                        roa=EXCLUDED.roa, eps=EXCLUDED.eps, bps=EXCLUDED.bps,
                        revenue=EXCLUDED.revenue,
                        operating_profit=EXCLUDED.operating_profit,
                        net_profit=EXCLUDED.net_profit,
                        operating_margin=EXCLUDED.operating_margin,
                        net_margin=EXCLUDED.net_margin,
                        debt_ratio=EXCLUDED.debt_ratio,
                        current_ratio=EXCLUDED.current_ratio,
                        dividend_yield=EXCLUDED.dividend_yield,
                        payout_ratio=EXCLUDED.payout_ratio
                """, (
                    ticker, today,
                    fundamentals.get('per'), fundamentals.get('pbr'),
                    fundamentals.get('roe'), fundamentals.get('roa'),
                    fundamentals.get('eps'), fundamentals.get('bps'),
                    fundamentals.get('revenue'), fundamentals.get('operating_profit'),
                    fundamentals.get('net_profit'), fundamentals.get('operating_margin'),
                    fundamentals.get('net_margin'), fundamentals.get('debt_ratio'),
                    fundamentals.get('current_ratio'), fundamentals.get('dividend_yield'),
                    fundamentals.get('payout_ratio'),
                ))
            else:
                cursor.execute("""
                    INSERT OR REPLACE INTO stock_fundamentals
                        (ticker, date, per, pbr, roe, roa, eps, bps,
                         revenue, operating_profit, net_profit,
                         operating_margin, net_margin,
                         debt_ratio, current_ratio,
                         dividend_yield, payout_ratio)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    ticker, today,
                    fundamentals.get('per'), fundamentals.get('pbr'),
                    fundamentals.get('roe'), fundamentals.get('roa'),
                    fundamentals.get('eps'), fundamentals.get('bps'),
                    fundamentals.get('revenue'), fundamentals.get('operating_profit'),
                    fundamentals.get('net_profit'), fundamentals.get('operating_margin'),
                    fundamentals.get('net_margin'), fundamentals.get('debt_ratio'),
                    fundamentals.get('current_ratio'), fundamentals.get('dividend_yield'),
                    fundamentals.get('payout_ratio'),
                ))

            conn.commit()
            result['saved'] = True
            logger.info(f"[stock_fundamentals] Saved fundamentals for {ticker} on {today}")

            # 6. 배당 이력 저장 (주당배당금이 있을 때만)
            if dividend_amount is not None:
                dividend_yield = fundamentals.get('dividend_yield')
                if USE_POSTGRES:
                    cursor.execute("""
                        INSERT INTO stock_distributions
                            (ticker, record_date, amount_per_share, distribution_type, yield_pct)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (ticker, record_date) DO UPDATE SET
                            amount_per_share=EXCLUDED.amount_per_share,
                            yield_pct=EXCLUDED.yield_pct
                    """, (ticker, today, dividend_amount, '현금배당', dividend_yield))
                else:
                    cursor.execute("""
                        INSERT OR REPLACE INTO stock_distributions
                            (ticker, record_date, amount_per_share, distribution_type, yield_pct)
                        VALUES (?, ?, ?, ?, ?)
                    """, (ticker, today, dividend_amount, '현금배당', dividend_yield))
                conn.commit()
                result['dividend_saved'] = True

        result['success'] = True

    except Exception as e:
        logger.error(f"[stock_fundamentals] DB error for {ticker}: {e}")
        result['error'] = str(e)

    return result
