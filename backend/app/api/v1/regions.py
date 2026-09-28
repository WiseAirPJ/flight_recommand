from datetime import date, datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, validator

from app.services.monthly_price_analyzer import MonthlyPriceAnalyzer
from app.services.region_service import RegionService

router = APIRouter(prefix="/regions", tags=["regions"])


#  Response 모델


class Airport(BaseModel):
    """공항 정보 모델"""

    iata: str = Field(..., description="IATA 코드", example="CTS")
    name: str = Field(..., description="공항 이름", example="신치토세공항")
    city: str = Field(..., description="도시명", example="삿포로")
    is_international: bool = Field(True, description="국제공항 여부")


class Region(BaseModel):
    """지역 정보 모델"""

    id: str = Field(..., description="지역 ID", example="hokkaido")
    name: str = Field(..., description="지역명", example="홋카이도")
    name_en: str = Field(..., description="영문명", example="Hokkaido")
    airports: List[Airport] = Field(..., description="공항 목록")
    main_airport: str = Field(..., description="주요 공항", example="CTS")


class RegionalPrice(BaseModel):
    """지역별 가격 정보"""

    region_id: str = Field(..., description="지역 ID")
    region_name: str = Field(..., description="지역명")
    price: int = Field(..., description="최저가 (원)", example=280000)
    departure_date: str = Field(..., description="출발일", example="2025-08-15")
    return_date: str = Field(..., description="귀국일", example="2025-08-18")
    duration_days: int = Field(..., description="여행 기간", example=4)
    airport: str = Field(..., description="공항 코드", example="CTS")
    last_updated: str = Field(..., description="마지막 업데이트")


class RegionsResponse(BaseModel):
    """지역 목록 응답"""

    success: bool = Field(True, description="성공 여부")
    message: str = Field(..., description="응답 메시지")
    data: Dict[str, Region] = Field(..., description="지역 데이터")


class LowestPricesResponse(BaseModel):
    """지역별 최저가 응답"""

    success: bool = Field(True, description="성공 여부")
    message: str = Field(..., description="응답 메시지")
    data: Dict[str, RegionalPrice] = Field(..., description="지역별 최저가 데이터")
    last_updated: str = Field(..., description="마지막 업데이트 시간")


class MonthlyAnalysisRequest(BaseModel):
    """월별 분석 요청 모델"""

    year: Optional[int] = Field(None, description="대상 연도 (미지정시 현재 연도)", example=2025)
    month: Optional[int] = Field(
        None, description="대상 월 (1-12, 미지정시 현재 월)", ge=1, le=12, example=8
    )
    origin: str = Field("ICN", description="출발지 IATA 코드", example="ICN")
    duration: int = Field(4, description="여행 기간 (일수)", ge=2, le=14, example=4)

    @validator("year")
    def validate_year(cls, v):
        if v is not None:
            current_year = datetime.now().year
            if v < current_year or v > current_year + 2:
                raise ValueError(f"연도는 {current_year}년부터 {current_year + 2}년까지 가능합니다")
        return v

    @validator("month")
    def validate_month(cls, v):
        if v is not None and (v < 1 or v > 12):
            raise ValueError("월은 1부터 12까지 가능합니다")
        return v


class MonthlyAnalysisResponse(BaseModel):
    """월별 분석 응답 모델"""

    success: bool = Field(..., description="성공 여부")
    message: str = Field(..., description="응답 메시지")
    data: Dict[str, Any] = Field(..., description="분석 결과")


def get_region_service() -> RegionService:
    """지역 서비스 인스턴스 반환"""
    return RegionService()


def get_monthly_analyzer() -> MonthlyPriceAnalyzer:
    """월별 가격 분석기 인스턴스 반환"""
    return MonthlyPriceAnalyzer()


# API 엔드포인트


