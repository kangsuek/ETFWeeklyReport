from typing import List, Optional
from datetime import date, datetime, timedelta
from app.models import ETF, PriceData, TradingFlow, ETFMetrics
from app.database import get_db_connection
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
        if not text or text == '':
            return None
        try:
            # 쉼표 제거 후 숫자로 변환
            cleaned = text.replace(',', '')
            return float(cleaned)
        except ValueError:
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
    
    def save_price_data(self, price_data: List[dict]) -> int:
        """
        가격 데이터를 데이터베이스에 저장
        
        Args:
            price_data: 저장할 가격 데이터 리스트
        
        Returns:
            저장된 레코드 수
        """
        if not price_data:
            return 0
        
        conn = get_db_connection()
        cursor = conn.cursor()
        saved_count = 0
        
        try:
            for data in price_data:
                try:
                    cursor.execute("""
                        INSERT OR REPLACE INTO prices 
                        (ticker, date, open_price, high_price, low_price, close_price, volume, daily_change_pct)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        data['ticker'],
                        data['date'],
                        data['open_price'],
                        data['high_price'],
                        data['low_price'],
                        data['close_price'],
                        data['volume'],
                        data['daily_change_pct']
                    ))
                    saved_count += 1
                except Exception as e:
                    logger.error(f"Failed to save price data for {data.get('ticker')} on {data.get('date')}: {e}")
            
            conn.commit()
            logger.info(f"Saved {saved_count} price records to database")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error while saving price data: {e}")
        finally:
            conn.close()
        
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
        
        # Rate limiting (서버 부하 방지)
        time.sleep(0.5)
        
        return saved_count
    
    def get_all_etfs(self) -> List[ETF]:
        """Get list of all ETFs from database"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM etfs")
        rows = cursor.fetchall()
        conn.close()
        
        return [ETF(**dict(row)) for row in rows]
    
    def get_etf_info(self, ticker: str) -> Optional[ETF]:
        """Get basic info for specific ETF"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM etfs WHERE ticker = ?", (ticker,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return ETF(**dict(row))
        return None
    
    def get_price_data(self, ticker: str, start_date: date, end_date: date) -> List[PriceData]:
        """Get price data for date range"""
        # TODO: Implement actual data collection from Naver Finance
        logger.info(f"Fetching prices for {ticker} from {start_date} to {end_date}")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT date, open_price, high_price, low_price, close_price, volume, daily_change_pct
            FROM prices
            WHERE ticker = ? AND date BETWEEN ? AND ?
            ORDER BY date DESC
        """, (ticker, start_date, end_date))
        rows = cursor.fetchall()
        conn.close()
        
        return [PriceData(**dict(row)) for row in rows]
    
    def get_trading_flow(self, ticker: str, start_date: date, end_date: date) -> List[TradingFlow]:
        """Get trading flow data"""
        logger.info(f"Fetching trading flow for {ticker} from {start_date} to {end_date}")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT date, individual_net, institutional_net, foreign_net
            FROM trading_flow
            WHERE ticker = ? AND date BETWEEN ? AND ?
            ORDER BY date DESC
        """, (ticker, start_date, end_date))
        rows = cursor.fetchall()
        conn.close()
        
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
