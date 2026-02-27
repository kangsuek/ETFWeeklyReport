"""
ETF 카탈로그 가격/수급 데이터 수집 서비스

stock_catalog 테이블의 ETF 종목에 대해 가격, 거래량, 수급 데이터를 수집합니다.
"""
import logging
import json
import time
import threading
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from datetime import datetime, date, timedelta
from app.utils.retry import retry_with_backoff
from app.utils.rate_limiter import RateLimiter
from app.constants import DEFAULT_RATE_LIMITER_INTERVAL
from app.database import get_db_connection, USE_POSTGRES
from app.exceptions import ScraperException

logger = logging.getLogger(__name__)


KOSPI_TOP_N_SUPPLY = 200    # 시가총액 상위 200개 - frgn.naver 수급 수집
KOSDAQ_TOP_N_SUPPLY = 300   # 시가총액 상위 300개 - frgn.naver 수급 수집
STOCK_SUPPLY_WORKERS = 10   # 병렬 수급 수집 워커 수


class CatalogDataCollector:
    """ETF 카탈로그 가격/수급 데이터 수집"""

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.rate_limiter = RateLimiter(min_interval=DEFAULT_RATE_LIMITER_INTERVAL)

    def collect_all(self) -> Dict[str, Any]:
        """
        전체 카탈로그 데이터 수집 (ETF 가격+수급 + KOSPI/KOSDAQ 가격)

        Returns:
            수집 통계 dict
        """
        from app.services.progress import update_progress, is_cancelled

        TASK_ID = "catalog-data"

        logger.info("Starting catalog data collection")
        start_time = datetime.now()

        try:
            # Phase 1: ETF 목록 페이지에서 가격/거래량 일괄 수집
            update_progress(TASK_ID, {
                "status": "in_progress",
                "step": "prices",
                "step_index": 0,
                "total_steps": 4,
                "items_collected": 0,
                "message": "ETF 가격/거래량 수집 중..."
            })

            price_data = self._collect_etf_prices()
            logger.info(f"Phase 1 완료: {len(price_data)}개 ETF 가격 수집")

            if is_cancelled(TASK_ID):
                update_progress(TASK_ID, {"status": "cancelled", "message": "수집이 중지되었습니다."})
                logger.info("Catalog data collection cancelled after Phase 1")
                return {"cancelled": True}

            # Phase 2: 개별 종목 수급 데이터 수집
            update_progress(TASK_ID, {
                "status": "in_progress",
                "step": "supply_demand",
                "step_index": 1,
                "total_steps": 4,
                "items_collected": len(price_data),
                "message": f"수급 데이터 수집 중... ({len(price_data):,}개 ETF)"
            })

            supply_data = self._collect_supply_demand(list(price_data.keys()))

            if is_cancelled(TASK_ID):
                # 이미 수집된 데이터는 저장
                logger.info("Cancelled during Phase 2, saving partial data")
                saved_count = self._save_to_database(price_data, supply_data)
                update_progress(TASK_ID, {
                    "status": "cancelled",
                    "message": f"수집 중지됨 (부분 저장: {saved_count:,}개)"
                })
                return {"cancelled": True, "saved_count": saved_count}

            logger.info(f"Phase 2 완료: {len(supply_data)}개 ETF 수급 수집")

            # Phase 3: ETF DB 저장
            update_progress(TASK_ID, {
                "status": "in_progress",
                "step": "saving",
                "step_index": 2,
                "total_steps": 4,
                "items_collected": len(price_data),
                "message": "ETF 데이터 저장 중..."
            })

            saved_count = self._save_to_database(price_data, supply_data)

            if is_cancelled(TASK_ID):
                update_progress(TASK_ID, {"status": "cancelled", "message": "수집이 중지되었습니다."})
                return {"cancelled": True, "saved_count": saved_count}

            # Phase 4: KOSPI/KOSDAQ 가격+수급 업데이트
            update_progress(TASK_ID, {
                "status": "in_progress",
                "step": "stock_prices",
                "step_index": 3,
                "total_steps": 4,
                "items_collected": saved_count,
                "message": "KOSPI/KOSDAQ 가격+수급 업데이트 중..."
            })

            stock_result = self._update_stock_prices()
            logger.info(
                f"Phase 4 완료: {stock_result['updated']}개 KOSPI/KOSDAQ 업데이트 "
                f"(수급 {stock_result['supply_updated']}개, 주간수익률 {stock_result['weekly_calc_count']}개)"
            )

            duration = (datetime.now() - start_time).total_seconds()
            result = {
                "price_count": len(price_data),
                "supply_count": len(supply_data),
                "saved_count": saved_count,
                "stock_updated": stock_result["updated"],
                "stock_supply_updated": stock_result["supply_updated"],
                "stock_weekly_calc": stock_result["weekly_calc_count"],
                "duration_seconds": round(duration, 1),
                "timestamp": datetime.now().isoformat()
            }

            update_progress(TASK_ID, {
                "status": "completed",
                "step": "done",
                "step_index": 4,
                "total_steps": 4,
                "items_collected": saved_count + stock_result["updated"],
                "message": (
                    f"수집 완료! ETF {saved_count:,}개 + "
                    f"주식 {stock_result['updated']:,}개 (수급 {stock_result['supply_updated']:,}개) "
                    f"업데이트 ({duration:.0f}초)"
                )
            })

            logger.info(f"Catalog data collection completed: {result}")
            return result

        except Exception as e:
            update_progress(TASK_ID, {
                "status": "error",
                "message": f"수집 실패: {str(e)}"
            })
            logger.error(f"Catalog data collection failed: {e}", exc_info=True)
            raise ScraperException(f"카탈로그 데이터 수집 실패: {e}")

    def _update_stock_prices(self) -> Dict[str, int]:
        """
        KOSPI/KOSDAQ 종목 가격+수급 데이터 업데이트 (방안 A+B)

        - 전체 종목: sise_market_sum에서 현재가/등락률/거래량 수집
        - 상위 N개(KOSPI 200 + KOSDAQ 300): frgn.naver 병렬 수집으로 수급+주간수익률 추가
        - 나머지 종목: week_base_price 기준으로 7일 누적 weekly_return 계산

        Returns:
            {updated, supply_updated, weekly_calc_count}
        """
        from app.services.ticker_catalog_collector import TickerCatalogCollector

        catalog_collector = TickerCatalogCollector()
        updated = 0
        supply_updated = 0
        weekly_calc_count = 0
        today_str = datetime.now().strftime("%Y-%m-%d")

        # 주간 수익률 기준일: 5거래일 ≈ 7달력일 전 (rolling window)
        today = date.today()
        target_base_date = today - timedelta(days=7)
        target_base_str = target_base_date.isoformat()

        try:
            from app.services.progress import is_cancelled
            
            # Step 1: sise_market_sum에서 전체 가격 수집 (시가총액 내림차순)
            kospi_stocks = catalog_collector._collect_sise_stocks(sosok=0, market="KOSPI", max_pages=80, task_id="catalog-data")
            if is_cancelled("catalog-data"):
                logger.info("Cancelled during KOSPI collection in Phase 4")
                return {"updated": updated, "supply_updated": supply_updated, "weekly_calc_count": weekly_calc_count}
                
            kosdaq_stocks = catalog_collector._collect_sise_stocks(sosok=1, market="KOSDAQ", max_pages=110, task_id="catalog-data")
            if is_cancelled("catalog-data"):
                logger.info("Cancelled during KOSDAQ collection in Phase 4")
                return {"updated": updated, "supply_updated": supply_updated, "weekly_calc_count": weekly_calc_count}
                
            logger.info(f"sise 수집: KOSPI {len(kospi_stocks)}개, KOSDAQ {len(kosdaq_stocks)}개")

            # {ticker: stock_dict} 매핑
            price_map = {s["ticker"]: s for s in kospi_stocks + kosdaq_stocks}

            # Step 1.5: price_map에서 ETF 티커 제외 (FIX-08)
            # sise_market_sum에는 KOSPI 상장 ETF도 포함되지만, ETF는 Phase 1~3에서
            # 이미 처리됨. Phase 4에서 ETF를 처리하면 weekly_return이 0.0으로 덮어써짐.
            with get_db_connection() as conn_or_cursor2:
                if USE_POSTGRES:
                    cursor2 = conn_or_cursor2
                else:
                    cursor2 = conn_or_cursor2.cursor()
                cursor2.execute("SELECT ticker FROM stock_catalog WHERE market = 'ETF'")
                etf_tickers = {row["ticker"] if isinstance(row, dict) else row[0] for row in cursor2.fetchall()}
            if etf_tickers:
                excluded = sum(1 for t in price_map if t in etf_tickers)
                price_map = {t: s for t, s in price_map.items() if t not in etf_tickers}
                if excluded > 0:
                    logger.info(f"Phase 4: ETF {excluded}개 제외 (price_map에서)")

            # Step 2: DB에서 기존 상태 일괄 조회
            with get_db_connection() as conn_or_cursor:
                if USE_POSTGRES:
                    cursor = conn_or_cursor
                    conn = cursor.connection
                    p = "%s"
                else:
                    conn = conn_or_cursor
                    cursor = conn.cursor()
                    p = "?"

                cursor.execute("""
                    SELECT ticker, close_price, week_base_price, week_base_date, weekly_return
                    FROM stock_catalog
                    WHERE market IN ('KOSPI', 'KOSDAQ')
                """)
                rows = cursor.fetchall()

                existing_db = {}
                for row in rows:
                    if isinstance(row, dict):
                        existing_db[row["ticker"]] = row
                    else:
                        existing_db[row[0]] = {
                            "ticker": row[0],
                            "close_price": row[1],
                            "week_base_price": row[2],
                            "week_base_date": row[3],
                            "weekly_return": row[4],
                        }

            # Step 3: 시가총액 상위 N개 frgn.naver 수급 병렬 수집
            top_stocks = kospi_stocks[:KOSPI_TOP_N_SUPPLY] + kosdaq_stocks[:KOSDAQ_TOP_N_SUPPLY]
            top_tickers = [s["ticker"] for s in top_stocks]
            logger.info(f"수급 수집 대상: {len(top_tickers)}개 (KOSPI {KOSPI_TOP_N_SUPPLY} + KOSDAQ {KOSDAQ_TOP_N_SUPPLY})")

            supply_map: Dict[str, Dict[str, Any]] = {}
            lock = threading.Lock()

            def fetch_supply(ticker: str):
                if is_cancelled("catalog-data"):
                    return ticker, None
                data = self._fetch_supply_data(ticker, use_rate_limiter=False)
                return ticker, data

            with ThreadPoolExecutor(max_workers=STOCK_SUPPLY_WORKERS) as executor:
                futures = {executor.submit(fetch_supply, t): t for t in top_tickers}
                for future in as_completed(futures):
                    if is_cancelled("catalog-data"):
                        logger.info("Cancelled during supply collection loop in Phase 4. Cancelling remaining futures.")
                        for f in futures:
                            f.cancel()
                        break
                        
                    ticker, data = future.result()
                    with lock:
                        if data:
                            supply_map[ticker] = data

            if is_cancelled("catalog-data"):
                logger.info("Cancelled after supply collection in Phase 4")
                return {"updated": updated, "supply_updated": supply_updated, "weekly_calc_count": weekly_calc_count}

            logger.info(f"수급 수집 완료: {len(supply_map)}/{len(top_tickers)}개")

            # Step 4+5: 전체 종목 UPDATE
            with get_db_connection() as conn_or_cursor:
                if USE_POSTGRES:
                    cursor = conn_or_cursor
                    conn = cursor.connection
                    p = "%s"
                else:
                    conn = conn_or_cursor
                    cursor = conn.cursor()
                    p = "?"

                top_ticker_set = set(top_tickers)

                for ticker, s in price_map.items():
                    close_price = s.get("close_price")
                    daily_change_pct = s.get("daily_change_pct")
                    volume = s.get("volume")
                    db_row = existing_db.get(ticker, {})

                    if ticker in top_ticker_set and ticker in supply_map:
                        # 상위 N개: 수급 포함 업데이트
                        # COALESCE: None(NULL) 값이 들어올 경우 기존 DB 값 보존 (FIX-02)
                        # week_base_date: target_base_str(이번 주 월요일) 사용 (FIX-03)
                        sup = supply_map[ticker]
                        cursor.execute(f"""
                            UPDATE stock_catalog
                            SET close_price = {p}, daily_change_pct = {p}, volume = {p},
                                weekly_return  = COALESCE({p}, weekly_return),
                                monthly_return = COALESCE({p}, monthly_return),
                                ytd_return     = COALESCE({p}, ytd_return),
                                foreign_net = {p}, institutional_net = {p},
                                week_base_price = {p}, week_base_date = {p},
                                ytd_base_date = COALESCE({p}, ytd_base_date),
                                catalog_updated_at = CURRENT_TIMESTAMP
                            WHERE ticker = {p}
                        """, (
                            close_price, daily_change_pct, volume,
                            sup.get("weekly_return"),
                            sup.get("monthly_return"),
                            sup.get("ytd_return"),
                            sup.get("foreign_net"), sup.get("institutional_net"),
                            close_price, target_base_str,
                            sup.get("ytd_base_date"),
                            ticker
                        ))
                        if cursor.rowcount > 0:
                            updated += 1
                            supply_updated += 1
                    else:
                        # 나머지 종목: 5거래일 rolling window 기준 weekly_return 계산
                        week_base_price = db_row.get("week_base_price")
                        week_base_date = db_row.get("week_base_date")

                        # 기준일로부터 경과일 계산 (5~9일이면 유효 = 5거래일 ± 휴일 여유)
                        base_days_ago = None
                        if week_base_date:
                            try:
                                base_days_ago = (today - date.fromisoformat(week_base_date)).days
                            except (ValueError, TypeError):
                                pass

                        if base_days_ago is not None and 5 <= base_days_ago <= 9 and week_base_price and week_base_price > 0 and close_price:
                            # 유효 기준일 → 기준가 vs 현재가로 5거래일 수익률 계산
                            new_weekly_return = round(
                                (close_price - week_base_price) / week_base_price * 100, 2
                            )
                            weekly_calc_count += 1
                            new_base_price = week_base_price
                            new_base_date = week_base_date  # 기존 기준일 유지
                        else:
                            # 기준일 유효하지 않음 → 오늘 현재가로 기준 초기화, 수익률 0%
                            new_base_price = close_price
                            new_base_date = today.isoformat()  # 오늘 실제 날짜 저장
                            new_weekly_return = 0.0

                        cursor.execute(f"""
                            UPDATE stock_catalog
                            SET close_price = {p}, daily_change_pct = {p}, volume = {p},
                                weekly_return = COALESCE({p}, weekly_return),
                                week_base_price = {p}, week_base_date = {p},
                                catalog_updated_at = CURRENT_TIMESTAMP
                            WHERE ticker = {p}
                        """, (
                            close_price, daily_change_pct, volume,
                            new_weekly_return,
                            new_base_price, new_base_date,
                            ticker
                        ))
                        if cursor.rowcount > 0:
                            updated += 1

                conn.commit()

        except Exception as e:
            logger.error(f"Failed to update KOSPI/KOSDAQ prices: {e}", exc_info=True)

        return {"updated": updated, "supply_updated": supply_updated, "weekly_calc_count": weekly_calc_count}

    @retry_with_backoff(
        max_retries=3,
        base_delay=1.0,
        exceptions=(requests.exceptions.RequestException, json.JSONDecodeError, ValueError)
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
            raise ValueError(f"ETF API 응답 실패: {data.get('resultCode')}")

        etf_list = data['result'].get('etfItemList', [])

        for item in etf_list:
            ticker = item.get('itemcode')
            if not ticker:
                continue

            # risefall: "2"=상승, "5"=하락, "3"=보합
            change_rate = item.get('changeRate')
            risefall = item.get('risefall')
            if risefall == '5' and change_rate is not None:
                change_rate = -abs(change_rate)
            elif risefall == '3':
                change_rate = 0.0

            result[ticker] = {
                'name': item.get('itemname'),
                'close_price': item.get('nowVal'),
                'daily_change_pct': change_rate,
                'volume': item.get('quant'),
            }

        logger.info(f"ETF JSON API: {len(result)}개 ETF 가격 수집")
        return result

    def _collect_supply_demand(self, tickers: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        개별 종목의 수급(외국인/기관 순매수) 데이터를 병렬 수집

        ThreadPoolExecutor로 최대 MAX_WORKERS개 동시 요청하여 수집 속도를 높입니다.
        서버 부하 방지를 위해 각 요청 후 REQUEST_DELAY만큼 대기합니다.

        Args:
            tickers: 수집 대상 티커 목록

        Returns:
            {ticker: {foreign_net, institutional_net, weekly_return}} dict
        """
        from app.services.progress import update_progress, is_cancelled

        MAX_WORKERS = 5
        REQUEST_DELAY = 0.2  # 각 워커 요청 후 대기 (초)

        result = {}
        total = len(tickers)
        completed_count = 0
        lock = threading.Lock()

        def fetch_one(ticker: str):
            """단일 종목 수급 데이터 수집 (워커 스레드)"""
            if is_cancelled("catalog-data"):
                return ticker, None

            try:
                data = self._fetch_supply_data(ticker, use_rate_limiter=False)
                time.sleep(REQUEST_DELAY)
                return ticker, data
            except Exception as e:
                logger.warning(f"[{ticker}] 수급 데이터 수집 실패: {e}")
                return ticker, None

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(fetch_one, t): t for t in tickers}

            for future in as_completed(futures):
                ticker, data = future.result()

                with lock:
                    completed_count += 1
                    if data:
                        result[ticker] = data

                    if completed_count % 10 == 0 or completed_count == 1:
                        pct = round(completed_count / total * 100)
                        update_progress("catalog-data", {
                            "status": "in_progress",
                            "step": "supply_demand",
                            "step_index": 1,
                            "total_steps": 4,
                            "items_collected": completed_count,
                            "items_total": total,
                            "percent": pct,
                            "message": f"수급 데이터 수집 중... ({completed_count:,}/{total:,})"
                        })

                    if completed_count % 50 == 0:
                        logger.info(f"수급 데이터 수집 진행: {completed_count}/{total}")

                if is_cancelled("catalog-data"):
                    logger.info(f"수급 데이터 수집 중지됨 ({completed_count}/{total})")
                    for f in futures:
                        f.cancel()
                    break

        return result

    def _fetch_supply_data(self, ticker: str, use_rate_limiter: bool = True) -> Optional[Dict[str, Any]]:
        """
        개별 종목 수급 데이터 수집 (외국인/기관 순매수, 주간/월간/YTD 수익률)

        Args:
            ticker: 종목 코드
            use_rate_limiter: True면 공유 rate limiter 사용, False면 건너뜀 (병렬 수집 시)

        Returns:
            {foreign_net, institutional_net, weekly_return, monthly_return, ytd_return} or None
        """
        foreign_net = None
        institutional_net = None
        prices_with_date = []  # [(date, price), ...]
        current_year = date.today().year

        # YTD 계산을 위해 올해 첫 거래일(1월 1~15일)에 도달할 때까지 동적으로 페이지 수집
        # 최대 15페이지(약 300거래일 = 1년치 이상)로 상한 설정 (FIX-01)
        MAX_SUPPLY_PAGES = 15

        def _has_ytd_base(prices):
            """수집 목록에 올해 1월 1~15일 데이터가 있으면 True (첫 거래일 도달 판단)"""
            for d, _ in prices:
                if d.year == current_year and d.month == 1 and d.day <= 15:
                    return True
            return False

        page = 1
        while page <= MAX_SUPPLY_PAGES:
            url = f"https://finance.naver.com/item/frgn.naver?code={ticker}&page={page}"

            try:
                if use_rate_limiter:
                    with self.rate_limiter:
                        response = requests.get(url, headers=self.headers, timeout=10)
                        response.raise_for_status()
                else:
                    response = requests.get(url, headers=self.headers, timeout=10)
                    response.raise_for_status()

                soup = BeautifulSoup(response.text, 'html.parser')

                tables = soup.find_all('table', {'class': 'type2'})
                if len(tables) < 2:
                    break

                table = tables[1]
                rows = table.find_all('tr')

                page_data_count = 0
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) < 7:
                        continue

                    date_text = cols[0].get_text(strip=True)
                    if not date_text or '.' not in date_text:
                        continue

                    try:
                        row_date = datetime.strptime(date_text, "%Y.%m.%d").date()
                        # 종가 (1번째 컬럼)
                        close_text = cols[1].get_text(strip=True).replace(',', '')
                        if close_text:
                            prices_with_date.append((row_date, float(close_text)))
                            page_data_count += 1

                        # 최근 1일 수급만 (첫 번째 페이지의 첫 번째 데이터 행)
                        if page == 1 and foreign_net is None:
                            inst_text = cols[5].get_text(strip=True).replace(',', '')
                            frgn_text = cols[6].get_text(strip=True).replace(',', '')
                            institutional_net = self._parse_int(inst_text)
                            foreign_net = self._parse_int(frgn_text)

                    except (ValueError, IndexError):
                        continue

                # 페이지에 데이터가 없으면 더 이상 페이지 없음
                if page_data_count == 0:
                    break

                # 월간(20개) + YTD 기준일 도달 시 수집 완료
                if len(prices_with_date) >= 20 and _has_ytd_base(prices_with_date):
                    break

                page += 1

            except Exception as e:
                logger.debug(f"[{ticker}] 수급 데이터 페이지 {page} 수집 실패: {e}")
                break

        if not prices_with_date:
            return None

        # 수익률 계산 함수
        def calc_ret(curr, prev):
            if prev and prev > 0:
                return round((curr - prev) / prev * 100, 2)
            return None

        current_val = prices_with_date[0][1]

        # 1. 주간수익률 (5거래일 전 종가 기준)
        weekly_return = calc_ret(current_val, prices_with_date[5][1] if len(prices_with_date) >= 6 else None)

        # 2. 월간수익률 (20거래일)
        monthly_return = calc_ret(current_val, prices_with_date[19][1] if len(prices_with_date) >= 20 else None)

        # 3. YTD수익률 (올해 첫 거래일)
        # _has_ytd_base()로 실제 1월 데이터에 도달했는지 확인 후 계산 (FIX-05)
        ytd_return = None
        ytd_base_date = None
        this_year_prices = [p for p in prices_with_date if p[0].year == current_year]
        if this_year_prices and _has_ytd_base(prices_with_date):
            # 올해의 가장 오래된 데이터 = 올해 첫 거래일에 가장 가까운 데이터
            base_val = this_year_prices[-1][1]
            ytd_base_date = this_year_prices[-1][0].strftime("%Y.%m.%d")
            ytd_return = calc_ret(current_val, base_val)
        elif this_year_prices:
            # 1월 데이터 미도달: 수집된 올해 데이터 중 가장 오래된 것으로 fallback
            # (신규 상장 종목 또는 연말 수집 실패 상황 대비)
            base_val = this_year_prices[-1][1]
            ytd_base_date = this_year_prices[-1][0].strftime("%Y.%m.%d")
            ytd_return = calc_ret(current_val, base_val)
            logger.debug(f"[{ticker}] YTD fallback: 1월 데이터 미도달, {this_year_prices[-1][0]} 기준 사용")

        return {
            'foreign_net': foreign_net,
            'institutional_net': institutional_net,
            'weekly_return': weekly_return,
            'monthly_return': monthly_return,
            'ytd_return': ytd_return,
            'ytd_base_date': ytd_base_date,
        }

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
                    name = price.get('name') or ticker

                    if USE_POSTGRES:
                        # UPSERT: 신규 ETF도 INSERT (stock_catalog가 비어 있을 때 포함)
                        cursor.execute(f"""
                            INSERT INTO stock_catalog
                                (ticker, name, type, market, is_active,
                                 close_price, daily_change_pct, volume,
                                 weekly_return, monthly_return, ytd_return,
                                 foreign_net, institutional_net,
                                 ytd_base_date,
                                 catalog_updated_at)
                            VALUES ({p}, {p}, 'ETF', 'ETF', TRUE,
                                    {p}, {p}, {p},
                                    {p}, {p}, {p},
                                    {p}, {p},
                                    {p},
                                    {p})
                            ON CONFLICT (ticker) DO UPDATE SET
                                name = COALESCE(EXCLUDED.name, stock_catalog.name),
                                close_price = COALESCE(EXCLUDED.close_price, stock_catalog.close_price),
                                daily_change_pct = COALESCE(EXCLUDED.daily_change_pct, stock_catalog.daily_change_pct),
                                volume = COALESCE(EXCLUDED.volume, stock_catalog.volume),
                                weekly_return = COALESCE(EXCLUDED.weekly_return, stock_catalog.weekly_return),
                                monthly_return = COALESCE(EXCLUDED.monthly_return, stock_catalog.monthly_return),
                                ytd_return = COALESCE(EXCLUDED.ytd_return, stock_catalog.ytd_return),
                                foreign_net = COALESCE(EXCLUDED.foreign_net, stock_catalog.foreign_net),
                                institutional_net = COALESCE(EXCLUDED.institutional_net, stock_catalog.institutional_net),
                                ytd_base_date = COALESCE(EXCLUDED.ytd_base_date, stock_catalog.ytd_base_date),
                                catalog_updated_at = EXCLUDED.catalog_updated_at
                        """, (
                            ticker, name,
                            price.get('close_price'),
                            price.get('daily_change_pct'),
                            price.get('volume'),
                            supply.get('weekly_return'),
                            supply.get('monthly_return'),
                            supply.get('ytd_return'),
                            supply.get('foreign_net'),
                            supply.get('institutional_net'),
                            supply.get('ytd_base_date'),
                            now,
                        ))
                    else:
                        # SQLite: UPDATE only (기존 동작 유지)
                        cursor.execute(f"""
                            UPDATE stock_catalog
                            SET close_price = COALESCE({p}, close_price),
                                daily_change_pct = COALESCE({p}, daily_change_pct),
                                volume = COALESCE({p}, volume),
                                weekly_return = COALESCE({p}, weekly_return),
                                monthly_return = COALESCE({p}, monthly_return),
                                ytd_return = COALESCE({p}, ytd_return),
                                foreign_net = COALESCE({p}, foreign_net),
                                institutional_net = COALESCE({p}, institutional_net),
                                ytd_base_date = COALESCE({p}, ytd_base_date),
                                catalog_updated_at = {p}
                            WHERE ticker = {p}
                        """, (
                            price.get('close_price'),
                            price.get('daily_change_pct'),
                            price.get('volume'),
                            supply.get('weekly_return'),
                            supply.get('monthly_return'),
                            supply.get('ytd_return'),
                            supply.get('foreign_net'),
                            supply.get('institutional_net'),
                            supply.get('ytd_base_date'),
                            now,
                            ticker
                        ))

                    if cursor.rowcount > 0:
                        saved += 1

                # sector가 NULL인 종목에 이름 기반 섹터 자동 매핑
                self._update_sectors(cursor, p)

                conn.commit()

            except Exception as e:
                logger.error(f"DB 저장 실패: {e}", exc_info=True)
                conn.rollback()
                raise

        logger.info(f"stock_catalog 업데이트: {saved}/{len(all_tickers)}건")
        return saved

    def _update_sectors(self, cursor, p: str) -> int:
        """
        sector가 NULL인 종목에 대해 이름 기반으로 섹터 자동 매핑

        Returns:
            업데이트된 종목 수
        """
        # ETF 이름 키워드 → 섹터 매핑 (순서 중요: 먼저 매칭되는 것 우선)
        SECTOR_KEYWORDS = [
            # 반도체
            (['반도체', '필라델피아', 'SOX'], '반도체'),
            # 2차전지/배터리
            (['2차전지', '배터리', '리튬', '에너지저장'], '2차전지'),
            # AI/로봇
            (['AI', '인공지능', '로봇', '자율주행', 'GPT', '생성형'], 'AI/로봇'),
            # 바이오/헬스케어
            (['바이오', '헬스케어', '제약', '의료', '게놈', '진단'], '바이오'),
            # 자동차/모빌리티
            (['자동차', '전기차', 'EV', '모빌리티', '완성차'], '자동차'),
            # 금융
            (['은행', '금융', '보험', '증권', 'KRX은행'], '금융'),
            # 에너지/소재
            (['태양광', '풍력', '신재생', '에너지', '원자력', '우라늄', '탄소'], '에너지'),
            # IT/소프트웨어
            (['소프트웨어', 'IT', '클라우드', '사이버보안', '게임', '미디어', '메타버스', '플랫폼'], 'IT/SW'),
            # 건설/인프라
            (['건설', '인프라', '조선', '해운', '항공', '운송'], '건설/인프라'),
            # 화학/소재
            (['화학', '소재', '철강', '비철금속', '희토류'], '화학/소재'),
            # 식품/유통
            (['식품', '유통', '음식료', '필수소비재'], '식품/유통'),
            # 방산/우주
            (['방산', '우주항공', '국방', '방위'], '방산/우주'),
            # 통신
            (['통신', '5G', '6G', 'K-뉴딜'], '통신'),
            # 부동산/리츠
            (['부동산', '리츠', 'REIT'], '부동산'),
            # 배당
            (['배당', '고배당', '커버드콜', '인컴'], '배당'),
            # 채권
            (['채권', '국채', '회사채', '금리', '국고채', '통안채'], '채권'),
            # 금/원자재 ('금'은 단독 사용 시 오분류 가능하므로 구체적 키워드 사용)
            (['골드', 'GOLD', '금현물', '순금', '은현물', '실버', '원자재', '구리', '곡물', '원유', 'WTI', '천연가스', '금선물'], '원자재'),
            # 미국/해외
            (['미국', 'S&P', '나스닥', 'NASDAQ', 'S&P500', '다우', '선진국', '글로벌'], '해외'),
            # 중국/신흥국
            (['중국', '차이나', '인도', '베트남', '일본', '신흥국'], '해외/신흥'),
            # 레버리지/인버스
            (['레버리지', '2X', '3X'], '레버리지'),
            (['인버스', 'INVERSE'], '인버스'),
            # 코스피/코스닥 지수
            (['코스피200', 'KOSPI', 'TOP10'], '지수'),
            (['코스닥150', 'KOSDAQ'], '코스닥지수'),
        ]

        is_active_cmp = "is_active = true" if USE_POSTGRES else "is_active = 1"
        cursor.execute(f"""
            SELECT ticker, name FROM stock_catalog
            WHERE (sector IS NULL OR sector = '') AND {is_active_cmp}
        """)
        rows = cursor.fetchall()

        updated = 0
        for row in rows:
            ticker = row['ticker'] if isinstance(row, dict) else row[0]
            name = row['name'] if isinstance(row, dict) else row[1]
            if not name:
                continue

            matched_sector = None
            name_upper = name.upper()
            for keywords, sector in SECTOR_KEYWORDS:
                for kw in keywords:
                    if kw.upper() in name_upper:
                        matched_sector = sector
                        break
                if matched_sector:
                    break

            if matched_sector:
                cursor.execute(
                    f"UPDATE stock_catalog SET sector = {p} WHERE ticker = {p}",
                    (matched_sector, ticker)
                )
                if cursor.rowcount > 0:
                    updated += 1

        logger.info(f"섹터 자동 매핑: {updated}/{len(rows)}건 업데이트")
        return updated

    @staticmethod
    def _parse_int(text: str) -> Optional[int]:
        """텍스트를 정수로 변환"""
        try:
            if not text or text.strip() in ('', '-'):
                return None
            return int(text.replace(',', '').strip())
        except (ValueError, AttributeError):
            return None
