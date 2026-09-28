"""Search contracts shared by one-way, round-trip and monthly searches."""

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.utils.validators import validate_date_format, validate_iata_code


class RouteRequest(BaseModel):
    origin: str
    destination: str

    @field_validator("origin", "destination")
    @classmethod
    def airport_code(cls, value):
        return validate_iata_code(value.strip())

    @model_validator(mode="after")
    def different_airports(self):
        if self.origin == self.destination:
            raise ValueError("출발공항과 도착공항은 달라야 합니다.")
        return self


class FlightSearchRequest(RouteRequest):
    departure_date: str
    return_date: Optional[str] = None
    adults: int = Field(1, ge=1, le=9)
    currency: str = Field("KRW", pattern=r"^[A-Z]{3}$")
    non_stop: bool = False

    @field_validator("departure_date", "return_date")
    @classmethod
    def travel_date(cls, value):
        return validate_date_format(value) if value else value

    @field_validator("currency", mode="before")
    @classmethod
    def currency_code(cls, value):
        return value.strip().upper() if isinstance(value, str) else value

    @model_validator(mode="after")
    def return_after_departure(self):
        if self.return_date and self.return_date < self.departure_date:
            raise ValueError("귀국일은 출발일보다 빠를 수 없습니다.")
        return self


class OneWayFlightSearchRequest(FlightSearchRequest):
    return_date: None = None


class FlightDurationSearchRequest(RouteRequest):
    departure_date: str
    duration_days: int = Field(..., ge=2, le=30)
    adults: int = Field(1, ge=1, le=9)
    currency: str = Field("KRW", pattern=r"^[A-Z]{3}$")
    non_stop: bool = False

    @field_validator("departure_date")
    @classmethod
    def travel_date(cls, value):
        return validate_date_format(value)


class CheapestDateRequest(RouteRequest):
    departure_date: str
    duration: Optional[int] = Field(None, ge=2, le=30)
    flexibility_days: int = Field(7, ge=1, le=15)
    trip_type: Literal["one-way", "round-trip"] = "round-trip"
    adults: int = Field(1, ge=1, le=9)
    currency: str = Field("KRW", pattern=r"^[A-Z]{3}$")
    non_stop: bool = False

    @field_validator("departure_date")
    @classmethod
    def travel_date(cls, value):
        return validate_date_format(value)


class MonthlySearchRequest(BaseModel):
    year: int = Field(..., ge=2000, le=2100)
    month: int = Field(..., ge=1, le=12)
    origin: str = "ICN"
    adults: int = Field(1, ge=1, le=9)
    duration_days: int = Field(4, ge=2, le=30)
    currency: str = Field("KRW", pattern=r"^[A-Z]{3}$")
    non_stop: bool = False

    @field_validator("origin")
    @classmethod
    def airport_code(cls, value):
        return validate_iata_code(value.strip())

    @model_validator(mode="after")
    def future_month(self):
        today = date.today()
        if (self.year, self.month) < (today.year, today.month):
            raise ValueError("과거 월은 현재 항공권 검색에 사용할 수 없습니다.")
        if self.year > today.year + 1:
            raise ValueError("검색 가능한 연도 범위를 벗어났습니다.")
        return self
