from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from celery.exceptions import Retry
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.api.v1.regions import get_monthly_search_service
from app.config.settings import settings
from app.core.database import Base, SessionLocal
from app.db_models.monthly_search import MonthlySearch
from app.db_models.price_observation import PriceObservation
from app.main import app
from app.models.flight_requests import MonthlySearchRequest
from app.services.amadeus_service import AmadeusService
from app.services.monthly_price_analyzer import MonthlyPriceAnalyzer
from app.services.monthly_search_service import LeaseLost, MonthlySearchService
from app.services.price_history_service import PriceHistoryService
from app.tasks import monthly_data_collection as tasks


def search_request(**changes):
    day = (date.today().replace(day=1) + timedelta(days=32)).replace(day=1)
    return MonthlySearchRequest(
        **{"year": day.year, "month": day.month, "origin": "PUS", **changes}
    )


def result_for(request):
    return {
        "success": True,
        "message": "ok",
        "data": {
            **request.model_dump(),
            "regions": {},
            "searched_at": datetime.now().isoformat(),
            "partial": False,
            "source": "demo",
            "is_demo": True,
        },
    }


@pytest.fixture
def store():
    clock = SimpleNamespace(now=datetime.utcnow())
    enqueue = Mock()
    service = MonthlySearchService(
        source="demo", enqueue=enqueue, clock=lambda: clock.now
    )
    return service, clock, enqueue


def complete(store, request):
    service, clock, enqueue = store
    service.request(request)
    key, token = enqueue.call_args.args
    assert service.claim(key, token)
    service.complete(key, token, result_for(request))
    return key, token


def test_cold_requests_enqueue_once_and_all_conditions_survive(store):
    service, _, enqueue = store
    request = search_request(adults=3, duration_days=6, non_stop=True, currency="USD")
    first = service.request(request)
    second = service.request(request)
    assert first["status_code"] == second["status_code"] == 202
    assert first["data"]["job_id"] == second["data"]["job_id"]
    enqueue.assert_called_once()
    key, token = enqueue.call_args.args
    payload, source, checkpoint = service.claim(key, token)
    assert payload == request.model_dump() and source == "demo" and checkpoint == {}
    assert service.claim(key, token) is None


def test_independent_instances_race_to_one_job(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'jobs.db'}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    enqueue = Mock()
    request = search_request()

    def call(_):
        return MonthlySearchService(factory, enqueue=enqueue, source="demo").request(
            request
        )["data"]["job_id"]

    try:
        with ThreadPoolExecutor(max_workers=8) as pool:
            ids = list(pool.map(call, range(16)))
        assert len(set(ids)) == 1
        enqueue.assert_called_once()
    finally:
        engine.dispose()


def test_stale_results_survive_refresh_failure_and_have_age_limit(store):
    service, clock, enqueue = store
    request = search_request()
    complete(store, request)
    assert service.request(request)["data"]["status"] == "ready"
    enqueue.reset_mock()
    clock.now += timedelta(seconds=settings.MONTHLY_CACHE_TTL + 1)
    stale = service.request(request)
    assert stale["status_code"] == 200 and stale["data"]["stale"]
    assert stale["data"]["refresh_status"] == "pending"
    key, token = enqueue.call_args.args
    service.fail(key, token, "broker offline")
    stale = service.request(request)
    assert (
        stale["status_code"] == 200
        and stale["data"]["refresh_error"] == "broker offline"
    )
    assert enqueue.call_count == 1
    clock.now += timedelta(seconds=settings.MONTHLY_STALE_TTL)
    expired = service.request(request)
    assert expired["status_code"] == 202 and not expired["data"]["from_cache"]


def test_enqueue_failure_has_cooldown_and_does_not_claim_success(store):
    service, clock, enqueue = store
    enqueue.side_effect = RuntimeError("broker offline")
    failed = service.request(search_request())
    assert failed["status_code"] == 503 and not failed["success"]
    assert failed["data"]["status"] == "failed"
    service.request(search_request())
    enqueue.assert_called_once()
    clock.now += timedelta(seconds=61)
    enqueue.side_effect = None
    assert service.request(search_request())["status_code"] == 202
    assert enqueue.call_count == 2


def test_expired_worker_cannot_overwrite_replacement_job(store):
    service, clock, enqueue = store
    request = search_request()
    service.request(request)
    key, old_token = enqueue.call_args.args
    service.claim(key, old_token)
    service.checkpoint(
        key, old_token, {"day": date.today().isoformat(), "quotes": {"done": {}}}
    )
    clock.now += timedelta(seconds=settings.MONTHLY_JOB_LEASE_SECONDS + 1)
    service.request(request)
    _, new_token = enqueue.call_args.args
    assert new_token != old_token
    assert service.claim(key, old_token) is None
    with pytest.raises(LeaseLost):
        service.complete(key, old_token, result_for(request))
    assert service.claim(key, new_token)[2]["quotes"] == {"done": {}}


