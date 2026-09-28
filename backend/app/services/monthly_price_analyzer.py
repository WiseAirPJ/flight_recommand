"""Sampled monthly fares, using the same provider/conditions as individual searches."""

import asyncio
import calendar
from datetime import date, datetime, timedelta, timezone

from app.config.settings import settings
from app.models.flight_requests import MonthlySearchRequest
from app.services.amadeus_service import AmadeusService
from app.services.cache_service import CacheService
from app.services.region_service import RegionService
from app.utils.cache_keys import monthly_search_key


class MonthlyPriceAnalyzer:
    def __init__(self, amadeus_service=None, cache_service=None):
        self.amadeus_service = amadeus_service or AmadeusService()
        self.cache_service = cache_service or CacheService()
        self.japan_regions = RegionService().regions_data

    def _get_search_dates(self, target_year, target_month):
        first = max(
            date(target_year, target_month, 1), date.today() + timedelta(days=1)
        )
        last = date(
            target_year, target_month, calendar.monthrange(target_year, target_month)[1]
        )
        dates = []
        while first <= last:
            dates.append(first)
            first += timedelta(days=settings.MONTHLY_SAMPLE_STEP)
        return dates

    async def get_monthly_cheapest_dates(
        self,
        target_year,
        target_month,
        origin="ICN",
        trip_duration=4,
        adults=1,
        currency="KRW",
        non_stop=False,
        force_refresh=False,
        progress=None,
        save_progress=None,
        heartbeat=None,
    ):
        request = MonthlySearchRequest(
            year=target_year,
            month=target_month,
            origin=origin,
            duration_days=trip_duration,
            adults=adults,
            currency=currency,
            non_stop=non_stop,
        )
        source = self.amadeus_service.source
        key = monthly_search_key(request, source)
        cached = (
            None
            if force_refresh
            else await asyncio.to_thread(self.cache_service.get_cache, key)
        )
        if cached is not None:
            cached["data"]["from_cache"] = True
            return cached
        dates = self._get_search_dates(request.year, request.month)
        if progress is not None:
            started = progress.get("started_at")
            now = datetime.now(timezone.utc)
            expired = (
                not started
                or (now - datetime.fromisoformat(started)).total_seconds()
                >= settings.MONTHLY_CACHE_TTL
            )
            if progress.get("day") != date.today().isoformat() or expired:
                progress.clear()
                progress.update(
                    day=date.today().isoformat(), started_at=now.isoformat(), quotes={}
                )
            progress.setdefault("dates", [day.isoformat() for day in dates])
            dates = [
                date.fromisoformat(day)
                for day in progress["dates"]
                if day > date.today().isoformat()
            ]
        regions, failures, searches, history_failures = {}, 0, 0, 0
        for region_id, region in self.japan_regions.items():
            options = []
            # Scope is explicitly listed: representative airports plus Tokyo Haneda.
            destinations = [region["main_airport"]]
            if region_id == "kanto":
                destinations.append("HND")
            for destination in destinations:
                for departure in dates:
                    return_date = departure + timedelta(days=request.duration_days - 1)
                    if heartbeat:
                        await heartbeat()
                    conditions = dict(
                        origin=request.origin,
                        destination=destination,
                        departure_date=departure.isoformat(),
                        return_date=return_date.isoformat(),
                        adults=request.adults,
                        currency=request.currency,
                        non_stop=request.non_stop,
                    )
                    quote_key = f"{destination}:{departure.isoformat()}"
                    result = (
                        progress["quotes"].get(quote_key)
                        if progress is not None
                        else None
                    )
                    if result is None:
                        result = await self.amadeus_service.search_flight_offers(
                            **conditions
                        )
                    elif (
                        source == "amadeus"
                        and result.get("data")
                        and not result.get("meta", {}).get("history_saved")
                    ):
                        await self.amadeus_service.save_history(result, **conditions)
                    if progress is not None and result.get("success"):
                        progress["quotes"][quote_key] = result
                        await save_progress(progress)
                    if (
                        source == "amadeus"
                        and result.get("data")
                        and not result.get("meta", {}).get("history_saved")
                    ):
                        history_failures += 1
                    searches += 1
                    if not result["success"]:
                        failures += 1
                        continue
                    offers = [
                        offer
                        for offer in result["data"]
                        if offer.get("price", {}).get("currency") == request.currency
                    ]
                    if not offers:
                        continue
                    offer = min(offers, key=lambda item: float(item["price"]["total"]))
                    options.append(
                        {
                            "departure_date": departure.isoformat(),
                            "return_date": return_date.isoformat(),
                            "duration_days": request.duration_days,
                            "airport": destination,
                            "price": float(offer["price"]["total"]),
                            "currency": request.currency,
                            "adults": request.adults,
                            "observed_at": result.get("meta", {}).get("observed_at"),
                            "offer_id": offer.get("id"),
                            "source": source,
                            "is_demo": source == "demo",
                            "display_price_is_estimate": result.get("meta", {}).get(
                                "display_price_is_estimate", False
                            ),
                            "baggage_policy": "provider_terms",
                            "price_basis": "total_for_all_adults",
                        }
                    )
            if options:
                options.sort(key=lambda option: option["price"])
                prices = [option["price"] for option in options]
                regions[region_id] = {
                    "region_name": region["name"],
                    "airport": options[0]["airport"],
                    "cheapest_option": options[0],
                    "all_options": options if progress is not None else options[:5],
                    "price_statistics": {
                        "min_price": min(prices),
                        "max_price": max(prices),
                        "avg_price": round(sum(prices) / len(prices), 2),
                        "price_samples": len(prices),
                    },
                }
        result = {
            "success": failures == 0 or failures < searches,
            "message": "조회한 날짜 중 최저가입니다. 예약 시 가격과 수하물 조건을 다시 확인하세요.",
            "data": {
                **request.model_dump(),
                "trip_duration": request.duration_days,
                "regions": regions,
                "total_regions": len(regions),
                "from_cache": False,
                "source": source,
                "is_demo": source == "demo",
                "partial": failures > 0 or history_failures > 0,
                "history_failures": history_failures,
                "failed_searches": failures,
                "total_searches": searches,
                "price_basis": "total_for_all_adults",
                "coverage": "sampled_dates",
                "sample_step_days": settings.MONTHLY_SAMPLE_STEP,
                "sampled_dates": [day.isoformat() for day in dates],
                "searched_airports": [
                    r["main_airport"] for r in self.japan_regions.values()
                ]
                + ["HND"],
                "searched_at": datetime.now(timezone.utc).isoformat(),
            },
        }
        if searches and failures == searches:
            result.update(
                status_code=503 if source == "unavailable" else 502,
                message="항공권 공급자 조회에 실패했습니다.",
            )
        result["data"]["cache_saved"] = False
        if (
            result["success"]
            and not failures
            and not history_failures
            and progress is None
        ):
            result["data"]["cache_saved"] = await asyncio.to_thread(
                self.cache_service.set_cache, key, result, settings.MONTHLY_CACHE_TTL
            )
        return result

    async def get_current_month_cheapest(self, origin="ICN", adults=1):
        today = date.today()
        return await self.get_monthly_cheapest_dates(
            today.year, today.month, origin, adults=adults
        )

    async def get_next_month_cheapest(self, origin="ICN", adults=1):
        next_month = (date.today().replace(day=1) + timedelta(days=32)).replace(day=1)
        return await self.get_monthly_cheapest_dates(
            next_month.year, next_month.month, origin, adults=adults
        )


async def search_monthly_cheapest_dates(year, month, origin="ICN", duration=4):
    return await MonthlyPriceAnalyzer().get_monthly_cheapest_dates(
        year, month, origin, duration
    )


async def get_this_month_cheapest(origin="ICN"):
    return await MonthlyPriceAnalyzer().get_current_month_cheapest(origin)
