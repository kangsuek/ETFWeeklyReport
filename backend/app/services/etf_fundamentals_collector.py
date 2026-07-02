"""
ETF 펀더멘털 데이터 수집 서비스

네이버 증권 모바일 JSON API(m.stock.naver.com)의 etfAnalysis 엔드포인트에서 수집합니다.
구형 finance.naver.com HTML 파싱보다 안정적이고 필드가 풍부합니다.

수집 항목 (→ etf_fundamentals):
- NAV, NAV 일간등락률, 총보수(펀드보수), AUM(순자산총액), 추적오차, 기초지수, 분배(TTM)
수집 항목 (→ etf_holdings):
- 구성종목 상위 10 (섹터는 stock_catalog로 보강)
"""

import json
import logging
import re
from datetime import datetime, date
from typing import Optional, List, Dict, Any

import requests

from app.database import get_db_connection

logger = logging.getLogger(__name__)

_API_BASE = "https://m.stock.naver.com/api/stock"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
    ),
    "Referer": "https://m.stock.naver.com/",
}


def _to_float(v) -> Optional[float]:
    """쉼표·%·+ 제거 후 float. 실패 시 None."""
    if v is None:
        return None
    try:
        return float(str(v).replace(',', '').replace('%', '').replace('+', '').strip())
    except (ValueError, TypeError):
        return None


def _to_int(v) -> Optional[int]:
    f = _to_float(v)
    return int(f) if f is not None else None


def _parse_korean_amount(text) -> Optional[float]:
    """
    '27조 9,110억' / '7,408억' → 억원 단위 float.

    1조 = 10,000억으로 환산하여 억원 단위 숫자를 반환한다.
    단위(조/억)가 없는 순수 숫자면 그대로 float 변환한다.
    """
    if text is None:
        return None
    s = str(text).replace(',', '').replace(' ', '')
    if not s or s in ('-', 'N/A'):
        return None
    try:
        m_jo = re.search(r'(\d+(?:\.\d+)?)조', s)
        m_eok = re.search(r'(\d+(?:\.\d+)?)억', s)
        if not m_jo and not m_eok:
            return float(s)
        total = 0.0
        if m_jo:
            total += float(m_jo.group(1)) * 10000
        if m_eok:
            total += float(m_eok.group(1))
        return total
    except ValueError:
        return None


def _parse_ref_date(d: dict) -> date:
    """etfAnalysis 응답의 기준일(YYYY.MM.DD)을 date로. 없으면 오늘."""
    ref = d.get('returnPerformanceReferenceDate') or d.get('navPerformanceReferenceDate')
    if ref:
        for fmt in ('%Y.%m.%d', '%Y-%m-%d', '%Y/%m/%d'):
            try:
                return datetime.strptime(ref, fmt).date()
            except ValueError:
                continue
    return date.today()


