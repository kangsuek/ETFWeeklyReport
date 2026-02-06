"""
분봉(Intraday) 데이터 수집 서비스

네이버 금융에서 시간별 체결 데이터를 수집하여 분봉 차트를 위한 데이터를 제공합니다.
"""

from typing import List, Optional, Dict
from datetime import datetime, date, timedelta
from app.database import get_db_connection, get_cursor, USE_POSTGRES
from app.utils.retry import retry_with_backoff
from app.utils.rate_limiter import RateLimiter
from app.constants import DEFAULT_RATE_LIMITER_INTERVAL
import logging
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class IntradayDataCollector:
    """분봉(시간별) 데이터 수집 서비스"""

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.rate_limiter = RateLimiter(min_interval=DEFAULT_RATE_LIMITER_INTERVAL)

    def get_last_trading_date(self, ticker: str) -> Optional[date]:
        """
        DB에서 마지막 거래일 조회

        Args:
            ticker: 종목 코드

        Returns:
            마지막 거래일 또는 None
        """
        p = "%s" if USE_POSTGRES else "?"

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

    @retry_with_backoff(
        max_retries=3,
        base_delay=1.0,
        exceptions=(requests.exceptions.RequestException, requests.exceptions.Timeout)
    )
    def fetch_intraday_data(self, ticker: str, pages: int = 10, target_date: Optional[date] = None) -> List[dict]:
        """
        네이버 금융에서 분봉(시간별 체결) 데이터 수집

        Args:
            ticker: 종목 코드
            pages: 수집할 페이지 수 (페이지당 약 10개 데이터)
            target_date: 조회할 날짜 (None이면 오늘, 오늘 데이터가 없으면 마지막 거래일)

        Returns:
            시간별 체결 데이터 리스트
        """
        intraday_data = []

        # 대상 날짜 결정
        if target_date is None:
            target_date = date.today()

        # thistime 파라미터 생성 (마지막 거래일 데이터 조회용)
        # 형식: YYYYMMDDHHMMSS (장 마감 시간으로 설정)
        thistime = target_date.strftime('%Y%m%d') + '153000'

        logger.info(f"[분봉 수집] {ticker} - {pages} 페이지 수집 시작 (날짜: {target_date})")

        for page in range(1, pages + 1):
            try:
                # thistime 파라미터를 추가하여 특정 날짜 데이터 조회
                url = f"https://finance.naver.com/item/sise_time.naver?code={ticker}&thistime={thistime}&page={page}"
                logger.debug(f"[분봉 수집] {ticker} - 페이지 {page} 요청")

                with self.rate_limiter:
                    response = requests.get(url, headers=self.headers, timeout=10)
                    response.raise_for_status()

                # EUC-KR 인코딩 처리
                response.encoding = 'euc-kr'
                soup = BeautifulSoup(response.text, 'html.parser')

                # 시간별 체결 테이블 찾기
                table = soup.find('table', {'class': 'type2'})
                if not table:
                    logger.warning(f"[분봉 수집] {ticker} - 페이지 {page}에서 테이블을 찾을 수 없음")
                    break

                rows = table.find_all('tr')
                page_data_count = 0

                for row in rows:
                    cols = row.find_all('td')
                    # 데이터 행: 체결시간, 체결가, 전일비, 매도, 매수, 거래량, 변동량
                    if len(cols) >= 7:
                        try:
                            time_text = cols[0].get_text(strip=True)
                            if not time_text or ':' not in time_text:
                                continue

                            # 체결가
                            price_text = cols[1].get_text(strip=True).replace(',', '')
                            if not price_text:
                                continue
                            price = float(price_text)

                            # 전일비 (등락)
                            change_text = cols[2].get_text(strip=True).replace(',', '')
                            change_amount = self._parse_change_amount(change_text, cols[2])

                            # 매도호가 잔량
                            ask_text = cols[3].get_text(strip=True).replace(',', '')
                            ask_volume = int(ask_text) if ask_text else None

                            # 매수호가 잔량
                            bid_text = cols[4].get_text(strip=True).replace(',', '')
                            bid_volume = int(bid_text) if bid_text else None

                            # 거래량
                            volume_text = cols[5].get_text(strip=True).replace(',', '')
                            volume = int(volume_text) if volume_text else None

                            # datetime 생성 (대상 날짜 + 시간)
                            hour, minute = map(int, time_text.split(':'))
                            dt = datetime.combine(target_date, datetime.min.time().replace(hour=hour, minute=minute))

                            intraday_data.append({
                                'ticker': ticker,
                                'datetime': dt,
                                'price': price,
                                'change_amount': change_amount,
                                'volume': volume,
                                'bid_volume': bid_volume,
                                'ask_volume': ask_volume
                            })
                            page_data_count += 1

                        except (ValueError, AttributeError, IndexError) as e:
                            logger.debug(f"[분봉 수집] 행 파싱 실패: {e}")
                            continue

                logger.debug(f"[분봉 수집] {ticker} - 페이지 {page}: {page_data_count}건")

                # 데이터가 없으면 더 이상 페이지가 없는 것
                if page_data_count == 0:
                    break

            except requests.exceptions.RequestException as e:
                logger.error(f"[분봉 수집] {ticker} - 페이지 {page} 요청 실패: {e}")
                break
            except Exception as e:
                logger.error(f"[분봉 수집] {ticker} - 페이지 {page} 처리 실패: {e}")
                break

        # 시간순 정렬 (오래된 시간 → 최신 시간)
        intraday_data.sort(key=lambda x: x['datetime'])

        logger.info(f"[분봉 수집] {ticker} - 총 {len(intraday_data)}건 수집 완료")
        return intraday_data

    def _parse_change_amount(self, text: str, cell) -> Optional[float]:
        """
        전일비 파싱 (상승/하락 구분)

        Args:
            text: 전일비 텍스트
            cell: BeautifulSoup td 셀 (이미지로 상승/하락 구분)

        Returns:
            전일비 금액 (하락 시 음수)
        """
        try:
            if not text:
                return None

            # 숫자만 추출
            import re
            num_text = re.sub(r'[^0-9]', '', text)
            if not num_text:
                return 0.0

            amount = float(num_text)

            # 이미지 alt 속성 또는 클래스로 상승/하락 구분
            img = cell.find('img')
            if img:
                alt = img.get('alt', '')
                if '하락' in alt or 'down' in alt.lower():
                    amount = -amount
            elif 'nv01' in str(cell):  # 하락 클래스
                amount = -amount

            return amount

        except Exception:
            return None

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
            if USE_POSTGRES:
                cursor = conn_or_cursor
                conn = cursor.connection
            else:
                conn = conn_or_cursor
                cursor = conn.cursor()

            try:
                if USE_POSTGRES:
                    cursor.executemany("""
                        INSERT INTO intraday_prices
                        (ticker, datetime, price, change_amount, volume, bid_volume, ask_volume)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (ticker, datetime) DO UPDATE SET
                            price = EXCLUDED.price,
                            change_amount = EXCLUDED.change_amount,
                            volume = EXCLUDED.volume,
                            bid_volume = EXCLUDED.bid_volume,
                            ask_volume = EXCLUDED.ask_volume
                    """, [
                        (
                            d['ticker'],
                            d['datetime'],
                            d['price'],
                            d.get('change_amount'),
                            d.get('volume'),
                            d.get('bid_volume'),
                            d.get('ask_volume')
                        )
                        for d in intraday_data
                    ])
                else:
                    cursor.executemany("""
                        INSERT OR REPLACE INTO intraday_prices
                        (ticker, datetime, price, change_amount, volume, bid_volume, ask_volume)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, [
                        (
                            d['ticker'],
                            d['datetime'],
                            d['price'],
                            d.get('change_amount'),
                            d.get('volume'),
                            d.get('bid_volume'),
                            d.get('ask_volume')
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
            pages: 수집할 페이지 수 (기본값: 10, 장 시작부터 수집하려면 최소 40 이상 권장)
            target_date: 수집할 날짜 (None이면 자동 감지)

        Returns:
            수집 결과 딕셔너리
        """
        logger.info(f"[분봉] {ticker} - 수집 시작 (pages={pages})")

        # 대상 날짜 결정
        actual_date = target_date or date.today()

        # 장 시작부터 수집하려면 충분한 페이지 수 필요
        # 장 시작(09:00) ~ 장 종료(15:30) = 6시간 30분 = 390분 = 약 390개 분봉
        # 페이지당 약 10개 데이터이므로, 최소 40페이지 필요
        # 기본값이 10이면 장 시작 데이터를 놓칠 수 있으므로, 자동으로 증가
        if pages < 40:
            logger.warning(f"[분봉] {ticker} - pages={pages}는 장 시작(09:00) 데이터 수집에 부족할 수 있습니다. 40으로 증가합니다.")
            pages = 40

        # 오늘 데이터 먼저 시도
        intraday_data = self.fetch_intraday_data(ticker, pages, actual_date)
        
        # 장 시작 시간(09:00) 데이터가 있는지 확인
        if intraday_data:
            first_datetime = intraday_data[0]['datetime']
            first_hour = first_datetime.hour
            first_minute = first_datetime.minute
            
            # 장 시작 시간(09:00) 이전 데이터가 있으면 더 많은 페이지 필요
            if first_hour > 9 or (first_hour == 9 and first_minute > 0):
                logger.info(f"[분봉] {ticker} - 첫 데이터 시간: {first_hour:02d}:{first_minute:02d}, 장 시작(09:00) 데이터를 위해 추가 수집 시도")
                # 추가로 20페이지 더 수집
                additional_data = self.fetch_intraday_data(ticker, pages + 20, actual_date)
                if additional_data:
                    # 기존 데이터와 병합 (중복 제거)
                    existing_datetimes = {d['datetime'] for d in intraday_data}
                    new_data = [d for d in additional_data if d['datetime'] not in existing_datetimes]
                    intraday_data.extend(new_data)
                    # 시간순 정렬
                    intraday_data.sort(key=lambda x: x['datetime'])
                    logger.info(f"[분봉] {ticker} - 추가 수집: {len(new_data)}건, 총 {len(intraday_data)}건")

        # 오늘 데이터가 없으면 마지막 거래일 데이터 시도
        if not intraday_data and target_date is None:
            last_trading_date = self.get_last_trading_date(ticker)
            if last_trading_date and last_trading_date != date.today():
                logger.info(f"[분봉] {ticker} - 오늘 데이터 없음, 마지막 거래일({last_trading_date}) 데이터 수집")
                actual_date = last_trading_date
                intraday_data = self.fetch_intraday_data(ticker, pages, last_trading_date)
                
                # 마지막 거래일 데이터도 장 시작 시간 확인
                if intraday_data:
                    first_datetime = intraday_data[0]['datetime']
                    first_hour = first_datetime.hour
                    first_minute = first_datetime.minute
                    
                    if first_hour > 9 or (first_hour == 9 and first_minute > 0):
                        logger.info(f"[분봉] {ticker} - 마지막 거래일 첫 데이터 시간: {first_hour:02d}:{first_minute:02d}, 추가 수집 시도")
                        additional_data = self.fetch_intraday_data(ticker, pages + 20, last_trading_date)
                        if additional_data:
                            existing_datetimes = {d['datetime'] for d in intraday_data}
                            new_data = [d for d in additional_data if d['datetime'] not in existing_datetimes]
                            intraday_data.extend(new_data)
                            intraday_data.sort(key=lambda x: x['datetime'])
                            logger.info(f"[분봉] {ticker} - 마지막 거래일 추가 수집: {len(new_data)}건, 총 {len(intraday_data)}건")

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
        p = "%s" if USE_POSTGRES else "?"

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
        증분 수집: DB의 마지막 시간 이후 데이터만 수집하여 빠르게 갱신

        네이버 금융 페이지 1(최신)부터 수집을 시작하고,
        DB에 이미 있는 시간에 도달하면 즉시 중단합니다.
        기존 데이터가 없으면 전체 수집으로 폴백합니다.

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
            return self.collect_and_save_intraday(ticker, pages=40, target_date=target_date)

        logger.info(f"[분봉 증분] {ticker} - 마지막 수집 시간: {last_collected.strftime('%H:%M')}, 이후 데이터만 수집")

        # 페이지 1(최신)부터 수집, 이미 있는 시간에 도달하면 중단
        new_data = []
        max_pages = 10  # 증분 수집은 최대 10페이지 (최근 ~100건)
        thistime = actual_date.strftime('%Y%m%d') + '153000'
        reached_existing = False

        for page in range(1, max_pages + 1):
            try:
                url = f"https://finance.naver.com/item/sise_time.naver?code={ticker}&thistime={thistime}&page={page}"
                logger.debug(f"[분봉 증분] {ticker} - 페이지 {page} 요청")

                with self.rate_limiter:
                    response = requests.get(url, headers=self.headers, timeout=10)
                    response.raise_for_status()

                response.encoding = 'euc-kr'
                soup = BeautifulSoup(response.text, 'html.parser')
                table = soup.find('table', {'class': 'type2'})
                if not table:
                    break

                rows = table.find_all('tr')
                page_new_count = 0

                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 7:
                        try:
                            time_text = cols[0].get_text(strip=True)
                            if not time_text or ':' not in time_text:
                                continue

                            hour, minute = map(int, time_text.split(':'))
                            dt = datetime.combine(actual_date, datetime.min.time().replace(hour=hour, minute=minute))

                            # 이미 수집된 시간 이하이면 중단
                            if dt <= last_collected:
                                reached_existing = True
                                break

                            price_text = cols[1].get_text(strip=True).replace(',', '')
                            if not price_text:
                                continue
                            price = float(price_text)

                            change_text = cols[2].get_text(strip=True).replace(',', '')
                            change_amount = self._parse_change_amount(change_text, cols[2])

                            ask_text = cols[3].get_text(strip=True).replace(',', '')
                            ask_volume = int(ask_text) if ask_text else None

                            bid_text = cols[4].get_text(strip=True).replace(',', '')
                            bid_volume = int(bid_text) if bid_text else None

                            volume_text = cols[5].get_text(strip=True).replace(',', '')
                            volume = int(volume_text) if volume_text else None

                            new_data.append({
                                'ticker': ticker,
                                'datetime': dt,
                                'price': price,
                                'change_amount': change_amount,
                                'volume': volume,
                                'bid_volume': bid_volume,
                                'ask_volume': ask_volume,
                            })
                            page_new_count += 1

                        except (ValueError, AttributeError, IndexError) as e:
                            logger.debug(f"[분봉 증분] 행 파싱 실패: {e}")
                            continue

                if reached_existing or page_new_count == 0:
                    break

            except requests.exceptions.RequestException as e:
                logger.error(f"[분봉 증분] {ticker} - 페이지 {page} 요청 실패: {e}")
                break
            except Exception as e:
                logger.error(f"[분봉 증분] {ticker} - 페이지 {page} 처리 실패: {e}")
                break

        if not new_data:
            logger.info(f"[분봉 증분] {ticker} - 새로운 데이터 없음")
            return {
                'ticker': ticker,
                'date': actual_date.isoformat(),
                'collected': 0,
                'message': '새로운 데이터 없음 (최신 상태)',
            }

        # 시간순 정렬 후 저장
        new_data.sort(key=lambda x: x['datetime'])
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

        p = "%s" if USE_POSTGRES else "?"

        with get_db_connection() as conn_or_cursor:
            cursor = get_cursor(conn_or_cursor)

            query = f"""
                SELECT datetime, price, change_amount, volume, bid_volume, ask_volume
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
        p = "%s" if USE_POSTGRES else "?"

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
        p = "%s" if USE_POSTGRES else "?"

        with get_db_connection() as conn_or_cursor:
            if USE_POSTGRES:
                cursor = conn_or_cursor
                conn = cursor.connection
            else:
                conn = conn_or_cursor
                cursor = conn.cursor()

            cursor.execute(f"""
                DELETE FROM intraday_prices WHERE datetime < {p}
            """, (cutoff_date,))

            deleted_count = cursor.rowcount
            conn.commit()

            logger.info(f"[분봉 정리] {deleted_count}건 삭제 ({days_to_keep}일 이전 데이터)")
            return deleted_count
