from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.services.cache_admin_service import CacheAdminService
from app.services.cache_refresh_service import CacheRefreshService

router = APIRouter(prefix="/cache", tags=["cache"])


# Request/Response 모델


class CacheRefreshRequest(BaseModel):
    """캐시 갱신 요청 모델"""

    regions: Optional[List[str]] = Field(
        None, description="호환성용 지역 목록. 현재 수집은 모든 지역을 대상으로 수행"
    )
    force_update: bool = Field(False, description="강제 갱신 여부")
    origin: str = Field("ICN", description="출발지 공항 코드")


def get_cache_service() -> CacheAdminService:
    """캐시 서비스 인스턴스 반환"""
    return CacheAdminService()


def get_cache_refresh_service() -> CacheRefreshService:
    return CacheRefreshService()


# API 엔드포인트


@router.get("/status")
def get_cache_status(
    cache_service: CacheAdminService = Depends(get_cache_service),
) -> Dict[str, Any]:
    """
    캐시 상태 및 마지막 업데이트 시간 확인

    **주요 용도**:
    - 앱 초기화 시 캐시 데이터 유효성 확인
    - 관리자 대시보드에서 시스템 상태 모니터링
    - 개발/디버깅 시 캐시 동작 확인

    **응답 정보**:
    - 전체 캐시 키 현황
    - 지역별 캐시 데이터 보유 현황
    - 마지막 업데이트 시간
    - 다음 예정 업데이트 시간
    """
    try:
        status_info = cache_service.get_cache_status()

        return {"success": True, "message": "캐시 상태 조회 완료", "data": status_info}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"캐시 상태 조회 중 오류가 발생했습니다: {str(e)}"
        )


@router.post("/refresh")
def refresh_cache(
    request: CacheRefreshRequest,
    cache_service: CacheRefreshService = Depends(get_cache_refresh_service),
) -> Dict[str, Any]:
    """
    수동 캐시 갱신 (관리자용)

    **사용 시나리오**:
    - 데이터 오류 발견 시 즉시 갱신
    - 새로운 항공편 스케줄 반영
    - 시스템 유지보수 후 캐시 리프레시

    **갱신 옵션**:
    - `regions`: 호환성용 입력이며 현재는 모든 지역 수집
    - `force_update`: 유효한 캐시도 강제 갱신
    - `origin`: 출발지 공항 (기본값: ICN)

    **주의사항**:
    - 전체 갱신시 5-10분 소요될 수 있음
    - API 사용량 급증할 수 있으므로 신중히 사용
    """
    try:
        refresh_result = cache_service.refresh_cache(
            regions=request.regions,
            force_update=request.force_update,
            origin=request.origin,
        )

        if refresh_result["success"]:
            return {
                "success": True,
                "message": "캐시 갱신이 시작되었습니다",
                "data": refresh_result["data"],
            }
        else:
            raise HTTPException(
                status_code=500, detail=f"캐시 갱신 실패: {refresh_result['message']}"
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"캐시 갱신 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/statistics")
def get_cache_statistics(
    cache_service: CacheAdminService = Depends(get_cache_service),
) -> Dict[str, Any]:
    """
    캐시 사용 통계 조회

    **제공 정보**:
    - 캐시 히트율 (성능 지표)
    - 총 요청 대비 캐시 활용률
    - 평균 응답 시간
    - 시간대별 사용 패턴
    """
    try:
        stats = cache_service.get_cache_statistics()

        return {"success": True, "message": "캐시 통계 조회 완료", "data": stats}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"캐시 통계 조회 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/keys")
def get_cache_keys(
    pattern: Optional[str] = Query(
        None, description="키 패턴 필터 (예: 'monthly_cheapest:*')"
    ),
    limit: int = Query(100, description="결과 개수 제한", ge=1, le=1000),
    cache_service: CacheAdminService = Depends(get_cache_service),
) -> Dict[str, Any]:
    """
    캐시 키 목록 조회 (개발/디버깅용)

    **사용 예시**:
    - `GET /cache/keys` → 모든 캐시 키 (최대 100개)
    - `GET /cache/keys?pattern=monthly_cheapest:*` → 월별 데이터 캐시만
    - `GET /cache/keys?pattern=*:2025:*&limit=50` → 2025년 데이터만
    """
    try:
        keys_info = cache_service.get_cache_keys(pattern=pattern, limit=limit)

        return {
            "success": True,
            "message": "캐시 키 목록 조회 완료",
            "data": {
                "pattern": pattern or "*",
                "total_found": len(keys_info["keys"]),
                "keys": keys_info["keys"],
                "sample_data": keys_info.get("sample_data", {}),
            },
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"캐시 키 조회 중 오류가 발생했습니다: {str(e)}"
        )