class ETFFundamentalsCollector:
    """ETF 펀더멘털 수집기 (네이버 증권 모바일 JSON API 기반)."""

    def _fetch_analysis(self, ticker: str) -> Optional[Dict[str, Any]]:
        """etfAnalysis JSON 조회. 실패 시 None."""
        url = f"{_API_BASE}/{ticker}/etfAnalysis"
        try:
            resp = requests.get(url, headers=_HEADERS, timeout=10)
            if resp.status_code != 200:
                logger.warning(
                    f"[ETFFundamentals] {ticker} etfAnalysis HTTP {resp.status_code}"
                )
                return None
            return resp.json()
        except Exception as e:
            logger.error(f"[ETFFundamentals] {ticker} fetch error: {e}")
            return None

    def _extract_fundamentals(self, d: dict) -> dict:
        """etfAnalysis → etf_fundamentals 컬럼 매핑."""
        # NAV 일간 변동률: navPerformanceList의 D1
        nav_change_pct = None
        for p in d.get('navPerformanceList', []) or []:
            if p.get('periodTypeCode') == 'D1':
                nav_change_pct = _to_float(p.get('value'))
                break

        div = d.get('dividend') or {}

        # 괴리율(부호 포함): 네이버 동시점 기준. deviationRate는 크기, deviationSign이 부호.
        # (프론트에서 "가격−NAV"를 날짜 불일치로 계산하면 허수가 나오므로 이 값을 저장·사용한다.)
        deviation_rate = _to_float(d.get('deviationRate'))
        if deviation_rate is not None and str(d.get('deviationSign', '')).strip() == '-':
            deviation_rate = -deviation_rate

        # 펀드 섹터 배분 (종목별 섹터는 API 미제공이라 펀드 단위 배분을 저장)
        sector_portfolio = None
        sectors = [
            {'code': s.get('detailTypeCode'), 'weight': _to_float(s.get('weight'))}
            for s in (d.get('sectorPortfolioList') or [])
            if s.get('detailTypeCode')
        ]
        if sectors:
            sector_portfolio = json.dumps(sectors, ensure_ascii=False)

        return {
            'date': _parse_ref_date(d),
            'nav': _to_float(d.get('nav')),
            'nav_change_pct': nav_change_pct,
            'aum': _parse_korean_amount(d.get('totalNav')),          # 억원 단위
            'tracking_error': _to_float(d.get('chaseErrorRate')),
            'expense_ratio': _to_float(d.get('totalFee')),
            'base_index': d.get('etfBaseIndex'),
            'dividend_yield': _to_float(div.get('dividendYieldTtm')),
            'dividend_per_share': _to_float(div.get('dividendPerShareTtm')),
            'sector_portfolio': sector_portfolio,
            'deviation_rate': deviation_rate,
        }

    def _extract_holdings(self, d: dict) -> List[dict]:
        """etfAnalysis → etf_holdings 상위 구성종목."""
        results = []
        for h in d.get('etfTop10MajorConstituentAssets', []) or []:
            code = h.get('itemCode')
            name = h.get('itemName')
            if not code or not name:
                continue
            results.append({
                'stock_code': code,
                'stock_name': name,
                'weight': _to_float(h.get('etfWeight')),
                'shares': _to_int(h.get('stockCount')),
            })
        return results

    def _sector_map(self, cursor, codes: List[str]) -> Dict[str, str]:
        """stock_catalog에서 종목코드→섹터 매핑 (구성종목 섹터 보강)."""
        if not codes:
            return {}
        placeholders = ','.join(['?'] * len(codes))
        cursor.execute(
            f"SELECT ticker, sector FROM stock_catalog WHERE ticker IN ({placeholders})",
            codes,
        )
        return {row[0]: row[1] for row in cursor.fetchall() if row[1]}

    def collect_all(self, ticker: str) -> Dict[str, bool]:
        """
        ETF 펀더멘털 + 구성종목을 한 번의 API 호출로 수집·저장.

        Returns:
            {'nav': bool, 'holdings': bool, 'distributions': bool, 'rebalancing': bool}
        """
        logger.info(f"[ETFFundamentals] collect_all started for {ticker}")
        data = self._fetch_analysis(ticker)
        if not data:
            return {'nav': False, 'holdings': False,
                    'distributions': True, 'rebalancing': True}

        f = self._extract_fundamentals(data)
        holdings = self._extract_holdings(data)
        param = '?'
        nav_ok = False
        holdings_ok = False

        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()

                if f['nav'] is not None:
                    cursor.execute(f"""
                        INSERT OR REPLACE INTO etf_fundamentals
                            (ticker, date, nav, nav_change_pct, aum, tracking_error,
                             expense_ratio, base_index, dividend_yield, dividend_per_share,
                             sector_portfolio, deviation_rate)
                        VALUES ({param},{param},{param},{param},{param},
                                {param},{param},{param},{param},{param},{param},{param})
                    """, (
                        ticker, f['date'], f['nav'], f['nav_change_pct'], f['aum'],
                        f['tracking_error'], f['expense_ratio'], f['base_index'],
                        f['dividend_yield'], f['dividend_per_share'], f['sector_portfolio'],
                        f['deviation_rate'],
                    ))
                    nav_ok = True

                if holdings:
                    sectors = self._sector_map(
                        cursor, [h['stock_code'] for h in holdings]
                    )
                    for h in holdings:
                        cursor.execute(f"""
                            INSERT OR REPLACE INTO etf_holdings
                                (ticker, date, stock_code, stock_name, weight, shares, sector)
                            VALUES ({param},{param},{param},{param},{param},{param},{param})
                        """, (
                            ticker, f['date'], h['stock_code'], h['stock_name'],
                            h['weight'], h['shares'], sectors.get(h['stock_code']),
                        ))
                    holdings_ok = True

                conn.commit()
            logger.info(
                f"[ETFFundamentals] {ticker}: nav={nav_ok}, holdings={len(holdings)}, "
                f"base_index={f['base_index']}, aum={f['aum']}"
            )
        except Exception as e:
            logger.error(
                f"[ETFFundamentals] DB error for {ticker}: {e}", exc_info=True
            )

        return {'nav': nav_ok, 'holdings': holdings_ok,
                'distributions': True, 'rebalancing': True}

    # ── 하위 호환용 개별 메서드 ────────────────────────────────
    def collect_nav_data(self, ticker: str) -> bool:
        return self.collect_all(ticker).get('nav', False)

    def collect_holdings(self, ticker: str) -> bool:
        return self.collect_all(ticker).get('holdings', False)

    def collect_distributions(self, ticker: str) -> bool:
        """분배 정보는 collect_all에서 etf_fundamentals에 함께 저장됨."""
        return True

    def collect_rebalancing(self, ticker: str) -> bool:
        """리밸런싱: 소스 미제공, no-op."""
        return True


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    collector = ETFFundamentalsCollector()
    print(collector.collect_all("069500"))
