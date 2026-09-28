from typing import List, Optional

from pydantic import BaseModel, Field


class Airport(BaseModel):
    """공항 정보 모델"""

    iata: str = Field(..., description="IATA 코드")
    name: str = Field(..., description="공항 이름")
    city: str = Field(..., description="도시명")
    is_international: bool = Field(True, description="국제공항 여부")

    model_config = {
        "json_schema_extra": {
            "example": {
                "iata": "CTS",
                "name": "신치토세공항",
                "city": "삿포로",
                "is_international": True,
            }
        }
    }


class Region(BaseModel):
    """지역 정보 모델"""

    id: str = Field(..., description="지역 ID")
    name: str = Field(..., description="지역명")
    name_en: str = Field(..., description="영문명")
    airports: List[Airport] = Field(..., description="공항 목록")
    main_airport: str = Field(..., description="주요 공항")
    coordinates: Optional[List[List[float]]] = Field(
        None, description="지도 폴리곤 좌표"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "hokkaido",
                "name": "홋카이도",
                "name_en": "Hokkaido",
                "main_airport": "CTS",
                "airports": [
                    {
                        "iata": "CTS",
                        "name": "신치토세공항",
                        "city": "삿포로",
                        "is_international": True,
                    }
                ],
            }
        }
    }


class RegionalPrice(BaseModel):
    """지역별 가격 정보 모델"""

    region_id: str = Field(..., description="지역 ID")
    region_name: str = Field(..., description="지역명")
    price: int = Field(..., description="최저가 (원)")
    departure_date: str = Field(..., description="출발일")
    return_date: str = Field(..., description="귀국일")
    duration_days: int = Field(..., description="여행 기간")
    airport: str = Field(..., description="공항 코드")
    last_updated: str = Field(..., description="마지막 업데이트")

    model_config = {
        "json_schema_extra": {
            "example": {
                "region_id": "hokkaido",
                "region_name": "홋카이도",
                "price": 280000,
                "departure_date": "2025-08-15",
                "return_date": "2025-08-18",
                "duration_days": 4,
                "airport": "CTS",
                "last_updated": "2025-07-04T10:00:00Z",
            }
        }
    }
