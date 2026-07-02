"""
네이버 금융에서 전체 종목 목록 수집

한국 주식/ETF 전체 목록을 수집하여 stock_catalog 테이블에 저장합니다.

- 주식(코스피/코스닥): 네이버 모바일 JSON API(/api/stocks/marketValue/{시장})
  구형 sise_market_sum HTML 190여 페이지 파싱을 대체 (페이지당 100건, stockEndType으로 주식만 필터)
- ETF: finance.naver.com/api/sise/etfItemList.nhn JSON
  Selenium 기반 동적 페이지 수집을 대체 (문자 포함 신형 코드 지원 확인됨)
"""
import logging
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from app.utils.retry import retry_with_backoff
from app.utils.rate_limiter import RateLimiter
from app.constants import DEFAULT_RATE_LIMITER_INTERVAL
from app.database import get_db_connection, get_cursor
from app.exceptions import ScraperException
from app.services.naver_stock_api import MOBILE_API_BASE, HEADERS, get_json, parse_number, parse_int

logger = logging.getLogger(__name__)

# marketValue JSON 페이지 병렬 수집 워커 수 (총 ~45페이지라 부담 적음)
SISE_PAGE_WORKERS = 8
# marketValue API의 페이지당 최대 건수 (100 초과 시 서버가 에러 응답)
MARKET_VALUE_PAGE_SIZE = 100

# 검색 결과 캐시 (최대 128개 쿼리 캐싱, 5분 TTL)
_search_cache: Dict[str, tuple[List[Dict[str, Any]], datetime]] = {}
_CACHE_TTL = timedelta(minutes=5)
_MAX_CACHE_SIZE = 128


