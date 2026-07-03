"""
매매동향(투자자별 순매수) 수집·조회 서비스

네이버 모바일 JSON API(/stock/{code}/trend)에서 투자자별 매매동향을 수집하고
DB에 저장·조회한다. ETFDataCollector가 이 Mixin을 상속해 기존 공개 API를 유지한다.
"""
from typing import List, Optional, Dict
from datetime import date, datetime
from app.models import TradingFlow
from app.database import get_db_connection, get_cursor
from app.utils.retry import retry_with_backoff
from app.services.naver_stock_api import (
    fetch_trend_page,
    parse_bizdate,
    parse_int as api_parse_int,
    parse_number as api_parse_number,
)
import logging
import requests

logger = logging.getLogger(__name__)


class TradingFlowCollectorMixin:
    """매매동향 수집/조회 메서드 모음 (self.rate_limiter는 ETFDataCollector가 제공)"""

    def get_trading_flow_data_range(self, ticker: str) -> Optional[Dict[str, date]]:
        """
        DB에 저장된 매매 동향 데이터의 날짜 범위 확인

        Args:
            ticker: 종목 코드

        Returns:
            {'min_date': date, 'max_date': date, 'count': int} 또는 None (데이터 없는 경우)
        """
        p = "?"
        with get_db_connection() as conn_or_cursor:
            cursor = get_cursor(conn_or_cursor)
            cursor.execute(f"""
                SELECT MIN(date) as min_date, MAX(date) as max_date, COUNT(*) as count
                FROM trading_flow
                WHERE ticker = {p}
            """, (ticker,))
            row = cursor.fetchone()

            if row and row['min_date'] and row['max_date']:
                return {
                    'min_date': datetime.strptime(row['min_date'], '%Y-%m-%d').date() if isinstance(row['min_date'], str) else row['min_date'],
                    'max_date': datetime.strptime(row['max_date'], '%Y-%m-%d').date() if isinstance(row['max_date'], str) else row['max_date'],
                    'count': row['count']
                }
            return None


    def get_trading_flow(self, ticker: str, start_date: date, end_date: date, limit: Optional[int] = None) -> List[TradingFlow]:
        """
        데이터베이스에서 매매 동향 데이터 조회

        지정된 날짜 범위의 매매 동향 데이터를 데이터베이스에서 조회합니다.
        데이터 수집은 collect_and_save_trading_flow 메서드를 통해 별도로 수행됩니다.

        Args:
            ticker: 종목 코드
            start_date: 시작 날짜
            end_date: 종료 날짜
            limit: 결과 개수 제한 (선택)

        Returns:
            TradingFlow 리스트 (날짜 내림차순 정렬)
        """
        logger.debug(f"Fetching trading flow for {ticker} from {start_date} to {end_date}" + (f" (limit: {limit})" if limit else ""))
        p = "?"

        with get_db_connection() as conn_or_cursor:
            cursor = get_cursor(conn_or_cursor)

            query = f"""
                SELECT date, individual_net, institutional_net, foreign_net
                FROM trading_flow
                WHERE ticker = {p} AND date BETWEEN {p} AND {p}
                ORDER BY date DESC
            """

            if limit is not None:
                query += f" LIMIT {limit}"

            cursor.execute(query, (ticker, start_date, end_date))
            rows = cursor.fetchall()
            return [TradingFlow(**dict(row)) for row in rows]
    

    @retry_with_backoff(
        max_retries=3,
        base_delay=1.0,
        exceptions=(requests.exceptions.RequestException, requests.exceptions.Timeout)
    )
    def fetch_naver_trading_flow(self, ticker: str, days: int = 10, start_date: Optional[date] = None, end_date: Optional[date] = None) -> List[dict]:
        """
        네이버 모바일 JSON API(/stock/{code}/trend)에서 투자자별 매매동향 수집

        HTML(frgn.naver) 파싱 대비 장점:
        - 개인 순매수 실측값 제공 (기존에는 -(기관+외국인) 근사치)
        - 외국인 보유율(foreignerHoldRatio) 추가 제공

        Args:
            ticker: 종목 코드
            days: 수집할 일수 (기본: 10일)
            start_date: 시작 날짜 (선택, 지정 시 해당 날짜 이후 데이터만 수집)
            end_date: 종료 날짜 (선택, 지정 시 해당 날짜까지 데이터만 수집)

        Returns:
            수집된 매매동향 데이터 리스트
        """
        trading_data = []
        page = 1
        # JSON API pageSize 최대 60 — 필요 일수만큼 페이지 계산 (여유 +2)
        page_size = min(max(days, 10), 60)
        max_pages = (days // page_size) + 2
        
        # 날짜 범위가 지정된 경우, 실제 필요한 최대 데이터 수 계산
        # (주말 제외를 고려하여 days보다 작을 수 있음)
        target_count = days
        if start_date and end_date:
            # 날짜 범위 내의 실제 거래일 수를 대략적으로 계산 (주말 제외)
            # 최대 days일이지만, 주말이 포함되면 더 적을 수 있음
            target_count = days  # 여전히 days를 목표로 하되, 날짜 범위를 벗어나면 종료

        logger.debug(f"Fetching trading flow from Naver Finance for {ticker} (target: {target_count} days, max pages: {max_pages}, date range: {start_date} to {end_date})")

        should_stop = False  # 전체 루프 종료 플래그

        while len(trading_data) < target_count and page <= max_pages and not should_stop:
            try:
                # 네이버 모바일 JSON API 호출 (페이지 단위)
                logger.debug(f"Fetching trading flow page {page} for {ticker}")

                with self.rate_limiter:
                    rows = fetch_trend_page(ticker, page=page, page_size=page_size)

                if not rows:
                    logger.info(f"No trend data on page {page} for {ticker}, stopping pagination")
                    break

                page_data_count = 0

                for row in rows:
                    # 이미 충분한 데이터를 수집했으면 중단
                    if len(trading_data) >= target_count:
                        break

                    try:
                        # 날짜 파싱 (bizdate: YYYYMMDD)
                        trade_date = parse_bizdate(row.get('bizdate'))
                        if not trade_date:
                            continue

                        # 날짜 범위 필터링 (지정된 경우)
                        if start_date and trade_date < start_date:
                            # 시작 날짜 이전 데이터를 만나면 더 이상 필요한 데이터가 없음
                            # (Naver Finance는 최신순으로 데이터 제공)
                            if len(trading_data) > 0:
                                # 이미 일부 데이터를 수집했으면 전체 루프 종료
                                should_stop = True
                                break
                            continue  # 시작 날짜 이전 데이터는 건너뜀
                        if end_date and trade_date > end_date:
                            continue  # 종료 날짜 이후 데이터는 건너뜀 (더 오래된 데이터가 나올 수 있으므로 계속 진행)

                        # 투자자별 순매수 (주 단위) — API 실측값
                        institutional_net = api_parse_int(row.get('organPureBuyQuant'))
                        foreign_net = api_parse_int(row.get('foreignerPureBuyQuant'))
                        # 개인: 기존 -(기관+외국인) 근사치 대신 실측값 사용
                        individual_net = api_parse_int(row.get('individualPureBuyQuant'))
                        # 외국인 보유율 (%)
                        foreign_hold_ratio = api_parse_number(row.get('foreignerHoldRatio'))

                        trading_data.append({
                            'ticker': ticker,
                            'date': trade_date,
                            'individual_net': individual_net,
                            'institutional_net': institutional_net,
                            'foreign_net': foreign_net,
                            'foreign_hold_ratio': foreign_hold_ratio
                        })

                        page_data_count += 1

                    except (ValueError, AttributeError, IndexError) as e:
                        logger.warning(f"Failed to parse trading flow row for {ticker} on page {page}: {e}")
                        continue

                logger.debug(f"Collected {page_data_count} trading flow records from page {page} for {ticker} (total: {len(trading_data)})")

                # 현재 페이지에서 데이터가 없으면 더 이상 페이지가 없는 것으로 간주
                if page_data_count == 0:
                    logger.info(f"No more data found on page {page} for {ticker}, stopping pagination")
                    break

                page += 1

            except requests.exceptions.Timeout:
                logger.error(f"Timeout fetching trading flow page {page} for {ticker}")
                break
            except requests.exceptions.RequestException as e:
                logger.error(f"Request error fetching trading flow page {page} for {ticker}: {e}")
                break
            except Exception as e:
                logger.error(f"Unexpected error fetching trading flow page {page} for {ticker}: {e}")
                break

        logger.debug(f"Collected total {len(trading_data)} trading flow records for {ticker} from {page-1} pages")
        return trading_data
    
    def validate_trading_flow_data(self, data: dict) -> bool:
        """
        매매동향 데이터 유효성 검증
        
        Args:
            data: 매매동향 데이터 딕셔너리
        
        Returns:
            유효하면 True, 아니면 False
        """
        # 필수 필드 확인
        required_fields = ['ticker', 'date']
        for field in required_fields:
            if field not in data or data[field] is None:
                logger.warning(f"Missing required field: {field}")
                return False
        
        # 날짜 타입 확인
        if not isinstance(data['date'], date):
            logger.warning(f"Invalid date type: {type(data['date'])}")
            return False
        
        # 적어도 하나의 매매동향 데이터가 있어야 함
        has_data = (
            data.get('individual_net') is not None or
            data.get('institutional_net') is not None or
            data.get('foreign_net') is not None
        )
        
        if not has_data:
            logger.warning("No trading flow data available")
            return False
        
        return True
    
    def save_trading_flow_data(self, trading_data: List[dict]) -> int:
        """
        매매동향 데이터를 데이터베이스에 저장

        Args:
            trading_data: 매매동향 데이터 리스트

        Returns:
            저장된 레코드 수
        """
        if not trading_data:
            logger.warning("No trading flow data to save")
            return 0

        # 데이터 검증
        valid_data = []
        for data in trading_data:
            if self.validate_trading_flow_data(data):
                valid_data.append(data)

        if not valid_data:
            logger.warning("No valid trading flow data after validation")
            return 0

        # 벌크 insert 수행
        with get_db_connection() as conn_or_cursor:
            conn = conn_or_cursor
            cursor = conn.cursor()

            try:
                cursor.executemany("""
                    INSERT OR REPLACE INTO trading_flow
                    (ticker, date, individual_net, institutional_net, foreign_net,
                     foreign_hold_ratio)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, [
                    (
                        data['ticker'],
                        data['date'],
                        data.get('individual_net'),
                        data.get('institutional_net'),
                        data.get('foreign_net'),
                        data.get('foreign_hold_ratio')
                    )
                    for data in valid_data
                ])

                conn.commit()
                saved_count = len(valid_data)
                logger.debug(f"Saved {saved_count} trading flow records (bulk insert)")

            except Exception as e:
                logger.error(f"Database error saving trading flow: {e}")
                conn.rollback()
                saved_count = 0  # 롤백 시 저장된 레코드 없음

        return saved_count

    def collect_and_save_trading_flow(self, ticker: str, days: int = 10, start_date: Optional[date] = None, end_date: Optional[date] = None) -> int:
        """
        매매동향 데이터를 수집하고 저장
        
        Args:
            ticker: 종목 코드
            days: 수집할 일수
            start_date: 시작 날짜 (선택)
            end_date: 종료 날짜 (선택)
        
        Returns:
            저장된 레코드 수
        """
        logger.debug(f"Starting trading flow collection for {ticker} (last {days} days, date range: {start_date} to {end_date})")

        # 데이터 수집
        trading_data = self.fetch_naver_trading_flow(ticker, days, start_date, end_date)
        
        if not trading_data:
            logger.warning(f"No trading flow data collected for {ticker}")
            return 0
        
        # 데이터 저장
        saved_count = self.save_trading_flow_data(trading_data)
        
        # Rate limiting은 fetch 함수에서 RateLimiter로 처리
        return saved_count
    
    def get_trading_flow_data(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        데이터베이스에서 매매동향 데이터 조회

        Args:
            ticker: 종목 코드
            start_date: 시작 날짜
            end_date: 종료 날짜
            limit: 결과 개수 제한 (선택)

        Returns:
            매매동향 데이터 리스트
        """
        logger.debug(f"Fetching trading flow for {ticker} from {start_date} to {end_date}" + (f" (limit: {limit})" if limit else ""))
        p = "?"

        with get_db_connection() as conn_or_cursor:
            cursor = get_cursor(conn_or_cursor)

            query = f"""
                SELECT date, individual_net, institutional_net, foreign_net
                FROM trading_flow
                WHERE ticker = {p} AND date BETWEEN {p} AND {p}
                ORDER BY date DESC
            """

            if limit is not None:
                query += f" LIMIT {limit}"

            cursor.execute(query, (ticker, start_date, end_date))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]


    def get_trading_flow_batch(
        self,
        tickers: List[str],
        start_date: date,
        end_date: date,
        limit: Optional[int] = None
    ) -> Dict[str, List[Dict]]:
        """
        배치 쿼리로 여러 종목의 매매동향 데이터를 한 번에 조회 (IN 절 활용)

        Args:
            tickers: 종목 코드 리스트
            start_date: 시작 날짜
            end_date: 종료 날짜
            limit: 종목별 결과 개수 제한 (선택)

        Returns:
            종목별 매매동향 데이터 딕셔너리 {ticker: [dict, ...]}
        """
        if not tickers:
            return {}

        logger.debug(f"Batch fetching trading flow for {len(tickers)} tickers from {start_date} to {end_date}")
        p = "?"

        with get_db_connection() as conn_or_cursor:
            cursor = get_cursor(conn_or_cursor)

            # IN 절을 위한 플레이스홀더 생성
            placeholders = ','.join([p] * len(tickers))

            # 쿼리 구성
            query = f"""
                SELECT ticker, date, individual_net, institutional_net, foreign_net
                FROM trading_flow
                WHERE ticker IN ({placeholders}) AND date BETWEEN {p} AND {p}
                ORDER BY ticker, date DESC
            """

            # 파라미터 구성
            params = list(tickers) + [start_date, end_date]

            cursor.execute(query, params)
            rows = cursor.fetchall()

            # 종목별로 그룹화
            result = {ticker: [] for ticker in tickers}
            for row in rows:
                row_dict = dict(row)
                ticker = row_dict.pop('ticker')
                result[ticker].append(row_dict)

            # limit 적용 (종목별로)
            if limit is not None:
                for ticker in result:
                    result[ticker] = result[ticker][:limit]

            logger.debug(f"Batch fetched {sum(len(v) for v in result.values())} total trading flow records")
            return result


    def collect_and_save_trading_flow_smart(self, ticker: str, days: int = 10) -> int:
        """
        스마트 매매동향 데이터 수집 (중복 방지)

        Args:
            ticker: 종목 코드
            days: 수집할 일수 (최대값)

        Returns:
            저장된 레코드 수
        """
        from datetime import date
        from app.database import update_collection_status, get_collection_status

        # collection_status에서 마지막 수집 날짜 확인
        status = get_collection_status(ticker)

        if status and status.get('last_trading_flow_date'):
            # 날짜가 date 객체/문자열 어느 쪽이든 안전하게 처리
            last_flow_date = status['last_trading_flow_date']
            last_date = last_flow_date if isinstance(last_flow_date, date) else date.fromisoformat(last_flow_date)
            today = date.today()

            if last_date >= today:
                logger.info(f"[{ticker}] 매매동향: 이미 최신 데이터 보유 → 스킵")
                return 0

            days_gap = (today - last_date).days
            actual_days = min(days_gap, days)
            logger.info(f"[{ticker}] 매매동향: {actual_days}일치 수집")
        else:
            actual_days = days
            logger.info(f"[{ticker}] 매매동향: 수집 이력 없음 → {actual_days}일 수집")

        # 데이터 수집
        trading_data = self.fetch_naver_trading_flow(ticker, actual_days)

        if not trading_data:
            logger.warning(f"[{ticker}] 매매동향: 데이터 없음")
            return 0

        # 데이터 저장
        saved_count = self.save_trading_flow_data(trading_data)

        # 수집 상태 업데이트
        if saved_count > 0:
            latest_date = max(d['date'] for d in trading_data)
            update_collection_status(
                ticker,
                trading_flow_date=latest_date.isoformat(),
                success=True
            )

        return saved_count
