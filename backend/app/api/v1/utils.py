from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.services.date_service import DateService
from app.services.region_service import RegionService

router = APIRouter(prefix="/utils", tags=["utils"])


# Request/Response 모델


class DateInfo(BaseModel):
    """날짜 정보 모델"""

    date: str = Field(..., description="날짜 (YYYY-MM-DD)")
    is_holiday: bool = Field(..., description="공휴일 여부")
    holiday_name: Optional[str] = Field(None, description="공휴일명")
    season: Optional[str] = Field(None, description="시즌/기간")
    price_impact: str = Field(..., description="가격 영향도", example="high")
    description: Optional[str] = Field(None, description="설명")


class AirportSearchResult(BaseModel):
    """공항 검색 결과 모델"""

    iata: str = Field(..., description="IATA 코드")
    name: str = Field(..., description="공항명")
    city: str = Field(..., description="도시명")
    region_id: str = Field(..., description="지역 ID")
    region_name: str = Field(..., description="지역명")
    is_international: bool = Field(..., description="국제공항 여부")


def get_date_service() -> DateService:
    """날짜 서비스 인스턴스 반환"""
    return DateService()


def get_region_service() -> RegionService:
    """지역 서비스 인스턴스 반환"""
    return RegionService()


# API 엔드포인트


@router.get("/date-info", response_model=Dict[str, Any])
async def get_date_info(
    date_str: str = Query(..., description="날짜 (YYYY-MM-DD)", alias="date"),
    date_service: DateService = Depends(get_date_service),
) -> Dict[str, Any]:
    """
    특정 날짜의 공휴일/시즌 정보 조회

    **사용 예시**:
    - `GET /utils/date-info?date=2025-05-03` → 헌법기념일 (골든위크)
    - `GET /utils/date-info?date=2025-04-05` → 벚꽃 시즌
    - `GET /utils/date-info?date=2025-08-15` → 오봉 기간

    **가격 영향도**:
    - `very_high`: 골든위크, 연말연시 등
    - `high`: 벚꽃시즌, 단풍시즌 등
    - `medium`: 3연휴, 오봉 등
    - `low`: 평일, 비수기
    """
    try:
        # 날짜 형식 검증
        try:
            datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="잘못된 날짜 형식입니다. YYYY-MM-DD 형식으로 입력해주세요.",
            )

        # 날짜 정보 조회
        date_info = await date_service.get_date_info(date_str)

        return {
            "success": True,
            "message": f"{date_str} 날짜 정보 조회 완료",
            "data": date_info,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"날짜 정보 조회 중 오류가 발생했습니다: {str(e)}")


@router.get("/airports/search")
async def search_airports(
    q: str = Query(..., description="검색어 (공항명, 도시명, IATA 코드)", min_length=1),
    limit: int = Query(10, description="결과 개수 제한", ge=1, le=50),
    international_only: bool = Query(False, description="국제공항만 검색"),
    region_service: RegionService = Depends(get_region_service),
) -> Dict[str, Any]:
    """
    공항 검색 (자동완성용)

    **사용 예시**:
    - `GET /utils/airports/search?q=나리타` → 나리타국제공항
    - `GET /utils/airports/search?q=NRT` → 나리타국제공항
    - `GET /utils/airports/search?q=도쿄` → 도쿄 지역 공항들
    - `GET /utils/airports/search?q=홋카이도&international_only=true` → 홋카이도 국제공항만
    """
    try:
        # 공항 검색 실행
        search_results = await region_service.search_airports(q)

        # 국제공항만 필터링 (옵션)
        if international_only:
            search_results = [
                airport
                for airport in search_results
                if airport.get("is_international", False)
            ]

        # 결과 개수 제한
        search_results = search_results[:limit]

        return {
            "success": True,
            "message": f"'{q}' 검색 완료",
            "data": {
                "query": q,
                "total_results": len(search_results),
                "results": search_results,
            },
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"공항 검색 중 오류가 발생했습니다: {str(e)}")


