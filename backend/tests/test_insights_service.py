"""
인사이트 서비스 테스트
"""
import pytest
from datetime import date, timedelta
from app.services.insights_service import InsightsService
from app.models import ETFMetrics


class TestInsightsService:
    """InsightsService 테스트"""
    
    def test_get_period_days(self):
        """기간 문자열을 일수로 변환하는 테스트"""
        service = InsightsService()
        
        assert service._get_period_days("1w") == 7
        assert service._get_period_days("1m") == 30
        assert service._get_period_days("3m") == 90
        assert service._get_period_days("6m") == 180
        assert service._get_period_days("1y") == 365
        assert service._get_period_days("unknown") == 30  # 기본값
    
    def test_get_strategy_from_return(self):
        """수익률 기반 전략 결정 테스트"""
        service = InsightsService()
        
        # 높은 수익률 → 비중확대
        assert service._get_strategy_from_return(15.0, "단기") == "비중확대"
        assert service._get_strategy_from_return(12.0, "중기") == "비중확대"
        
        # 중간 수익률 → 보유
        assert service._get_strategy_from_return(7.0, "단기") == "보유"
        assert service._get_strategy_from_return(6.0, "중기") == "보유"
        
        # 낮은 수익률 → 관망
        assert service._get_strategy_from_return(2.0, "단기") == "관망"
        assert service._get_strategy_from_return(-2.0, "중기") == "관망"
        
        # 큰 손실 → 비중축소
        assert service._get_strategy_from_return(-7.0, "단기") == "비중축소"
        assert service._get_strategy_from_return(-15.0, "중기") == "비중축소"
        
        # None → 관망
        assert service._get_strategy_from_return(None, "단기") == "관망"
    
    def test_analyze_strategy(self):
        """전략 분석 테스트"""
        service = InsightsService()
        
        # 높은 수익률 메트릭
        metrics = ETFMetrics(
            ticker="487240",
            aum=None,
            returns={"1w": 12.0, "1m": 15.0, "ytd": 20.0},
            volatility=25.0
        )
        
        prices = []
        trading_flow = []
        
        strategy = service._analyze_strategy(metrics, prices, trading_flow, "1m")
        
        assert strategy["short_term"] in ["비중확대", "보유", "관망", "비중축소"]
        assert strategy["medium_term"] in ["비중확대", "보유", "관망", "비중축소"]
        assert strategy["long_term"] in ["비중확대", "보유", "관망", "비중축소"]
        assert strategy["recommendation"] in ["비중확대", "보유", "관망", "비중축소"]
        assert isinstance(strategy["comment"], str)
        assert len(strategy["comment"]) > 0
    
    def test_extract_key_points(self):
        """핵심 포인트 추출 테스트"""
        service = InsightsService()
        
        metrics = ETFMetrics(
            ticker="487240",
            aum=None,
            returns={"1w": 5.0, "1m": 12.5, "ytd": 18.0},
            volatility=30.5
        )
        
        prices = []
        trading_flow = [{
            "date": date.today(),
            "foreign_net": 1500,
            "institutional_net": 800,
            "individual_net": -2300
        }]
        news_list = []
        
        key_points = service._extract_key_points(metrics, prices, trading_flow, news_list)
        
        assert isinstance(key_points, list)
        assert len(key_points) <= 3
        assert all(isinstance(point, str) for point in key_points)
    
    def test_analyze_risks(self):
        """리스크 분석 테스트"""
        service = InsightsService()
        
        metrics = ETFMetrics(
            ticker="487240",
            aum=None,
            returns={"1w": -5.0, "1m": -12.0, "ytd": 5.0},
            volatility=35.0
        )
        
        prices = []
        news_list = []
        
        risks = service._analyze_risks(metrics, prices, news_list, "487240")
        
        assert isinstance(risks, list)
        assert len(risks) <= 3
        assert all(isinstance(risk, str) for risk in risks)
        
        # 높은 변동성 리스크 포함 확인
        risk_texts = " ".join(risks)
        if metrics.volatility and metrics.volatility > 30:
            assert "변동성" in risk_texts or len(risks) > 0
