import logging
import sys
from typing import Any, Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.api.v1.cache import router as cache_router
from app.api.v1.flights import router as flights_router
from app.api.v1.llm import router as llm_router
from app.api.v1.prediction import router as prediction_router
from app.api.v1.regions import router as regions_router
from app.api.v1.utils import router as utils_router
from app.config.settings import settings

# 로깅 설정
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# FastAPI 앱 생성
app = FastAPI(
    title=settings.APP_NAME,
    description="""
    ## 지능형 일본 항공권 분석기 API

    일본 여행 항공권의 **가격**뿐만 아니라 **가치**를 분석하여 최적의 선택을 도와주는 API입니다.

    ### 🎯 Phase 1 MVP 주요 기능

    #### 📍 지역 관리
    - `GET /api/v1/regions` - 일본 지역 목록
    - `GET /api/v1/regions/lowest-prices` - **지도 메인 화면용 핵심 API**
    - `GET /api/v1/regions/{region_id}/airports` - 지역별 공항 목록

    #### ✈️ 항공편 검색
    - `POST /api/v1/flights/search` - 기본 항공편 검색 (왕복/편도 모두 지원)
    - `POST /api/v1/flights/search-oneway` - **편도 항공편 전용 검색**
    - `POST /api/v1/flights/search-by-duration` - **기간별 검색 (3박4일, 4박5일 등)**
    - `POST /api/v1/flights/cheapest-dates` - 최저가 날짜 검색 (편도/왕복 모두 지원)

    #### 🛠️ 유틸리티
    - `GET /api/v1/utils/date-info` - 날짜/공휴일/시즌 정보
    - `GET /api/v1/utils/airports/search` - 공항 검색 (자동완성)
    - `GET /api/v1/utils/exchange-rate` - 환율 정보

    #### 💾 캐시 관리
    - `GET /api/v1/cache/status` - 캐시 상태 확인
    - `POST /api/v1/cache/refresh` - 캐시 갱신 (관리자용)

    ### 🚀 빠른 시작

    1. **지역별 최저가 조회**: `GET /api/v1/regions/lowest-prices`
    2. **4일 여행 검색**: `POST /api/v1/flights/search-by-duration`
    3. **날짜 정보 확인**: `GET /api/v1/utils/date-info?date=2025-05-03`

    ### 📊 데이터 소스
    - **항공편 데이터**: Amadeus for Developers API
    - **캐싱 시스템**: Redis (메모리 캐시 대체 지원)
    - **배경 작업**: Celery + Redis

    ### 🔧 기술 스택
    - **Backend**: Python 3.12 + FastAPI + Pydantic
    - **외부 API**: Amadeus API, OpenAI API (Phase 2)
    - **캐시**: Redis
    - **작업 큐**: Celery
    """,
    version=settings.VERSION,
    debug=settings.DEBUG,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

#  API 라우터 등록

app.include_router(regions_router, prefix="/api/v1")  # 지역 관리 (메인 화면용)
app.include_router(flights_router, prefix="/api/v1")  # 항공편 검색
app.include_router(utils_router, prefix="/api/v1")  # 유틸리티
app.include_router(cache_router, prefix="/api/v1")  # 캐시 관리
app.include_router(llm_router, prefix="/api/v1")  # LLM 분석 및 환율 서비스
app.include_router(
    prediction_router, prefix="/api/v1/prediction", tags=["Price Prediction"]
)  # 가격 예측

# 월별 분석 기능은 regions 라우터

logger.info("모든 API 라우터 등록 완료")


# 기본 엔드포인트


@app.get("/", include_in_schema=False)
async def root_redirect():
    """루트 경로에서 API 문서로 리다이렉트"""
    return RedirectResponse(url="/docs")


@app.get("/api", include_in_schema=False)
async def api_redirect():
    """API 경로에서 문서로 리다이렉트"""
    return RedirectResponse(url="/docs")


@app.get("/api/v1", tags=["System"])
async def api_v1_info() -> Dict[str, Any]:
    """API v1 정보"""
    return {
        "message": f"{settings.APP_NAME} API v1",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "python_version": (
            f"{sys.version_info.major}.{sys.version_info.minor}."
            f"{sys.version_info.micro}"
        ),
        "phase": "Phase 1 MVP",
        "status": "완성",
        "available_routes": {
            "regions": "/api/v1/regions",
            "flights": "/api/v1/flights",
            "utils": "/api/v1/utils",
            "cache": "/api/v1/cache",
            "llm": "/api/v1/llm",
            "monthly_analysis": "/api/v1/regions/monthly-analysis",
        },
        "core_features": [
            "지역별 최저가 조회",
            "기간별 항공편 검색",
            "날짜/시즌 정보",
            "캐시 시스템",
            "LLM 기반 항공편 분석",
            "실시간 가격 알림",
            "환율 변환 서비스",
        ],
    }


@app.get("/health", tags=["System"])
async def health_check() -> Dict[str, Any]:
    """전체 시스템 헬스 체크"""
    from app.services.amadeus_service import AmadeusService
    from app.services.cache_service import CacheService
    from app.services.region_service import RegionService

    try:
        # 각 서비스 상태 확인
        amadeus_service = AmadeusService()
        cache_service = CacheService()
        region_service = RegionService()

        # 서비스별 헬스 체크
        health_status = {
            "status": "healthy",
            "timestamp": "2025-07-04T10:00:00Z",
            "environment": settings.ENVIRONMENT,
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}",
            "services": {
                "amadeus_api": {
                    "status": "healthy" if amadeus_service.is_active else "degraded",
                    "active": amadeus_service.is_active,
                },
                "cache_system": {
                    "status": "healthy" if cache_service.is_connected else "degraded",
                    "connected": cache_service.is_connected,
                    "type": "redis" if cache_service.is_connected else "memory",
                },
                "region_data": {
                    "status": "healthy",
                    "loaded_regions": len(region_service.regions_data),
                },
            },
            "api_endpoints": {
                "total_routes": len(app.routes),
                "core_apis": [
                    "/api/v1/regions/lowest-prices",
                    "/api/v1/flights/search-oneway",
                    "/api/v1/flights/search-by-duration",
                    "/api/v1/utils/date-info",
                    "/api/v1/cache/status",
                ],
            },
        }

        # 전체 상태 결정
        service_statuses = [s["status"] for s in health_status["services"].values()]
        if "unhealthy" in service_statuses:
            health_status["status"] = "unhealthy"
        elif "degraded" in service_statuses:
            health_status["status"] = "degraded"

        return health_status

    except Exception as e:
        logger.error(f"헬스 체크 실패: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": "2025-07-04T10:00:00Z",
        }


