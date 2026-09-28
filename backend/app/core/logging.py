"""로깅 설정 및 유틸리티"""

import json
import logging
import sys
from copy import copy
from datetime import datetime
from typing import Any, Dict

from app.core.config import settings


class JSONFormatter(logging.Formatter):
    """JSON 형식 로그 포매터 (운영 환경용)"""

    def format(self, record: logging.LogRecord) -> str:
        """
        로그 레코드를 JSON 형식으로 변환

        Args:
            record: 로그 레코드

        Returns:
            str: JSON 형식 로그 문자열
        """
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # 추가 컨텍스트 정보
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id

        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id

        # 예외 정보
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False)


class ColoredFormatter(logging.Formatter):
    """컬러 로그 포매터 (개발 환경용)"""

    # ANSI 컬러 코드
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        """
        로그 레코드를 컬러 형식으로 변환

        Args:
            record: 로그 레코드

        Returns:
            str: 컬러가 적용된 로그 문자열
        """
        record = copy(record)
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logging() -> None:
    """
    로깅 시스템 초기화

    - 개발 환경: 컬러 포맷 + 상세 정보
    - 운영 환경: JSON 포맷 + 구조화된 로그
    """
    # 로그 레벨 설정
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # 기존 핸들러 제거
    for handler in list(root_logger.handlers):
        if getattr(handler, "flight_app_handler", False):
            root_logger.removeHandler(handler)

    # 콘솔 핸들러
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.flight_app_handler = True

    # 포맷 설정 (환경에 따라 다름)
    if settings.is_production:
        # 운영 환경: JSON 포맷
        formatter = JSONFormatter()
    else:
        # 개발 환경: 컬러 포맷
        formatter = ColoredFormatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s "
            "[%(filename)s:%(lineno)d]",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 외부 라이브러리 로그 레벨 조정
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("passlib").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    모듈별 로거 획득

    Args:
        name: 로거 이름 (보통 __name__ 사용)

    Returns:
        logging.Logger: 로거 인스턴스

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("API 호출 성공", extra={"user_id": 123})
    """
    return logging.getLogger(name)


# 편의 함수들
def log_api_call(
    method: str, path: str, status_code: int, duration: float, **kwargs
) -> None:
    """
    API 호출 로깅

    Args:
        method: HTTP 메서드
        path: API 경로
        status_code: 응답 상태 코드
        duration: 처리 시간 (초)
        **kwargs: 추가 컨텍스트
    """
    logger = get_logger("api")
    logger.info(
        f"{method} {path} - {status_code} ({duration:.3f}s)",
        extra={
            "method": method,
            "path": path,
            "status_code": status_code,
            "duration": duration,
            **kwargs,
        },
    )


def log_db_query(query: str, duration: float, **kwargs) -> None:
    """
    데이터베이스 쿼리 로깅

    Args:
        query: SQL 쿼리
        duration: 실행 시간 (초)
        **kwargs: 추가 컨텍스트
    """
    logger = get_logger("database")
    logger.debug(
        f"Query executed in {duration:.3f}s",
        extra={"query": query, "duration": duration, **kwargs},
    )


def log_error(error: Exception, context: Dict[str, Any] = None) -> None:
    """
    에러 로깅

    Args:
        error: 발생한 예외
        context: 추가 컨텍스트 정보
    """
    logger = get_logger("error")
    logger.error(
        f"{type(error).__name__}: {str(error)}",
        exc_info=True,
        extra=context or {},
    )
