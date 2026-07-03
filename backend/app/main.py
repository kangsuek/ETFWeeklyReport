from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.routers import etfs, news, data, settings, alerts, scanner, simulation
from app.database import init_db, run_migrations, close_connection_pool
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
import logging
import os
import re
import time

# uvicorn access 로그에서 폴링 경로(collect-progress 등) 제외
class SuppressPollingAccessLog(logging.Filter):
    """OPTIONS/GET to collect-progress 등 반복 폴링 요청 로그를 출력하지 않음."""

    def filter(self, record: logging.LogRecord) -> bool:
        # uvicorn access: record.args = (client_addr, method, full_path, http_version, status_code)
        if getattr(record, "args", None) and len(record.args) >= 3:
            full_path = record.args[2]
            if "collect-progress" in str(full_path):
                return False
        return True


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

# uvicorn 접근 로그에서 collect-progress 폴링 요청 숨김 (앱 로드 시점에 필터 등록)
logging.getLogger("uvicorn.access").addFilter(SuppressPollingAccessLog())

logger = get_logger(__name__)

# 앱 시작/종료 수명주기 (구 @app.on_event startup/shutdown 대체)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- startup ---
    # 저장된 API 키 로드 (api-keys.json → os.environ)
    from app.routers.settings import load_api_keys_to_env
    load_api_keys_to_env()

    logger.info(message="initializing_database", phase="app_startup")
    init_db()
    run_migrations()
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

    yield

    # --- shutdown ---
    scheduler = get_scheduler()
    scheduler.stop()
    close_connection_pool()


app = FastAPI(
    title="ETF Weekly Report API",
    description="API for Korean ETF analysis and reporting",
    version="1.0.0",
    lifespan=lifespan,
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

    # X-No-Cache 헤더가 있으면 백엔드 캐시 무효화 (프론트엔드 새로고침 용도)
    # 전체 삭제 대신 요청 경로/쿼리의 티커(6자리 코드) 범위로 축소해
    # 한 클라이언트의 새로고침이 다른 캐시까지 날리지 않도록 한다
    if request.headers.get("X-No-Cache") == "true":
        from app.utils.cache import get_cache
        cache = get_cache()
        tickers = set(re.findall(r"\b\d{6}\b", f"{request.url.path}?{request.url.query}"))
        if tickers:
            for ticker in tickers:
                cache.invalidate_pattern(ticker)
            logger.info(f"Cache invalidated via X-No-Cache header: {sorted(tickers)}")
        else:
            # 티커가 없는 경로(목록·배치 요약 등)는 전체 삭제로 폴백
            cache.clear()
            logger.info("Cache cleared via X-No-Cache header (no ticker in path)")

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

# Include routers
app.include_router(etfs.router, prefix="/api/etfs", tags=["ETFs"])
app.include_router(data.router, prefix="/api/data", tags=["Data Collection"])
app.include_router(news.router, prefix="/api/news", tags=["News"])
app.include_router(settings.router, prefix="/api/settings", tags=["Settings"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["Alerts"])
app.include_router(scanner.router, prefix="/api/scanner", tags=["Scanner"])
app.include_router(simulation.router, prefix="/api/simulation", tags=["Simulation"])

@app.get("/api/health")
async def health_check():
    health = {"status": "healthy", "message": "ETF Report API is running"}
    # DB 연결 확인
    try:
        from app.database import get_db_connection, get_cursor
        with get_db_connection() as conn_or_cursor:
            cursor = get_cursor(conn_or_cursor)
            cursor.execute("SELECT 1")
            cursor.fetchone()
        health["database"] = "connected"
    except Exception as e:
        health["status"] = "degraded"
        health["database"] = f"error: {str(e)}"
        logger.error(f"Health check - DB connection failed: {e}")
    return health

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
