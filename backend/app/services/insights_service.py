"""
인사이트 서비스

종목의 투자 전략, 핵심 포인트, 리스크를 분석하여 제공합니다.
typed 포인트(points)·리스크 계산의 정본 — 프론트 InsightSummary는 표시만 담당.
"""
from typing import Any, Dict, List, Optional
from datetime import date, timedelta
from app.services.data_collector import ETFDataCollector
from app.services.news_scraper import NewsScraper
from app.services import metrics_service
import logging

logger = logging.getLogger(__name__)


def _flow_field(item: Any, name: str) -> float:
    """TradingFlow 객체 또는 dict에서 순매수 필드 추출 (None → 0)"""
    if hasattr(item, name):
        return getattr(item, name) or 0
    if isinstance(item, dict):
        return item.get(name, 0) or 0
    return 0


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
        logger.debug(f"Generating insights for {ticker} (period: {period})")
        
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

        # typed 인사이트 포인트 (가격 추세·매매동향·기술지표 기반, InsightSummary 표시용)
        points = self._generate_points(prices, trading_flow_data)
        point_risks = self._generate_point_risks(prices, trading_flow_data)

        return {
            "strategy": strategy,
            "key_points": key_points,
            "risks": risks,
            "points": points,
            "point_risks": point_risks,
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

    # ------------------------------------------------------------------
    # typed 인사이트 포인트 (구 frontend utils/insights.js 이식)
    # ------------------------------------------------------------------

    @staticmethod
    def _count_consecutive(items: List, field: str) -> Dict[str, int]:
        """연속 순매수/순매도 일수 (최신순 데이터 기준)"""
        if not items:
            return {"buy": 0, "sell": 0}

        buy = sell = 0
        first = _flow_field(items[0], field)
        if first > 0:
            for item in items:
                if _flow_field(item, field) > 0:
                    buy += 1
                else:
                    break
        elif first < 0:
            for item in items:
                if _flow_field(item, field) < 0:
                    sell += 1
                else:
                    break
        return {"buy": buy, "sell": sell}

    @staticmethod
    def _moving_average(prices: List, period: int) -> Optional[float]:
        """최신순 가격 데이터의 앞 period개 평균"""
        if not prices or len(prices) < period:
            return None
        closes = [p.close_price if hasattr(p, "close_price") else p["close_price"]
                  for p in prices[:period]]
        return sum(closes) / period

    def _generate_trading_points(self, trading_flow: List) -> List[Dict]:
        """매매동향 기반 포인트"""
        if not trading_flow:
            return []

        points = []

        foreign = self._count_consecutive(trading_flow, "foreign_net")
        if foreign["buy"] >= 3:
            points.append({"type": "positive", "category": "trading", "priority": 1,
                           "text": f"외국인 순매수 {foreign['buy']}일 연속 지속 중"})
        elif foreign["sell"] >= 3:
            points.append({"type": "warning", "category": "trading", "priority": 1,
                           "text": f"외국인 순매도 {foreign['sell']}일 연속 지속 중"})

        inst = self._count_consecutive(trading_flow, "institutional_net")
        if inst["buy"] >= 3:
            points.append({"type": "positive", "category": "trading", "priority": 2,
                           "text": f"기관 순매수 {inst['buy']}일 연속 지속 중"})
        elif inst["sell"] >= 3:
            points.append({"type": "warning", "category": "trading", "priority": 2,
                           "text": f"기관 순매도 {inst['sell']}일 연속 지속 중"})

        # 최근 3일 외국인+기관 합산 (10억 원 이상일 때만)
        if len(trading_flow) >= 3:
            recent = trading_flow[:3]
            combined = sum(_flow_field(d, "foreign_net") for d in recent) \
                + sum(_flow_field(d, "institutional_net") for d in recent)
            if abs(combined) > 1_000_000_000:
                amount = f"{abs(combined) / 100_000_000:.0f}"
                if combined > 0:
                    points.append({"type": "positive", "category": "trading", "priority": 3,
                                   "text": f"최근 3일 외국인+기관 순매수 약 {amount}억원"})
                else:
                    points.append({"type": "warning", "category": "trading", "priority": 3,
                                   "text": f"최근 3일 외국인+기관 순매도 약 {amount}억원"})

        return points

    def _generate_price_points(self, prices: List) -> List[Dict]:
        """가격·기술지표 기반 포인트 (prices: 최신순)"""
        if not prices or len(prices) < 5:
            return []

        points = []
        current_price = prices[0].close_price if hasattr(prices[0], "close_price") \
            else prices[0]["close_price"]

        # 이동평균선 추세 + 골든/데드크로스
        ma5 = self._moving_average(prices, 5)
        ma20 = self._moving_average(prices, 20)
        if ma5 and ma20:
            if current_price > ma5 > ma20:
                points.append({"type": "positive", "category": "trend", "priority": 1,
                               "text": "단기 상승 추세 (5일선 > 20일선)"})
            elif current_price < ma5 < ma20:
                points.append({"type": "warning", "category": "trend", "priority": 1,
                               "text": "단기 하락 추세 (5일선 < 20일선)"})

            if len(prices) >= 25:
                prev_ma5 = self._moving_average(prices[5:], 5)
                prev_ma20 = self._moving_average(prices[5:], 20)
                if prev_ma5 and prev_ma20:
                    if prev_ma5 < prev_ma20 and ma5 > ma20:
                        points.append({"type": "positive", "category": "trend", "priority": 0,
                                       "text": "최근 골든크로스 발생 (단기 상승 신호)"})
                    elif prev_ma5 > prev_ma20 and ma5 < ma20:
                        points.append({"type": "warning", "category": "trend", "priority": 0,
                                       "text": "최근 데드크로스 발생 (단기 하락 신호)"})

        # 변동성 (조회 기간의 일간 표준편차 — 기간을 텍스트에 명시)
        volatility = metrics_service.daily_volatility(prices)
        if volatility is not None:
            if volatility > 3:
                points.append({"type": "warning", "category": "volatility", "priority": 2,
                               "text": f"변동성 확대 구간 (최근 {len(prices)}일 일간 {volatility:.1f}%)"})
            elif volatility < 1:
                points.append({"type": "neutral", "category": "volatility", "priority": 3,
                               "text": f"낮은 변동성 유지 (최근 {len(prices)}일 일간 {volatility:.1f}%)"})

        # 20일 최고/최저가 근접
        if len(prices) >= 20:
            closes20 = [p.close_price if hasattr(p, "close_price") else p["close_price"]
                        for p in prices[:20]]
            high, low = max(closes20), min(closes20)
            price_range = high - low
            if price_range > 0:
                if (high - current_price) / price_range * 100 < 5:
                    points.append({"type": "positive", "category": "price", "priority": 2,
                                   "text": "20일 최고가 근접 구간"})
                elif (current_price - low) / price_range * 100 < 5:
                    points.append({"type": "warning", "category": "price", "priority": 2,
                                   "text": "20일 최저가 근접 구간"})

        # 연속 상승/하락일 (최근 10일 내)
        consecutive_up = consecutive_down = 0
        for i in range(min(len(prices) - 1, 10)):
            change = _flow_field(prices[i], "daily_change_pct")
            if change > 0:
                if consecutive_down == 0:
                    consecutive_up += 1
                else:
                    break
            elif change < 0:
                if consecutive_up == 0:
                    consecutive_down += 1
                else:
                    break
            else:
                break

        if consecutive_up >= 4:
            points.append({"type": "positive", "category": "momentum", "priority": 1,
                           "text": f"{consecutive_up}일 연속 상승 중"})
        elif consecutive_down >= 4:
            points.append({"type": "warning", "category": "momentum", "priority": 1,
                           "text": f"{consecutive_down}일 연속 하락 중"})

        # RSI(14) — 30건 이상일 때
        closes_asc = [p.close_price if hasattr(p, "close_price") else p["close_price"]
                      for p in reversed(prices)]
        if len(prices) >= 30:
            rsi = metrics_service.rsi_series(closes_asc, 14)
            valid_rsi = [v for v in rsi if v is not None]
            if valid_rsi:
                last_rsi = valid_rsi[-1]
                if last_rsi >= 70:
                    points.append({"type": "warning", "category": "technical", "priority": 1,
                                   "text": f"RSI {last_rsi:.1f} - 과매수 구간 (매도 시그널)"})
                elif last_rsi <= 30:
                    points.append({"type": "positive", "category": "technical", "priority": 1,
                                   "text": f"RSI {last_rsi:.1f} - 과매도 구간 (매수 시그널)"})

        # MACD(12,26,9) 골든/데드크로스 — 40건 이상일 때
        if len(prices) >= 40:
            macd = metrics_service.macd_series(closes_asc, 12, 26, 9)
            valid = [d for d in macd if d["macd"] is not None and d["signal"] is not None]
            if len(valid) >= 2:
                last, prev = valid[-1], valid[-2]
                if prev["macd"] <= prev["signal"] and last["macd"] > last["signal"]:
                    points.append({"type": "positive", "category": "technical", "priority": 1,
                                   "text": "MACD 골든크로스 발생 (상승 전환 시그널)"})
                elif prev["macd"] >= prev["signal"] and last["macd"] < last["signal"]:
                    points.append({"type": "warning", "category": "technical", "priority": 1,
                                   "text": "MACD 데드크로스 발생 (하락 전환 시그널)"})

        return points

    def _generate_points(self, prices: List, trading_flow: List) -> List[Dict]:
        """가격+매매동향 typed 포인트 통합 (우선순위 정렬, 최대 4개)"""
        all_points = self._generate_price_points(prices) \
            + self._generate_trading_points(trading_flow)
        all_points.sort(key=lambda p: p.get("priority", 99))
        return [
            {"type": p["type"], "category": p.get("category"), "text": p["text"]}
            for p in all_points[:4]
        ]

    def _generate_point_risks(self, prices: List, trading_flow: List) -> List[str]:
        """리스크 요약 (최대 3개) — InsightSummary 표시용"""
        risks = []

        # 높은 변동성 (조회 기간의 일간 표준편차 > 4%)
        volatility = metrics_service.daily_volatility(prices)
        if volatility is not None and volatility > 4:
            risks.append(f"높은 변동성 주의 (최근 {len(prices)}일 일간 {volatility:.1f}%)")

        # 외국인+기관 동반 순매도 3일 연속
        if trading_flow and len(trading_flow) >= 3:
            recent = trading_flow[:3]
            if all(_flow_field(d, "foreign_net") < 0 for d in recent) and \
                    all(_flow_field(d, "institutional_net") < 0 for d in recent):
                risks.append("외국인+기관 동반 순매도 3일 연속")

        # 최근 5일 내 -5% 이상 급락일 존재
        if prices and len(prices) >= 5:
            if any(_flow_field(p, "daily_change_pct") < -5 for p in prices[:5]):
                risks.append("최근 급락일 발생 (단기 변동성 주의)")

        return risks[:3]
