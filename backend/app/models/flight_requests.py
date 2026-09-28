from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.utils.validators import (
    validate_date_format,
    validate_duration,
    validate_passenger_count,
)


class FlightSearchRequest(BaseModel):
    """기본 항공편 검색 요청"""

    origin: str = Field(..., description="출발지 IATA 코드")
    destination: str = Field(..., description="도착지 IATA 코드")
    departure_date: str = Field(..., description="출발 날짜 (YYYY-MM-DD)")
    return_date: Optional[str] = Field(None, description="귀국 날짜 (YYYY-MM-DD)")
    adults: int = Field(1, description="성인 승객 수", ge=1, le=9)
    currency: str = Field("KRW", description="통화 코드")

    @field_validator("departure_date", "return_date")
    @classmethod
    def validate_dates(cls, v):
        return validate_date_format(v) if v else v

    @field_validator("adults")
    @classmethod
    def validate_adults(cls, v):
        return validate_passenger_count(v)


class FlightDurationSearchRequest(BaseModel):
    """여행 기간 기반 검색 요청"""

    origin: str = Field("ICN", description="출발지 IATA 코드")
    destination: str = Field(..., description="도착지 IATA 코드")
    departure_date: str = Field(..., description="출발 날짜 (YYYY-MM-DD)")
    duration_days: int = Field(..., description="여행 기간 (일수)", ge=2, le=30)
    adults: int = Field(1, description="성인 승객 수", ge=1, le=9)
    currency: str = Field("KRW", description="통화 코드")

    @field_validator("departure_date")
    @classmethod
    def validate_departure_date(cls, v):
        return validate_date_format(v)

    @field_validator("duration_days")
    @classmethod
    def validate_duration(cls, v):
        return validate_duration(v)

    @field_validator("adults")
    @classmethod
    def validate_adults(cls, v):
        return validate_passenger_count(v)


class OneWayFlightSearchRequest(BaseModel):
    """편도 항공편 검색 요청"""

    origin: str = Field(..., description="출발지 IATA 코드")
    destination: str = Field(..., description="도착지 IATA 코드")
    departure_date: str = Field(..., description="출발 날짜 (YYYY-MM-DD)")
    adults: int = Field(1, description="성인 승객 수", ge=1, le=9)
    currency: str = Field("KRW", description="통화 코드")

    @field_validator("departure_date")
    @classmethod
    def validate_departure_date(cls, v):
        return validate_date_format(v)

    @field_validator("adults")
    @classmethod
    def validate_adults(cls, v):
        return validate_passenger_count(v)


class CheapestDateRequest(BaseModel):
    """최저가 날짜 검색 요청"""

    origin: str = Field(..., description="출발지 IATA 코드")
    destination: str = Field(..., description="도착지 IATA 코드")
    departure_date: str = Field(..., description="기준 출발 날짜 (YYYY-MM-DD)")
    duration: Optional[int] = Field(None, description="여행 기간 (일수)", ge=1, le=30)
    flexibility_days: int = Field(7, description="날짜 유연성 (±일수)", ge=1, le=15)
    trip_type: str = Field("round-trip", description="여행 유형 (one-way, round-trip)")

    @field_validator("departure_date")
    @classmethod
    def validate_departure_date(cls, v):
        return validate_date_format(v)

    @field_validator("duration")
    @classmethod
    def validate_duration(cls, v):
        return validate_duration(v, min_days=1) if v else v

    @field_validator("trip_type")
    @classmethod
    def validate_trip_type(cls, v):
        if v not in ["one-way", "round-trip"]:
            raise ValueError("trip_type must be 'one-way' or 'round-trip'")
        return v
