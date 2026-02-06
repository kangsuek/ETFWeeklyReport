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