class TickerCatalogCollector:
    """네이버 금융에서 종목 목록 수집 서비스"""

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.rate_limiter = RateLimiter(min_interval=DEFAULT_RATE_LIMITER_INTERVAL)

    def collect_all_stocks(self) -> Dict[str, Any]:
        """
        전체 종목 목록 수집 (코스피, 코스닥, ETF)

        Returns:
            Dict with collection statistics
        """
        from app.services.progress import update_progress

        logger.info("Starting ticker catalog collection from Naver Finance")

        all_stocks = []

        try:
            # 1. 코스피 종목 수집
            update_progress("ticker-catalog", {
                "status": "in_progress",
                "step": "kospi",
                "step_index": 0,
                "total_steps": 4,
                "items_collected": 0,
                "message": "코스피 종목 수집 중..."
            })
            logger.info("Collecting KOSPI stocks...")
            kospi_stocks = self._collect_kospi_stocks()
            all_stocks.extend(kospi_stocks)
            logger.info(f"Collected {len(kospi_stocks)} KOSPI stocks")

            # 2. 코스닥 종목 수집
            update_progress("ticker-catalog", {
                "status": "in_progress",
                "step": "kosdaq",
                "step_index": 1,
                "total_steps": 4,
                "items_collected": len(kospi_stocks),
                "message": f"코스닥 종목 수집 중... (코스피 {len(kospi_stocks)}개 완료)"
            })
            logger.info("Collecting KOSDAQ stocks...")
            kosdaq_stocks = self._collect_kosdaq_stocks()
            all_stocks.extend(kosdaq_stocks)
            logger.info(f"Collected {len(kosdaq_stocks)} KOSDAQ stocks")

            # 3. ETF 종목 수집
            update_progress("ticker-catalog", {
                "status": "in_progress",
                "step": "etf",
                "step_index": 2,
                "total_steps": 4,
                "items_collected": len(kospi_stocks) + len(kosdaq_stocks),
                "message": f"ETF 종목 수집 중... (코스피 {len(kospi_stocks)}개, 코스닥 {len(kosdaq_stocks)}개 완료)"
            })
            logger.info("Collecting ETF stocks...")
            etf_stocks = self._collect_etf_stocks()
            all_stocks.extend(etf_stocks)
            logger.info(f"Collected {len(etf_stocks)} ETF stocks")

            # 4. 데이터베이스에 저장
            update_progress("ticker-catalog", {
                "status": "in_progress",
                "step": "saving",
                "step_index": 3,
                "total_steps": 4,
                "items_collected": len(all_stocks),
                "message": f"데이터베이스에 저장 중... (총 {len(all_stocks)}개)"
            })
            logger.info(f"Saving {len(all_stocks)} stocks to database...")
            saved_count = self._save_to_database(all_stocks)

            # 5. 검색 캐시 무효화 (새로운 데이터가 추가되었으므로)
            self.clear_search_cache()

            result = {
                "total_collected": len(all_stocks),
                "kospi_count": len(kospi_stocks),
                "kosdaq_count": len(kosdaq_stocks),
                "etf_count": len(etf_stocks),
                "saved_count": saved_count,
                "timestamp": datetime.now().isoformat()
            }

            update_progress("ticker-catalog", {
                "status": "completed",
                "step": "done",
                "step_index": 4,
                "total_steps": 4,
                "items_collected": len(all_stocks),
                "message": f"수집 완료! 총 {saved_count}개 저장"
            })

            logger.info(f"Ticker catalog collection completed: {result}")
            return result

        except Exception as e:
            update_progress("ticker-catalog", {
                "status": "error",
                "message": f"수집 실패: {str(e)}"
            })
            logger.error(f"Error collecting ticker catalog: {e}", exc_info=True)
            raise ScraperException(f"종목 목록 수집 실패: {e}")

    def _fetch_market_value_page(self, market: str, page: int) -> Optional[Dict[str, Any]]:
        """
        marketValue JSON 단일 페이지 조회.

        Returns:
            응답 dict({'totalCount', 'stocks', ...}). 요청/파싱 오류는 None.
        """
        url = f"{MOBILE_API_BASE}/stocks/marketValue/{market}"
        data = get_json(url, params={"page": page, "pageSize": MARKET_VALUE_PAGE_SIZE})
        if not isinstance(data, dict):
            return None
        return data

    @staticmethod
    def _parse_market_value_rows(rows: List[dict], market: str) -> List[Dict[str, Any]]:
        """
        marketValue 응답의 stocks 배열 → stock_catalog 저장 형식으로 변환.

        목록에는 ETF/ETN도 섞여 있으므로 stockEndType == 'stock'만 취한다
        (ETF는 etfItemList에서 별도 수집; ETN은 주식이 아니므로 제외).
        """
        stocks = []
        for s in rows:
            if s.get('stockEndType') != 'stock':
                continue
            ticker = s.get('itemCode')
            name = s.get('stockName')
            if not ticker or not name:
                continue
            volume = parse_int(s.get('accumulatedTradingVolume'))
            stocks.append({
                "ticker": ticker,
                "name": name,
                "type": "STOCK",
                "market": market,
                "sector": None,
                "listed_date": None,
                "is_active": 1,
                "close_price": parse_number(s.get('closePrice')),
                "daily_change_pct": parse_number(s.get('fluctuationsRatio')),
                "volume": volume,
            })
        return stocks

    def _collect_sise_stocks(self, sosok: int, market: str, max_pages: int) -> List[Dict[str, Any]]:
        """
        네이버 모바일 JSON API에서 종목 목록 + 가격 데이터 수집 (KOSPI/KOSDAQ 공통)

        1페이지로 totalCount를 얻어 전체 페이지 수를 확정한 뒤 나머지를 병렬 수집한다.
        시가총액 내림차순 순서를 보존하기 위해 페이지 오름차순으로 합친다.

        Args:
            sosok: (하위 호환용, 무시됨 — market 문자열로 시장을 지정)
            market: 'KOSPI' | 'KOSDAQ'
            max_pages: 페이지 수 상한 (안전장치)
        """
        first = self._fetch_market_value_page(market, 1)
        if not first:
            logger.error(f"{market} marketValue page 1 fetch failed")
            return []

        total_count = first.get('totalCount') or 0
        total_pages = min(max_pages, -(-total_count // MARKET_VALUE_PAGE_SIZE))
        stocks = self._parse_market_value_rows(first.get('stocks') or [], market)
        logger.debug(f"{market}: totalCount={total_count}, pages={total_pages}")

        if total_pages <= 1:
            return stocks

        # 2페이지부터 병렬 수집 후 페이지 순서대로 병합
        results: Dict[int, Optional[Dict[str, Any]]] = {}
        with ThreadPoolExecutor(max_workers=SISE_PAGE_WORKERS) as executor:
            futures = {
                executor.submit(self._fetch_market_value_page, market, p): p
                for p in range(2, total_pages + 1)
            }
            for future in as_completed(futures):
                results[futures[future]] = future.result()

        for p in range(2, total_pages + 1):
            data = results.get(p)
            if not data:
                logger.warning(f"{market} page {p} fetch failed — 해당 페이지 건너뜀")
                continue
            page_stocks = self._parse_market_value_rows(data.get('stocks') or [], market)
            stocks.extend(page_stocks)
            logger.debug(f"{market} page {p}: collected {len(page_stocks)} stocks")

        return stocks

    @retry_with_backoff(
        max_retries=3,
        base_delay=1.0,
        exceptions=(requests.exceptions.RequestException, requests.exceptions.Timeout)
    )
    def _collect_kospi_stocks(self) -> List[Dict[str, Any]]:
        """코스피 종목 목록 + 가격 데이터 수집"""
        return self._collect_sise_stocks(sosok=0, market="KOSPI", max_pages=80)

    @retry_with_backoff(
        max_retries=3,
        base_delay=1.0,
        exceptions=(requests.exceptions.RequestException, requests.exceptions.Timeout)
    )
    def _collect_kosdaq_stocks(self) -> List[Dict[str, Any]]:
        """코스닥 종목 목록 + 가격 데이터 수집"""
        return self._collect_sise_stocks(sosok=1, market="KOSDAQ", max_pages=110)

    @retry_with_backoff(
        max_retries=3,
        base_delay=1.0,
        exceptions=(requests.exceptions.RequestException, requests.exceptions.Timeout)
    )
    def _collect_etf_stocks(self) -> List[Dict[str, Any]]:
        """
        ETF 종목 목록 수집 (etfItemList JSON — 전체 ETF를 1회 호출로 반환)

        구형 sise/etf.naver는 JavaScript 동적 로딩이라 Selenium이 필요했으나,
        JSON 엔드포인트는 문자 포함 신형 코드까지 전체 목록을 그대로 제공한다.
        """
        url = "https://finance.naver.com/api/sise/etfItemList.nhn"

        with self.rate_limiter:
            response = requests.get(url, headers=HEADERS, timeout=10)
            response.raise_for_status()

        try:
            items = response.json().get('result', {}).get('etfItemList', []) or []
        except ValueError as e:
            logger.error(f"ETF list JSON parse error: {e}")
            return []

        stocks = []
        seen_tickers = set()
        for item in items:
            ticker = item.get('itemcode')
            name = item.get('itemname')
            if not ticker or not name or ticker in seen_tickers:
                continue
            seen_tickers.add(ticker)
            stocks.append({
                "ticker": ticker,
                "name": name,
                "type": "ETF",
                "market": "ETF",
                "sector": None,
                "listed_date": None,
                "is_active": 1,
                "close_price": parse_number(item.get('nowVal')),
                "daily_change_pct": parse_number(item.get('changeRate')),
                "volume": parse_int(item.get('quant')),
            })

        logger.info(f"Collected {len(stocks)} ETF stocks from etfItemList JSON")
        return stocks
    
    def _save_to_database(self, stocks: List[Dict[str, Any]]) -> int:
        """
        수집한 종목 목록을 데이터베이스에 저장

        기존 종목과 비교하여:
        - 신규 종목: 추가
        - 기존 종목: 업데이트 (종목명 변경 반영)
        - 상장폐지 종목: is_active = 0/FALSE로 표시
        """
        if not stocks:
            return 0

        saved_count = 0
        updated_count = 0
        deactivated_count = 0

        # SQLite 파라미터 플레이스홀더
        param_placeholder = "?"

        with get_db_connection() as conn_or_cursor:
            conn = conn_or_cursor
            cursor = conn.cursor()

            try:
                # 현재 수집된 종목의 티커 코드 집합
                collected_tickers = {stock["ticker"] for stock in stocks}

                # 1단계: 먼저 수집된 종목을 모두 저장 (is_active = 1/TRUE로 설정)
                failed_stocks = []
                
                for stock in stocks:
                    try:
                        # 데이터 검증
                        if not stock.get("ticker") or not stock.get("name") or not stock.get("type"):
                            logger.warning(f"Skipping invalid stock data: {stock}")
                            failed_stocks.append(stock.get("ticker", "unknown"))
                            continue
                        
                        # 기존 종목인지 확인
                        cursor.execute(f"SELECT name FROM stock_catalog WHERE ticker = {param_placeholder}", (stock["ticker"],))
                        existing = cursor.fetchone()

                        if existing:
                            # 기존 종목 업데이트 (종목명 변경 반영)
                            existing_name = existing[0]
                            if existing_name != stock["name"]:
                                logger.debug(f"Updating stock name: {stock['ticker']} - {existing_name} -> {stock['name']}")
                            updated_count += 1
                        else:
                            # 신규 종목 추가
                            logger.debug(f"Adding new stock: {stock['ticker']} - {stock['name']}")

                        close_price = stock.get("close_price")
                        daily_change_pct = stock.get("daily_change_pct")
                        volume = stock.get("volume")
                        # 가격 데이터가 있으면 catalog_updated_at 설정
                        has_price = close_price is not None

                        cursor.execute("""
                            INSERT INTO stock_catalog
                            (ticker, name, type, market, sector, listed_date, last_updated, is_active,
                             close_price, daily_change_pct, volume, catalog_updated_at)
                            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?,
                                    ?, ?, ?, CASE WHEN ? THEN CURRENT_TIMESTAMP ELSE NULL END)
                            ON CONFLICT(ticker) DO UPDATE SET
                                name = EXCLUDED.name,
                                type = EXCLUDED.type,
                                market = EXCLUDED.market,
                                sector = EXCLUDED.sector,
                                listed_date = EXCLUDED.listed_date,
                                last_updated = CURRENT_TIMESTAMP,
                                is_active = EXCLUDED.is_active,
                                close_price = COALESCE(EXCLUDED.close_price, stock_catalog.close_price),
                                daily_change_pct = COALESCE(EXCLUDED.daily_change_pct, stock_catalog.daily_change_pct),
                                volume = COALESCE(EXCLUDED.volume, stock_catalog.volume),
                                catalog_updated_at = CASE WHEN EXCLUDED.catalog_updated_at IS NOT NULL
                                                     THEN EXCLUDED.catalog_updated_at
                                                     ELSE stock_catalog.catalog_updated_at END
                        """, (
                            stock["ticker"],
                            stock["name"],
                            stock["type"],
                            stock["market"],
                            stock["sector"],
                            stock["listed_date"],
                            stock["is_active"],
                            close_price,
                            daily_change_pct,
                            volume,
                            1 if has_price else 0,
                        ))
                        saved_count += 1
                    except Exception as e:
                        logger.error(f"Failed to save stock {stock.get('ticker')}: {e}", exc_info=True)
                        failed_stocks.append(stock.get("ticker", "unknown"))
                        # SQLite는 continue로 계속 진행
                        continue
                
                # 실패한 종목이 있는 경우 로그 출력
                if failed_stocks:
                    logger.warning(f"Failed to save {len(failed_stocks)} stocks: {failed_stocks[:10]}{'...' if len(failed_stocks) > 10 else ''}")

                # 2단계: 수집된 종목 저장 후, 상장폐지 종목 찾기 및 비활성화
                # 기존 데이터베이스의 모든 종목 조회 (수집 전 상태)
                cursor.execute("SELECT ticker FROM stock_catalog")
                all_existing_tickers = {row[0] for row in cursor.fetchall()}

                # 상장폐지된 종목 찾기 (기존에는 있지만 수집된 목록에는 없음)
                deactivated_tickers = all_existing_tickers - collected_tickers

                # 상장폐지 종목 비활성화
                if deactivated_tickers:
                    placeholders = ','.join(['?'] * len(deactivated_tickers))
                    cursor.execute(f"""
                        UPDATE stock_catalog
                        SET is_active = 0, last_updated = CURRENT_TIMESTAMP
                        WHERE ticker IN ({placeholders})
                    """, list(deactivated_tickers))
                    deactivated_count = cursor.rowcount
                    logger.info(f"Deactivated {deactivated_count} stocks (delisted)")

                conn.commit()
            except Exception as e:
                # 트랜잭션 에러 발생 시 rollback
                logger.error(f"Database transaction error: {e}", exc_info=True)
                raise

        logger.info(
            f"Saved {saved_count} stocks to stock_catalog table "
            f"(updated: {updated_count}, deactivated: {deactivated_count})"
        )
        
        # 저장 건수와 수집 건수가 다른 경우 경고
        if len(stocks) != saved_count:
            logger.warning(
                f"Collection count mismatch: collected {len(stocks)} stocks but saved {saved_count} stocks. "
                f"Difference: {len(stocks) - saved_count} stocks failed to save."
            )
        
        return saved_count

    def search_stocks(self, query: str, stock_type: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        """
        종목 목록 검색 (자동완성용)
        
        검색 결과는 5분간 캐싱되어 빠른 응답을 제공합니다.
        
        Args:
            query: 검색어 (티커 코드 또는 종목명)
            stock_type: 종목 타입 필터 (STOCK, ETF)
            limit: 최대 결과 수
        
        Returns:
            검색 결과 리스트
        """
        if not query or len(query) < 2:
            return []
        
        # 캐시 키 생성
        cache_key = f"{query.lower()}:{stock_type or 'all'}:{limit}"
        now = datetime.now()
        
        # 캐시 확인
        if cache_key in _search_cache:
            cached_result, cache_time = _search_cache[cache_key]
            if now - cache_time < _CACHE_TTL:
                logger.debug(f"Cache hit for query: {query}")
                return cached_result
            else:
                # 만료된 캐시 제거
                del _search_cache[cache_key]
        
        # 캐시 크기 제한 (LRU 방식)
        if len(_search_cache) >= _MAX_CACHE_SIZE:
            # 가장 오래된 항목 제거
            oldest_key = min(_search_cache.keys(), key=lambda k: _search_cache[k][1])
            del _search_cache[oldest_key]
        
        # 데이터베이스에서 검색
        # SQLite 파라미터 플레이스홀더
        p = "?"

        with get_db_connection() as conn_or_cursor:
            cursor = get_cursor(conn_or_cursor)

            # 티커 코드 또는 종목명으로 검색
            # 검색 시에는 is_active 필터를 제거하여 모든 종목 검색 가능
            # (활성 종목 우선 정렬)
            if stock_type:
                cursor.execute(f"""
                    SELECT ticker, name, type, market, sector
                    FROM stock_catalog
                    WHERE type = {p}
                      AND (ticker LIKE {p} OR name LIKE {p})
                    ORDER BY
                        is_active DESC,
                        CASE
                            WHEN ticker = {p} THEN 1
                            WHEN ticker LIKE {p} THEN 2
                            WHEN name LIKE {p} THEN 3
                            ELSE 4
                        END,
                        name
                    LIMIT {p}
                """, (
                    stock_type,
                    f"%{query}%",
                    f"%{query}%",
                    query,
                    f"{query}%",
                    f"{query}%",
                    limit
                ))
            else:
                cursor.execute(f"""
                    SELECT ticker, name, type, market, sector
                    FROM stock_catalog
                    WHERE (ticker LIKE {p} OR name LIKE {p})
                    ORDER BY
                        is_active DESC,
                        CASE
                            WHEN ticker = {p} THEN 1
                            WHEN ticker LIKE {p} THEN 2
                            WHEN name LIKE {p} THEN 3
                            ELSE 4
                        END,
                        name
                    LIMIT {p}
                """, (
                    f"%{query}%",
                    f"%{query}%",
                    query,
                    f"{query}%",
                    f"{query}%",
                    limit
                ))
            
            rows = cursor.fetchall()
            
            result = [
                {
                    "ticker": row["ticker"],
                    "name": row["name"],
                    "type": row["type"],
                    "market": row["market"],
                    "sector": row["sector"]
                }
                for row in rows
            ]
            
            # 결과 캐싱
            _search_cache[cache_key] = (result, now)
            logger.debug(f"Cached search result for query: {query} ({len(result)} results)")
            
            return result

    @staticmethod
    def clear_search_cache():
        """검색 결과 캐시 초기화"""
        global _search_cache
        _search_cache.clear()
        logger.info("Search cache cleared")

