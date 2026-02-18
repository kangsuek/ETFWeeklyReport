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
                "total_steps": 3,
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
                "total_steps": 3,
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

            # Phase 3: DB 저장
            update_progress(TASK_ID, {
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

            update_progress(TASK_ID, {
                "status": "completed",
                "step": "done",
                "step_index": 3,
                "total_steps": 3,
                "items_collected": saved_count,
                "message": f"수집 완료! {saved_count:,}개 ETF 업데이트 ({duration:.0f}초)"
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
                            "total_steps": 3,
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
        개별 종목 수급 데이터 수집 (외국인/기관 순매수, 주간수익률)

        Args:
            ticker: 종목 코드
            use_rate_limiter: True면 공유 rate limiter 사용, False면 건너뜀 (병렬 수집 시)

        Returns:
            {foreign_net, institutional_net, weekly_return} or None
        """
        url = f"https://finance.naver.com/item/frgn.naver?code={ticker}"

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

                    # COALESCE로 새 값이 NULL이면 기존 값 유지 (부분 수집/취소 시 데이터 보존)
                    cursor.execute(f"""
                        UPDATE stock_catalog
                        SET close_price = COALESCE({p}, close_price),
                            daily_change_pct = COALESCE({p}, daily_change_pct),
                            volume = COALESCE({p}, volume),
                            weekly_return = COALESCE({p}, weekly_return),
                            foreign_net = COALESCE({p}, foreign_net),
                            institutional_net = COALESCE({p}, institutional_net),
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