@router.delete("/keys/{key}")
def delete_cache_key(
    key: str, cache_service: CacheAdminService = Depends(get_cache_service)
) -> Dict[str, Any]:
    """
    특정 캐시 키 삭제 (관리자용)

    **사용 시나리오**:
    - 잘못된 데이터 캐시 제거
    - 테스트 데이터 정리
    - 특정 날짜/지역 데이터 리셋
    """
    try:
        deleted = cache_service.delete_cache_key(key)

        if deleted:
            return {
                "success": True,
                "message": f"캐시 키 '{key}' 삭제 완료",
                "data": {"deleted_key": key},
            }
        else:
            raise HTTPException(
                status_code=404, detail=f"캐시 키 '{key}'를 찾을 수 없습니다"
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"캐시 키 삭제 중 오류가 발생했습니다: {str(e)}"
        )


@router.post("/cleanup")
def cleanup_expired_cache(
    cache_service: CacheAdminService = Depends(get_cache_service),
) -> Dict[str, Any]:
    """
    만료된 캐시 데이터 정리

    **동작**:
    - 메모리 캐시의 만료된 저장 항목 제거
    - Redis는 자체 TTL로 자동 만료되므로 별도 삭제하지 않음
    - 저장된 데이터의 expires_at 필드는 만료 기준으로 사용하지 않음
    """
    try:
        cleanup_result = cache_service.cleanup_expired_cache()

        return {
            "success": True,
            "message": "만료된 캐시 정리 완료",
            "data": cleanup_result,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"캐시 정리 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/memory")
def get_memory_usage(
    cache_service: CacheAdminService = Depends(get_cache_service),
) -> Dict[str, Any]:
    """
    Redis 메모리 사용량 조회

    **제공 정보**:
    - 총 메모리 사용량
    - 키별 메모리 사용량
    - 메모리 사용 상위 항목들
    - 메모리 최적화 권장사항
    """
    try:
        memory_info = cache_service.get_memory_usage()

        return {
            "success": True,
            "message": "메모리 사용량 조회 완료",
            "data": memory_info,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"메모리 사용량 조회 중 오류가 발생했습니다: {str(e)}",
        )


@router.get("/performance")
def get_cache_performance(
    hours: int = Query(24, description="조회 기간 (시간)", ge=1, le=168),
    cache_service: CacheAdminService = Depends(get_cache_service),
) -> Dict[str, Any]:
    """
    캐시 성능 지표 조회

    **성능 지표**:
    - 시간대별 히트율
    - 응답 시간 분포
    - 자주 사용되는 캐시 키
    - 성능 개선 권장사항
    """
    try:
        performance_data = cache_service.get_performance_metrics(hours=hours)

        return {
            "success": True,
            "message": f"최근 {hours}시간 성능 지표 조회 완료",
            "data": performance_data,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"성능 지표 조회 중 오류가 발생했습니다: {str(e)}"
        )


@router.post("/warmup")
def warmup_cache(
    regions: Optional[List[str]] = Query(None, description="워밍업할 지역 목록"),
    months_ahead: int = Query(3, description="미리 준비할 개월 수", ge=1, le=12),
    cache_service: CacheRefreshService = Depends(get_cache_refresh_service),
) -> Dict[str, Any]:
    """
    캐시 워밍업 (사전 데이터 로드)

    **용도**:
    - 시스템 시작 시 주요 데이터 미리 로드
    - 성수기 전 데이터 사전 준비
    - 사용자 경험 개선을 위한 예측 로딩

    **옵션**:
    - `regions`: 호환성용 입력이며 현재는 모든 지역 수집
    - `months_ahead`: 향후 몇 개월치 데이터 준비
    """
    try:
        warmup_result = cache_service.warmup_cache(
            regions=regions, months_ahead=months_ahead
        )

        if not warmup_result["success"]:
            raise HTTPException(status_code=503, detail=warmup_result)
        return {
            "success": True,
            "message": "캐시 워밍업이 시작되었습니다",
            "data": warmup_result,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"캐시 워밍업 중 오류가 발생했습니다: {str(e)}"
        )


# 헬스 체크


@router.get("/health")
def cache_health_check(
    cache_service: CacheAdminService = Depends(get_cache_service),
) -> Dict[str, Any]:
    """
    캐시 서비스 상태 확인

    **확인 항목**:
    - Redis 연결 상태
    - 기본 읽기/쓰기 동작
    - 메모리 사용률
    - 응답 시간
    """
    try:
        health_info = cache_service.health_check()

        return {
            "service": "cache",
            "status": "healthy" if health_info["redis_connected"] else "unhealthy",
            "redis_info": health_info,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        return {
            "service": "cache",
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }
