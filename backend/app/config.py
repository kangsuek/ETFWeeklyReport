from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # API Settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: List[str] = ["http://localhost:5173", "http://localhost:3000"]
    
    # Database
    database_url: str = "sqlite:///./data/etf_data.db"
    
    # Data Collection
    cache_ttl_minutes: int = 10
    news_max_results: int = 5
    
    class Config:
        env_file = ".env"

settings = Settings()