@app.get("/api/v1/status", tags=["System"])
async def api_status() -> Dict[str, Any]:
    """API 상태 및 통계"""
    return {
        "api_version": "v1",
        "phase": "Phase 1 MVP Complete",
        "completion_status": {
            "regions_api": "✅ 완성",
            "flights_api": "✅ 완성",
            "utils_api": "✅ 완성",
            "cache_api": "✅ 완성",
            "monthly_api": "✅ 완성 (호환성)",
        },
        "next_phase": "Phase 2 - LLM 분석 기능",
        "ready_for_frontend": True,
        "documentation": {
            "swagger_ui": "/docs",
            "redoc": "/redoc",
            "openapi_json": "/openapi.json",
        },
    }


#  앱 시작 이벤트


@app.on_event("startup")
async def startup_event():
    """애플리케이션 시작 시 실행"""
    logger.info(f"{settings.APP_NAME} v{settings.VERSION} 시작")
    logger.info(f"환경: {settings.ENVIRONMENT}")
    logger.info(f"디버그 모드: {settings.DEBUG}")
    logger.info("Phase 1 MVP 시스템 준비 완료")

    # 기본 서비스 초기화 확인
    try:
        from app.services.region_service import RegionService

        region_service = RegionService()
        logger.info(f"지역 데이터 로드 완료: {len(region_service.regions_data)}개 지역")

        from app.services.cache_service import CacheService

        cache_service = CacheService()
        logger.info(
            f"캐시 시스템 초기화: {'Redis' if cache_service.is_connected else '메모리 캐시'}"
        )

    except Exception as e:
        logger.warning(f"서비스 초기화 중 일부 오류: {str(e)}")


@app.on_event("shutdown")
async def shutdown_event():
    """애플리케이션 종료 시 실행"""
    logger.info(f"{settings.APP_NAME} 종료")


#  예외 처리


@app.exception_handler(404)
async def not_found_handler(request, exc):
    """404 에러 핸들러"""
    return {
        "success": False,
        "error": {
            "code": "NOT_FOUND",
            "message": "요청한 리소스를 찾을 수 없습니다.",
            "details": f"경로 '{request.url.path}'는 존재하지 않습니다.",
        },
        "suggestions": [
            "API 문서를 확인해보세요: /docs",
            "사용 가능한 엔드포인트: /api/v1",
        ],
        "timestamp": "2025-07-04T10:00:00Z",
    }


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """500 에러 핸들러"""
    logger.error(f"내부 서버 오류: {str(exc)}")
    return {
        "success": False,
        "error": {
            "code": "INTERNAL_SERVER_ERROR",
            "message": "서버 내부 오류가 발생했습니다.",
            "details": "일시적인 오류일 수 있습니다. 잠시 후 다시 시도해주세요.",
        },
        "timestamp": "2025-07-04T10:00:00Z",
    }


# 개발 환경에서만 추가 정보 표시
if settings.DEBUG:

    @app.get("/debug/routes", tags=["Debug"], include_in_schema=False)
    async def debug_routes():
        """등록된 모든 라우트 목록 (개발용)"""
        routes = []
        for route in app.routes:
            if hasattr(route, "methods") and hasattr(route, "path"):
                routes.append(
                    {
                        "path": route.path,
                        "methods": list(route.methods),
                        "name": getattr(route, "name", "Unknown"),
                    }
                )

        return {"total_routes": len(routes), "routes": routes}


if __name__ == "__main__":
    import uvicorn

    logger.info("개발 서버 시작")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