@router.get("/", response_model=RegionsResponse)
async def get_regions(
    region_service: RegionService = Depends(get_region_service),
) -> Dict[str, Any]:
    """
    일본 지역 목록 조회

    앱 초기화 시 사용하는 기본 지역 정보를 제공합니다.
    각 지역의 공항 정보와 지도 표시용 메타데이터를 포함합니다.
    """
    try:
        regions_data = await region_service.get_all_regions()

        return {"success": True, "message": "지역 목록 조회 완료", "data": regions_data}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"지역 목록 조회 중 오류가 발생했습니다: {str(e)}")


@router.get("/{region_id}/airports")
async def get_region_airports(
    region_id: str, region_service: RegionService = Depends(get_region_service)
) -> Dict[str, Any]:
    """
    특정 지역의 공항 목록 조회

    사용자가 지역을 선택했을 때 해당 지역의
    이용 가능한 공항 목록을 제공합니다.
    """
    try:
        airports = await region_service.get_region_airports(region_id)

        if not airports:
            raise HTTPException(status_code=404, detail=f"지역 '{region_id}'를 찾을 수 없습니다")

        return {
            "success": True,
            "message": f"{region_id} 지역 공항 목록 조회 완료",
            "data": {"region_id": region_id, "airports": airports},
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"공항 목록 조회 중 오류가 발생했습니다: {str(e)}")


@router.get("/lowest-prices", response_model=LowestPricesResponse)
async def get_regions_lowest_prices(
    origin: str = Query("ICN", description="출발지 IATA 코드"),
    adults: int = Query(1, description="성인 승객 수", ge=1, le=9),
    month: Optional[int] = Query(
        None, description="대상 월 (1-12, 기본값: 현재 월)", ge=1, le=12
    ),
    region_service: RegionService = Depends(get_region_service),
    analyzer: MonthlyPriceAnalyzer = Depends(get_monthly_analyzer),
) -> Dict[str, Any]:
    """
    지역별 최저가 정보 조회 (메인 화면용)

    **이것이 앱의 핵심 API입니다!**

    사용자가 앱을 실행했을 때 지도에 표시할
    각 일본 지역별 이번 달 최저 왕복 항공권 가격을 제공합니다.

    **사용 예시**:
    - `GET /regions/lowest-prices` → 이번 달 모든 지역 최저가 (성인 1명)
    - `GET /regions/lowest-prices?adults=2&month=8` → 8월 모든 지역 최저가 (성인 2명)
    - `GET /regions/lowest-prices?origin=PUS&adults=4&month=10` → 부산 출발, 10월 최저가 (성인 4명)
    """
    try:
        # 월 설정 (기본값: 현재 월)
        today = date.today()
        target_month = month if month is not None else today.month
        target_year = today.year

        # 과거 월 체크
        if target_year == today.year and target_month < today.month:
            target_month = today.month

        # 월별 최저가 데이터 조회
        analysis_result = await analyzer.get_monthly_cheapest_dates(
            target_year=target_year,
            target_month=target_month,
            origin=origin,
            trip_duration=4,
            adults=adults,
        )

        if not analysis_result["success"]:
            raise HTTPException(
                status_code=500,
                detail=f"가격 데이터 조회 실패: {analysis_result['message']}",
            )

        # 프론트엔드 친화적 형태로 변환
        regional_prices = {}
        regions_data = analysis_result["data"].get("regions", {})

        for region_id, region_data in regions_data.items():
            if region_data and "cheapest_option" in region_data:
                cheapest = region_data["cheapest_option"]

                regional_prices[region_id] = {
                    "region_id": region_id,
                    "region_name": region_data["region_name"],
                    "price": int(cheapest["price"]),
                    "departure_date": cheapest["departure_date"],
                    "return_date": cheapest["return_date"],
                    "duration_days": cheapest["duration_days"],
                    "airport": region_data["airport"],
                    "last_updated": datetime.now().isoformat(),
                }

        return {
            "success": True,
            "message": f"{target_year}년 {target_month}월 지역별 최저가 조회 완료",
            "data": regional_prices,
            "last_updated": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"지역별 최저가 조회 중 오류가 발생했습니다: {str(e)}",
        )


