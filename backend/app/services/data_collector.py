from typing import List, Optional, Dict
from datetime import date, datetime, timedelta
from app.models import ETF, PriceData, TradingFlow, ETFMetrics
from app.database import get_db_connection
from app.utils.retry import retry_with_backoff
from app.utils.rate_limiter import RateLimiter
import logging
import requests
from bs4 import BeautifulSoup
import time
import re

logger = logging.getLogger(__name__)

class ETFDataCollector:
    """Service for collecting ETF/Stock data from various sources"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        # Rate Limiter 초기화 (요청 간 0.5초 대기)
        self.rate_limiter = RateLimiter(min_interval=0.5)
    
    @retry_with_backoff(
        max_retries=3,
        base_delay=1.0,
        exceptions=(requests.exceptions.RequestException, requests.exceptions.Timeout)
    )
    def fetch_naver_finance_prices(self, ticker: str, days: int = 10) -> List[dict]:
        """
        Naver Finance에서 가격 데이터 수집
        
        Args:
            ticker: 종목 코드 (예: "487240")
            days: 수집할 일수 (기본: 10일)
        
        Returns:
            수집된 가격 데이터 리스트
        """
        try:
            url = f"https://finance.naver.com/item/sise_day.naver?code={ticker}"
            logger.info(f"Fetching data from Naver Finance for {ticker}")
            
            with self.rate_limiter:
                response = requests.get(url, headers=self.headers, timeout=10)
                response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 시세 테이블 찾기
            table = soup.find('table', {'class': 'type2'})
            if not table:
                logger.error(f"Price table not found for {ticker}")
                return []
            
            # 데이터 행 추출
            rows = table.find_all('tr')
            price_data = []
            
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 7:  # 날짜, 종가, 전일비, 시가, 고가, 저가, 거래량
                    date_cell = cols[0].get_text(strip=True)
                    
                    # 날짜 형식 확인 (YYYY.MM.DD)
                    if date_cell and '.' in date_cell:
                        try:
                            # 데이터 파싱
                            date_str = date_cell  # 2025.11.07
                            close_price = self._parse_number(cols[1].get_text(strip=True))
                            change_str = cols[2].get_text(strip=True)  # 예: "상승205" 또는 "하락1,375"
                            open_price = self._parse_number(cols[3].get_text(strip=True))
                            high_price = self._parse_number(cols[4].get_text(strip=True))
                            low_price = self._parse_number(cols[5].get_text(strip=True))
                            volume = self._parse_number(cols[6].get_text(strip=True))
                            
                            # 등락률 계산
                            daily_change_pct = self._parse_change(change_str, close_price)
                            
                            # 날짜 변환 (YYYY.MM.DD → YYYY-MM-DD)
                            date_obj = datetime.strptime(date_str, '%Y.%m.%d').date()
                            
                            price_data.append({
                                'ticker': ticker,
                                'date': date_obj,
                                'open_price': open_price,
                                'high_price': high_price,
                                'low_price': low_price,
                                'close_price': close_price,
                                'volume': volume,
                                'daily_change_pct': daily_change_pct
                            })
                            
                            # 요청한 일수만큼 수집하면 종료
                            if len(price_data) >= days:
                                break
                                
                        except Exception as e:
                            logger.warning(f"Failed to parse row for {ticker}: {e}")
                            continue
            
            logger.info(f"Collected {len(price_data)} price records for {ticker}")
            return price_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error while fetching {ticker}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error while fetching {ticker}: {e}")
            return []
    
    def _parse_number(self, text: str) -> Optional[float]:
        """숫자 문자열을 float로 변환 (쉼표 제거)"""
        if not text or not text.strip():
            return None
        try:
            # 쉼표 제거 후 숫자로 변환
            cleaned = text.replace(',', '')
            return float(cleaned)
        except (ValueError, AttributeError):
            return None
    
    def _parse_change(self, change_str: str, close_price: Optional[float]) -> Optional[float]:
        """
        전일비 문자열을 등락률(%)로 변환
        
        Args:
            change_str: "상승205", "하락1,375", "보합0" 형식
            close_price: 현재 종가
        
        Returns:
            등락률 (%) 또는 None
        """
        if not change_str or not close_price or close_price == 0:
            return None
        
        try:
            # "상승", "하락", "보합" 제거하고 숫자만 추출
            number_str = re.sub(r'[^0-9,-]', '', change_str)
            if not number_str or number_str == '0':
                return 0.0
            
            change_amount = float(number_str.replace(',', ''))
            
            # 하락이면 음수로
            if '하락' in change_str:
                change_amount = -change_amount
            
            # 등락률 계산: (전일비 / (종가 - 전일비)) * 100
            prev_price = close_price - change_amount
            if prev_price != 0:
                return round((change_amount / prev_price) * 100, 2)
            
            return None
        except Exception as e:
            logger.warning(f"Failed to parse change string '{change_str}': {e}")
            return None
    
    def validate_price_data(self, data: dict) -> tuple[bool, Optional[str]]:
        """
        가격 데이터 유효성 검증
        
        Args:
            data: 검증할 가격 데이터
        
        Returns:
            (is_valid, error_message) 튜플
        """
        # 필수 필드 확인
        required_fields = ['ticker', 'date', 'close_price']
        for field in required_fields:
            if field not in data or data[field] is None:
                return False, f"Missing required field: {field}"
        
        # 날짜 타입 확인
        if not isinstance(data['date'], date):
            return False, f"Invalid date type: {type(data['date'])}"
        
        # 종가 검증 (양수)
        if data['close_price'] <= 0:
            return False, f"Invalid close_price: {data['close_price']} (must be > 0)"
        
        # 시가/고가/저가 검증 (있는 경우)
        for price_field in ['open_price', 'high_price', 'low_price']:
            if price_field in data and data[price_field] is not None:
                if data[price_field] <= 0:
                    return False, f"Invalid {price_field}: {data[price_field]} (must be > 0)"
        
        # 거래량 검증 (0 이상)
        if 'volume' in data and data['volume'] is not None:
            if data['volume'] < 0:
                return False, f"Invalid volume: {data['volume']} (must be >= 0)"
        
        # 고가 >= 저가 검증
        if (data.get('high_price') is not None and 
            data.get('low_price') is not None):
            if data['high_price'] < data['low_price']:
                return False, f"high_price ({data['high_price']}) < low_price ({data['low_price']})"
        
        # 시가/고가/저가가 모두 있는 경우 범위 검증
        if (data.get('open_price') is not None and 
            data.get('high_price') is not None and 
            data.get('low_price') is not None):
            if not (data['low_price'] <= data['open_price'] <= data['high_price']):
                return False, f"open_price ({data['open_price']}) out of range [{data['low_price']}, {data['high_price']}]"
        
        # 종가 범위 검증
        if (data.get('high_price') is not None and 
            data.get('low_price') is not None):
            if not (data['low_price'] <= data['close_price'] <= data['high_price']):
                return False, f"close_price ({data['close_price']}) out of range [{data['low_price']}, {data['high_price']}]"
        
        return True, None
    
    def clean_price_data(self, data: dict) -> dict:
        """
        가격 데이터 정제 및 정규화
        
        Args:
            data: 정제할 가격 데이터
        
        Returns:
            정제된 가격 데이터
        """
        cleaned = data.copy()
        
        # 거래량이 None인 경우 0으로 처리
        if cleaned.get('volume') is None:
            cleaned['volume'] = 0
        
        # 거래량을 정수로 변환
        if isinstance(cleaned.get('volume'), float):
            cleaned['volume'] = int(cleaned['volume'])
        
        # 가격 필드를 소수점 2자리로 반올림 (누락된 필드는 None으로 유지)
        price_fields = ['open_price', 'high_price', 'low_price', 'close_price']
        for field in price_fields:
            if field not in cleaned:
                cleaned[field] = None
            elif cleaned[field] is not None:
                cleaned[field] = round(float(cleaned[field]), 2)
        
        # 등락률을 소수점 2자리로 반올림 (누락된 경우 None)
        if 'daily_change_pct' not in cleaned:
            cleaned['daily_change_pct'] = None
        elif cleaned['daily_change_pct'] is not None:
            cleaned['daily_change_pct'] = round(float(cleaned['daily_change_pct']), 2)
        
        return cleaned
    
    def save_price_data(self, price_data: List[dict]) -> int:
        """
        가격 데이터를 데이터베이스에 저장 (검증 및 정제 포함)

        Args:
            price_data: 저장할 가격 데이터 리스트

        Returns:
            저장된 레코드 수
        """
        if not price_data:
            return 0

        saved_count = 0

        with get_db_connection() as conn:
            cursor = conn.cursor()

            try:
                for data in price_data:
                    # 데이터 검증
                    is_valid, error_msg = self.validate_price_data(data)
                    if not is_valid:
                        logger.warning(f"Skipping invalid data for {data.get('ticker')} on {data.get('date')}: {error_msg}")
                        continue

                    # 데이터 정제
                    cleaned_data = self.clean_price_data(data)

                    try:
                        cursor.execute("""
                            INSERT OR REPLACE INTO prices
                            (ticker, date, open_price, high_price, low_price, close_price, volume, daily_change_pct)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            cleaned_data['ticker'],
                            cleaned_data['date'],
                            cleaned_data['open_price'],
                            cleaned_data['high_price'],
                            cleaned_data['low_price'],
                            cleaned_data['close_price'],
                            cleaned_data['volume'],
                            cleaned_data['daily_change_pct']
                        ))
                        saved_count += 1
                    except Exception as e:
                        logger.error(f"Failed to save price data for {cleaned_data.get('ticker')} on {cleaned_data.get('date')}: {e}")

                conn.commit()
                logger.info(f"Saved {saved_count} price records to database")

            except Exception as e:
                conn.rollback()
                logger.error(f"Database error while saving price data: {e}")

        return saved_count
    
    def collect_and_save_prices(self, ticker: str, days: int = 10) -> int:
        """
        Naver Finance에서 데이터 수집 후 데이터베이스에 저장
        
        Args:
            ticker: 종목 코드
            days: 수집할 일수
        
        Returns:
            저장된 레코드 수
        """
        logger.info(f"Starting price collection for {ticker} (last {days} days)")
        
        # 데이터 수집
        price_data = self.fetch_naver_finance_prices(ticker, days)
        
        if not price_data:
            logger.warning(f"No data collected for {ticker}")
            return 0
        
        # 데이터 저장
        saved_count = self.save_price_data(price_data)
        
        # Rate limiting은 fetch 함수에서 RateLimiter로 처리
        return saved_count
    
    def get_all_etfs(self) -> List[ETF]:
        """Get list of all ETFs from database"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM etfs")
            rows = cursor.fetchall()
            return [ETF(**dict(row)) for row in rows]
    
    def get_etf_info(self, ticker: str) -> Optional[ETF]:
        """Get basic info for specific ETF"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM etfs WHERE ticker = ?", (ticker,))
            row = cursor.fetchone()

            if row:
                return ETF(**dict(row))
            return None
    
    def get_price_data(self, ticker: str, start_date: date, end_date: date) -> List[PriceData]:
        """Get price data for date range"""
        # TODO: Implement actual data collection from Naver Finance
        logger.info(f"Fetching prices for {ticker} from {start_date} to {end_date}")

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT date, open_price, high_price, low_price, close_price, volume, daily_change_pct
                FROM prices
                WHERE ticker = ? AND date BETWEEN ? AND ?
                ORDER BY date DESC
            """, (ticker, start_date, end_date))
            rows = cursor.fetchall()
            return [PriceData(**dict(row)) for row in rows]
    
    def get_trading_flow(self, ticker: str, start_date: date, end_date: date) -> List[TradingFlow]:
        """Get trading flow data"""
        logger.info(f"Fetching trading flow for {ticker} from {start_date} to {end_date}")

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT date, individual_net, institutional_net, foreign_net
                FROM trading_flow
                WHERE ticker = ? AND date BETWEEN ? AND ?
                ORDER BY date DESC
            """, (ticker, start_date, end_date))
            rows = cursor.fetchall()
            return [TradingFlow(**dict(row)) for row in rows]
    
    def get_etf_metrics(self, ticker: str) -> ETFMetrics:
        """Calculate key metrics for ETF"""
        # TODO: Implement metrics calculation
        logger.info(f"Calculating metrics for {ticker}")
        
        return ETFMetrics(
            ticker=ticker,
            aum=None,
            returns={"1w": 0.0, "1m": 0.0, "ytd": 0.0},
            volatility=None
        )
    
    def collect_all_tickers(self, days: int = 1) -> dict:
        """
        모든 종목의 가격 데이터를 일괄 수집
        
        Args:
            days: 수집할 일수 (기본: 1일 - 당일 데이터)
        
        Returns:
            수집 결과 딕셔너리 {
                'success_count': 성공한 종목 수,
                'fail_count': 실패한 종목 수,
                'total_records': 총 수집된 레코드 수,
                'details': 종목별 상세 결과
            }
        """
        start_time = datetime.now()
        logger.info(f"[일괄 수집] 시작: {days}일치 데이터")
        
        # 전체 종목 조회
        all_etfs = self.get_all_etfs()
        tickers = [etf.ticker for etf in all_etfs]
        
        success_count = 0
        fail_count = 0
        total_records = 0
        details = []
        
        for ticker in tickers:
            try:
                # 종목 정보 확인
                etf_info = self.get_etf_info(ticker)
                if not etf_info:
                    logger.warning(f"[일괄 수집] 종목 정보 없음: {ticker}")
                    fail_count += 1
                    details.append({
                        'ticker': ticker,
                        'status': 'failed',
                        'reason': 'ETF info not found',
                        'collected': 0
                    })
                    continue
                
                # 데이터 수집
                collected_count = self.collect_and_save_prices(ticker, days)
                
                if collected_count > 0:
                    logger.info(f"[일괄 수집] {ticker} ({etf_info.name}): {collected_count}개 수집 성공")
                    success_count += 1
                    total_records += collected_count
                    details.append({
                        'ticker': ticker,
                        'name': etf_info.name,
                        'status': 'success',
                        'collected': collected_count
                    })
                else:
                    logger.warning(f"[일괄 수집] {ticker}: 수집 데이터 없음")
                    fail_count += 1
                    details.append({
                        'ticker': ticker,
                        'name': etf_info.name,
                        'status': 'failed',
                        'reason': 'No data collected',
                        'collected': 0
                    })
                    
            except Exception as e:
                logger.error(f"[일괄 수집] {ticker} 실패: {e}")
                fail_count += 1
                details.append({
                    'ticker': ticker,
                    'status': 'failed',
                    'reason': str(e),
                    'collected': 0
                })
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        result = {
            'success_count': success_count,
            'fail_count': fail_count,
            'total_records': total_records,
            'total_tickers': len(tickers),
            'duration_seconds': round(duration, 2),
            'details': details
        }
        
        logger.info(
            f"[일괄 수집] 완료: 성공 {success_count}/{len(tickers)}, "
            f"총 {total_records}개 레코드, 소요 시간 {duration:.2f}초"
        )
        
        return result
    
    def backfill_all_tickers(self, days: int = 90) -> dict:
        """
        모든 종목의 히스토리 데이터를 백필
        
        Args:
            days: 백필할 일수 (기본: 90일)
        
        Returns:
            백필 결과 딕셔너리
        """
        start_time = datetime.now()
        logger.info(f"[백필] 시작: {days}일치 데이터")
        
        # 전체 종목 조회
        all_etfs = self.get_all_etfs()
        tickers = [etf.ticker for etf in all_etfs]
        
        success_count = 0
        fail_count = 0
        total_records = 0
        details = []
        
        for ticker in tickers:
            try:
                etf_info = self.get_etf_info(ticker)
                if not etf_info:
                    logger.warning(f"[백필] 종목 정보 없음: {ticker}")
                    fail_count += 1
                    details.append({
                        'ticker': ticker,
                        'status': 'failed',
                        'reason': 'ETF info not found',
                        'collected': 0
                    })
                    continue
                
                # 히스토리 데이터 수집
                collected_count = self.collect_and_save_prices(ticker, days)
                
                if collected_count > 0:
                    logger.info(f"[백필] {ticker} ({etf_info.name}): {collected_count}개 수집")
                    total_records += collected_count
                    success_count += 1
                    details.append({
                        'ticker': ticker,
                        'name': etf_info.name,
                        'status': 'success',
                        'collected': collected_count
                    })
                else:
                    logger.warning(f"[백필] {ticker}: 수집 데이터 없음")
                    fail_count += 1
                    details.append({
                        'ticker': ticker,
                        'name': etf_info.name,
                        'status': 'failed',
                        'reason': 'No data collected',
                        'collected': 0
                    })
                    
            except Exception as e:
                logger.error(f"[백필] {ticker} 실패: {e}")
                fail_count += 1
                details.append({
                    'ticker': ticker,
                    'status': 'failed',
                    'reason': str(e),
                    'collected': 0
                })
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        result = {
            'success_count': success_count,
            'fail_count': fail_count,
            'total_records': total_records,
            'total_tickers': len(tickers),
            'days': days,
            'duration_seconds': round(duration, 2),
            'details': details
        }
        
        logger.info(
            f"[백필] 완료: 성공 {success_count}/{len(tickers)}, "
            f"총 {total_records}개 레코드, 소요 시간 {duration:.2f}초"
        )
        
        return result
    
    @retry_with_backoff(
        max_retries=3,
        base_delay=1.0,
        exceptions=(requests.exceptions.RequestException, requests.exceptions.Timeout)
    )
    def fetch_naver_trading_flow(self, ticker: str, days: int = 10) -> List[dict]:
        """
        Naver Finance에서 투자자별 매매동향 데이터 수집
        
        Args:
            ticker: 종목 코드
            days: 수집할 일수 (기본: 10일)
        
        Returns:
            수집된 매매동향 데이터 리스트
        """
        try:
            # Naver Finance 투자자별 매매동향 페이지
            url = f"https://finance.naver.com/item/frgn.naver?code={ticker}"
            logger.info(f"Fetching trading flow from Naver Finance for {ticker}")
            
            with self.rate_limiter:
                response = requests.get(url, headers=self.headers, timeout=10)
                response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 매매동향 테이블 찾기 (두 번째 type2 테이블)
            # 첫 번째는 증권사별 매매, 두 번째가 투자자별 매매동향
            tables = soup.find_all('table', {'class': 'type2'})
            if len(tables) < 2:
                logger.error(f"Trading flow table not found for {ticker}")
                return []
            
            table = tables[1]  # 두 번째 테이블 선택
            
            # 데이터 행 추출
            rows = table.find_all('tr')
            trading_data = []
            count = 0
            
            for row in rows:
                if count >= days:
                    break
                
                cols = row.find_all('td')
                # 실제 데이터 행은 7개 이상의 컬럼을 가짐
                # [0]날짜 [1]종가 [2]전일비 [3]등락률 [4]거래량 [5]기관 [6]외국인 [7]외국인보유 [8]지분율
                if len(cols) < 7:
                    continue
                
                try:
                    # 날짜 추출
                    date_text = cols[0].get_text(strip=True)
                    if not date_text or date_text == '날짜' or '.' not in date_text:
                        continue
                    
                    # 날짜 파싱 (YYYY.MM.DD 형식)
                    trade_date = datetime.strptime(date_text, '%Y.%m.%d').date()
                    
                    # 투자자별 순매수 추출 (천주 단위)
                    # 기관 (5번 컬럼)
                    institutional_text = cols[5].get_text(strip=True)
                    institutional_net = self._parse_trading_volume(institutional_text)
                    
                    # 외국인 (6번 컬럼)
                    foreign_text = cols[6].get_text(strip=True)
                    foreign_net = self._parse_trading_volume(foreign_text)
                    
                    # 개인 = -(기관 + 외국인)
                    # None 처리: 기관이나 외국인이 None이면 개인도 None
                    if institutional_net is not None and foreign_net is not None:
                        individual_net = -(institutional_net + foreign_net)
                    else:
                        individual_net = None
                    
                    trading_data.append({
                        'ticker': ticker,
                        'date': trade_date,
                        'individual_net': individual_net,
                        'institutional_net': institutional_net,
                        'foreign_net': foreign_net
                    })
                    
                    count += 1
                    
                except (ValueError, AttributeError, IndexError) as e:
                    logger.warning(f"Failed to parse trading flow row for {ticker}: {e}")
                    continue
            
            logger.info(f"Collected {len(trading_data)} trading flow records for {ticker}")
            return trading_data
            
        except requests.exceptions.Timeout:
            logger.error(f"Timeout fetching trading flow for {ticker}")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error fetching trading flow for {ticker}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching trading flow for {ticker}: {e}")
            return []
    
    def _parse_trading_volume(self, text: str) -> Optional[int]:
        """
        거래량 텍스트를 정수로 변환 (천주 단위)
        
        Args:
            text: 거래량 텍스트 (예: "1,234", "-5,678")
        
        Returns:
            정수로 변환된 거래량 (천주 단위), 실패 시 None
        """
        try:
            if not text or text.strip() == '':
                return None
            
            # 쉼표 제거 및 숫자 추출
            cleaned = text.replace(',', '').strip()
            
            # 빈 문자열이면 None
            if not cleaned or cleaned == '-':
                return None
            
            return int(cleaned)
            
        except (ValueError, AttributeError):
            return None
    
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

        saved_count = 0

        with get_db_connection() as conn:
            cursor = conn.cursor()

            try:
                for data in valid_data:
                    try:
                        cursor.execute("""
                            INSERT OR REPLACE INTO trading_flow
                            (ticker, date, individual_net, institutional_net, foreign_net)
                            VALUES (?, ?, ?, ?, ?)
                        """, (
                            data['ticker'],
                            data['date'],
                            data.get('individual_net'),
                            data.get('institutional_net'),
                            data.get('foreign_net')
                        ))
                        saved_count += 1

                    except Exception as e:
                        logger.error(f"Failed to save trading flow record: {e}")
                        continue

                conn.commit()
                logger.info(f"Saved {saved_count} trading flow records")

            except Exception as e:
                logger.error(f"Database error saving trading flow: {e}")
                conn.rollback()

        return saved_count
    
    def collect_and_save_trading_flow(self, ticker: str, days: int = 10) -> int:
        """
        매매동향 데이터를 수집하고 저장
        
        Args:
            ticker: 종목 코드
            days: 수집할 일수
        
        Returns:
            저장된 레코드 수
        """
        logger.info(f"Starting trading flow collection for {ticker} (last {days} days)")
        
        # 데이터 수집
        trading_data = self.fetch_naver_trading_flow(ticker, days)
        
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
        end_date: date
    ) -> List[Dict]:
        """
        데이터베이스에서 매매동향 데이터 조회

        Args:
            ticker: 종목 코드
            start_date: 시작 날짜
            end_date: 종료 날짜

        Returns:
            매매동향 데이터 리스트
        """
        logger.info(f"Fetching trading flow for {ticker} from {start_date} to {end_date}")

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT date, individual_net, institutional_net, foreign_net
                FROM trading_flow
                WHERE ticker = ? AND date BETWEEN ? AND ?
                ORDER BY date DESC
            """, (ticker, start_date, end_date))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
