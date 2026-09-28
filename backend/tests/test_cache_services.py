"""Cache expiration, maintenance safety and collection dispatch regressions."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock, call

import pytest
from fastapi.testclient import TestClient

from app.api.v1.cache import get_cache_refresh_service, get_cache_service
from app.config.settings import settings
from app.main import app
from app.models.flight_requests import MonthlySearchRequest
from app.services.cache_admin_service import CacheAdminService
from app.services.cache_refresh_service import CacheRefreshService
from app.services.cache_service import CacheService
from app.utils.cache_keys import monthly_search_key


@pytest.fixture
def timed_cache():
    clock = SimpleNamespace(now=datetime(2026, 9, 28, 12))
    return CacheService(clock=lambda: clock.now), clock


@pytest.fixture
def redis_cache():
    cache = CacheService()
    cache.is_connected = True
    cache.redis_client = Mock()
    cache.redis_client.info.return_value = {}
    return cache


def test_expiry_boundary_is_identical_for_read_validity_and_admin(timed_cache):
    cache, clock = timed_cache
    admin = CacheAdminService(cache)
    cache.set_cache("flight_search:expired", [10], 10)
    cache.set_cache("flight_search:live", [20], 11)
    clock.now += timedelta(seconds=10)
    assert admin.get_cache_status()["total_keys"] == 1
    assert admin.get_cache_statistics()["total_keys"] == 1
    assert admin.get_cache_keys("flight_search:*")["keys"] == ["flight_search:live"]
    assert admin.get_memory_usage()["total_keys"] == 1
    assert admin.health_check()["memory_keys"] == 1
    assert not cache.is_cache_valid("flight_search:expired")
    assert cache.get_cache("flight_search:expired") is None
    assert cache.get_cache("flight_search:live") == [20]


def test_memory_cleanup_uses_envelope_not_payload(timed_cache):
    cache, clock = timed_cache
    payload = {"expires_at": "2000-01-01T00:00:00", "prices": [100]}
    cache.set_cache("live", payload, 20)
    cache.set_cache("expired", [200], 10)
    clock.now += timedelta(seconds=10)
    assert CacheAdminService(cache).cleanup_expired_cache()["cleaned_count"] == 1
    assert cache.get_cache("live") == payload
    assert CacheAdminService(cache).cleanup_expired_cache()["cleaned_count"] == 0


def test_updating_full_cache_and_nonpositive_ttl_do_not_evict_other_keys(monkeypatch):
    cache = CacheService()
    monkeypatch.setattr(cache, "MEMORY_LIMIT", 2)
    cache.set_cache("first", 1)
    cache.set_cache("second", 2)
    cache.set_cache("second", 20)
    assert cache.get_cache("first") == 1
    cache.set_cache("absent", 3, 0)
    assert cache.get_cache("first") == 1
    assert cache.get_cache("second") == 20
    cache.set_cache("second", 99, -1)
    assert not cache.is_cache_valid("second")
    cache.set_cache("third", 3)
    cache.set_cache("fourth", 4)
    assert cache.get_cache("first") is None
    assert cache.get_cache("third") == 3


def test_expired_entry_is_reclaimed_before_live_eviction(timed_cache, monkeypatch):
    cache, clock = timed_cache
    monkeypatch.setattr(cache, "MEMORY_LIMIT", 2)
    cache.set_cache("first-live", 1, 20)
    cache.set_cache("second-expired", 2, 10)
    clock.now += timedelta(seconds=10)
    cache.set_cache("third", 3)
    assert cache.get_cache("first-live") == 1
    assert cache.get_cache("third") == 3


def test_memory_snapshots_cannot_mutate_cached_values():
    cache = CacheService()
    cache.set_cache("flight_search:one", [1])
    snapshot = cache.memory_snapshot()
    snapshot["flight_search:one"]["data"].append(2)
    assert cache.get_cache("flight_search:one") == [1]
    cache.set_cache("holidays:2026", [])
    assert cache.clear_cache_pattern("flight_search:*") == 1
    assert cache.is_cache_valid("holidays:2026")


def test_shared_memory_is_safe_across_worker_threads():
    def use_cache(index):
        cache = CacheService()
        key = f"flight_search:{index}"
        assert cache.set_cache(key, [index])
        assert cache.get_cache(key) == [index]
        assert cache.delete_cache(key)

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(use_cache, range(200)))
    assert CacheService().memory_snapshot() == {}


@pytest.mark.parametrize(
    "payload", [[{"price": 10}], {"expires_at": "2000-01-01T00:00:00"}, 0, False, ""]
)
def test_redis_cleanup_never_parses_or_deletes_valid_payload(redis_cache, payload):
    redis_cache.set_cache("monthly_cheapest:test", payload, 60)
    encoded = redis_cache.redis_client.setex.call_args.args[2]
    redis_cache.redis_client.get.return_value = encoded
    admin = CacheAdminService(redis_cache)
    assert admin.cleanup_expired_cache()["cleaned_count"] == 0
    redis_cache.redis_client.get.assert_not_called()
    redis_cache.redis_client.delete.assert_not_called()
    assert redis_cache.get_cache("monthly_cheapest:test") == payload


@pytest.mark.parametrize("ttl,valid", [(0, True), (-1, True), (-2, False), (10, True)])
def test_redis_validity_includes_subsecond_keys(redis_cache, ttl, valid):
    redis_cache.redis_client.ttl.return_value = ttl
    assert redis_cache.is_cache_valid("key") is valid


def test_redis_memory_report_tolerates_keys_expiring_during_sampling(redis_cache):
    redis_cache.redis_client.scan.side_effect = lambda **kwargs: (
        0,
        ["holidays:2026"] if kwargs["match"] == "holidays:*" else [],
    )
    redis_cache.redis_client.memory_usage.return_value = None
    result = CacheAdminService(redis_cache).get_memory_usage()
    assert result["app_cache_info"]["total_app_keys"] == 1
    assert result["app_cache_info"]["sampled_keys"] == 0
    assert result["app_cache_info"]["avg_key_size"] == 0


def test_redis_health_checks_use_distinct_keys_and_verify_contents(redis_cache):
    values = {}
    redis_cache.redis_client.setex.side_effect = (
        lambda key, ttl, value: values.update({key: value}) or True
    )
    redis_cache.redis_client.get.side_effect = values.get
    admin = CacheAdminService(redis_cache)
    assert admin.health_check()["read_write_test"]
    assert admin.health_check()["read_write_test"]
    keys = [c.args[0] for c in redis_cache.redis_client.setex.call_args_list]
    assert len(set(keys)) == 2
    assert all(k.startswith("cache_health:") for k in keys)
    assert redis_cache.redis_client.delete.call_args_list == [call(k) for k in keys]
    redis_cache.redis_client.get.side_effect = lambda key: "wrong-value"
    assert not admin.health_check()["read_write_test"]


def test_refresh_skips_only_matching_source_and_origin(monkeypatch):
    from app.tasks.monthly_data_collection import collect_monthly_cheapest_data

    monkeypatch.setattr(settings, "ENABLE_DUMMY_FALLBACK", True)
    dispatch = Mock(return_value=SimpleNamespace(id="task-id"))
    monkeypatch.setattr(collect_monthly_cheapest_data, "delay", dispatch)
    cache = CacheService()
    service = CacheRefreshService(cache)
    months = service._get_months_to_refresh()
    year, month = months[0]
    request = MonthlySearchRequest(year=year, month=month, origin="PUS")
    cache.set_cache(monthly_search_key(request, "demo"), {})
    result = service.refresh_cache(origin="PUS")
    assert result["success"]
    dispatch.assert_called_once_with(*months[1], "PUS")
    dispatch.reset_mock()
    service.refresh_cache(origin="PUS", force_update=True)
    assert dispatch.call_args_list == [call(y, m, "PUS") for y, m in months]
    dispatch.reset_mock()
    service.refresh_cache(origin="CJJ")
    assert dispatch.call_count == 2
    dispatch.reset_mock()
    monkeypatch.setattr(settings, "ENABLE_DUMMY_FALLBACK", False)
    service.refresh_cache(origin="PUS")
    assert dispatch.call_count == 2


def test_warmup_and_refresh_cross_year_boundary(monkeypatch):
    from app.services import cache_refresh_service
    from app.tasks.monthly_data_collection import collect_monthly_cheapest_data

    fake_datetime = Mock()
    fake_datetime.now.return_value = datetime(2026, 12, 20)
    monkeypatch.setattr(cache_refresh_service, "datetime", fake_datetime)
    monkeypatch.setattr(settings, "COLLECTION_ORIGINS", ["ICN", "PUS", "CJJ"])
    dispatch = Mock(return_value=SimpleNamespace(id="task-id"))
    monkeypatch.setattr(collect_monthly_cheapest_data, "delay", dispatch)
    service = CacheRefreshService()
    assert service._get_months_to_refresh() == [(2026, 12), (2027, 1)]
    result = service.warmup_cache(months_ahead=3)
    assert result["success"]
    assert dispatch.call_args_list == [
        call(year, month, origin)
        for year, month in [(2026, 12), (2027, 1), (2027, 2)]
        for origin in ["ICN", "PUS", "CJJ"]
    ]


def test_dispatch_failure_is_reported(monkeypatch):
    from app.tasks.monthly_data_collection import collect_monthly_cheapest_data

    monkeypatch.setattr(
        collect_monthly_cheapest_data,
        "delay",
        Mock(side_effect=RuntimeError("broker unavailable")),
    )
    service = CacheRefreshService()
    assert not service.refresh_cache()["success"]
    assert not service.warmup_cache()["success"]


def test_admin_routes_preserve_contract_and_run_blocking_work_off_event_loop(
    monkeypatch,
):
    monkeypatch.setattr(settings, "ADMIN_API_KEY", "test-admin-token")
    cache = CacheService()
    cache.set_cache("flight_search:test", [1])
    admin = CacheAdminService(cache)
    original = admin.get_cache_status

    def status_in_worker():
        with pytest.raises(RuntimeError, match="no running event loop"):
            asyncio.get_running_loop()
        return original()

    monkeypatch.setattr(admin, "get_cache_status", status_in_worker)
    app.dependency_overrides[get_cache_service] = lambda: admin
    try:
        with TestClient(app) as client:
            headers = {"X-Admin-Key": "test-admin-token"}
            for path in ["status", "statistics", "keys", "memory", "performance"]:
                result = client.get(f"/api/v1/cache/{path}", headers=headers)
                assert result.status_code == 200
                assert result.json()["success"]
            assert (
                client.get("/api/v1/cache/health", headers=headers).status_code == 200
            )
            assert (
                client.post("/api/v1/cache/cleanup", headers=headers).json()["data"][
                    "cache_type"
                ]
                == "memory"
            )
            assert (
                client.delete(
                    "/api/v1/cache/keys/flight_search:test", headers=headers
                ).status_code
                == 200
            )
            assert (
                client.delete(
                    "/api/v1/cache/keys/flight_search:test", headers=headers
                ).status_code
                == 404
            )
    finally:
        app.dependency_overrides.pop(get_cache_service, None)


def test_redis_failures_behave_as_cache_misses(redis_cache):
    import redis

    for name in ["get", "setex", "delete", "ttl", "scan"]:
        getattr(redis_cache.redis_client, name).side_effect = redis.ConnectionError(
            "offline"
        )
    assert redis_cache.get_cache("key") is None
    assert not redis_cache.set_cache("key", [])
    assert not redis_cache.delete_cache("key")
    assert not redis_cache.is_cache_valid("key")
    assert redis_cache.clear_cache_pattern("flight_search:*") == 0


def test_refresh_routes_use_scheduler_dependency(monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_API_KEY", "test-admin-token")
    scheduler = Mock()
    scheduler.refresh_cache.return_value = {
        "success": True,
        "data": {"tasks_created": []},
    }
    scheduler.warmup_cache.return_value = {
        "success": True,
        "data": {"tasks_created": []},
    }
    app.dependency_overrides[get_cache_refresh_service] = lambda: scheduler
    try:
        with TestClient(app) as client:
            headers = {"X-Admin-Key": "test-admin-token"}
            response = client.post(
                "/api/v1/cache/refresh",
                headers=headers,
                json={"origin": "PUS", "force_update": True},
            )
            assert response.status_code == 200
            assert response.json()["data"] == {"tasks_created": []}
            scheduler.refresh_cache.assert_called_once_with(
                regions=None, origin="PUS", force_update=True
            )
            response = client.post(
                "/api/v1/cache/warmup?months_ahead=2", headers=headers
            )
            assert response.status_code == 200
            scheduler.warmup_cache.assert_called_once_with(regions=None, months_ahead=2)
            scheduler.refresh_cache.return_value = {
                "success": False,
                "message": "broker unavailable",
            }
            assert (
                client.post(
                    "/api/v1/cache/refresh", headers=headers, json={}
                ).status_code
                == 500
            )
    finally:
        app.dependency_overrides.pop(get_cache_refresh_service, None)
