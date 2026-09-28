from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class BaseResponse(BaseModel):
    """기본 응답 모델"""

    success: bool = Field(..., description="성공 여부")
    message: str = Field(..., description="응답 메시지")
    timestamp: Optional[str] = Field(None, description="응답 시간")


class SuccessResponse(BaseResponse):
    """성공 응답 모델"""

    data: Dict[str, Any] = Field(..., description="응답 데이터")
    meta: Optional[Dict[str, Any]] = Field(None, description="메타 데이터")


class ErrorResponse(BaseResponse):
    """에러 응답 모델"""

    error: Dict[str, Any] = Field(..., description="에러 정보")

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": False,
                "message": "요청 처리 중 오류가 발생했습니다",
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "잘못된 날짜 형식입니다",
                    "details": "YYYY-MM-DD 형식으로 입력해주세요",
                },
                "timestamp": "2025-07-04T10:00:00Z",
            }
        }
    }


class PaginatedResponse(BaseResponse):
    """페이지네이션 응답 모델"""

    data: List[Any] = Field(..., description="데이터 목록")
    pagination: Dict[str, Any] = Field(..., description="페이지네이션 정보")

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "message": "조회 완료",
                "data": [],
                "pagination": {
                    "page": 1,
                    "per_page": 20,
                    "total": 150,
                    "total_pages": 8,
                },
            }
        }
    }
