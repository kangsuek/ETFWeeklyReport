"""
분봉(Intraday) 데이터 수집 서비스

네이버 차트 JSON API(api.stock.naver.com/chart/domestic/item/{code}/minute)에서
하루 세션 전체(09:00~15:30, 381분)를 한 번의 호출로 수집합니다.

구형 sise_time.naver HTML 파싱(하루치 = 40+ 페이지 요청) 대비:
- 요청 수 수십 → 1
- 분당 OHLC(시가/고가/저가/종가) 제공 → 분봉 캔들차트 가능
- 문자 포함 신형 코드(예: 0101N0)도 동작 (startDateTime/endDateTime 명시 필수)

주의:
- API의 accumulatedTradingVolume은 이름과 달리 '분당' 거래량 →
  기존 스키마/차트와의 호환을 위해 누적합으로 변환해 volume에 저장
- change_amount(전일비)는 API 미제공 → 전일 종가(prices 테이블) 기준으로 계산
- bid/ask 호가 잔량은 API 미제공 → NULL 저장 (프론트 툴팁은 옵셔널 처리됨)
"""

from typing import List, Optional, Dict
from datetime import datetime, date, timedelta
from app.database import get_db_connection, get_cursor
from app.utils.retry import retry_with_backoff
from app.utils.rate_limiter import RateLimiter
from app.constants import DEFAULT_RATE_LIMITER_INTERVAL
from app.services.naver_stock_api import CHART_API_BASE, HEADERS
import logging
import requests

logger = logging.getLogger(__name__)


