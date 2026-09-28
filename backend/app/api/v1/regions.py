"""Map and monthly search API. All fare metadata is retained for the UI."""

import asyncio
from datetime import date
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.models.flight_requests import MonthlySearchRequest
from app.services.monthly_search_service import MonthlySearchService
from app.services.region_service import RegionService

router = APIRouter(prefix="/regions", tags=["regions"])


@lru_cache
def get_region_service():
    return RegionService()


@lru_cache
def get_monthly_search_service():
    return MonthlySearchService()


@router.get("/")
async def get_regions(service=Depends(get_region_service)):
    return {"success": True, "data": await service.get_all_regions()}


@router.get("/departure-airports")
async def departure_airports():
    return {
        "success": True,
        "message": "검색 출발공항 목록입니다. 운항 여부는 검색 결과에서 확인하세요.",
        "data": [
            {"iata": code, "name": name}
            for code, name in [
                ("ICN", "인천"),
                ("GMP", "김포"),
                ("PUS", "부산·김해"),
                ("CJJ", "청주"),
                ("TAE", "대구"),
                ("CJU", "제주"),
                ("MWX", "무안"),
                ("YNY", "양양"),
            ]
        ],
    }


async def _get_monthly_result(request, search_service):
    result = await asyncio.to_thread(search_service.request, request)
    result.pop("enqueued", None)
    if not result["success"]:
        raise HTTPException(result.get("status_code", 502), result["message"])
    return result


@router.get("/lowest-prices")
async def get_regions_lowest_prices(
    origin: str = "ICN",
    adults: int = Query(1, ge=1, le=9),
    year: int | None = None,
    month: int | None = Query(None, ge=1, le=12),
    duration_days: int = Query(4, ge=2, le=30),
    currency: str = "KRW",
    non_stop: bool = False,
    search_service=Depends(get_monthly_search_service),
):
    today = date.today()
    target_month = month or today.month
    target_year = (
        year if year is not None else today.year + (target_month < today.month)
    )
    try:
        request = MonthlySearchRequest(
            year=target_year,
            month=target_month,
            origin=origin,
            adults=adults,
            duration_days=duration_days,
            currency=currency,
            non_stop=non_stop,
        )
    except ValidationError as exc:
        raise HTTPException(422, "검색 월·출발공항·통화를 확인하세요.") from exc
    result = await _get_monthly_result(request, search_service)
    data = result["data"]
    prices = {
        region_id: {
            **region["cheapest_option"],
            "region_id": region_id,
            "region_name": region["region_name"],
            "last_updated": region["cheapest_option"]["observed_at"],
        }
        for region_id, region in data["regions"].items()
    }
    return JSONResponse(
        status_code=result.get("status_code", 200),
        headers={"Retry-After": "5"} if result.get("status_code") == 202 else {},
        content={
            "success": True,
            "message": result["message"],
            "data": prices,
            "meta": {key: value for key, value in data.items() if key != "regions"},
            "last_updated": data["searched_at"],
        },
    )


@router.post("/monthly-analysis")
async def monthly_analysis(
    request: MonthlySearchRequest, search_service=Depends(get_monthly_search_service)
):
    result = await _get_monthly_result(request, search_service)
    return JSONResponse(
        status_code=result.get("status_code", 200),
        headers={"Retry-After": "5"} if result.get("status_code") == 202 else {},
        content=result,
    )


@router.get("/monthly-analysis")
async def get_monthly_analysis(
    year: int | None = None,
    month: int | None = Query(None, ge=1, le=12),
    origin: str = "ICN",
    adults: int = Query(1, ge=1, le=9),
    duration_days: int | None = Query(None, ge=2, le=30),
    duration: int | None = Query(None, ge=2, le=30, deprecated=True),
    currency: str = "KRW",
    non_stop: bool = False,
    search_service=Depends(get_monthly_search_service),
):
    today = date.today()
    target_month = month or today.month
    target_year = (
        year if year is not None else today.year + (target_month < today.month)
    )
    return await monthly_analysis_by_month(
        target_year,
        target_month,
        origin,
        adults,
        duration_days,
        duration,
        currency,
        non_stop,
        search_service,
    )


@router.get("/monthly-analysis/{year}/{month}")
async def monthly_analysis_by_month(
    year: int,
    month: int,
    origin: str = "ICN",
    adults: int = Query(1, ge=1, le=9),
    duration_days: int | None = Query(None, ge=2, le=30),
    duration: int | None = Query(None, ge=2, le=30, deprecated=True),
    currency: str = "KRW",
    non_stop: bool = False,
    search_service=Depends(get_monthly_search_service),
):
    if duration is not None and duration_days is not None and duration != duration_days:
        raise HTTPException(422, "여행 기간 조건이 서로 다릅니다.")
    try:
        request = MonthlySearchRequest(
            year=year,
            month=month,
            origin=origin,
            adults=adults,
            duration_days=duration_days or duration or 4,
            currency=currency,
            non_stop=non_stop,
        )
    except ValidationError as exc:
        raise HTTPException(422, "검색 조건을 확인하세요.") from exc
    result = await _get_monthly_result(request, search_service)
    return JSONResponse(
        status_code=result.get("status_code", 200),
        headers={"Retry-After": "5"} if result.get("status_code") == 202 else {},
        content=result,
    )


@router.get("/statistics")
async def region_statistics(service=Depends(get_region_service)):
    return {"success": True, "data": await service.get_regions_summary()}


@router.get("/health")
async def region_health(service=Depends(get_region_service)):
    return {
        "service": "regions",
        "status": "healthy",
        "loaded_regions": len(service.regions_data),
    }


@router.get("/{region_id}/airports")
async def get_region_airports(region_id: str, service=Depends(get_region_service)):
    airports = await service.get_region_airports(region_id)
    if not airports:
        raise HTTPException(404, "지역을 찾을 수 없습니다.")
    return {"success": True, "data": {"region_id": region_id, "airports": airports}}
