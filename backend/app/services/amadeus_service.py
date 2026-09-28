import asyncio
import logging
from typing import Any, Dict, Optional

from amadeus import Client, ResponseError

from app.config.settings import settings
from app.services.exchange_rate_service import ExchangeRateService

logger = logging.getLogger(__name__)


class AmadeusService:
    def __init__(self):
        """Amadeus 클라이언트 초기화"""
        if settings.AMADEUS_CLIENT_ID and settings.AMADEUS_CLIENT_SECRET:
            self.client = Client(
                client_id=settings.AMADEUS_CLIENT_ID,
                client_secret=settings.AMADEUS_CLIENT_SECRET,
                hostname=settings.AMADEUS_HOSTNAME,
            )
            self.is_active = True
            logger.info("AmadeusService initialized with real API client")
        else:
            self.client = None
            self.is_active = False
            logger.warning(
                "AmadeusService initialized in dummy mode - API keys not provided"
            )

        self.exchange_rate_service = ExchangeRateService()

    async def search_cheapest_dates(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        duration: Optional[int] = None,
        one_way: bool = False,
    ) -> Dict[str, Any]:
        """특정 구간의 최저가 날짜 검색"""
        if not self.is_active:
            return await self._get_dummy_cheapest_dates(
                origin, destination, departure_date, duration, one_way
            )

        try:
            logger.info(f"Searching cheapest dates: {origin} -> {destination}")
            loop = asyncio.get_event_loop()

            def _search():
                params = {
                    "origin": origin,
                    "destination": destination,
                    "departureDate": departure_date,
                    "oneWay": one_way,
                    "currency": "KRW",
                    "maxPrice": 2000000,
                }

                if duration:
                    params["duration"] = duration

                return self.client.shopping.flight_dates.get(**params)

            response = await loop.run_in_executor(None, _search)

            if response.data:
                return {
                    "success": True,
                    "data": response.data,
                    "meta": getattr(response, "meta", {}),
                }
            else:
                return {
                    "success": False,
                    "message": "검색 결과가 없습니다.",
                    "data": [],
                }

        except ResponseError as error:
            logger.error(f"Amadeus API 오류: {error}")
            return {
                "success": False,
                "message": f"API 오류: {error.description}",
                "data": [],
            }
        except Exception as error:
            logger.error(f"예상치 못한 오류: {error}")
            return {
                "success": False,
                "message": "서버 오류가 발생했습니다.",
                "data": [],
            }

    async def search_flight_offers(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: Optional[str] = None,
        adults: int = 1,
        currency: str = "KRW",
    ) -> Dict[str, Any]:
        """실시간 항공편 검색"""
        if not self.is_active:
            return await self._get_dummy_flight_offers(
                origin, destination, departure_date, return_date, adults, currency
            )

        try:
            logger.info(f"Searching flight offers: {origin} -> {destination}")

            loop = asyncio.get_event_loop()

            def _search():
                # KRW 요청 시 JPY로 검색 후 변환
                search_currency = "JPY" if currency == "KRW" else currency

                params = {
                    "originLocationCode": origin,
                    "destinationLocationCode": destination,
                    "departureDate": departure_date,
                    "adults": adults,
                    "currencyCode": search_currency,
                    "max": 10,
                }

                if return_date:
                    params["returnDate"] = return_date

                return self.client.shopping.flight_offers_search.get(**params)

            response = await loop.run_in_executor(None, _search)

            if response.data:
                data = response.data

                # JPY로 검색했을 때 KRW로 변환
                if currency == "KRW":
                    data = await self._convert_prices_to_krw(data, "JPY")

                return {
                    "success": True,
                    "data": data,
                    "meta": getattr(response, "meta", {}),
                    "dictionaries": getattr(response, "dictionaries", {}),
                }
            else:
                return {
                    "success": False,
                    "message": "검색 결과가 없습니다.",
                    "data": [],
                }

        except ResponseError as error:
            logger.error(f"Amadeus API 오류: {error}")
            return {
                "success": False,
                "message": f"API 오류: {error.description}",
                "data": [],
            }
        except Exception as error:
            logger.error(f"예상치 못한 오류: {error}")
            return {
                "success": False,
                "message": "서버 오류가 발생했습니다.",
                "data": [],
            }

    async def get_airport_info(self, iata_code: str) -> Dict[str, Any]:
        """공항 정보 조회"""
        if not self.is_active:
            return await self._get_dummy_airport_info(iata_code)

        try:
            logger.info(f"Getting airport info for: {iata_code}")

            loop = asyncio.get_event_loop()

            def _search():
                return self.client.reference_data.locations.get(
                    keyword=iata_code, subType="AIRPORT"
                )

            response = await loop.run_in_executor(None, _search)

            if response.data:
                return {
                    "success": True,
                    "data": response.data[0] if response.data else {},
                }
            else:
                return {
                    "success": False,
                    "message": "공항 정보를 찾을 수 없습니다.",
                    "data": {},
                }

        except ResponseError as error:
            logger.error(f"Amadeus API 오류: {error}")
            return {
                "success": False,
                "message": f"API 오류: {error.description}",
                "data": {},
            }
        except Exception as error:
            logger.error(f"예상치 못한 오류: {error}")
            return {
                "success": False,
                "message": "서버 오류가 발생했습니다.",
                "data": {},
            }

    async def _get_dummy_cheapest_dates(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        duration: Optional[int],
        one_way: bool = False,
    ) -> Dict[str, Any]:
        """더미 최저가 날짜 데이터"""
        dummy_data = {
            "type": "flight-date",
            "origin": origin,
            "destination": destination,
            "departureDate": departure_date,
            "price": {"total": "180000" if one_way else "280000", "currency": "KRW"},
        }

        if not one_way:
            dummy_data["returnDate"] = "2025-08-18"

        return {
            "success": True,
            "data": [dummy_data],
            "meta": {"count": 1},
        }

    async def _get_dummy_flight_offers(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: Optional[str],
        adults: int,
        currency: str,
    ) -> Dict[str, Any]:
        """더미 항공편 검색 데이터"""
        return {
            "success": True,
            "data": [
                {
                    "type": "flight-offer",
                    "id": f"dummy-{origin}-{destination}-{departure_date}",
                    "source": "GDS",
                    "itineraries": [
                        {
                            "duration": "PT2H30M",
                            "segments": [
                                {
                                    "departure": {
                                        "iataCode": origin,
                                        "at": f"{departure_date}T09:00:00",
                                    },
                                    "arrival": {
                                        "iataCode": destination,
                                        "at": f"{departure_date}T11:30:00",
                                    },
                                    "carrierCode": "KE",
                                    "number": "704",
                                }
                            ],
                        }
                    ],
                    "price": {
                        "currency": currency,
                        "total": "280000",
                        "base": "250000",
                    },
                    "travelerPricings": [
                        {
                            "travelerId": "1",
                            "fareOption": "STANDARD",
                            "travelerType": "ADULT",
                            "price": {
                                "currency": currency,
                                "total": "280000",
                                "base": "250000",
                            },
                        }
                    ],
                }
            ],
            "meta": {"count": 1},
        }

    async def _get_dummy_airport_info(self, iata_code: str) -> Dict[str, Any]:
        """더미 공항 정보"""
        airport_data = {
            "ICN": {
                "type": "location",
                "subType": "AIRPORT",
                "name": "Incheon International Airport",
                "iataCode": "ICN",
                "address": {
                    "cityName": "Seoul",
                    "countryName": "South Korea",
                    "countryCode": "KR",
                },
            },
            "NRT": {
                "type": "location",
                "subType": "AIRPORT",
                "name": "Narita International Airport",
                "iataCode": "NRT",
                "address": {
                    "cityName": "Tokyo",
                    "countryName": "Japan",
                    "countryCode": "JP",
                },
            },
            "HND": {
                "type": "location",
                "subType": "AIRPORT",
                "name": "Haneda International Airport",
                "iataCode": "HND",
                "address": {
                    "cityName": "Tokyo",
                    "countryName": "Japan",
                    "countryCode": "JP",
                },
            },
        }

        if iata_code in airport_data:
            return {"success": True, "data": airport_data[iata_code]}
        else:
            return {
                "success": False,
                "message": "공항 정보를 찾을 수 없습니다.",
                "data": {},
            }

    async def _convert_prices_to_krw(self, data, from_currency: str):
        """가격 데이터를 KRW로 변환"""
        try:
            # 환율 정보 가져오기 (캐시 우선 사용으로 API 호출 최소화)
            rates_response = await self.exchange_rate_service.get_current_rates(
                [from_currency]
            )
            if not rates_response.success or not rates_response.rates:
                logger.warning(f"환율 정보를 가져올 수 없습니다: {from_currency}")
                return data

            rate = rates_response.rates[0].base_rate

            if isinstance(data, list):
                for offer in data:
                    if "price" in offer:
                        self._convert_price_dict(offer["price"], rate)
                    if "travelerPricings" in offer:
                        for traveler in offer["travelerPricings"]:
                            if "price" in traveler:
                                self._convert_price_dict(traveler["price"], rate)

            return data
        except Exception as e:
            logger.error(f"가격 변환 중 오류 발생: {e}")
            return data

    def _convert_price_dict(self, price_dict: dict, rate: float):
        """가격 딕셔너리의 통화를 KRW로 변환"""
        try:
            if "total" in price_dict:
                original_total = float(price_dict["total"])
                price_dict["total"] = str(int(original_total * rate))

            if "base" in price_dict:
                original_base = float(price_dict["base"])
                price_dict["base"] = str(int(original_base * rate))

            price_dict["currency"] = "KRW"
        except (ValueError, TypeError) as e:
            logger.error(f"가격 변환 중 오류: {e}")
            pass
