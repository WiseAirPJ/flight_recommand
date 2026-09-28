from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy import select

from app.config.settings import settings
from app.core.database import SessionLocal
from app.db_models.price_observation import PriceObservation
from app.services.amadeus_service import AmadeusService
from app.services.exchange_rate_service import ExchangeRate, ExchangeRateResponse


def future(days=30):
    return (date.today() + timedelta(days=days)).isoformat()


def sdk(offers):
    client = Mock()
    client.shopping.flight_offers_search.get.return_value = SimpleNamespace(
        data=offers, dictionaries={}
    )
    return client


def offer(currency="USD", total="123.45"):
    return {
        "id": "one",
        "price": {"currency": currency, "total": total},
        "itineraries": [],
    }


def test_service_explicit_client():
    client = sdk([])
    assert AmadeusService(client=client).client is client
    assert AmadeusService().source == "unavailable"


@pytest.mark.asyncio
async def test_provider_required_unless_explicit_demo(monkeypatch):
    service = AmadeusService()
    assert (await service.search_flight_offers("PUS", "KIX", future()))[
        "status_code"
    ] == 503
    monkeypatch.setattr(settings, "ENABLE_DUMMY_FALLBACK", True)
    result = await service.search_flight_offers(
        "PUS", "KIX", future(), future(33), adults=2
    )
    assert result["meta"]["is_demo"]
    assert len(result["data"][0]["itineraries"]) == 2
    assert result["data"][0]["price"]["total"] == "560000"
    with SessionLocal() as session:
        assert session.scalars(select(PriceObservation)).all() == []


@pytest.mark.asyncio
async def test_production_quote_persists_conditions(monkeypatch):
    monkeypatch.setattr(settings, "AMADEUS_HOSTNAME", "production")
    client = sdk([offer()])
    result = await AmadeusService(client=client).search_flight_offers(
        "CJJ", "NRT", future(), future(33), adults=3, currency="USD", non_stop=True
    )
    assert result["success"] and result["meta"]["history_saved"]
    params = client.shopping.flight_offers_search.get.call_args.kwargs
    assert (params["adults"], params["nonStop"], params["returnDate"]) == (
        3,
        True,
        future(33),
    )
    with SessionLocal() as session:
        row = session.scalars(select(PriceObservation)).one()
        assert (row.origin, row.currency, row.adults) == ("CJJ", "USD", 3)
        assert str(row.total_price) == "123.45"
        assert row.search_conditions["non_stop"] is True
        assert row.observed_at and row.return_date == date.fromisoformat(future(33))


@pytest.mark.asyncio
async def test_test_provider_not_historical():
    result = await AmadeusService(client=sdk([offer()])).search_flight_offers(
        "ICN", "NRT", future(), currency="USD"
    )
    assert result["success"] and not result["meta"]["history_saved"]
    with SessionLocal() as session:
        assert session.scalars(select(PriceObservation)).all() == []


@pytest.mark.asyncio
async def test_krw_conversion_and_original_price():
    rate = ExchangeRate("JPY", "엔", 9.5, 0, 0, 0, 0, "20260928")
    exchange = Mock(
        get_current_rates=AsyncMock(
            return_value=ExchangeRateResponse(True, [rate], "now")
        )
    )
    raw = offer("JPY", "10000")
    raw["travelerPricings"] = [
        {"price": {"currency": "JPY", "total": "10000", "taxes": [{"amount": "100"}]}}
    ]
    client = sdk([raw])
    result = await AmadeusService(
        client=client, exchange_rate_service=exchange
    ).search_flight_offers("ICN", "NRT", future())
    converted = result["data"][0]
    assert converted["price"] == {"currency": "KRW", "total": "95000"}
    assert converted["travelerPricings"][0]["price"]["taxes"][0]["amount"] == "950"
    assert converted["original_price"]["currency"] == "JPY"
    assert result["meta"]["display_price_is_estimate"]
    assert raw["price"]["currency"] == "JPY"


@pytest.mark.asyncio
async def test_missing_exchange_never_relabels_price():
    exchange = Mock(
        get_current_rates=AsyncMock(return_value=ExchangeRateResponse(False, [], "now"))
    )
    result = await AmadeusService(
        client=sdk([offer("JPY")]), exchange_rate_service=exchange
    ).search_flight_offers("ICN", "NRT", future())
    assert not result["success"] and result["data"] == []


@pytest.mark.asyncio
@pytest.mark.parametrize("price", ["NaN", "-1", "0", "Infinity"])
async def test_invalid_prices_fail(price):
    result = await AmadeusService(
        client=sdk([offer(total=price)])
    ).search_flight_offers("ICN", "NRT", future(), currency="USD")
    assert not result["success"]


@pytest.mark.asyncio
async def test_provider_failure_does_not_become_demo(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_DUMMY_FALLBACK", True)
    client = sdk([])
    client.shopping.flight_offers_search.get.side_effect = RuntimeError("unavailable")
    result = await AmadeusService(client=client).search_flight_offers(
        "ICN", "NRT", future()
    )
    assert result["status_code"] == 502 and not result["success"]


@pytest.mark.asyncio
async def test_cheapest_dates_conditions(monkeypatch):
    service = AmadeusService()
    service.search_flight_offers = AsyncMock(
        return_value={"success": True, "data": [offer()]}
    )
    result = await service.search_cheapest_dates(
        "PUS", "KIX", future(), duration=4, flexibility_days=1, adults=2, currency="USD"
    )
    assert len(result["data"]) == 3
    for call in service.search_flight_offers.call_args_list:
        _, _, departure, returning, adults, currency, _ = call.args
        assert (date.fromisoformat(returning) - date.fromisoformat(departure)).days == 3
        assert (adults, currency) == (2, "USD")
    service.search_flight_offers.reset_mock()
    await service.search_cheapest_dates(
        "PUS", "KIX", future(), one_way=True, flexibility_days=1
    )
    assert all(
        call.args[3] is None for call in service.search_flight_offers.call_args_list
    )
