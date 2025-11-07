from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import etfs, reports, news
from app.database import init_db
from app.services.scheduler import get_scheduler
import logging

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

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database and scheduler on startup
@app.on_event("startup")
async def startup_event():
    logger.info("Initializing database...")
    init_db()
    logger.info("Database initialized successfully")
    
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
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
app.include_router(news.router, prefix="/api/news", tags=["News"])

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
