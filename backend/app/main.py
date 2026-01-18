from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.routers import etfs, reports, news, data, settings
from app.database import init_db
from app.services.scheduler import get_scheduler
from app.config import Config
from app.utils import stocks_manager
from app.middleware.rate_limit import limiter, rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import logging
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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

# 요청 로깅 미들웨어
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    logger.info(f"[요청] {request.method} {request.url.path} - 클라이언트: {request.client.host if request.client else 'unknown'}")
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        logger.info(f"[응답] {request.method} {request.url.path} - 상태: {response.status_code} - 소요시간: {process_time:.3f}초")
        return response
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(f"[에러] {request.method} {request.url.path} - 에러: {e} - 소요시간: {process_time:.3f}초", exc_info=True)
        raise

# Initialize database and scheduler on startup
@app.on_event("startup")
async def startup_event():
    logger.info("Initializing database...")
    init_db()
    logger.info("Database initialized successfully")

    # stocks.json → DB 자동 동기화
    logger.info("Synchronizing stocks.json to database...")
    try:
        synced_count = stocks_manager.sync_stocks_to_db()
        logger.info(f"Synchronized {synced_count} stocks to database")
    except Exception as e:
        logger.error(f"Failed to sync stocks to database: {e}", exc_info=True)

    # 스케줄러 시작
    logger.info("Starting scheduler...")
    scheduler = get_scheduler()
    scheduler.start()
    logger.info("Scheduler started successfully")

# Graceful shutdown on application shutdown
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down scheduler...")
    scheduler = get_scheduler()
    scheduler.stop()
    logger.info("Scheduler stopped successfully")

# Include routers
app.include_router(etfs.router, prefix="/api/etfs", tags=["ETFs"])
app.include_router(data.router, prefix="/api/data", tags=["Data Collection"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
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