def test_policy_and_search_conditions_have_distinct_jobs(store, monkeypatch):
    service, _, enqueue = store
    baseline = service.request(search_request())["data"]["job_id"]
    for changes in [
        {"origin": "CJJ"},
        {"adults": 2},
        {"currency": "USD"},
        {"duration_days": 5},
        {"non_stop": True},
    ]:
        assert service.request(search_request(**changes))["data"]["job_id"] != baseline
    monkeypatch.setattr(settings, "MONTHLY_SAMPLE_STEP", 2)
    assert service.request(search_request())["data"]["job_id"] != baseline
    service.source = "amadeus_test"
    assert service.request(search_request())["data"]["job_id"] != baseline
    assert enqueue.call_count == 8


def test_retry_rejects_previous_delivery_and_owner(store):
    service, _, enqueue = store
    service.request(search_request())
    key, old_token = enqueue.call_args.args
    service.claim(key, old_token)
    new_token = service.retry(key, old_token, delay=60)
    assert service.claim(key, old_token) is None
    assert new_token and new_token != old_token
    assert service.claim(key, new_token) is not None
    with pytest.raises(LeaseLost):
        service.heartbeat(key, old_token)
    with pytest.raises(LeaseLost):
        service.complete(key, old_token, result_for(search_request()))
    service.fail(key, old_token, "late failure")
    service.complete(key, new_token, result_for(search_request()))
    assert service.request(search_request())["data"]["status"] == "ready"


def test_replacement_keeps_previous_day_checkpoint_for_history_recovery(store):
    service, clock, enqueue = store
    service.request(search_request())
    key, token = enqueue.call_args.args
    service.claim(key, token)
    checkpoint = {
        "day": (date.today() - timedelta(days=1)).isoformat(),
        "quotes": {"NRT:old": {"meta": {"history_saved": False}}},
    }
    service.checkpoint(key, token, checkpoint)
    clock.now += timedelta(seconds=settings.MONTHLY_JOB_LEASE_SECONDS + 1)
    service.request(search_request())
    _, replacement = enqueue.call_args.args
    assert service.claim(key, replacement)[2] == checkpoint


def test_map_cold_response_is_202_without_calling_provider(store, monkeypatch):
    service, _, enqueue = store
    provider = AsyncMock(side_effect=AssertionError("API must not collect quotes"))
    monkeypatch.setattr(AmadeusService, "search_flight_offers", provider)
    app.dependency_overrides[get_monthly_search_service] = lambda: service
    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/regions/lowest-prices", params=search_request().model_dump()
            )
            assert response.status_code == 202
            assert response.json()["data"] == {}
            assert response.json()["meta"]["status"] == "pending"
            assert response.json()["last_updated"] is None
            enqueue.assert_called_once()
            provider.assert_not_called()
    finally:
        app.dependency_overrides.pop(get_monthly_search_service, None)


def test_worker_retries_only_failed_quote_and_fences_duplicate_delivery(
    store, monkeypatch
):
    service, _, enqueue = store
    request = search_request(currency="USD")
    service.request(request)
    key, token = enqueue.call_args.args
    failed_once = set()

    async def search(**kwargs):
        destination = kwargs["destination"]
        if destination == "CTS" and destination not in failed_once:
            failed_once.add(destination)
            return {"success": False, "data": []}
        return {"success": True, "data": [], "meta": {}}

    provider = SimpleNamespace(
        source="demo",
        search_flight_offers=AsyncMock(side_effect=search),
        save_history=AsyncMock(),
    )
    analyzer = MonthlyPriceAnalyzer(amadeus_service=provider)
    monkeypatch.setattr(
        analyzer, "_get_search_dates", lambda *_: [date(request.year, request.month, 1)]
    )
    monkeypatch.setattr(tasks, "MonthlySearchService", lambda: service)
    monkeypatch.setattr(tasks, "MonthlyPriceAnalyzer", lambda: analyzer)
    monkeypatch.setattr(tasks, "configured_source", lambda: "demo")
    monkeypatch.setattr(tasks.run_monthly_search, "retry", Mock(side_effect=Retry()))
    with pytest.raises(Retry):
        tasks.run_monthly_search.run(key, token)
    assert provider.search_flight_offers.call_count == 7
    with SessionLocal() as session:
        row = session.get(MonthlySearch, key)
        assert row.status == "pending" and len(row.checkpoint["quotes"]) == 6
    retry_args = tasks.run_monthly_search.retry.call_args.kwargs["args"]
    assert retry_args[0] == key and retry_args[1] != token
    assert tasks.run_monthly_search.run(key, token)["status"] == "superseded"
    assert tasks.run_monthly_search.run(*retry_args)["status"] == "ready"
    assert provider.search_flight_offers.call_count == 8
    assert tasks.run_monthly_search.run(key, token)["status"] == "superseded"
    assert provider.search_flight_offers.call_count == 8
    assert service.request(request)["data"]["status"] == "ready"


