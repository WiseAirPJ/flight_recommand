"""커스텀 예외 및 에러 핸들러"""

from typing import Any, Dict, Optional

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.core.logging import log_error


class AppException(Exception):
    """애플리케이션 기본 예외 클래스"""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class NotFoundException(AppException):
    """리소스를 찾을 수 없음"""

    def __init__(self, message: str = "리소스를 찾을 수 없습니다", **kwargs):
        super().__init__(message, status_code=status.HTTP_404_NOT_FOUND, **kwargs)


class UnauthorizedException(AppException):
    """인증 실패"""

    def __init__(self, message: str = "인증에 실패했습니다", **kwargs):
        super().__init__(message, status_code=status.HTTP_401_UNAUTHORIZED, **kwargs)


class ForbiddenException(AppException):
    """권한 없음"""

    def __init__(self, message: str = "접근 권한이 없습니다", **kwargs):
        super().__init__(message, status_code=status.HTTP_403_FORBIDDEN, **kwargs)


class BadRequestException(AppException):
    """잘못된 요청"""

    def __init__(self, message: str = "잘못된 요청입니다", **kwargs):
        super().__init__(message, status_code=status.HTTP_400_BAD_REQUEST, **kwargs)


class ConflictException(AppException):
    """리소스 충돌 (예: 중복 이메일)"""

    def __init__(self, message: str = "이미 존재하는 리소스입니다", **kwargs):
        super().__init__(message, status_code=status.HTTP_409_CONFLICT, **kwargs)


class ValidationException(AppException):
    """데이터 유효성 검증 실패"""

    def __init__(self, message: str = "유효하지 않은 데이터입니다", **kwargs):
        super().__init__(
            message, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, **kwargs
        )


class ExternalAPIException(AppException):
    """외부 API 호출 실패"""

    def __init__(self, message: str = "외부 API 호출에 실패했습니다", **kwargs):
        super().__init__(message, status_code=status.HTTP_502_BAD_GATEWAY, **kwargs)


class DatabaseException(AppException):
    """데이터베이스 오류"""

    def __init__(self, message: str = "데이터베이스 오류가 발생했습니다", **kwargs):
        super().__init__(
            message, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, **kwargs
        )


# 전역 예외 핸들러
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """
    애플리케이션 커스텀 예외 핸들러

    Args:
        request: FastAPI 요청 객체
        exc: 발생한 예외

    Returns:
        JSONResponse: 에러 응답
    """
    log_error(exc, context={"path": request.url.path, "method": request.method})

    return JSONResponse(
        status_code=exc.status_code,
        headers=getattr(exc, "headers", None),
        content={
            "error": {
                "message": exc.message,
                "details": exc.details,
                "path": request.url.path,
            }
        },
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    Pydantic 유효성 검증 오류 핸들러

    Args:
        request: FastAPI 요청 객체
        exc: 유효성 검증 오류

    Returns:
        JSONResponse: 에러 응답
    """
    errors = []
    for error in exc.errors():
        errors.append(
            {
                "field": " -> ".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            }
        )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "message": "입력 데이터가 유효하지 않습니다",
                "details": {"validation_errors": errors},
                "path": request.url.path,
            }
        },
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    FastAPI HTTP 예외 핸들러

    Args:
        request: FastAPI 요청 객체
        exc: HTTP 예외

    Returns:
        JSONResponse: 에러 응답
    """
    return JSONResponse(
        status_code=exc.status_code,
        headers=getattr(exc, "headers", None),
        content={
            "error": {
                "message": exc.detail,
                "path": request.url.path,
            }
        },
    )


async def sqlalchemy_exception_handler(
    request: Request, exc: SQLAlchemyError
) -> JSONResponse:
    """
    SQLAlchemy 오류 핸들러

    Args:
        request: FastAPI 요청 객체
        exc: SQLAlchemy 오류

    Returns:
        JSONResponse: 에러 응답
    """
    log_error(exc, context={"path": request.url.path, "method": request.method})

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "message": "데이터베이스 오류가 발생했습니다",
                "path": request.url.path,
            }
        },
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    일반 예외 핸들러 (catch-all)

    Args:
        request: FastAPI 요청 객체
        exc: 예외

    Returns:
        JSONResponse: 에러 응답
    """
    log_error(exc, context={"path": request.url.path, "method": request.method})

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "message": "서버 오류가 발생했습니다",
                "path": request.url.path,
            }
        },
    )
