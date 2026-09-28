from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class FlightSegment(BaseModel):
    """항공편 구간 정보"""

    departure: Dict[str, Any] = Field(..., description="출발 정보")
    arrival: Dict[str, Any] = Field(..., description="도착 정보")
    carrier_code: str = Field(..., description="항공사 코드")
    flight_number: str = Field(..., description="항공편 번호")
    duration: Optional[str] = Field(None, description="비행 시간")


class FlightItinerary(BaseModel):
    """항공편 일정"""

    duration: str = Field(..., description="총 소요 시간")
    segments: List[FlightSegment] = Field(..., description="구간 목록")


class FlightPrice(BaseModel):
    """항공편 가격 정보"""

    currency: str = Field(..., description="통화")
    total: str = Field(..., description="총 가격")
    base: Optional[str] = Field(None, description="기본 요금")
    fees: Optional[List[Dict[str, Any]]] = Field(None, description="수수료 목록")


class FlightOffer(BaseModel):
    """항공편 제안"""

    id: str = Field(..., description="항공편 ID")
    source: str = Field(..., description="데이터 소스")
    itineraries: List[FlightItinerary] = Field(..., description="일정 목록")
    price: FlightPrice = Field(..., description="가격 정보")
    traveler_pricings: Optional[List[Dict[str, Any]]] = Field(
        None, description="승객별 가격"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "1",
                "source": "GDS",
                "price": {"currency": "KRW", "total": "280000", "base": "250000"},
            }
        }
    }
