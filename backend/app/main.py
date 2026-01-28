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
    log_request,
    log_response,
    log_error,
)
from dotenv import load_dotenv
import os
import time

# Load environment variables
load_dotenv()

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
    allow_headers=["Content-Type", "X-API-Key", "Authorization"],
    expose_headers=["X-Total-Count"],
    max_age=3600,
)

# 요청 로깅 미들웨어 (구조화된 로깅 사용)
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    client_host = request.client.host if request.client else "unknown"
    
    # 요청 로깅
    log_request(
        logger,
        method=request.method,
        path=str(request.url.path),
        client_host=client_host,
        query_params=str(request.url.query) if request.url.query else None,
    )
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # 응답 로깅
        log_response(
            logger,
            method=request.method,
            path=str(request.url.path),
            status_code=response.status_code,
            duration_ms=process_time,
        )
        
        return response
    except Exception as e:
        process_time = time.time() - start_time
        
        # 에러 로깅
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
    logger.info(message="scheduler_started", phase="app_startup", status="success")

# Graceful shutdown on application shutdown
@app.on_event("shutdown")
async def shutdown_event():
    logger.info(message="stopping_scheduler", phase="app_shutdown")
    scheduler = get_scheduler()
    scheduler.stop()
    logger.info(message="scheduler_stopped", phase="app_shutdown", status="success")

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
