"""
API 인증 미들웨어

API Key 기반 인증 시스템:
- X-API-Key 헤더를 검증
- 민감한 엔드포인트만 보호 (데이터 수정/삭제)
- 공개 엔드포인트는 인증 불필요
"""
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import APIKeyHeader
from typing import Optional
import logging

from app.config import Config

logger = logging.getLogger(__name__)

# API Key 헤더 정의
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class APIKeyAuth:
    """API Key 인증 클래스"""

    # 인증이 필요 없는 공개 엔드포인트 (읽기 전용)
    PUBLIC_ENDPOINTS = [
        "/",
        "/api/health",
        "/docs",
        "/redoc",
        "/openapi.json",
    ]

    # 인증이 필요 없는 공개 경로 패턴 (읽기 전용)
    PUBLIC_PATH_PATTERNS = [
        "/api/etfs",  # GET만 허용 (목록 조회)
        "/api/news",  # GET만 허용 (뉴스 조회)
    ]

    # 읽기 전용 메서드 (인증 불필요)
    READ_ONLY_METHODS = ["GET", "HEAD", "OPTIONS"]

    @classmethod
    def is_public_endpoint(cls, path: str, method: str) -> bool:
        """
        공개 엔드포인트 여부 확인

        Args:
            path: 요청 경로
            method: HTTP 메서드

        Returns:
            bool: 공개 엔드포인트면 True
        """
        # 정확히 일치하는 공개 엔드포인트
        if path in cls.PUBLIC_ENDPOINTS:
            return True

        # 읽기 전용 메서드는 대부분 공개
        if method in cls.READ_ONLY_METHODS:
            # /api/etfs, /api/news로 시작하는 GET 요청은 공개
            for pattern in cls.PUBLIC_PATH_PATTERNS:
                if path.startswith(pattern):
                    return True

        return False

    @classmethod
    def verify_api_key(cls, api_key: Optional[str]) -> bool:
        """
        API Key 검증

        Args:
            api_key: 클라이언트가 제공한 API Key

        Returns:
            bool: 유효한 API Key면 True
        """
        if not api_key:
            return False

        # 환경 변수에서 API Key 로드
        valid_api_key = Config.API_KEY

        if not valid_api_key:
            logger.error("API_KEY가 환경 변수에 설정되지 않았습니다. 보안을 위해 모든 요청을 거부합니다.")
            return False  # API Key 미설정 시 모든 요청 거부 (보안 강화)

        return api_key == valid_api_key


async def verify_api_key_dependency(api_key: Optional[str] = Depends(api_key_header)) -> str:
    """
    API Key 검증 의존성 함수

    Protected 엔드포인트에 Depends()로 추가하여 사용

    Args:
        api_key: X-API-Key 헤더 값

    Returns:
        str: 검증된 API Key

    Raises:
        HTTPException: 401 Unauthorized (API Key 없음 또는 잘못됨)

    Example:
        ```python
        @router.delete("/api/data/reset")
        async def reset_data(api_key: str = Depends(verify_api_key_dependency)):
            # 이 함수는 API Key가 검증된 경우에만 실행됨
            return {"status": "ok"}
        ```
    """
    logger.info(f"[인증] API Key 검증 시작 - 제공된 API Key: {'있음' if api_key else '없음'}")

    # 개발 모드: API_KEY가 설정되지 않은 경우 경고와 함께 허용
    if not Config.API_KEY:
        import os
        env = os.getenv("RENDER", "") or os.getenv("RAILWAY_ENVIRONMENT", "") or os.getenv("FLY_APP_NAME", "")
        if env:
            logger.error("[인증] 프로덕션 환경에서 API_KEY가 설정되지 않았습니다! 요청을 거부합니다.")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="서버 구성 오류: API_KEY가 설정되지 않았습니다. 관리자에게 문의하세요.",
            )
        logger.warning("[인증] 개발 모드: API_KEY 미설정, 모든 요청 허용. 프로덕션에서는 반드시 API_KEY를 설정하세요.")
        return "dev-mode"  # Placeholder API key for development

    if not api_key:
        logger.warning("[인증] API Key가 제공되지 않았습니다.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key가 필요합니다. X-API-Key 헤더를 포함해주세요.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if not APIKeyAuth.verify_api_key(api_key):
        logger.warning("[인증] 잘못된 API Key 시도")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="잘못된 API Key입니다.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    logger.info("[인증] API Key 검증 성공")
    return api_key
