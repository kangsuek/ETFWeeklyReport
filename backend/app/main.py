from fastapi import FastAPI
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
