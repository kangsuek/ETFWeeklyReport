"""
Application configuration management
"""
import os
import json
from typing import Dict, Any, Optional, List
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class Config:
    """Application configuration from environment variables and JSON files"""
    
    # API Settings
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", "8000"))

    # API Key for authentication (optional in development)
    # If not set, all requests are allowed
    API_KEY = os.getenv("API_KEY")

    # CORS Settings
    # Parse comma-separated origins from environment variable
    CORS_ORIGINS = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://localhost:3000"
    ).split(",")

    # Naver API
    NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
    NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")

    # Scheduler Settings
    SCRAPING_INTERVAL_MINUTES = int(os.getenv("SCRAPING_INTERVAL_MINUTES", "3"))

    # 뉴스는 3분 주기 수집 루프에서 매번 호출할 필요가 없다(같은 기사가 대부분).
    # 이 간격(분) 이내면 주기 수집에서 뉴스 단계를 건너뛴다. 가격/매매동향은 그대로 매 주기 수집.
    NEWS_COLLECT_INTERVAL_MINUTES = int(os.getenv("NEWS_COLLECT_INTERVAL_MINUTES", "30"))

    # 시각 기반 cron 작업(일일 15:30, 카탈로그 03:00, 카탈로그데이터 16:00, 펀더멘털 16:30,
    # 백필 일 02:00) 활성화 여부. 웹 배포(데몬)에서는 True로 유지, 데스크톱 App(비데몬)에서는
    # 그 시각에 앱이 떠 있어야만 발화하므로 False로 꺼서 "실행 시 + 버튼" 온디맨드로 일원화한다.
    ENABLE_SCHEDULED_JOBS = os.getenv("ENABLE_SCHEDULED_JOBS", "true").lower() == "true"

    # Intraday Settings
    # 종목상세 조회 중 장중 분봉 재수집 임계값(초). 마지막 체결이 이 값보다
    # 오래되면 증분 재수집을 트리거한다. 네이버 sise_time은 약 1분 간격
    # 체결을 제공하므로 기본 60초로 분단위 갱신을 보장한다.
    INTRADAY_RECOLLECT_THRESHOLD_SECONDS = int(
        os.getenv("INTRADAY_RECOLLECT_THRESHOLD_SECONDS", "60")
    )

    # Scanner (catalog data) Settings
    # 종목발굴 데이터 수집 freshness 가드. 스캐너 데이터는 일 단위 확정
    # 데이터라 최근 장 마감분을 확보했으면 재수집을 스킵한다. 장중(09:00~15:30)에는
    # 가격만 움직이므로 이 TTL(시간) 이내면 재수집을 스킵한다. force=true면 무시.
    SCANNER_COLLECT_TTL_HOURS = int(os.getenv("SCANNER_COLLECT_TTL_HOURS", "6"))

    # sise_market_sum(KOSPI 80p + KOSDAQ 110p) 크롤 결과 공유 TTL(분). 종목목록 수집과
    # 스캐너 데이터 수집이 이 시간 이내 연달아 실행되면 뒤쪽이 앞쪽 크롤 결과를 재사용한다(D1).
    SISE_CACHE_TTL_MINUTES = int(os.getenv("SISE_CACHE_TTL_MINUTES", "30"))

    # Cache Settings (메모리 캐시 구현됨)
    CACHE_TTL_MINUTES = float(os.getenv("CACHE_TTL_MINUTES", "3"))
    
    # Stock Configuration File Path
    STOCK_CONFIG_PATH = os.getenv(
        "STOCK_CONFIG_PATH",
        str(Path(__file__).parent.parent / "config" / "stocks.json")
    )
    
    _stock_config_cache: Optional[Dict[str, Any]] = None
    
    @classmethod
    def get_stock_config(cls) -> Dict[str, Any]:
        """
        Get stock configuration from JSON file
        
        Returns:
            Dict[str, Any]: Stock configuration with ticker as key
            
        Example:
            {
                "487240": {
                    "name": "삼성 KODEX AI전력핵심설비 ETF",
                    "type": "ETF",
                    "search_keyword": "AI 전력",
                    "relevance_keywords": ["AI", "전력", "데이터센터"]
                },
                ...
            }
        """
        # Use cached config if available
        if cls._stock_config_cache is not None:
            return cls._stock_config_cache
        
        try:
            config_path = Path(cls.STOCK_CONFIG_PATH)
            
            if not config_path.exists():
                logger.error(f"Stock config file not found: {config_path}")
                return cls._get_fallback_config()
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            logger.debug(f"Loaded {len(config)} stocks from {config_path}")
            cls._stock_config_cache = config
            return config
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse stock config JSON: {e}")
            return cls._get_fallback_config()
        except Exception as e:
            logger.error(f"Error loading stock config: {e}")
            return cls._get_fallback_config()
    
    @classmethod
    def _get_fallback_config(cls) -> Dict[str, Any]:
        """
        Fallback default configuration
        Used when stock config file is not available
        """
        logger.warning("Using fallback stock configuration")
        return {
            "487240": {
                "name": "삼성 KODEX AI전력핵심설비 ETF",
                "type": "ETF",
                "theme": "AI/전력",
                "launch_date": "2024-03-15",
                "expense_ratio": 0.0045,
                "search_keyword": "AI 전력",
                "relevance_keywords": ["AI", "전력", "데이터센터"]
            },
            "466920": {
                "name": "신한 SOL 조선TOP3플러스 ETF",
                "type": "ETF",
                "theme": "조선",
                "launch_date": "2023-08-10",
                "expense_ratio": 0.0050,
                "search_keyword": "조선 ETF",
                "relevance_keywords": ["조선", "ETF", "한화오션", "HD현대중공업"]
            },
            "0020H0": {
                "name": "KoAct 글로벌양자컴퓨팅액티브 ETF",
                "type": "ETF",
                "theme": "양자컴퓨팅",
                "launch_date": "2024-05-20",
                "expense_ratio": 0.0070,
                "search_keyword": "양자컴퓨팅 ETF",
                "relevance_keywords": ["양자컴퓨팅", "ETF"]
            },
            "442320": {
                "name": "KB RISE 글로벌원자력 iSelect ETF",
                "type": "ETF",
                "theme": "원자력",
                "launch_date": "2024-01-25",
                "expense_ratio": 0.0055,
                "search_keyword": "원자력 ETF",
                "relevance_keywords": ["원자력", "ETF", "SMR"]
            },
            "042660": {
                "name": "한화오션",
                "type": "STOCK",
                "theme": "조선/방산",
                "launch_date": None,
                "expense_ratio": None,
                "search_keyword": "한화오션",
                "relevance_keywords": ["한화오션", "조선", "방산"]
            },
            "034020": {
                "name": "두산에너빌리티",
                "type": "STOCK",
                "theme": "에너지/전력",
                "launch_date": None,
                "expense_ratio": None,
                "search_keyword": "두산에너빌리티",
                "relevance_keywords": ["두산에너빌리티", "원자력", "에너지"]
            }
        }
    
    @classmethod
    def get_stock_info(cls, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Get specific stock information
        
        Args:
            ticker: Stock ticker code (e.g., "487240")
            
        Returns:
            Dict with stock info or None if not found
        """
        config = cls.get_stock_config()
        return config.get(ticker)
    
    @classmethod
    def get_all_tickers(cls) -> List[str]:
        """
        Get all configured ticker codes
        
        Returns:
            List of ticker codes
        """
        config = cls.get_stock_config()
        return list(config.keys())
    
    @classmethod
    def reload_stock_config(cls):
        """
        Reload stock configuration from file
        Useful when config file is updated
        """
        cls._stock_config_cache = None
        return cls.get_stock_config()
