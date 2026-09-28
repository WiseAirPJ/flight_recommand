from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config.settings import Settings, settings
from app.main import app
from app.models.flight_requests import (
    FlightSearchRequest,
    MonthlySearchRequest,
    OneWayFlightSearchRequest,
)
from app.services.cache_service import CacheService
from app.utils.cache_keys import flight_search_key


def test_cache_keys_separate_every_quote_condition():
    data = {
        "origin": "PUS",
        "destination": "KIX",
        "departure_date": (date.today() + timedelta(days=20)).isoformat(),
    }
    base = flight_search_key(FlightSearchRequest(**data))
    for change in [
        {"currency": "USD"},
        {"adults": 2},
        {"non_stop": True},
        {"origin": "CJJ"},
        {"return_date": (date.today() + timedelta(days=23)).isoformat()},
    ]:
        assert base != flight_search_key(FlightSearchRequest(**{**data, **change}))
    request = FlightSearchRequest(**data)
    assert flight_search_key(
        request, amadeus_service=SimpleNamespace(source="demo")
    ) != flight_search_key(request, amadeus_service=SimpleNamespace(source="amadeus"))
    with pytest.raises(ValidationError):
        OneWayFlightSearchRequest(
            **data, return_date=(date.today() + timedelta(days=23)).isoformat()
        )
    with pytest.raises(ValidationError):
        FlightSearchRequest(**{**data, "origin": "KIX"})
    with pytest.raises(ValidationError):
        MonthlySearchRequest(year=date.today().year + 2, month=1)


def test_memory_cache_shared_copied_and_expires():
    first, second = CacheService(), CacheService()
    value = {"prices": [12]}
    first.set_cache("test", value)
    value["prices"].append(99)
    retrieved = second.get_cache("test")
    assert retrieved == {"prices": [12]}
    retrieved["prices"].append(20)
    assert first.get_cache("test") == {"prices": [12]}
    first.set_cache("expired", {}, 0)
    assert second.get_cache("expired") is None


def test_admin_guard_and_real_http_errors(monkeypatch):
    with TestClient(app) as client:
        assert client.get("/api/v1/cache/status").status_code == 503
        monkeypatch.setattr(settings, "ADMIN_API_KEY", "test-admin-token")
        assert client.get("/api/v1/cache/status").status_code == 401
        assert (
            client.get(
                "/api/v1/cache/status", headers={"X-Admin-Key": "wrong"}
            ).status_code
            == 401
        )
        assert (
            client.get(
                "/api/v1/cache/status", headers={"X-Admin-Key": "test-admin-token"}
            ).status_code
            == 200
        )
        missing = client.get("/not-a-route")
        assert (
            missing.status_code == 404
            and missing.headers["content-type"] == "application/json"
        )
        assert client.get("/health").json()["flight_source"] == "unavailable"
        assert client.get("/api/v1/status").json()["experimental_features"] is False
        assert client.get("/", follow_redirects=False).status_code == 307
        schema = client.get("/openapi.json").json()
        assert not any(
            "prediction" in path or "/llm/" in path for path in schema["paths"]
        )


def test_production_settings_reject_demo_and_automatic_tables():
    for changes in [{"INIT_DB_ON_STARTUP": True}, {"ENABLE_DUMMY_FALLBACK": True}]:
        with pytest.raises(ValidationError):
            Settings(
                _env_file=None,
                ENVIRONMENT="production",
                **{"INIT_DB_ON_STARTUP": False, **changes},
            )


def test_password_hash_and_token():
    from app.core.security import (
        create_access_token,
        get_password_hash,
        verify_password,
        verify_token,
    )

    hashed = get_password_hash("a-test-password")
    assert verify_password("a-test-password", hashed)
    assert not verify_password("wrong", hashed)
    assert verify_token(create_access_token({"sub": "test-user"}))["sub"] == "test-user"
    assert verify_token("invalid") is None


