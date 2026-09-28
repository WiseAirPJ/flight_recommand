from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class CacheKey(BaseModel):
    """캐시 키 정보 모델"""

    key: str = Field(..., description="캐시 키")
    ttl: int = Field(..., description="TTL (초, -1은 영구)")
    type: str = Field(..., description="데이터 타입")
    size_bytes: Optional[int] = Field(None, description="크기 (바이트)")


class CacheStatus(BaseModel):
    """캐시 상태 모델"""

    cache_type: str = Field(..., description="캐시 타입")
    status: str = Field(..., description="상태")
    total_keys: int = Field(..., description="전체 키 수")
    active_keys: int = Field(..., description="활성 키 수")
    expired_keys: int = Field(..., description="만료된 키 수")
    memory_usage: Dict[str, Any] = Field(..., description="메모리 사용량")
    last_updated: str = Field(..., description="마지막 업데이트")

    model_config = {
        "json_schema_extra": {
            "example": {
                "cache_type": "redis",
                "status": "healthy",
                "total_keys": 150,
                "active_keys": 142,
                "expired_keys": 8,
                "memory_usage": {
                    "used_memory_human": "2.5MB",
                    "mem_fragmentation_ratio": 1.1,
                },
                "last_updated": "2025-07-04T10:00:00Z",
            }
        }
    }


class CacheStatistics(BaseModel):
    """캐시 통계 모델"""

    cache_hit_rate: float = Field(..., description="캐시 히트율")
    total_requests: int = Field(..., description="총 요청 수")
    cache_hits: int = Field(..., description="캐시 히트 수")
    cache_misses: int = Field(..., description="캐시 미스 수")
    avg_response_time: Optional[float] = Field(None, description="평균 응답 시간 (ms)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "cache_hit_rate": 85.6,
                "total_requests": 1250,
                "cache_hits": 1070,
                "cache_misses": 180,
                "avg_response_time": 45.2,
            }
        }
    }
