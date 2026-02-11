"""
ETF 카탈로그 가격/수급 데이터 수집 서비스

stock_catalog 테이블의 ETF 종목에 대해 가격, 거래량, 수급 데이터를 수집합니다.
"""
import logging
import json
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.utils.retry import retry_with_backoff
from app.utils.rate_limiter import RateLimiter
from app.constants import DEFAULT_RATE_LIMITER_INTERVAL
from app.database import get_db_connection, get_cursor, USE_POSTGRES
from app.exceptions import ScraperException

logger = logging.getLogger(__name__)


class CatalogDataCollector:
    """ETF 카탈로그 가격/수급 데이터 수집"""

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.rate_limiter = RateLimiter(min_interval=DEFAULT_RATE_LIMITER_INTERVAL)

    def collect_all(self) -> Dict[str, Any]:
        """
        전체 ETF 카탈로그 데이터 수집 (가격 + 수급)

        Returns:
            수집 통계 dict
        """
        from app.services.progress import update_progress

        logger.info("Starting catalog data collection")
        start_time = datetime.now()

        try:
            # Phase 1: ETF 목록 페이지에서 가격/거래량 일괄 수집
            update_progress("catalog-data", {
                "status": "in_progress",
                "step": "prices",
                "step_index": 0,
                "total_steps": 3,
                "items_collected": 0,
                "message": "ETF 가격/거래량 수집 중..."
            })

            price_data = self._collect_etf_prices()
            logger.info(f"Phase 1 완료: {len(price_data)}개 ETF 가격 수집")

            # Phase 2: 개별 종목 수급 데이터 수집
            update_progress("catalog-data", {
                "status": "in_progress",
                "step": "supply_demand",
                "step_index": 1,
                "total_steps": 3,
                "items_collected": len(price_data),
                "message": f"수급 데이터 수집 중... ({len(price_data)}개 ETF)"
            })

            supply_data = self._collect_supply_demand(list(price_data.keys()))
            logger.info(f"Phase 2 완료: {len(supply_data)}개 ETF 수급 수집")

            # Phase 3: DB 저장
            update_progress("catalog-data", {
                "status": "in_progress",
                "step": "saving",
                "step_index": 2,
                "total_steps": 3,
                "items_collected": len(price_data),
                "message": "데이터베이스 저장 중..."
            })

            saved_count = self._save_to_database(price_data, supply_data)

            duration = (datetime.now() - start_time).total_seconds()
            result = {
                "price_count": len(price_data),
                "supply_count": len(supply_data),
                "saved_count": saved_count,
                "duration_seconds": round(duration, 1),
                "timestamp": datetime.now().isoformat()
            }

            update_progress("catalog-data", {
                "status": "completed",
                "step": "done",
                "step_index": 3,
                "total_steps": 3,
                "items_collected": saved_count,
                "message": f"수집 완료! {saved_count}개 ETF 업데이트 ({duration:.0f}초)"
            })

            logger.info(f"Catalog data collection completed: {result}")
            return result

        except Exception as e:
            update_progress("catalog-data", {
                "status": "error",
                "message": f"수집 실패: {str(e)}"
            })
            logger.error(f"Catalog data collection failed: {e}", exc_info=True)
            raise ScraperException(f"카탈로그 데이터 수집 실패: {e}")

    @retry_with_backoff(
        max_retries=3,
        base_delay=1.0,
        exceptions=(requests.exceptions.RequestException, requests.exceptions.Timeout)
    )
    def _collect_etf_prices(self) -> Dict[str, Dict[str, Any]]:
        """
        네이버 금융 ETF JSON API로 가격/거래량 일괄 수집

        API: /api/sise/etfItemList.nhn (전체 ETF 한 번에 반환)

        Returns:
            {ticker: {close_price, daily_change_pct, volume}} dict
        """
        result = {}
        url = "https://finance.naver.com/api/sise/etfItemList.nhn?etfType=0&targetColumn=market_sum&sortOrder=desc"

        with self.rate_limiter:
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()

        data = json.loads(response.text)

        if data.get('resultCode') != 'success' or 'result' not in data:
            logger.warning(f"ETF API 응답 실패: {data.get('resultCode')}")
            return result

        etf_list = data['result'].get('etfItemList', [])

        for item in etf_list:
            ticker = item.get('itemcode')
            if not ticker:
                continue

            # risefall: "2"=상승, "5"=하락, "3"=보합
            change_rate = item.get('changeRate')
            if item.get('risefall') == '5' and change_rate is not None:
                change_rate = -abs(change_rate)

            result[ticker] = {
                'close_price': item.get('nowVal'),
                'daily_change_pct': change_rate,
                'volume': item.get('quant'),
            }

        logger.info(f"ETF JSON API: {len(result)}개 ETF 가격 수집")
        return result

    def _collect_supply_demand(self, tickers: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        개별 종목의 수급(외국인/기관 순매수) 데이터 수집

        Args:
            tickers: 수집 대상 티커 목록

        Returns:
            {ticker: {foreign_net, institutional_net, weekly_return}} dict
        """
        from app.services.progress import update_progress

        result = {}
        total = len(tickers)

        for idx, ticker in enumerate(tickers):
            try:
                data = self._fetch_supply_data(ticker)
                if data:
                    result[ticker] = data

                if (idx + 1) % 10 == 0 or idx == 0:
                    pct = round((idx + 1) / total * 100)
                    update_progress("catalog-data", {
                        "status": "in_progress",
                        "step": "supply_demand",
                        "step_index": 1,
                        "total_steps": 3,
                        "items_collected": idx + 1,
                        "items_total": total,
                        "percent": pct,
                        "message": f"수급 데이터 수집 중... ({idx + 1}/{total}, {pct}%)"
                    })

                if (idx + 1) % 50 == 0:
                    logger.info(f"수급 데이터 수집 진행: {idx + 1}/{total}")

            except Exception as e:
                logger.warning(f"[{ticker}] 수급 데이터 수집 실패: {e}")
                continue

        return result

    def _fetch_supply_data(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        개별 종목 수급 데이터 수집 (외국인/기관 순매수, 주간수익률)

        Args:
            ticker: 종목 코드

        Returns:
            {foreign_net, institutional_net, weekly_return} or None
        """
        url = f"https://finance.naver.com/item/frgn.naver?code={ticker}"

        try:
            with self.rate_limiter:
                response = requests.get(url, headers=self.headers, timeout=10)
                response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            tables = soup.find_all('table', {'class': 'type2'})
            if len(tables) < 2:
                return None

            table = tables[1]
            rows = table.find_all('tr')

            foreign_net = None
            institutional_net = None
            prices_for_weekly = []

            for row in rows:
                cols = row.find_all('td')
                if len(cols) < 7:
                    continue

                date_text = cols[0].get_text(strip=True)
                if not date_text or '.' not in date_text:
                    continue

                try:
                    # 종가 (1번째 컬럼)
                    close_text = cols[1].get_text(strip=True).replace(',', '')
                    if close_text:
                        prices_for_weekly.append(float(close_text))

                    # 최근 1일 수급만 (첫 번째 데이터 행)
                    if foreign_net is None:
                        inst_text = cols[5].get_text(strip=True).replace(',', '')
                        frgn_text = cols[6].get_text(strip=True).replace(',', '')
                        institutional_net = self._parse_int(inst_text)
                        foreign_net = self._parse_int(frgn_text)

                    # 주간수익률 계산을 위해 최대 6일치 수집
                    if len(prices_for_weekly) >= 6:
                        break

                except (ValueError, IndexError):
                    continue

            # 주간수익률 계산 (현재가 vs 5일 전)
            weekly_return = None
            if len(prices_for_weekly) >= 2:
                current = prices_for_weekly[0]
                # 5일 전 (또는 가능한 가장 오래된 가격)
                past = prices_for_weekly[min(5, len(prices_for_weekly) - 1)]
                if past > 0:
                    weekly_return = round((current - past) / past * 100, 2)

            return {
                'foreign_net': foreign_net,
                'institutional_net': institutional_net,
                'weekly_return': weekly_return
            }

        except Exception as e:
            logger.debug(f"[{ticker}] 수급 데이터 수집 실패: {e}")
            return None

    def _save_to_database(
        self,
        price_data: Dict[str, Dict[str, Any]],
        supply_data: Dict[str, Dict[str, Any]]
    ) -> int:
        """수집된 데이터를 stock_catalog 테이블에 업데이트"""
        p = "%s" if USE_POSTGRES else "?"
        saved = 0
        now = datetime.now().isoformat()

        with get_db_connection() as conn_or_cursor:
            if USE_POSTGRES:
                cursor = conn_or_cursor
                conn = cursor.connection
            else:
                conn = conn_or_cursor
                cursor = conn.cursor()

            try:
                all_tickers = set(price_data.keys()) | set(supply_data.keys())

                for ticker in all_tickers:
                    price = price_data.get(ticker, {})
                    supply = supply_data.get(ticker, {})

                    cursor.execute(f"""
                        UPDATE stock_catalog
                        SET close_price = {p},
                            daily_change_pct = {p},
                            volume = {p},
                            weekly_return = {p},
                            foreign_net = {p},
                            institutional_net = {p},
                            catalog_updated_at = {p}
                        WHERE ticker = {p}
                    """, (
                        price.get('close_price'),
                        price.get('daily_change_pct'),
                        price.get('volume'),
                        supply.get('weekly_return'),
                        supply.get('foreign_net'),
                        supply.get('institutional_net'),
                        now,
                        ticker
                    ))

                    if cursor.rowcount > 0:
                        saved += 1

                conn.commit()

            except Exception as e:
                logger.error(f"DB 저장 실패: {e}", exc_info=True)
                if USE_POSTGRES:
                    conn.rollback()
                raise

        logger.info(f"stock_catalog 업데이트: {saved}/{len(all_tickers)}건")
        return saved

    @staticmethod
    def _parse_int(text: str) -> Optional[int]:
        """텍스트를 정수로 변환"""
        try:
            if not text or text.strip() in ('', '-'):
                return None
            return int(text.replace(',', '').strip())
        except (ValueError, AttributeError):
            return None
