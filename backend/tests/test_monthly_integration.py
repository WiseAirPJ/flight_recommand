from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient

from app.api.v1.regions import get_monthly_analyzer
from app.config.settings import settings
from app.main import app
from app.services.cache_service import CacheService
from app.services.monthly_price_analyzer import MonthlyPriceAnalyzer


def target_month():
    day = (date.today().replace(day=1) + timedelta(days=32)).replace(day=1)
    return day.year, day.month


def provider():
    async def search(**kwargs):
        amount = (100 if kwargs["destination"] == "HND" else 200) * kwargs["adults"]
        return {
            "success": True,
            "data": [
                {
                    "id": "quote",
                    "price": {"currency": kwargs["currency"], "total": str(amount)},
                }
            ],
            "meta": {
                "source": "amadeus_test",
                "observed_at": "2026-09-28T00:00:00+00:00",
            },
        }

    return SimpleNamespace(
        source="amadeus_test", search_flight_offers=AsyncMock(side_effect=search)
    )


@pytest.mark.asyncio
async def test_monthly_uses_conditions_cheapest_airport_and_cache():
    service = provider()
    analyzer = MonthlyPriceAnalyzer(amadeus_service=service)
    year, month = target_month()
    first = await analyzer.get_monthly_cheapest_dates(
        year, month, "PUS", adults=2, currency="USD", non_stop=True
    )
    data = first["data"]
    assert data["coverage"] == "sampled_dates" and data["total_regions"] == 6
    assert data["regions"]["kanto"]["airport"] == "HND"
    assert data["regions"]["kanto"]["cheapest_option"]["price"] == 200
    for call in service.search_flight_offers.call_args_list:
        params = call.kwargs
        assert (
            params["origin"],
            params["adults"],
            params["currency"],
            params["non_stop"],
        ) == ("PUS", 2, "USD", True)
        assert (
            date.fromisoformat(params["return_date"])
            - date.fromisoformat(params["departure_date"])
        ).days == 3
    count = service.search_flight_offers.call_count
    cached = await analyzer.get_monthly_cheapest_dates(
        year, month, "PUS", adults=2, currency="USD", non_stop=True
    )
    assert (
        cached["data"]["from_cache"]
        and service.search_flight_offers.call_count == count
    )
    assert not first["data"]["from_cache"]
    for change in [
        {"adults": 3},
        {"currency": "JPY"},
        {"origin": "CJJ"},
        {"trip_duration": 5},
        {"non_stop": False},
    ]:
        params = {
            "origin": "PUS",
            "adults": 2,
            "currency": "USD",
            "non_stop": True,
            **change,
        }
        await analyzer.get_monthly_cheapest_dates(year, month, **params)
        assert service.search_flight_offers.call_count > count
        count = service.search_flight_offers.call_count


@pytest.mark.asyncio
async def test_empty_dates_safe_and_month_boundary_allowed(monkeypatch):
    analyzer = MonthlyPriceAnalyzer(amadeus_service=provider())
    year, month = target_month()
    monkeypatch.setattr(analyzer, "_get_search_dates", lambda *_: [])
    result = await analyzer.get_monthly_cheapest_dates(year, month)
    assert result["success"] and result["data"]["regions"] == {}
    assert analyzer._get_search_dates(year, month) == []
    last = (date(year, month, 1) + timedelta(days=32)).replace(day=1) - timedelta(
        days=1
    )
    monkeypatch.setattr(analyzer, "_get_search_dates", lambda *_: [last])
    result = await analyzer.get_monthly_cheapest_dates(year, month, force_refresh=True)
    option = result["data"]["regions"]["kanto"]["cheapest_option"]
    assert date.fromisoformat(option["return_date"]).month != month


def test_past_month_date_generator_is_empty():
    analyzer = MonthlyPriceAnalyzer(amadeus_service=provider())
    assert analyzer._get_search_dates(2000, 1) == []


@pytest.mark.asyncio
async def test_provider_failure_not_empty_success_or_cached():
    service = provider()
    service.search_flight_offers = AsyncMock(
        return_value={"success": False, "data": []}
    )
    analyzer = MonthlyPriceAnalyzer(amadeus_service=service)
    result = await analyzer.get_monthly_cheapest_dates(*target_month())
    assert not result["success"] and result["status_code"] == 502
    assert not CacheService._shared_memory_cache


