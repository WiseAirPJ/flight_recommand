from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query

from app.models.flight_requests import (
    CheapestDateRequest,
    FlightDurationSearchRequest,
    FlightSearchRequest,
    OneWayFlightSearchRequest,
)
from app.services.amadeus_service import AmadeusService
from app.services.cache_service import CacheService
from app.utils.cache_keys import (
    airport_info_key,
    cheapest_dates_key,
    duration_search_key,
    flight_search_key,
    popular_routes_key,
)
from app.utils.decorators import cached_response, enhance_response, handle_exceptions
from app.utils.response_enhancers import (
    enhance_airport_info_response,
    enhance_cheapest_dates_response,
    enhance_duration_search_response,
    enhance_flight_search_response,
    get_popular_routes_data,
)
from app.utils.validators import validate_iata_code

router = APIRouter(prefix="/flights", tags=["flights"])


def get_amadeus_service() -> AmadeusService:
    return AmadeusService()


def get_cache_service() -> CacheService:
    return CacheService()


@router.post("/search")
@handle_exceptions("항공편 검색 중 오류가 발생했습니다")
@cached_response(flight_search_key, ttl_seconds=900)
@enhance_response(enhance_flight_search_response)
async def search_flights(
    request: FlightSearchRequest,
    amadeus_service: AmadeusService = Depends(get_amadeus_service),
    cache_service: CacheService = Depends(get_cache_service),
) -> Dict[str, Any]:
    result = await amadeus_service.search_flight_offers(
        origin=request.origin,
        destination=request.destination,
        departure_date=request.departure_date,
        return_date=request.return_date,
        adults=request.adults,
        currency=request.currency,
    )

    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["message"])

    return {
        "success": True,
        "message": "항공편 검색 완료",
        "data": result["data"],
        "meta": result.get("meta", {}),
        "dictionaries": result.get("dictionaries", {}),
    }


@router.post("/search-oneway")
@handle_exceptions("편도 항공편 검색 중 오류가 발생했습니다")
@cached_response(flight_search_key, ttl_seconds=900)
@enhance_response(enhance_flight_search_response)
async def search_oneway_flights(
    request: OneWayFlightSearchRequest,
    amadeus_service: AmadeusService = Depends(get_amadeus_service),
    cache_service: CacheService = Depends(get_cache_service),
) -> Dict[str, Any]:
    """
    편도 항공편 검색

    단순하고 명확한 편도 항공편 검색을 위한 전용 API입니다.
    왕복 여행과 달리 귀국 날짜 없이 편도만 검색합니다.
    """
    result = await amadeus_service.search_flight_offers(
        origin=request.origin,
        destination=request.destination,
        departure_date=request.departure_date,
        return_date=None,  # 편도이므로 없음
        adults=request.adults,
        currency=request.currency,
    )

    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["message"])

    return {
        "success": True,
        "message": "편도 항공편 검색 완료",
        "data": result["data"],
        "meta": result.get("meta", {}),
        "dictionaries": result.get("dictionaries", {}),
        "trip_type": "one-way",
    }


@router.post("/search-by-duration")
@handle_exceptions("기간별 항공편 검색 중 오류가 발생했습니다")
@cached_response(duration_search_key, ttl_seconds=1800)
@enhance_response(enhance_duration_search_response)
async def search_flights_by_duration(
    request: FlightDurationSearchRequest,
    amadeus_service: AmadeusService = Depends(get_amadeus_service),
    cache_service: CacheService = Depends(get_cache_service),
) -> Dict[str, Any]:
    from datetime import datetime, timedelta

    departure = datetime.strptime(request.departure_date, "%Y-%m-%d").date()
    return_date = departure + timedelta(days=request.duration_days - 1)

    result = await amadeus_service.search_flight_offers(
        origin=request.origin,
        destination=request.destination,
        departure_date=request.departure_date,
        return_date=return_date.strftime("%Y-%m-%d"),
        adults=request.adults,
        currency=request.currency,
    )

    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["message"])

    return {
        "success": True,
        "message": f"{request.duration_days}일 여행 항공편 검색 완료",
        "data": result["data"],
        "meta": result.get("meta", {}),
        "dictionaries": result.get("dictionaries", {}),
    }


@router.post("/cheapest-dates")
@handle_exceptions("최저가 날짜 검색 중 오류가 발생했습니다")
@cached_response(cheapest_dates_key, ttl_seconds=3600)
@enhance_response(enhance_cheapest_dates_response)
async def search_cheapest_dates(
    request: CheapestDateRequest,
    amadeus_service: AmadeusService = Depends(get_amadeus_service),
    cache_service: CacheService = Depends(get_cache_service),
) -> Dict[str, Any]:
    result = await amadeus_service.search_cheapest_dates(
        origin=request.origin,
        destination=request.destination,
        departure_date=request.departure_date,
        duration=request.duration,
        one_way=(request.trip_type == "one-way"),
    )

    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["message"])

    return {
        "success": True,
        "message": "최저가 날짜 검색 완료",
        "data": result["data"],
        "meta": result.get("meta", {}),
    }


@router.get("/airport/{iata_code}")
@handle_exceptions("공항 정보 조회 중 오류가 발생했습니다")
@cached_response(airport_info_key, ttl_seconds=86400)
@enhance_response(enhance_airport_info_response)
async def get_airport_info(
    iata_code: str,
    amadeus_service: AmadeusService = Depends(get_amadeus_service),
    cache_service: CacheService = Depends(get_cache_service),
) -> Dict[str, Any]:
    validated_code = validate_iata_code(iata_code)

    result = await amadeus_service.get_airport_info(validated_code)

    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["message"])

    return {"success": True, "message": "공항 정보 조회 완료", "data": result["data"]}


@router.get("/popular-routes")
@handle_exceptions("인기 노선 조회 중 오류가 발생했습니다")
@cached_response(popular_routes_key, ttl_seconds=7200)  # 2시간으로 단축
async def get_popular_routes(
    origin: str = Query("ICN", description="출발지 IATA 코드"),
    limit: int = Query(10, description="결과 개수", ge=1, le=50),
    cache_service: CacheService = Depends(get_cache_service),
) -> Dict[str, Any]:
    result_data = get_popular_routes_data(origin, limit)

    return {
        "success": True,
        "message": f"{origin} 출발 인기 노선 조회 완료",
        "data": result_data,
    }


@router.get("/health")
async def flights_health_check(
    amadeus_service: AmadeusService = Depends(get_amadeus_service),
) -> Dict[str, Any]:
    return {
        "service": "flights",
        "status": "healthy",
        "amadeus_active": amadeus_service.is_active,
        "available_endpoints": [
            "search",
            "search-oneway",
            "search-by-duration",
            "cheapest-dates",
            "airport/{iata_code}",
            "popular-routes",
        ],
        "timestamp": datetime.now().isoformat(),
    }
