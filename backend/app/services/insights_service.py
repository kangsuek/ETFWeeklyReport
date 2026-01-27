"""
인사이트 서비스

종목의 투자 전략, 핵심 포인트, 리스크를 분석하여 제공합니다.
"""
from typing import Dict, List, Optional
from datetime import date, timedelta
from app.database import get_db_connection, get_cursor, USE_POSTGRES
from app.services.data_collector import ETFDataCollector
from app.services.news_scraper import NewsScraper
import logging
import math

logger = logging.getLogger(__name__)


class InsightsService:
    """종목 인사이트 생성 서비스"""
    
    def __init__(self):
        self.data_collector = ETFDataCollector()
        self.news_scraper = NewsScraper()
    
    def get_insights(
        self,
        ticker: str,
        period: str = "1m"
    ) -> Dict:
        """
        종목 인사이트 생성
        
        Args:
            ticker: 종목 코드
            period: 분석 기간 ("1w", "1m", "3m", "6m", "1y")
        
        Returns:
            {
                "strategy": {...},
                "key_points": [...],
                "risks": [...]
            }
        """
        logger.info(f"Generating insights for {ticker} (period: {period})")
        
        # 기간에 따른 날짜 범위 계산
        today = date.today()
        period_days = self._get_period_days(period)
        start_date = today - timedelta(days=period_days)
        
        # 데이터 수집
        metrics = self.data_collector.get_etf_metrics(ticker)
        prices = self.data_collector.get_price_data(ticker, start_date, today)
        trading_flow_data = self.data_collector.get_trading_flow(ticker, start_date, today)
        
        # 뉴스 데이터 (최근 7일)
        news_start = today - timedelta(days=7)
        news_list = self.news_scraper.get_news_for_ticker(ticker, news_start, today)
        
        # 전략 분석
        strategy = self._analyze_strategy(metrics, prices, trading_flow_data, period)
        
        # 핵심 포인트 추출
        key_points = self._extract_key_points(metrics, prices, trading_flow_data, news_list)
        
        # 리스크 분석
        risks = self._analyze_risks(metrics, prices, news_list, ticker)
        
        return {
            "strategy": strategy,
            "key_points": key_points,
            "risks": risks
        }
    
    def _get_period_days(self, period: str) -> int:
        """기간 문자열을 일수로 변환"""
        period_map = {
            "1w": 7,
            "1m": 30,
            "3m": 90,
            "6m": 180,
            "1y": 365
        }
        return period_map.get(period, 30)
    
    def _analyze_strategy(
        self,
        metrics,
        prices: List,
        trading_flow: List,
        period: str
    ) -> Dict:
        """
        투자 전략 분석
        
        Returns:
            {
                "short_term": "관망",
                "medium_term": "비중확대",
                "long_term": "보유",
                "recommendation": "비중확대",
                "comment": "..."
            }
        """
        # 수익률 기반 분석
        returns = metrics.returns if hasattr(metrics, 'returns') else {}
        volatility = metrics.volatility if hasattr(metrics, 'volatility') else None
        
        # 단기 전략 (1주 수익률 기반)
        short_term_return = returns.get("1w")
        short_term = self._get_strategy_from_return(short_term_return, "단기")
        
        # 중기 전략 (1개월 수익률 기반)
        medium_term_return = returns.get("1m")
        medium_term = self._get_strategy_from_return(medium_term_return, "중기")
        
        # 장기 전략 (YTD 수익률 기반)
        long_term_return = returns.get("ytd")
        long_term = self._get_strategy_from_return(long_term_return, "장기")
        
        # 종합 추천 (중기 전략 우선)
        recommendation = medium_term if medium_term else short_term
        
        # 코멘트 생성
        comment = self._generate_strategy_comment(
            short_term_return,
            medium_term_return,
            volatility,
            trading_flow
        )
        
        return {
            "short_term": short_term,
            "medium_term": medium_term,
            "long_term": long_term,
            "recommendation": recommendation,
            "comment": comment
        }
    
    def _get_strategy_from_return(self, return_pct: Optional[float], period_type: str) -> str:
        """수익률 기반 전략 결정"""
        if return_pct is None:
            return "관망"
        
        if return_pct > 10:
            return "비중확대"
        elif return_pct > 5:
            return "보유"
        elif return_pct > -5:
            return "관망"
        elif return_pct > -10:
            return "비중축소"
        else:
            return "비중축소"
    
    def _generate_strategy_comment(
        self,
        short_term_return: Optional[float],
        medium_term_return: Optional[float],
        volatility: Optional[float],
        trading_flow: List
    ) -> str:
        """전략 코멘트 생성"""
        comments = []
        
        # 단기 수익률 코멘트
        if short_term_return is not None:
            if short_term_return > 5:
                comments.append("단기 급등 구간")
            elif short_term_return < -5:
                comments.append("단기 하락 압력")
        
        # 변동성 코멘트
        if volatility is not None:
            if volatility > 30:
                comments.append("변동성 확대 예상")
            elif volatility < 15:
                comments.append("변동성 안정적")
        
        # 매매동향 코멘트
        if trading_flow:
            recent_flow = trading_flow[0] if trading_flow else None
            if recent_flow:
                # TradingFlow 객체 또는 dict 처리
                if hasattr(recent_flow, 'foreign_net'):
                    foreign_net = recent_flow.foreign_net or 0
                    institutional_net = recent_flow.institutional_net or 0
                elif isinstance(recent_flow, dict):
                    foreign_net = recent_flow.get("foreign_net", 0) or 0
                    institutional_net = recent_flow.get("institutional_net", 0) or 0
                else:
                    foreign_net = 0
                    institutional_net = 0
            else:
                foreign_net = 0
                institutional_net = 0
            
            if foreign_net > 0 and institutional_net > 0:
                comments.append("기관·외국인 동시 매수")
            elif foreign_net < 0 and institutional_net < 0:
                comments.append("기관·외국인 동시 매도")
        
        if not comments:
            return "현재 시장 상황을 지속적으로 모니터링 필요"
        
        return ", ".join(comments)
    
    def _extract_key_points(
        self,
        metrics,
        prices: List,
        trading_flow: List,
        news_list: List
    ) -> List[str]:
        """핵심 포인트 추출"""
        key_points = []
        
        # 수익률 포인트
        returns = metrics.returns if hasattr(metrics, 'returns') else {}
        if returns.get("1m"):
            return_1m = returns["1m"]
            if return_1m > 10:
                key_points.append(f"1개월 수익률 {return_1m:.1f}%로 강세 지속")
            elif return_1m < -10:
                key_points.append(f"1개월 수익률 {return_1m:.1f}%로 약세 지속")
        
        # 변동성 포인트
        volatility = metrics.volatility if hasattr(metrics, 'volatility') else None
        if volatility:
            if volatility > 30:
                key_points.append("변동성 확대 구간, 리스크 관리 필요")
            elif volatility < 15:
                key_points.append("변동성 안정적, 안전자산 선호 시 유리")
        
        # 매매동향 포인트
        if trading_flow:
            recent_flow = trading_flow[0] if trading_flow else None
            if recent_flow:
                # TradingFlow 객체 또는 dict 처리
                if hasattr(recent_flow, 'foreign_net'):
                    foreign_net = recent_flow.foreign_net or 0
                elif isinstance(recent_flow, dict):
                    foreign_net = recent_flow.get("foreign_net", 0) or 0
                else:
                    foreign_net = 0
            else:
                foreign_net = 0
            
            if foreign_net > 1000:  # 천주 단위
                key_points.append("외국인 대규모 순매수 지속")
            elif foreign_net < -1000:
                key_points.append("외국인 대규모 순매도 지속")
        
        # 뉴스 기반 포인트
        if news_list:
            # 최근 뉴스 키워드 분석
            recent_news_count = len(news_list)
            if recent_news_count >= 5:
                key_points.append(f"최근 7일간 관련 뉴스 {recent_news_count}건으로 관심도 높음")
        
        # 기본 포인트 (데이터 부족 시)
        if not key_points:
            key_points.append("충분한 데이터 확보 후 분석 진행")
        
        # 최대 3개까지만 반환
        return key_points[:3]
    
    def _analyze_risks(
        self,
        metrics,
        prices: List,
        news_list: List,
        ticker: str
    ) -> List[str]:
        """리스크 분석"""
        risks = []
        
        # 변동성 리스크
        volatility = metrics.volatility if hasattr(metrics, 'volatility') else None
        if volatility and volatility > 30:
            risks.append("높은 변동성으로 인한 가격 급등락 리스크")
        
        # 하락 리스크
        returns = metrics.returns if hasattr(metrics, 'returns') else {}
        if returns.get("1m") and returns["1m"] < -10:
            risks.append("최근 하락세 지속으로 추가 하락 가능성")
        
        # 뉴스 기반 리스크 키워드 분석
        risk_keywords = ["규제", "관세", "금리", "환율", "경기", "리스크"]
        news_titles = [news.title for news in news_list if hasattr(news, 'title')]
        
        for keyword in risk_keywords:
            if any(keyword in title for title in news_titles):
                if keyword == "규제":
                    risks.append("규제 리스크: 정부 규제 강화 가능성")
                elif keyword == "관세":
                    risks.append("관세 리스크: 무역 분쟁 확대 우려")
                elif keyword == "금리":
                    risks.append("금리 리스크: 금리 변동성 확대")
                elif keyword == "환율":
                    risks.append("환율 리스크: 원/달러 환율 변동성 확대")
                break  # 첫 번째 매칭만
        
        # 기본 리스크 (데이터 부족 시)
        if not risks:
            risks.append("시장 전반의 변동성 리스크 존재")
        
        # 최대 3개까지만 반환
        return risks[:3]