@router.get("/statistics")
async def get_regions_statistics(
    region_service: RegionService = Depends(get_region_service),
) -> Dict[str, Any]:
    """
    지역 통계 정보

    개발/디버깅용 지역 관련 통계를 제공합니다.
    """
    try:
        regions = await region_service.get_all_regions()

        stats = {
            "total_regions": len(regions),
            "total_airports": sum(len(r["airports"]) for r in regions.values()),
            "regions_list": list(regions.keys()),
            "international_airports": [
                airport["iata"]
                for region in regions.values()
                for airport in region["airports"]
                if airport.get("is_international", True)
            ],
        }

        return {"success": True, "message": "지역 통계 조회 완료", "data": stats}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"통계 조회 중 오류가 발생했습니다: {str(e)}")


@router.get("/monthly-analysis", response_model=MonthlyAnalysisResponse)
async def get_monthly_analysis(
    year: Optional[int] = Query(None, description="대상 연도 (기본값: 현재 연도)"),
    month: Optional[int] = Query(None, description="대상 월 (기본값: 현재 월)", ge=1, le=12),
    origin: str = Query("ICN", description="출발지 IATA 코드"),
    adults: int = Query(1, description="성인 승객 수", ge=1, le=9),
    duration: int = Query(4, description="여행 기간 (일수)", ge=2, le=14),
    analyzer: MonthlyPriceAnalyzer = Depends(get_monthly_analyzer),
) -> Dict[str, Any]:
    """
    월별 지역별 최저가 상세 분석

    지역별 최저가 조회보다 더 자세한 분석 정보를 제공합니다.

    **사용 예시**:
    - `GET /regions/monthly-analysis` → 이번 달 상세 분석
    - `GET /regions/monthly-analysis?month=8&adults=2` → 8월 상세 분석 (성인 2명)
    - `GET /regions/monthly-analysis?year=2025&month=12` → 2025년 12월 상세 분석
    """
    try:
        # 기본값 설정
        today = date.today()
        target_year = year if year is not None else today.year
        target_month = month if month is not None else today.month

        # 과거 날짜 검증
        if target_year == today.year and target_month < today.month:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"과거 월({target_month}월)은 검색할 수 없습니다. "
                    f"현재 월({today.month}월) 이후를 선택해주세요."
                ),
            )

        # 월별 최저가 검색 실행
        result = await analyzer.get_monthly_cheapest_dates(
            target_year=target_year,
            target_month=target_month,
            origin=origin,
            trip_duration=duration,
            adults=adults,
        )

        if result["success"]:
            # 프론트엔드용 데이터 구조로 변환
            frontend_data = _format_for_frontend(result["data"])

            return {
                "success": True,
                "message": f"{target_year}년 {target_month}월 지역별 최저가 상세 분석 완료",
                "data": frontend_data,
            }
        else:
            raise HTTPException(status_code=500, detail=result["message"])

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"월별 분석 중 오류가 발생했습니다: {str(e)}")


