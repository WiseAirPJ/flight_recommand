"""One quote path for map, date and individual flight searches."""

import asyncio
import logging
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal

from amadeus import Client, ResponseError

from app.config.settings import settings
from app.services.exchange_rate_service import ExchangeRateService
from app.services.price_history_service import PriceHistoryService

logger = logging.getLogger(__name__)


class AmadeusService:
    def __init__(self, client=None, exchange_rate_service=None, history_service=None):
        self.client = client
        if client is None and settings.USE_REAL_AMADEUS:
            self.client = Client(
                client_id=settings.AMADEUS_CLIENT_ID,
                client_secret=settings.AMADEUS_CLIENT_SECRET,
                hostname=settings.AMADEUS_HOSTNAME,
            )
        self.is_active = self.client is not None
        self.exchange_rate_service = exchange_rate_service or ExchangeRateService()
        self.history_service = history_service or PriceHistoryService()

    @property
    def source(self):
        if self.is_active:
            return (
                "amadeus"
                if settings.AMADEUS_HOSTNAME == "production"
                else "amadeus_test"
            )
        return "demo" if settings.ENABLE_DUMMY_FALLBACK else "unavailable"

    async def search_flight_offers(
        self,
        origin,
        destination,
        departure_date,
        return_date=None,
        adults=1,
        currency="KRW",
        non_stop=False,
    ):
        timestamp = datetime.now(timezone.utc).isoformat()
        if not self.is_active:
            if not settings.ENABLE_DUMMY_FALLBACK:
                return {
                    "success": False,
                    "data": [],
                    "status_code": 503,
                    "message": "항공권 검색 공급자가 설정되지 않았습니다.",
                }
            result = await self._get_dummy_flight_offers(
                origin, destination, departure_date, return_date, adults, currency
            )
            result["meta"] = {
                "source": "demo",
                "is_demo": True,
                "observed_at": timestamp,
            }
            return result
        try:
            search_currency = "JPY" if currency == "KRW" else currency
            params = {
                "originLocationCode": origin,
                "destinationLocationCode": destination,
                "departureDate": departure_date,
                "adults": adults,
                "currencyCode": search_currency,
                "max": 10,
                "travelClass": "ECONOMY",
                "nonStop": non_stop,
            }
            if return_date:
                params["returnDate"] = return_date
            response = await asyncio.to_thread(
                self.client.shopping.flight_offers_search.get, **params
            )
            offers = deepcopy(response.data or [])
            for offer in offers:
                amount = Decimal(str(offer["price"]["total"]))
                if not amount.is_finite() or amount <= 0:
                    raise ValueError("유효하지 않은 항공권 가격")
                if offer["price"].get("currency") != search_currency:
                    raise ValueError("공급자 통화 불일치")
            if offers and currency == "KRW":
                offers = await self._convert_prices_to_krw(offers, "JPY")
            if any(o.get("price", {}).get("currency") != currency for o in offers):
                raise ValueError("요청한 통화와 검색 결과의 통화가 다릅니다.")
            history_saved = False
            try:
                saved_count = await asyncio.to_thread(
                    self.history_service.record_offers,
                    offers,
                    origin=origin,
                    destination=destination,
                    departure_date=departure_date,
                    return_date=return_date,
                    adults=adults,
                    currency=currency,
                    source=self.source,
                    non_stop=non_stop,
                    observed_at=datetime.fromisoformat(timestamp),
                )
                history_saved = saved_count > 0
            except Exception:
                history_saved = False
                logger.exception("가격 이력 저장 실패")
            return {
                "success": True,
                "data": offers,
                "meta": {
                    "source": self.source,
                    "is_demo": False,
                    "observed_at": timestamp,
                    "history_saved": history_saved,
                    "display_price_is_estimate": currency == "KRW",
                    "price_basis": "total_for_all_adults",
                },
                "dictionaries": getattr(response, "dictionaries", {}),
            }
        except ResponseError:
            logger.exception("Amadeus 검색 실패")
            return {
                "success": False,
                "data": [],
                "status_code": 502,
                "message": "항공권 공급자 검색에 실패했습니다.",
            }
        except Exception:
            logger.exception("항공권 가격 처리 실패")
            return {
                "success": False,
                "data": [],
                "status_code": 502,
                "message": "항공권 가격을 확인하지 못했습니다. 잠시 후 다시 시도해주세요.",
            }

    async def search_cheapest_dates(
        self,
        origin,
        destination,
        departure_date,
        duration=None,
        one_way=False,
        flexibility_days=7,
        adults=1,
        currency="KRW",
        non_stop=False,
    ):
        center = date.fromisoformat(departure_date)
        results, errors = [], 0
        for offset in range(-flexibility_days, flexibility_days + 1):
            departure = center + timedelta(days=offset)
            if departure <= date.today():
                continue
            returning = (
                None
                if one_way
                else (departure + timedelta(days=(duration or 4) - 1)).isoformat()
            )
            result = await self.search_flight_offers(
                origin,
                destination,
                departure.isoformat(),
                returning,
                adults,
                currency,
                non_stop,
            )
            if not result["success"]:
                errors += 1
                continue
            if result["data"]:
                offer = min(result["data"], key=lambda o: Decimal(o["price"]["total"]))
                results.append(
                    {
                        "origin": origin,
                        "destination": destination,
                        "departureDate": departure.isoformat(),
                        "returnDate": returning,
                        "price": offer["price"],
                        "offer": offer,
                    }
                )
        if not results and errors:
            return {
                "success": False,
                "data": [],
                "message": "날짜별 항공권 조회에 실패했습니다.",
                "status_code": 502,
            }
        return {
            "success": True,
            "data": sorted(results, key=lambda x: Decimal(x["price"]["total"])),
            "meta": {
                "source": self.source,
                "is_demo": self.source == "demo",
                "failed_searches": errors,
            },
        }

    async def get_airport_info(self, iata_code):
        if not self.is_active:
            return {
                "success": True,
                "data": {"iataCode": iata_code},
                "meta": {"source": "local", "is_demo": False},
            }
        try:
            response = await asyncio.to_thread(
                self.client.reference_data.locations.get,
                keyword=iata_code,
                subType="AIRPORT",
            )
            return {"success": True, "data": response.data[0] if response.data else {}}
        except ResponseError:
            return {
                "success": False,
                "data": {},
                "message": "공항 조회에 실패했습니다.",
                "status_code": 502,
            }

    async def _convert_prices_to_krw(self, data, from_currency):
        rates = await self.exchange_rate_service.get_current_rates([from_currency])
        rate = next(
            (r.base_rate for r in rates.rates if r.currency_code == from_currency), None
        )
        if not rates.success or not rate or rate <= 0:
            raise ValueError("원화 환율을 확인하지 못했습니다.")
        rate_date = next(
            r.exchange_date for r in rates.rates if r.currency_code == from_currency
        )
        for offer in data:
            offer["original_price"] = deepcopy(offer["price"])
            offer["exchange_rate"] = {
                "from_currency": from_currency,
                "to_currency": "KRW",
                "rate": rate,
                "date": rate_date,
            }
            if offer["price"].get("currency") != from_currency:
                raise ValueError("환산 전 통화 불일치")
            self._convert_price_dict(offer["price"], rate)
            for traveler in offer.get("travelerPricings", []):
                self._convert_price_dict(traveler["price"], rate)
        return data

    def _convert_price_dict(self, price_dict, rate):
        for key in ("total", "base", "grandTotal"):
            if key in price_dict:
                price_dict[key] = str(
                    (Decimal(str(price_dict[key])) * Decimal(str(rate))).quantize(
                        Decimal("1"), rounding=ROUND_HALF_UP
                    )
                )
        for fee in price_dict.get("fees", []) + price_dict.get("taxes", []):
            if "amount" in fee:
                fee["amount"] = str(
                    (Decimal(str(fee["amount"])) * Decimal(str(rate))).quantize(
                        Decimal("1"), rounding=ROUND_HALF_UP
                    )
                )
        price_dict["currency"] = "KRW"

    async def _get_dummy_flight_offers(
        self, origin, destination, departure_date, return_date, adults, currency
    ):
        # Explicit demo mode only; these offers are never stored as historical fares.
        itineraries = [
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
                        "carrierCode": "DEMO",
                        "number": "001",
                    }
                ],
            }
        ]
        if return_date:
            itineraries.append(
                {
                    "duration": "PT2H30M",
                    "segments": [
                        {
                            "departure": {
                                "iataCode": destination,
                                "at": f"{return_date}T17:00:00",
                            },
                            "arrival": {
                                "iataCode": origin,
                                "at": f"{return_date}T19:30:00",
                            },
                            "carrierCode": "DEMO",
                            "number": "002",
                        }
                    ],
                }
            )
        unit = {"KRW": 280000, "JPY": 28000, "USD": 200, "EUR": 180}.get(currency, 200)
        return {
            "success": True,
            "data": [
                {
                    "id": f"demo-{origin}-{destination}-{departure_date}",
                    "source": "demo",
                    "itineraries": itineraries,
                    "price": {"total": str(unit * adults), "currency": currency},
                    "travelerPricings": [
                        {
                            "travelerId": str(i + 1),
                            "price": {"total": str(unit), "currency": currency},
                        }
                        for i in range(adults)
                    ],
                }
            ],
            "meta": {"source": "demo", "is_demo": True},
        }