def test_worker_uses_same_app_and_all_origins(monkeypatch):
    from app.tasks import monthly_data_collection as tasks
    from app.tasks.celery_app import celery_app

    monkeypatch.setattr(settings, "COLLECTION_ORIGINS", ["PUS", "CJJ"])
    store = Mock()
    store.request.return_value = {"success": True, "data": {"job_id": "task-id"}}
    monkeypatch.setattr(tasks, "MonthlySearchService", lambda: store)
    assert tasks.run_monthly_search.app is celery_app
    assert tasks.collect_current_month_data.run() == ["task-id", "task-id"]
    assert {c.args[0].origin for c in store.request.call_args_list} == {"PUS", "CJJ"}
    store.reset_mock()
    assert tasks.collect_next_month_data.run() == ["task-id", "task-id"]
    result = tasks.collect_popular_months_data.run()
    assert len(result) == 10 and all(isinstance(item, str) for item in result)


def test_worker_collection_contract(monkeypatch):
    from app.tasks import monthly_data_collection as tasks

    result = {"success": True, "data": {"status": "pending"}}
    store = Mock()
    store.request.return_value = result
    monkeypatch.setattr(tasks, "MonthlySearchService", lambda: store)
    future = (date.today().replace(day=1) + timedelta(days=32)).replace(day=1)
    assert (
        tasks.collect_monthly_cheapest_data.run(future.year, future.month, "CJJ")
        == result
    )
    assert store.request.call_args.args[0].origin == "CJJ"
    assert store.request.call_args.kwargs == {"force_refresh": True}


def test_migrations_upgrade_downgrade_and_model_consistency(tmp_path, monkeypatch):
    from sqlalchemy import create_engine, inspect

    from alembic import command
    from alembic.config import Config
    from app.core.database import Base

    url = f"sqlite:///{tmp_path / 'migration.db'}"
    monkeypatch.setattr(settings, "DATABASE_URL", url)
    from pathlib import Path

    backend_root = Path(__file__).resolve().parents[1]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "alembic"))
    command.upgrade(config, "head")
    engine = create_engine(url)
    assert set(Base.metadata.tables) <= set(inspect(engine).get_table_names())
    command.check(config)
    command.downgrade(config, "base")
    assert inspect(engine).get_table_names() == ["alembic_version"]
    command.upgrade(config, "head")
    engine.dispose()


def test_redis_preserves_lists_like_memory():
    import json

    service = CacheService()
    service.is_connected = True
    service.redis_client = Mock()
    records = [{"holiday": "a"}, {"holiday": "b"}]
    service.set_cache("holidays", records)
    encoded = service.redis_client.setex.call_args.args[2]
    assert json.loads(encoded) == records
    service.redis_client.get.return_value = encoded
    assert service.get_cache("holidays") == records


def test_oneway_cache_real_route_and_duration(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_DUMMY_FALLBACK", True)
    departure = date.today() + timedelta(days=15)
    data = {
        "origin": "PUS",
        "destination": "KIX",
        "departure_date": departure.isoformat(),
    }
    with TestClient(app) as client:
        first = client.post("/api/v1/flights/search-oneway", json=data).json()
        second = client.post("/api/v1/flights/search-oneway", json=data).json()
        assert first["meta"]["is_demo"] and not first["data"]["from_cache"]
        assert second["data"]["from_cache"]
        assert first["data"]["search_params"]["return_date"] is None
        assert len(first["data"]["flights"][0]["itineraries"]) == 1
        usd = client.post(
            "/api/v1/flights/search-oneway", json={**data, "currency": "USD"}
        ).json()
        assert (
            not usd["data"]["from_cache"]
            and usd["data"]["flights"][0]["price"]["currency"] == "USD"
        )
        duration = client.post(
            "/api/v1/flights/search-by-duration", json={**data, "duration_days": 4}
        ).json()
        assert (
            duration["data"]["trip_details"]["return_date"]
            == (departure + timedelta(days=3)).isoformat()
        )
        cheapest = client.post(
            "/api/v1/flights/cheapest-dates",
            json={**data, "currency": "USD", "flexibility_days": 1},
        ).json()
        assert len(cheapest["data"]["cheapest_options"]) == 3
        assert "USD" in cheapest["data"]["price_analysis"]["savings_potential"]