@router.get("/holidays")
async def get_holidays(
    year: int = Query(..., description="연도", ge=2025, le=2027),
    date_service: DateService = Depends(get_date_service),
) -> Dict[str, Any]:
    """
    연도별 일본 공휴일 목록 조회

    **사용 예시**:
    - `GET /utils/holidays?year=2025` → 2025년 일본 공휴일
    - `GET /utils/holidays?year=2026` → 2026년 일본 공휴일
    """
    try:
        holidays = await date_service.get_year_holidays(year)

        return {
            "success": True,
            "message": f"{year}년 공휴일 목록 조회 완료",
            "data": {
                "year": year,
                "total_holidays": len(holidays),
                "holidays": holidays,
            },
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"공휴일 조회 중 오류가 발생했습니다: {str(e)}")


@router.get("/seasons")
async def get_travel_seasons() -> Dict[str, Any]:
    """
    일본 여행 시즌 정보 조회

    각 시즌별 특징과 예상 가격 영향도를 제공합니다.
    """
    try:
        seasons_info = {
            "spring": {
                "name": "봄 (벚꽃 시즌)",
                "period": "3월 말 ~ 5월 초",
                "peak_months": [3, 4],
                "price_impact": "very_high",
                "description": "벚꽃 개화 시기로 연중 최고 성수기",
                "recommendation": "최소 3개월 전 예약 권장",
            },
            "summer": {
                "name": "여름",
                "period": "6월 ~ 8월",
                "peak_months": [7, 8],
                "price_impact": "high",
                "description": "여름휴가철, 습하고 더운 날씨",
                "recommendation": "오봉 기간(8월 중순) 피하기 권장",
            },
            "autumn": {
                "name": "가을 (단풍 시즌)",
                "period": "9월 ~ 11월",
                "peak_months": [10, 11],
                "price_impact": "high",
                "description": "단풍 시즌으로 인기 높은 시기",
                "recommendation": "9월이 상대적으로 저렴",
            },
            "winter": {
                "name": "겨울",
                "period": "12월 ~ 2월",
                "peak_months": [12, 1],
                "price_impact": "medium",
                "description": "연말연시 제외하면 비교적 저렴",
                "recommendation": "1월 중순~2월이 가장 저렴",
            },
        }

        return {
            "success": True,
            "message": "여행 시즌 정보 조회 완료",
            "data": seasons_info,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"시즌 정보 조회 중 오류가 발생했습니다: {str(e)}")


@router.get("/price-trends")
async def get_price_trends(
    region_id: Optional[str] = Query(None, description="지역 ID (전체 조회시 생략)"),
    region_service: RegionService = Depends(get_region_service),
) -> Dict[str, Any]:
    """
    지역별 가격 동향 정보

    **사용 예시**:
    - `GET /utils/price-trends` → 전체 지역 가격 동향
    - `GET /utils/price-trends?region_id=hokkaido` → 홋카이도 가격 동향
    """
    try:
        # 지역 유효성 검증
        if region_id:
            if not region_service.is_valid_region(region_id):
                raise HTTPException(
                    status_code=404, detail=f"지역 '{region_id}'를 찾을 수 없습니다"
                )

        # 더미 가격 동향 데이터 (실제로는 DB에서 조회)
        price_trends = {
            "hokkaido": {"avg_price": 320000, "trend": "상승", "season_factor": 1.2},
            "kanto": {"avg_price": 280000, "trend": "안정", "season_factor": 1.0},
            "kansai": {"avg_price": 250000, "trend": "하락", "season_factor": 0.9},
            "chubu": {"avg_price": 270000, "trend": "안정", "season_factor": 1.0},
            "kyushu": {"avg_price": 230000, "trend": "상승", "season_factor": 1.1},
            "okinawa": {"avg_price": 350000, "trend": "상승", "season_factor": 1.3},
        }

        if region_id:
            trend_data = price_trends.get(region_id, {})
            result_data = {region_id: trend_data} if trend_data else {}
        else:
            result_data = price_trends

        return {
            "success": True,
            "message": "가격 동향 조회 완료",
            "data": {
                "trends": result_data,
                "last_updated": datetime.now().isoformat(),
                "note": "더미 데이터입니다. 실제 운영시에는 실시간 분석 필요",
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"가격 동향 조회 중 오류가 발생했습니다: {str(e)}")


# 헬스 체크


@router.get("/health")
async def utils_health_check() -> Dict[str, Any]:
    """
    유틸리티 서비스 상태 확인
    """
    return {
        "service": "utils",
        "status": "healthy",
        "available_endpoints": [
            "date-info",
            "airports/search",
            "holidays",
            "seasons",
            "price-trends",
        ],
        "timestamp": datetime.now().isoformat(),
    }
