"""
ETF 펀더멘털 데이터 수집 서비스

네이버 금융 종목 메인 페이지에서 실제 데이터를 수집합니다.

수집 항목:
- NAV 추이 (날짜, 종가, NAV, 괴리율) → etf_fundamentals
- 펀드보수 → etf_fundamentals.expense_ratio
- 구성종목 상위 10개 → etf_holdings

1차 범위 외 (네이버 main에 미노출):
- etf_distributions (분배금): no-op
- etf_rebalancing (리밸런싱): no-op
"""

import logging
import re
from datetime import datetime, date
from typing import Optional, List, Dict

from app.database import get_db_connection, USE_POSTGRES
from app.services.naver_finance_scraper import fetch_main_page

logger = logging.getLogger(__name__)


def _parse_number(text: str) -> Optional[float]:
    """쉼표·%·+·공백 제거 후 float 변환. 변환 불가이면 None."""
    if not text:
        return None
    cleaned = re.sub(r'[,+%\s]', '', text.strip())
    if cleaned in ('', '-', 'N/A'):
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_date(text: str) -> Optional[date]:
    """YYYY.MM.DD 형식 → date. 실패 시 None."""
    text = text.strip()
    for fmt in ('%Y.%m.%d', '%Y-%m-%d', '%Y/%m/%d'):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