@router.get("/monthly-analysis/{year}/{month}", response_model=MonthlyAnalysisResponse)
async def get_specific_month_analysis(
    year: int,
    month: int,
    origin: str = Query("ICN", description="출발지 IATA 코드"),
    adults: int = Query(1, description="성인 승객 수", ge=1, le=9),
    duration: int = Query(4, description="여행 기간 (일수)", ge=2, le=14),
    analyzer: MonthlyPriceAnalyzer = Depends(get_monthly_analyzer),
) -> Dict[str, Any]:
    """
    특정 월 지역별 최저가 상세 분석 (RESTful 방식)

    **사용 예시**:
    - `GET /regions/monthly-analysis/2025/8` → 2025년 8월
    - `GET /regions/monthly-analysis/2026/12` → 2026년 12월
    """
    # 날짜 유효성 검증
    current_year = datetime.now().year
    if year < current_year or year > current_year + 2:
        raise HTTPException(
            status_code=400,
            detail=f"연도는 {current_year}년부터 {current_year + 2}년까지 가능합니다",
        )

    if month < 1 or month > 12:
        raise HTTPException(status_code=400, detail="월은 1부터 12까지 가능합니다")

    # 과거 날짜 검증
    today = date.today()
    if year == today.year and month < today.month:
        raise HTTPException(
            status_code=400,
            detail=f"과거 월은 검색할 수 없습니다. 현재 월({today.month}월) 이후를 선택해주세요.",
        )

    try:
        result = await analyzer.get_monthly_cheapest_dates(
            target_year=year,
            target_month=month,
            origin=origin,
            trip_duration=duration,
            adults=adults,
        )

        if result["success"]:
            frontend_data = _format_for_frontend(result["data"])

            return {
                "success": True,
                "message": f"{year}년 {month}월 지역별 최저가 상세 분석 완료",
                "data": frontend_data,
            }
        else:
            raise HTTPException(status_code=500, detail=result["message"])

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"{year}년 {month}월 분석 중 오류가 발생했습니다: {str(e)}",
        )


def _format_for_frontend(analysis_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    프론트엔드에서 사용하기 쉬운 형태로 데이터 변환
    """
    if not analysis_data or "regions" not in analysis_data:
        return analysis_data

    # 지역별 데이터를 프론트엔드 친화적으로 변환
    formatted_regions = {}

    for region_id, region_data in analysis_data["regions"].items():
        if region_data and "cheapest_option" in region_data:
            cheapest = region_data["cheapest_option"]
            stats = region_data.get("price_statistics", {})

            formatted_regions[region_id] = {
                "region_name": region_data["region_name"],
                "airport": region_data["airport"],
                "best_dates": {
                    "departure_date": cheapest["departure_date"],
                    "return_date": cheapest["return_date"],
                    "duration_days": cheapest["duration_days"],
                },
                "price_info": {
                    "best_price": cheapest["price"],
                    "currency": cheapest["currency"],
                    "avg_price": stats.get("avg_price", 0),
                    "min_price": stats.get("min_price", 0),
                    "max_price": stats.get("max_price", 0),
                },
                "alternatives": region_data.get("all_options", [])[:3],  # 상위 3개 대안
            }

    # 가격순으로 정렬
    sorted_regions = dict(
        sorted(
            formatted_regions.items(), key=lambda x: x[1]["price_info"]["best_price"]
        )
    )

    return {
        "search_info": {
            "year": analysis_data["year"],
            "month": analysis_data["month"],
            "origin": analysis_data["origin"],
            "trip_duration": analysis_data["trip_duration"],
            "search_date_range": analysis_data["search_date_range"],
        },
        "regions": sorted_regions,
        "summary": {
            "total_regions": len(sorted_regions),
            "cheapest_region": (
                min(
                    sorted_regions.keys(),
                    key=lambda x: sorted_regions[x]["price_info"]["best_price"],
                )
                if sorted_regions
                else None
            ),
            "price_range": {
                "min": (
                    min(
                        [r["price_info"]["best_price"] for r in sorted_regions.values()]
                    )
                    if sorted_regions
                    else 0
                ),
                "max": (
                    max(
                        [r["price_info"]["best_price"] for r in sorted_regions.values()]
                    )
                    if sorted_regions
                    else 0
                ),
            },
        },
    }


#  헬스 체크


@router.get("/health")
async def regions_health_check(
    region_service: RegionService = Depends(get_region_service),
) -> Dict[str, Any]:
    """
    지역 서비스 상태 확인
    """
    try:
        regions = await region_service.get_all_regions()

        return {
            "service": "regions",
            "status": "healthy",
            "regions_loaded": len(regions),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        return {
            "service": "regions",
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }
