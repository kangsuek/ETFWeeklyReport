from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.routers import etfs, news, data, settings
from app.database import init_db
from app.services.scheduler import get_scheduler
from app.config import Config
from app.utils import stocks_manager
from app.middleware.rate_limit import limiter, rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.utils.structured_logging import (
    setup_structured_logging,
    get_logger,
    log_error,
)
from pathlib import Path
from dotenv import load_dotenv
import os
import time

# 프로젝트 루트의 .env 로드
_root_dir = Path(__file__).resolve().parent.parent.parent
load_dotenv(_root_dir / ".env")

# 구조화된 로깅 설정
# JSON 형식으로 출력 (프로덕션), 개발 환경에서는 콘솔 형식
json_logging = os.getenv("JSON_LOGGING", "false").lower() == "true"
log_level = os.getenv("LOG_LEVEL", "INFO")

setup_structured_logging(
    log_level=log_level,
    json_output=json_logging,
    include_timestamp=True,
)

logger = get_logger(__name__)

app = FastAPI(
    title="ETF Weekly Report API",
    description="API for Korean ETF analysis and reporting",
    version="1.0.0"
)

# Rate Limiter 설정
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=Config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key", "Authorization", "X-No-Cache"],
    expose_headers=["X-Total-Count"],
    max_age=3600,
)

# HTTP 미들웨어 (요청/응답 매 요청 로깅은 제거, 에러 시에만 로깅)
@app.middleware("http")
async def http_middleware(request: Request, call_next):
    start_time = time.time()
    client_host = request.client.host if request.client else "unknown"

    # X-No-Cache 헤더가 있으면 백엔드 캐시 클리어 (프론트엔드 새로고침 용도)
    if request.headers.get("X-No-Cache") == "true":
        from app.utils.cache import get_cache
        cache = get_cache()
        cache.clear()
        logger.info("Cache cleared via X-No-Cache header")

    try:
        response = await call_next(request)
        return response
    except Exception as e:
        process_time = time.time() - start_time
        log_error(
            logger,
            error=e,
            context={
                "method": request.method,
                "path": str(request.url.path),
                "client_host": client_host,
                "duration_ms": process_time,
            },
        )
        raise

# Initialize database and scheduler on startup
@app.on_event("startup")
async def startup_event():
    # 저장된 API 키 로드 (api-keys.json → os.environ)
    from app.routers.settings import load_api_keys_to_env
    load_api_keys_to_env()

    logger.info(message="initializing_database", phase="app_startup")
    init_db()
    logger.info(message="database_initialized", phase="app_startup", status="success")

    # stocks.json → DB 자동 동기화
    logger.info(message="syncing_stocks", phase="app_startup")
    try:
        synced_count = stocks_manager.sync_stocks_to_db()
        logger.info(message="stocks_synced", phase="app_startup", count=synced_count)
    except Exception as e:
        log_error(logger, error=e, context={"phase": "stocks_sync_failed"})

    # 스케줄러 시작
    logger.info(message="starting_scheduler", phase="app_startup")
    scheduler = get_scheduler()
    scheduler.start()

# Graceful shutdown on application shutdown
@app.on_event("shutdown")
async def shutdown_event():
    scheduler = get_scheduler()
    scheduler.stop()

# Include routers
app.include_router(etfs.router, prefix="/api/etfs", tags=["ETFs"])
app.include_router(data.router, prefix="/api/data", tags=["Data Collection"])
app.include_router(news.router, prefix="/api/news", tags=["News"])
app.include_router(settings.router, prefix="/api/settings", tags=["Settings"])

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "message": "ETF Report API is running"}

@app.get("/")
async def root():
    return {
        "message": "ETF Weekly Report API",
        "docs": "/docs",
        "health": "/api/health"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