class IntradayDataCollector:
    """분봉(시간별) 데이터 수집 서비스"""

    def __init__(self):
        self.rate_limiter = RateLimiter(min_interval=DEFAULT_RATE_LIMITER_INTERVAL)

    def get_last_trading_date(self, ticker: str) -> Optional[date]:
        """
        DB에서 마지막 거래일 조회

        Args:
            ticker: 종목 코드

        Returns:
            마지막 거래일 또는 None
        """
        p = "?"

        with get_db_connection() as conn_or_cursor:
            cursor = get_cursor(conn_or_cursor)
            cursor.execute(f"""
                SELECT MAX(date) as last_date
                FROM prices
                WHERE ticker = {p}
            """, (ticker,))

            row = cursor.fetchone()
            if row and row['last_date']:
                last_date = row['last_date']
                if isinstance(last_date, str):
                    return datetime.strptime(last_date, '%Y-%m-%d').date()
                return last_date
            return None

    def _get_previous_close(self, ticker: str, target_date: date) -> Optional[float]:
        """전일비(change_amount) 계산용: target_date 이전 마지막 종가 조회."""
        p = "?"
        with get_db_connection() as conn_or_cursor:
            cursor = get_cursor(conn_or_cursor)
            cursor.execute(f"""
                SELECT close_price
                FROM prices
                WHERE ticker = {p} AND date < {p}
                ORDER BY date DESC
                LIMIT 1
            """, (ticker, target_date))
            row = cursor.fetchone()
            if row and row['close_price'] is not None:
                return float(row['close_price'])
            return None

    @retry_with_backoff(
        max_retries=3,
        base_delay=1.0,
        exceptions=(requests.exceptions.RequestException, requests.exceptions.Timeout)
    )
    def fetch_intraday_data(self, ticker: str, pages: int = 10, target_date: Optional[date] = None) -> List[dict]:
        """
        네이버 차트 JSON API에서 분봉 데이터 수집 (세션 전체를 1회 호출)

        Args:
            ticker: 종목 코드
            pages: (하위 호환용, 무시됨 — JSON API는 세션 전체를 한 번에 반환)
            target_date: 조회할 날짜 (None이면 오늘)

        Returns:
            시간순(오름차순) 분봉 데이터 리스트
        """
        # 대상 날짜 결정
        if target_date is None:
            target_date = date.today()

        # 날짜를 명시하지 않으면 '오늘' 세션만 반환되어 자정 이후/휴장일에 비게 되므로
        # 항상 startDateTime/endDateTime을 명시한다 (신형 문자코드 종목도 이 방식만 동작).
        day = target_date.strftime('%Y%m%d')
        url = (
            f"{CHART_API_BASE}/chart/domestic/item/{ticker}/minute"
            f"?startDateTime={day}090000&endDateTime={day}153000"
        )

        logger.info(f"[분봉 수집] {ticker} - 세션 조회 (날짜: {target_date})")

        with self.rate_limiter:
            response = requests.get(url, headers=HEADERS, timeout=10)
            response.raise_for_status()

        try:
            rows = response.json()
        except ValueError as e:
            logger.error(f"[분봉 수집] {ticker} - JSON 파싱 실패: {e}")
            return []

        if not isinstance(rows, list) or not rows:
            logger.info(f"[분봉 수집] {ticker} - 데이터 없음 (휴장일 또는 미개장)")
            return []

        # 전일 종가 (change_amount 계산용, 없으면 None 저장)
        prev_close = self._get_previous_close(ticker, target_date)

        intraday_data = []
        cumulative_volume = 0

        for r in rows:
            try:
                dt_text = r.get('localDateTime')  # 'YYYYMMDDHHMMSS'
                price = r.get('currentPrice')
                if not dt_text or price is None:
                    continue

                dt = datetime.strptime(str(dt_text), '%Y%m%d%H%M%S')
                price = float(price)

                # API의 accumulatedTradingVolume은 분당 거래량 → 누적합으로 변환
                minute_volume = r.get('accumulatedTradingVolume') or 0
                cumulative_volume += int(minute_volume)

                intraday_data.append({
                    'ticker': ticker,
                    'datetime': dt,
                    'price': price,
                    'open_price': float(r['openPrice']) if r.get('openPrice') is not None else None,
                    'high_price': float(r['highPrice']) if r.get('highPrice') is not None else None,
                    'low_price': float(r['lowPrice']) if r.get('lowPrice') is not None else None,
                    'change_amount': round(price - prev_close, 2) if prev_close else None,
                    'volume': cumulative_volume,
                    'bid_volume': None,   # JSON API 미제공
                    'ask_volume': None,   # JSON API 미제공
                })
            except (ValueError, TypeError, KeyError) as e:
                logger.debug(f"[분봉 수집] 행 파싱 실패: {e}")
                continue

        # 시간순 정렬 (API가 오름차순이지만 방어적으로 보장)
        intraday_data.sort(key=lambda x: x['datetime'])

        logger.info(f"[분봉 수집] {ticker} - 총 {len(intraday_data)}건 수집 완료")
        return intraday_data

    def save_intraday_data(self, intraday_data: List[dict]) -> int:
        """
        분봉 데이터를 DB에 저장

        Args:
            intraday_data: 분봉 데이터 리스트

        Returns:
            저장된 레코드 수
        """
        if not intraday_data:
            return 0

        with get_db_connection() as conn_or_cursor:
            conn = conn_or_cursor
            cursor = conn.cursor()

            try:
                cursor.executemany("""
                    INSERT OR REPLACE INTO intraday_prices
                    (ticker, datetime, price, change_amount, volume, bid_volume, ask_volume,
                     open_price, high_price, low_price)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    (
                        d['ticker'],
                        d['datetime'],
                        d['price'],
                        d.get('change_amount'),
                        d.get('volume'),
                        d.get('bid_volume'),
                        d.get('ask_volume'),
                        d.get('open_price'),
                        d.get('high_price'),
                        d.get('low_price')
                    )
                    for d in intraday_data
                ])

                conn.commit()
                saved_count = len(intraday_data)
                logger.info(f"[분봉 저장] {saved_count}건 저장 완료")
                return saved_count

            except Exception as e:
                logger.error(f"[분봉 저장] DB 저장 실패: {e}")
                conn.rollback()
                return 0

    def collect_and_save_intraday(self, ticker: str, pages: int = 10, target_date: Optional[date] = None) -> Dict:
        """
        분봉 데이터 수집 및 저장

        Args:
            ticker: 종목 코드
            pages: (하위 호환용, 무시됨)
            target_date: 수집할 날짜 (None이면 오늘 → 없으면 마지막 거래일 폴백)

        Returns:
            수집 결과 딕셔너리
        """
        logger.info(f"[분봉] {ticker} - 수집 시작")

        # 대상 날짜 결정
        actual_date = target_date or date.today()

        # 오늘 데이터 먼저 시도 (JSON API는 세션 전체를 한 번에 반환)
        intraday_data = self.fetch_intraday_data(ticker, target_date=actual_date)

        # 오늘 데이터가 없으면 마지막 거래일 데이터 시도
        if not intraday_data and target_date is None:
            last_trading_date = self.get_last_trading_date(ticker)
            if last_trading_date and last_trading_date != date.today():
                logger.info(f"[분봉] {ticker} - 오늘 데이터 없음, 마지막 거래일({last_trading_date}) 데이터 수집")
                actual_date = last_trading_date
                intraday_data = self.fetch_intraday_data(ticker, target_date=last_trading_date)

        if not intraday_data:
            return {
                'ticker': ticker,
                'date': actual_date.isoformat(),
                'collected': 0,
                'message': '수집된 데이터 없음 (장 마감 또는 휴장일)'
            }

        # DB 저장
        saved_count = self.save_intraday_data(intraday_data)

        return {
            'ticker': ticker,
            'date': actual_date.isoformat(),
            'collected': saved_count,
            'first_time': intraday_data[0]['datetime'].strftime('%H:%M') if intraday_data else None,
            'last_time': intraday_data[-1]['datetime'].strftime('%H:%M') if intraday_data else None,
            'message': f'{saved_count}건 수집 완료 ({actual_date})'
        }

    def get_last_collected_datetime(self, ticker: str, target_date: Optional[date] = None) -> Optional[datetime]:
        """
        DB에 저장된 해당 날짜의 마지막 분봉 데이터 시간 조회

        Args:
            ticker: 종목 코드
            target_date: 조회할 날짜 (기본: 오늘)

        Returns:
            마지막 분봉 데이터 datetime 또는 None
        """
        if target_date is None:
            target_date = date.today()

        start_dt = datetime.combine(target_date, datetime.min.time().replace(hour=9, minute=0))
        end_dt = datetime.combine(target_date, datetime.min.time().replace(hour=15, minute=30))
        p = "?"

        with get_db_connection() as conn_or_cursor:
            cursor = get_cursor(conn_or_cursor)
            cursor.execute(f"""
                SELECT MAX(datetime) as last_dt
                FROM intraday_prices
                WHERE ticker = {p} AND datetime BETWEEN {p} AND {p}
            """, (ticker, start_dt, end_dt))
            row = cursor.fetchone()
            if row and row['last_dt']:
                last_dt = row['last_dt']
                if isinstance(last_dt, str):
                    return datetime.fromisoformat(last_dt.replace(' ', 'T'))
                return last_dt
            return None

    def incremental_collect_and_save(self, ticker: str, target_date: Optional[date] = None) -> Dict:
        """
        증분 수집: DB의 마지막 시간 이후 데이터만 저장하여 빠르게 갱신

        JSON API는 세션 전체를 1회 호출로 반환하므로, 전체를 받아
        누적 거래량을 정확히 계산한 뒤 신규 분만 저장한다.
        기존 데이터가 없으면 전체 수집으로 폴백한다.

        Args:
            ticker: 종목 코드
            target_date: 수집할 날짜 (기본: 오늘)

        Returns:
            수집 결과 딕셔너리
        """
        actual_date = target_date or date.today()
        last_collected = self.get_last_collected_datetime(ticker, actual_date)

        if last_collected is None:
            # 기존 데이터 없음 → 전체 수집
            logger.info(f"[분봉 증분] {ticker} - 기존 데이터 없음, 전체 수집으로 전환")
            return self.collect_and_save_intraday(ticker, target_date=target_date)

        logger.info(f"[분봉 증분] {ticker} - 마지막 수집 시간: {last_collected.strftime('%H:%M')}, 이후 데이터만 저장")

        # 세션 전체 조회 (1회 호출) 후 신규 분만 필터
        # 누적 거래량은 세션 전체 기준으로 계산되므로 신규 분에도 정확하다.
        session_data = self.fetch_intraday_data(ticker, target_date=actual_date)
        new_data = [d for d in session_data if d['datetime'] > last_collected]

        if not new_data:
            logger.info(f"[분봉 증분] {ticker} - 새로운 데이터 없음")
            return {
                'ticker': ticker,
                'date': actual_date.isoformat(),
                'collected': 0,
                'message': '새로운 데이터 없음 (최신 상태)',
            }

        saved_count = self.save_intraday_data(new_data)

        logger.info(f"[분봉 증분] {ticker} - {saved_count}건 증분 수집 완료 "
                    f"({new_data[0]['datetime'].strftime('%H:%M')} ~ {new_data[-1]['datetime'].strftime('%H:%M')})")

        return {
            'ticker': ticker,
            'date': actual_date.isoformat(),
            'collected': saved_count,
            'first_time': new_data[0]['datetime'].strftime('%H:%M'),
            'last_time': new_data[-1]['datetime'].strftime('%H:%M'),
            'message': f'{saved_count}건 증분 수집 완료 ({actual_date})',
        }

    def get_intraday_data(
        self,
        ticker: str,
        target_date: Optional[date] = None,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        DB에서 분봉 데이터 조회

        Args:
            ticker: 종목 코드
            target_date: 조회할 날짜 (기본: 오늘)
            limit: 결과 개수 제한

        Returns:
            분봉 데이터 리스트
        """
        if target_date is None:
            target_date = date.today()

        # 날짜 범위 설정 (해당 날짜의 09:00 ~ 15:30)
        start_dt = datetime.combine(target_date, datetime.min.time().replace(hour=9, minute=0))
        end_dt = datetime.combine(target_date, datetime.min.time().replace(hour=15, minute=30))

        p = "?"

        with get_db_connection() as conn_or_cursor:
            cursor = get_cursor(conn_or_cursor)

            query = f"""
                SELECT datetime, price, change_amount, volume, bid_volume, ask_volume,
                       open_price, high_price, low_price
                FROM intraday_prices
                WHERE ticker = {p} AND datetime BETWEEN {p} AND {p}
                ORDER BY datetime ASC
            """

            if limit:
                query += f" LIMIT {limit}"

            cursor.execute(query, (ticker, start_dt, end_dt))
            rows = cursor.fetchall()

            return [dict(row) for row in rows]

    def get_latest_intraday_date(self, ticker: str) -> Optional[date]:
        """
        DB에 저장된 가장 최근 분봉 데이터의 날짜 조회

        Args:
            ticker: 종목 코드

        Returns:
            최근 분봉 데이터 날짜 또는 None
        """
        p = "?"

        with get_db_connection() as conn_or_cursor:
            cursor = get_cursor(conn_or_cursor)

            cursor.execute(f"""
                SELECT MAX(datetime) as last_datetime
                FROM intraday_prices
                WHERE ticker = {p}
            """, (ticker,))

            row = cursor.fetchone()
            if row and row['last_datetime']:
                last_dt = row['last_datetime']
                if isinstance(last_dt, str):
                    last_dt = datetime.fromisoformat(last_dt)
                return last_dt.date()
            return None

    def clear_old_intraday_data(self, days_to_keep: int = 7) -> int:
        """
        오래된 분봉 데이터 정리

        Args:
            days_to_keep: 보관할 일수 (기본 7일)

        Returns:
            삭제된 레코드 수
        """
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        p = "?"

        with get_db_connection() as conn_or_cursor:
            conn = conn_or_cursor
            cursor = conn.cursor()

            cursor.execute(f"""
                DELETE FROM intraday_prices WHERE datetime < {p}
            """, (cutoff_date,))

            deleted_count = cursor.rowcount
            conn.commit()

            logger.info(f"[분봉 정리] {deleted_count}건 삭제 ({days_to_keep}일 이전 데이터)")
            return deleted_count
