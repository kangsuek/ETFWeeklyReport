"""
구조화된 로깅 설정 유틸리티
JSON 형식으로 로그를 출력하여 로그 분석 및 모니터링 도구와 연동 가능
"""

import structlog
import logging
import sys
from typing import Any, Dict


def setup_structured_logging(
    log_level: str = "INFO",
    json_output: bool = True,
    include_timestamp: bool = True,
) -> None:
    """
    구조화된 로깅 설정
    
    Args:
        log_level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_output: JSON 형식으로 출력할지 여부
        include_timestamp: 타임스탬프 포함 여부
    """
    # 프로세서 체인 구성
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        # PositionalArgumentsFormatter 제거 - 키워드 인자와 충돌 방지
        # structlog.stdlib.PositionalArgumentsFormatter(),
    ]
    
    # 타임스탬프 추가
    if include_timestamp:
        processors.append(structlog.processors.TimeStamper(fmt="iso"))
    
    # 스택 정보 및 예외 정보 추가
    processors.extend([
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ])
    
    # 출력 형식 결정
    if json_output:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(
            structlog.dev.ConsoleRenderer(colors=True)
        )
    
    # structlog 설정
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # 표준 로깅 설정
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )


def get_logger(name: str = None) -> structlog.BoundLogger:
    """
    구조화된 로거 가져오기
    
    Args:
        name: 로거 이름 (기본값: 호출 모듈 이름)
    
    Returns:
        structlog.BoundLogger 인스턴스
    """
    return structlog.get_logger(name)


# 로깅 헬퍼 함수들
def log_request(
    logger: structlog.BoundLogger,
    method: str,
    path: str,
    client_host: str = None,
    **kwargs: Any
) -> None:
    """HTTP 요청 로깅"""
    logger.info(
        message="http_request",
        method=method,
        path=path,
        client_host=client_host,
        **kwargs
    )


def log_response(
    logger: structlog.BoundLogger,
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    **kwargs: Any
) -> None:
    """HTTP 응답 로깅"""
    log_level = "info" if status_code < 400 else "warning" if status_code < 500 else "error"
    getattr(logger, log_level)(
        message="http_response",
        method=method,
        path=path,
        status_code=status_code,
        duration_ms=round(duration_ms * 1000, 2),
        **kwargs
    )


def log_error(
    logger: structlog.BoundLogger,
    error: Exception,
    context: Dict[str, Any] = None,
    **kwargs: Any
) -> None:
    """에러 로깅"""
    logger.error(
        message="error_occurred",
        error_type=type(error).__name__,
        error_message=str(error),
        context=context or {},
        exc_info=True,
        **kwargs
    )


def log_performance(
    logger: structlog.BoundLogger,
    operation: str,
    duration_ms: float,
    **kwargs: Any
) -> None:
    """성능 메트릭 로깅"""
    logger.info(
        message="performance_metric",
        operation=operation,
        duration_ms=round(duration_ms, 2),
        **kwargs
    )