@pytest.mark.asyncio
async def test_history_failure_retries_saved_quotes_without_provider_calls(monkeypatch):
    request = search_request(currency="USD")
    history = PriceHistoryService()
    persist = Mock(wraps=history.record_offers)
    history.record_offers = persist
    persist.side_effect = RuntimeError("temporary database failure")
    client = Mock()
    client.shopping.flight_offers_search.get.return_value = SimpleNamespace(
        data=[{"id": "same", "price": {"currency": "USD", "total": "100"}}],
        dictionaries={},
    )
    monkeypatch.setattr(settings, "AMADEUS_HOSTNAME", "production")
    provider = AmadeusService(client=client, history_service=history)
    analyzer = MonthlyPriceAnalyzer(amadeus_service=provider)
    monkeypatch.setattr(
        analyzer, "_get_search_dates", lambda *_: [date(request.year, request.month, 1)]
    )
    progress = {}
    params = dict(
        currency="USD", force_refresh=True, progress=progress, save_progress=AsyncMock()
    )
    first = await analyzer.get_monthly_cheapest_dates(
        request.year, request.month, **params
    )
    assert first["data"]["history_failures"] == 7 and first["data"]["partial"]
    assert len(progress["quotes"]) == 7
    persist.side_effect = None
    second = await analyzer.get_monthly_cheapest_dates(
        request.year, request.month, **params
    )
    assert not second["data"]["partial"] and second["data"]["history_failures"] == 0
    assert client.shopping.flight_offers_search.get.call_count == 7
    with SessionLocal() as session:
        assert len(session.scalars(select(PriceObservation)).all()) == 7
    # Replaying a captured observation is idempotent, even after an uncertain commit.
    for quote in progress["quotes"].values():
        quote["meta"]["history_saved"] = False
    await analyzer.get_monthly_cheapest_dates(request.year, request.month, **params)
    with SessionLocal() as session:
        assert len(session.scalars(select(PriceObservation)).all()) == 7


@pytest.mark.asyncio
@pytest.mark.parametrize("expiry", ["ttl", "day"])
async def test_expired_checkpoint_preserves_unsaved_observations(monkeypatch, expiry):
    request = search_request(adults=2, duration_days=5, currency="USD", non_stop=True)
    departure = date(request.year, request.month, 1)
    observed = datetime.now(timezone.utc) - timedelta(hours=2)
    quote = {
        "success": True,
        "data": [{"id": "captured", "price": {"currency": "USD", "total": "100"}}],
        "meta": {
            "source": "amadeus",
            "observed_at": observed.isoformat(),
            "history_saved": False,
        },
    }
    progress = {
        "day": (date.today() - timedelta(days=expiry == "day")).isoformat(),
        "started_at": (
            observed if expiry == "ttl" else datetime.now(timezone.utc)
        ).isoformat(),
        "dates": [departure.isoformat()],
        "quotes": {f"NRT:{departure.isoformat()}": quote},
    }
    captured = deepcopy(progress)
    history = PriceHistoryService()
    persist = Mock(wraps=history.record_offers, side_effect=RuntimeError("offline"))
    history.record_offers = persist
    client = Mock()
    client.shopping.flight_offers_search.get.return_value = SimpleNamespace(
        data=[], dictionaries={}
    )
    monkeypatch.setattr(settings, "AMADEUS_HOSTNAME", "production")
    provider = AmadeusService(client=client, history_service=history)
    analyzer = MonthlyPriceAnalyzer(amadeus_service=provider)
    monkeypatch.setattr(analyzer, "_get_search_dates", lambda *_: [departure])
    snapshots = []
    save = AsyncMock(
        side_effect=lambda checkpoint: snapshots.append(deepcopy(checkpoint))
    )
    heartbeat = AsyncMock()
    params = dict(
        origin=request.origin,
        adults=request.adults,
        trip_duration=request.duration_days,
        currency=request.currency,
        non_stop=request.non_stop,
        force_refresh=True,
        progress=progress,
        save_progress=save,
        heartbeat=heartbeat,
    )
    with pytest.raises(RuntimeError, match="history"):
        await analyzer.get_monthly_cheapest_dates(request.year, request.month, **params)
    assert progress == captured
    client.shopping.flight_offers_search.get.assert_not_called()
    persist.side_effect = None
    await analyzer.get_monthly_cheapest_dates(request.year, request.month, **params)
    with SessionLocal() as session:
        rows = session.scalars(select(PriceObservation)).all()
        assert len(rows) == 1
        row = rows[0]
        assert row.observed_at == observed.replace(tzinfo=None)
        assert row.origin == request.origin and row.destination == "NRT"
        assert row.adults == 2 and row.search_conditions["non_stop"] is True
        assert row.return_date == departure + timedelta(days=4)
    assert client.shopping.flight_offers_search.get.call_count == 7
    assert any(
        snapshot["quotes"]
        .get(f"NRT:{departure.isoformat()}", {})
        .get("meta", {})
        .get("history_saved")
        for snapshot in snapshots
    )
    heartbeat.assert_awaited()