class ETFFundamentalsCollector:
    """ETF 펀더멘털 데이터 수집기 (네이버 금융 main 페이지 기반)"""

    def collect_nav_data(self, ticker: str) -> bool:
        """
        NAV 추이 테이블과 펀드보수를 수집하여 etf_fundamentals에 저장합니다.

        Args:
            ticker: ETF 종목 코드

        Returns:
            저장 성공 여부
        """
        logger.info(f"[ETFFundamentals] Collecting NAV data for {ticker}")

        soup = fetch_main_page(ticker)
        if not soup:
            logger.error(f"[ETFFundamentals] Failed to fetch page for {ticker}")
            return False

        # 1. 펀드보수 파싱 (투자정보 섹션)
        expense_ratio = self._parse_expense_ratio(soup)
        logger.debug(f"[ETFFundamentals] Expense ratio for {ticker}: {expense_ratio}")

        # 2. NAV 추이 테이블 파싱
        nav_rows = self._parse_nav_table(soup)
        if not nav_rows:
            logger.warning(f"[ETFFundamentals] No NAV data found for {ticker}")
            return False

        # 3. DB 저장
        param = '%s' if USE_POSTGRES else '?'
        try:
            with get_db_connection() as conn_or_cursor:
                if USE_POSTGRES:
                    cursor = conn_or_cursor
                    conn = cursor.connection
                else:
                    conn = conn_or_cursor
                    cursor = conn.cursor()
                saved = 0

                for row in nav_rows:
                    if USE_POSTGRES:
                        cursor.execute(f"""
                            INSERT INTO etf_fundamentals
                                (ticker, date, nav, nav_change_pct, expense_ratio)
                            VALUES ({param},{param},{param},{param},{param})
                            ON CONFLICT (ticker, date) DO UPDATE SET
                                nav=EXCLUDED.nav,
                                nav_change_pct=EXCLUDED.nav_change_pct,
                                expense_ratio=EXCLUDED.expense_ratio
                        """, (ticker, row['date'], row['nav'], row['nav_change_pct'], expense_ratio))
                    else:
                        cursor.execute(f"""
                            INSERT OR REPLACE INTO etf_fundamentals
                                (ticker, date, nav, nav_change_pct, expense_ratio)
                            VALUES ({param},{param},{param},{param},{param})
                        """, (ticker, row['date'], row['nav'], row['nav_change_pct'], expense_ratio))
                    saved += 1

                conn.commit()
            logger.info(f"[ETFFundamentals] Saved {saved} NAV rows for {ticker}")
            return True

        except Exception as e:
            logger.error(f"[ETFFundamentals] DB error saving NAV for {ticker}: {e}")
            return False

    def _parse_expense_ratio(self, soup) -> Optional[float]:
        """펀드보수 테이블에서 총보수(%) 파싱."""
        try:
            # summary="펀드보수 정보" 테이블 찾기
            table = soup.find('table', summary=re.compile('펀드보수'))
            if not table:
                return None
            em = table.find('em')
            if em:
                return _parse_number(em.get_text(strip=True))
        except Exception as e:
            logger.debug(f"[ETFFundamentals] Expense ratio parse error: {e}")
        return None

    def _parse_nav_table(self, soup) -> List[dict]:
        """
        NAV 추이 테이블 파싱.

        Returns:
            [{'date': date, 'nav': float, 'nav_change_pct': float}, ...]
        """
        rows = []
        try:
            # "순자산가치 NAV 추이" 헤딩 탐색 — get_text()로 자식 요소 포함 검색
            heading = soup.find(
                lambda t: re.match(r'^h[2-5]$', t.name) and 'NAV 추이' in t.get_text()
            )
            if heading:
                nav_table = heading.find_next('table')
            else:
                # fallback: 날짜 형식(YYYY.MM.DD) td를 포함하는 첫 번째 table
                nav_table = None
                date_pattern = re.compile(r'^\d{4}\.\d{2}\.\d{2}$')
                for t in soup.find_all('table'):
                    if t.find('td', string=date_pattern):
                        nav_table = t
                        break

            if not nav_table:
                return rows

            for tr in nav_table.find_all('tr'):
                tds = tr.find_all('td')
                if len(tds) < 3:
                    continue

                row_date = _parse_date(tds[0].get_text(strip=True))
                if not row_date:
                    continue

                # 컬럼: 날짜, 종가, NAV, 괴리율
                nav = _parse_number(tds[2].get_text(strip=True))
                nav_change_pct = _parse_number(tds[3].get_text(strip=True)) if len(tds) > 3 else None

                if nav:
                    rows.append({
                        'date': row_date,
                        'nav': nav,
                        'nav_change_pct': nav_change_pct,
                    })

        except Exception as e:
            logger.error(f"[ETFFundamentals] NAV table parse error: {e}")
        return rows

    def collect_distributions(self, ticker: str) -> bool:
        """
        분배금 수집 — 네이버 main 페이지에 미노출.
        1차 범위 외: no-op.
        """
        logger.debug(f"[ETFFundamentals] Distributions skipped (out of scope) for {ticker}")
        return True

    def collect_rebalancing(self, ticker: str) -> bool:
        """
        리밸런싱 수집 — 네이버 main 페이지에 미노출.
        1차 범위 외: no-op.
        """
        logger.debug(f"[ETFFundamentals] Rebalancing skipped (out of scope) for {ticker}")
        return True

    def collect_holdings(self, ticker: str) -> bool:
        """
        구성종목 상위 10개를 수집하여 etf_holdings에 저장합니다.

        Args:
            ticker: ETF 종목 코드

        Returns:
            저장 성공 여부
        """
        logger.info(f"[ETFFundamentals] Collecting holdings for {ticker}")

        soup = fetch_main_page(ticker)
        if not soup:
            return False

        holdings = self._parse_holdings_table(soup)
        if not holdings:
            logger.warning(f"[ETFFundamentals] No holdings data found for {ticker}")
            return False

        today = date.today()
        param = '%s' if USE_POSTGRES else '?'
        try:
            with get_db_connection() as conn_or_cursor:
                if USE_POSTGRES:
                    cursor = conn_or_cursor
                    conn = cursor.connection
                else:
                    conn = conn_or_cursor
                    cursor = conn.cursor()
                saved = 0

                for h in holdings:
                    if USE_POSTGRES:
                        cursor.execute(f"""
                            INSERT INTO etf_holdings
                                (ticker, date, stock_code, stock_name, weight, shares)
                            VALUES ({param},{param},{param},{param},{param},{param})
                            ON CONFLICT (ticker, date, stock_code) DO UPDATE SET
                                stock_name=EXCLUDED.stock_name,
                                weight=EXCLUDED.weight,
                                shares=EXCLUDED.shares
                        """, (ticker, today, h['stock_code'], h['stock_name'], h['weight'], h['shares']))
                    else:
                        cursor.execute(f"""
                            INSERT OR REPLACE INTO etf_holdings
                                (ticker, date, stock_code, stock_name, weight, shares)
                            VALUES ({param},{param},{param},{param},{param},{param})
                        """, (ticker, today, h['stock_code'], h['stock_name'], h['weight'], h['shares']))
                    saved += 1

                conn.commit()
            logger.info(f"[ETFFundamentals] Saved {saved} holdings for {ticker}")
            return True

        except Exception as e:
            logger.error(f"[ETFFundamentals] DB error saving holdings for {ticker}: {e}")
            return False

    def _parse_holdings_table(self, soup) -> List[dict]:
        """
        구성종목 테이블 파싱 (class="tb_type1 tb_type1_a").

        Returns:
            [{'stock_code': str, 'stock_name': str, 'weight': float, 'shares': int}, ...]
        """
        results = []
        try:
            # 1순위: class에 tb_type1_a 포함하는 table 탐색 (KODEX 등)
            table = soup.find('table', class_=re.compile(r'tb_type1_a'))

            # 2순위: summary에 '상위' + '종목' 또는 '구성' 포함
            if not table:
                for t in soup.find_all('table'):
                    summ = t.get('summary', '')
                    if ('상위' in summ or '구성' in summ) and ('종목' in summ or '10' in summ):
                        table = t
                        break

            # 3순위: 헤더 행에 '구성종목' 또는 '구성비중' 텍스트 포함 (ACE 등)
            if not table:
                for t in soup.find_all('table'):
                    first_row = t.find('tr')
                    if first_row:
                        header_text = first_row.get_text()
                        if '구성종목' in header_text or '구성비중' in header_text:
                            table = t
                            break

            if not table:
                return results

            for tr in table.find_all('tr'):
                tds = tr.find_all('td')
                if len(tds) < 3:
                    continue

                # 첫 번째 td: 종목 링크 → 종목코드·종목명
                first_td = tds[0]
                link = first_td.find('a')
                if not link:
                    continue

                stock_name = link.get_text(strip=True)
                href = link.get('href', '')
                code_match = re.search(r'code=(\d+)', href)
                if not code_match:
                    continue
                stock_code = code_match.group(1)

                # 두 번째 td: 주식수
                shares_str = tds[1].get_text(strip=True).replace(',', '')
                try:
                    shares = int(shares_str) if shares_str and shares_str != '-' else None
                except ValueError:
                    shares = None

                # 세 번째 td: 구성비중 (21.52%)
                weight = _parse_number(tds[2].get_text(strip=True))

                if stock_code and stock_name and weight is not None:
                    results.append({
                        'stock_code': stock_code,
                        'stock_name': stock_name,
                        'weight': weight,
                        'shares': shares,
                    })

                if len(results) >= 10:
                    break

        except Exception as e:
            logger.error(f"[ETFFundamentals] Holdings parse error: {e}")
        return results

    def collect_all(self, ticker: str) -> Dict[str, bool]:
        """
        모든 펀더멘털 데이터 수집 (단일 페이지 요청 최적화).

        Args:
            ticker: ETF 종목 코드

        Returns:
            {'nav': bool, 'holdings': bool, 'distributions': bool, 'rebalancing': bool}
        """
        logger.info(f"[ETFFundamentals] collect_all started for {ticker}")

        # 한 번만 페이지를 가져와서 NAV와 holdings를 모두 파싱
        soup = fetch_main_page(ticker)
        if not soup:
            logger.error(f"[ETFFundamentals] Failed to fetch page for {ticker}")
            return {'nav': False, 'holdings': False, 'distributions': True, 'rebalancing': True}

        # NAV + 펀드보수
        expense_ratio = self._parse_expense_ratio(soup)
        nav_rows = self._parse_nav_table(soup)

        nav_ok = False
        if nav_rows:
            param = '%s' if USE_POSTGRES else '?'
            try:
                with get_db_connection() as conn_or_cursor:
                    if USE_POSTGRES:
                        cursor = conn_or_cursor
                        conn = cursor.connection
                    else:
                        conn = conn_or_cursor
                        cursor = conn.cursor()
                    for row in nav_rows:
                        if USE_POSTGRES:
                            cursor.execute(f"""
                                INSERT INTO etf_fundamentals
                                    (ticker, date, nav, nav_change_pct, expense_ratio)
                                VALUES ({param},{param},{param},{param},{param})
                                ON CONFLICT (ticker, date) DO UPDATE SET
                                    nav=EXCLUDED.nav,
                                    nav_change_pct=EXCLUDED.nav_change_pct,
                                    expense_ratio=EXCLUDED.expense_ratio
                            """, (ticker, row['date'], row['nav'], row['nav_change_pct'], expense_ratio))
                        else:
                            cursor.execute(f"""
                                INSERT OR REPLACE INTO etf_fundamentals
                                    (ticker, date, nav, nav_change_pct, expense_ratio)
                                VALUES ({param},{param},{param},{param},{param})
                            """, (ticker, row['date'], row['nav'], row['nav_change_pct'], expense_ratio))
                    conn.commit()
                nav_ok = True
                logger.info(f"[ETFFundamentals] Saved {len(nav_rows)} NAV rows for {ticker}")
            except Exception as e:
                logger.error(f"[ETFFundamentals] DB error (NAV) for {ticker}: {e}")

        # 구성종목
        holdings = self._parse_holdings_table(soup)
        holdings_ok = False
        if holdings:
            today = date.today()
            param = '%s' if USE_POSTGRES else '?'
            try:
                with get_db_connection() as conn_or_cursor:
                    if USE_POSTGRES:
                        cursor = conn_or_cursor
                        conn = cursor.connection
                    else:
                        conn = conn_or_cursor
                        cursor = conn.cursor()
                    for h in holdings:
                        if USE_POSTGRES:
                            cursor.execute(f"""
                                INSERT INTO etf_holdings
                                    (ticker, date, stock_code, stock_name, weight, shares)
                                VALUES ({param},{param},{param},{param},{param},{param})
                                ON CONFLICT (ticker, date, stock_code) DO UPDATE SET
                                    stock_name=EXCLUDED.stock_name,
                                    weight=EXCLUDED.weight,
                                    shares=EXCLUDED.shares
                            """, (ticker, today, h['stock_code'], h['stock_name'], h['weight'], h['shares']))
                        else:
                            cursor.execute(f"""
                                INSERT OR REPLACE INTO etf_holdings
                                    (ticker, date, stock_code, stock_name, weight, shares)
                                VALUES ({param},{param},{param},{param},{param},{param})
                            """, (ticker, today, h['stock_code'], h['stock_name'], h['weight'], h['shares']))
                    conn.commit()
                holdings_ok = True
                logger.info(f"[ETFFundamentals] Saved {len(holdings)} holdings for {ticker}")
            except Exception as e:
                logger.error(f"[ETFFundamentals] DB error (holdings) for {ticker}: {e}")

        results = {
            'nav': nav_ok,
            'holdings': holdings_ok,
            'distributions': True,   # no-op
            'rebalancing': True,      # no-op
        }
        logger.info(f"[ETFFundamentals] collect_all completed for {ticker}: {results}")
        return results


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    collector = ETFFundamentalsCollector()
    results = collector.collect_all("487240")
    print(f"\nCollection results: {results}")