@pytest.mark.asyncio
async def test_partial_results_disclosed_and_not_cached():
    service = provider()
    original = service.search_flight_offers.side_effect

    async def partial(**kwargs):
        return (
            {"success": False, "data": []}
            if kwargs["destination"] == "CTS"
            else await original(**kwargs)
        )

    service.search_flight_offers.side_effect = partial
    result = await MonthlyPriceAnalyzer(
        amadeus_service=service
    ).get_monthly_cheapest_dates(*target_month())
    assert result["success"] and result["data"]["partial"]
    assert result["data"]["failed_searches"] > 0
    assert not CacheService._shared_memory_cache


def test_map_endpoint_preserves_metadata_and_validates():
    analyzer = MonthlyPriceAnalyzer(amadeus_service=provider())
    app.dependency_overrides[get_monthly_analyzer] = lambda: analyzer
    try:
        with TestClient(app) as client:
            year, month = target_month()
            response = client.get(
                "/api/v1/regions/lowest-prices",
                params={
                    "year": year,
                    "month": month,
                    "origin": "CJJ",
                    "adults": 2,
                    "currency": "USD",
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["meta"]["origin"] == "CJJ"
            assert data["data"]["kanto"]["currency"] == "USD"
            assert data["data"]["kanto"]["price_basis"] == "total_for_all_adults"
            assert (
                client.get(
                    "/api/v1/regions/lowest-prices?year=2000&month=1"
                ).status_code
                == 422
            )
            assert (
                client.get("/api/v1/regions/lowest-prices?origin=잘못됨").status_code
                == 422
            )
            assert (
                client.post(
                    "/api/v1/regions/monthly-analysis",
                    json={"year": year, "month": month, "origin": "PUS"},
                ).status_code
                == 200
            )
            assert (
                client.get(
                    f"/api/v1/regions/monthly-analysis/{year}/{month}"
                ).status_code
                == 200
            )
            assert (
                client.get("/api/v1/regions/monthly-analysis/2000/1").status_code == 422
            )
            assert client.get("/api/v1/regions/").json()["data"]["kanto"]["coordinates"]
            assert client.get("/api/v1/regions/kanto/airports").status_code == 200
            assert client.get("/api/v1/regions/missing/airports").status_code == 404
            codes = {
                row["iata"]
                for row in client.get("/api/v1/regions/departure-airports").json()[
                    "data"
                ]
            }
            assert {"ICN", "PUS", "CJJ", "TAE", "GMP"} <= codes
    finally:
        app.dependency_overrides.pop(get_monthly_analyzer, None)


def test_map_query_rolls_past_month_to_next_year(monkeypatch):
    class FixedDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 12, 15)

    import app.api.v1.regions as api

    monkeypatch.setattr(api, "date", FixedDate)
    request_seen = []

    async def capture(request, analyzer):
        request_seen.append(request)
        return {"data": {"regions": {}, "searched_at": "now"}, "message": "ok"}

    monkeypatch.setattr(api, "_analyze", capture)
    # Month model still sees real time, so choose a supported next year.
    if date.today().year != 2026:
        monkeypatch.setattr("app.models.flight_requests.date", FixedDate)
    with TestClient(app) as client:
        assert client.get("/api/v1/regions/lowest-prices?month=1").status_code == 200
    assert (request_seen[0].year, request_seen[0].month) == (2027, 1)


def test_legacy_monthly_query_duration_alias():
    analyzer = MonthlyPriceAnalyzer(amadeus_service=provider())
    app.dependency_overrides[get_monthly_analyzer] = lambda: analyzer
    year, month = target_month()
    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/regions/monthly-analysis",
                params={"year": year, "month": month, "duration": 5},
            )
            assert (
                response.status_code == 200
                and response.json()["data"]["duration_days"] == 5
            )
            assert (
                client.get(
                    f"/api/v1/regions/monthly-analysis/{year}/{month}?duration=5&duration_days=4"
                ).status_code
                == 422
            )
            assert client.get("/api/v1/regions/health").status_code == 200
            assert (
                client.get("/api/v1/regions/statistics").json()["data"]["total_regions"]
                == 6
            )
    finally:
        app.dependency_overrides.pop(get_monthly_analyzer, None)