def test_worker_recovers_history_before_rejecting_past_month(store, monkeypatch):
    service, _, enqueue = store
    service.source = "amadeus"
    request = search_request(currency="USD")
    service.request(request)
    key, token = enqueue.call_args.args
    past = date.today().replace(day=1) - timedelta(days=1)
    with SessionLocal() as session:
        row = session.get(MonthlySearch, key)
        row.request = {**request.model_dump(), "year": past.year, "month": past.month}
        row.checkpoint = {
            "quotes": {
                f"NRT:{past.isoformat()}": {
                    "success": True,
                    "data": [
                        {"id": "old", "price": {"currency": "USD", "total": "100"}}
                    ],
                    "meta": {
                        "source": "amadeus",
                        "history_saved": False,
                        "observed_at": datetime.now(timezone.utc).isoformat(),
                    },
                }
            }
        }
        session.commit()
    monkeypatch.setattr(settings, "AMADEUS_HOSTNAME", "production")
    client = Mock()
    analyzer = MonthlyPriceAnalyzer(amadeus_service=AmadeusService(client=client))
    monkeypatch.setattr(tasks, "MonthlySearchService", lambda: service)
    monkeypatch.setattr(tasks, "MonthlyPriceAnalyzer", lambda: analyzer)
    monkeypatch.setattr(tasks, "configured_source", lambda: "amadeus")
    with pytest.raises(ValueError, match="과거 월"):
        tasks.run_monthly_search.run(key, token)
    client.shopping.flight_offers_search.get.assert_not_called()
    with SessionLocal() as session:
        observations = session.scalars(select(PriceObservation)).all()
        assert len(observations) == 1 and observations[0].departure_date == past
        row = session.get(MonthlySearch, key)
        assert row.status == "failed"
        assert row.checkpoint["quotes"][f"NRT:{past.isoformat()}"]["meta"][
            "history_saved"
        ]


def test_terminal_worker_failure_keeps_last_result(store, monkeypatch):
    service, clock, enqueue = store
    request = search_request()
    complete(store, request)
    clock.now += timedelta(seconds=settings.MONTHLY_CACHE_TTL + 1)
    service.request(request)
    key, token = enqueue.call_args.args
    monkeypatch.setattr(tasks, "MonthlySearchService", lambda: service)
    monkeypatch.setattr(tasks, "configured_source", lambda: "wrong-environment")
    with pytest.raises(ValueError):
        tasks.run_monthly_search.run(key, token)
    response = service.request(request)
    assert response["status_code"] == 200
    assert response["data"]["refresh_status"] == "failed"


def test_expired_departures_are_removed_without_losing_later_options(store):
    service, _, enqueue = store
    request = search_request()
    service.request(request)
    key, token = enqueue.call_args.args
    service.claim(key, token)
    result = result_for(request)
    past = {"price": 1, "airport": "NRT", "departure_date": date.today().isoformat()}
    future = [
        {
            "price": 100 + i,
            "airport": "HND",
            "departure_date": (date.today() + timedelta(days=i + 1)).isoformat(),
        }
        for i in range(7)
    ]
    result["data"]["regions"] = {
        "kanto": {"all_options": [past] + future},
        "expired": {"all_options": [past]},
    }
    service.complete(key, token, result)
    response = service.request(request)
    assert response["data"]["total_regions"] == 1
    region = response["data"]["regions"]["kanto"]
    assert region["cheapest_option"]["price"] == 100
    assert region["airport"] == "HND"
    assert len(region["all_options"]) == 5
    assert region["price_statistics"]["price_samples"] == 7
    assert region["price_statistics"]["max_price"] == 106


@pytest.mark.asyncio
async def test_search_cache_io_runs_outside_event_loop():
    import asyncio

    from app.utils.decorators import cached_response

    def read(key):
        with pytest.raises(RuntimeError, match="no running event loop"):
            asyncio.get_running_loop()
        return None

    def write(*args):
        with pytest.raises(RuntimeError, match="no running event loop"):
            asyncio.get_running_loop()
        return True

    cache = Mock(get_cache=Mock(side_effect=read), set_cache=Mock(side_effect=write))

    @cached_response(lambda **kwargs: "quote")
    async def search(cache_service):
        return {"success": True, "data": []}

    assert (await search(cache_service=cache))["success"]
    cache.set_cache.assert_called_once()
