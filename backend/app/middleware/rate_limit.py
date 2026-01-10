"""
Rate Limiting 미들웨어

slowapi를 사용한 요청 빈도 제한:
- 클라이언트 IP별 요청 제한
- 엔드포인트별 차등 제한
- 429 Too Many Requests 응답
- Rate Limit 헤더 자동 추가
"""
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)

# Limiter 인스턴스 생성
# key_func: 클라이언트 식별 방법 (IP 주소 기반)
limiter = Limiter(key_func=get_remote_address)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """
    Rate Limit 초과 시 에러 핸들러

    Args:
        request: FastAPI Request 객체
        exc: RateLimitExceeded 예외

    Returns:
        JSONResponse: 429 상태 코드와 에러 메시지
    """
    # 클라이언트 IP 로깅
    client_ip = get_remote_address(request)
    logger.warning(f"Rate limit exceeded for IP: {client_ip} on {request.url.path}")

    return JSONResponse(
        status_code=429,
        content={
            "error": "Too Many Requests",
            "detail": "요청 횟수 제한을 초과했습니다. 잠시 후 다시 시도해주세요.",
            "retry_after": exc.detail if hasattr(exc, 'detail') else "60 seconds"
        },
        headers={
            "Retry-After": "60"  # 60초 후 재시도 권장
        }
    )


# Rate Limit 설정값
class RateLimitConfig:
    """Rate Limit 설정 상수"""

    # 기본 제한 (대부분의 엔드포인트)
    DEFAULT = "100/minute"  # 분당 100 요청

    # 데이터 수집 엔드포인트 (외부 API 호출)
    DATA_COLLECTION = "10/minute"  # 분당 10 요청

    # 검색 엔드포인트
    SEARCH = "30/minute"  # 분당 30 요청

    # 읽기 전용 엔드포인트 (더 관대함)
    READ_ONLY = "200/minute"  # 분당 200 요청

    # 위험한 작업 (삭제, 초기화)
    DANGEROUS = "5/minute"  # 분당 5 요청
