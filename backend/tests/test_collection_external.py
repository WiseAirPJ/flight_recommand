"""Opt-in PostgreSQL/Redis integration; each test owns an isolated DB schema."""

import os
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from multiprocessing import get_context
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
import redis
from celery.contrib.testing.worker import start_worker
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from alembic import command
from alembic.config import Config
from app.config.settings import settings
from app.core.database import Base
from app.models.flight_requests import MonthlySearchRequest
from app.services.amadeus_service import AmadeusService
from app.services.monthly_search_service import MonthlySearchService
from app.services.provider_http import ProviderHTTP
from app.tasks import monthly_data_collection as tasks
from app.tasks.celery_app import celery_app
from tests.test_background_monthly_search import search_request


@pytest.fixture
def pg_url():
    url = os.getenv("TEST_POSTGRES_URL")
    if not url:
        pytest.skip("TEST_POSTGRES_URL is not set")
    schema = "flight_test_" + uuid4().hex
    admin = create_engine(url)
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    isolated = make_url(url).update_query_dict({"options": f"-csearch_path={schema}"})
    try:
        yield isolated.render_as_string(hide_password=False)
    finally:
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


@pytest.fixture
def pg_sessions(pg_url):
    engine = create_engine(pg_url)
    Base.metadata.create_all(engine)
    try:
        yield sessionmaker(bind=engine, expire_on_commit=False)
    finally:
        engine.dispose()


def claim_from_process(url, payload):
    engine = create_engine(url)
    try:
        service = MonthlySearchService(
            sessionmaker(bind=engine, expire_on_commit=False),
            enqueue=lambda *_: None,
            source="demo",
        )
        result = service.request(MonthlySearchRequest(**payload))
        return result["data"]["job_id"], result["enqueued"]
    finally:
        engine.dispose()


def test_postgres_coordinates_independent_api_processes(pg_url, pg_sessions):
    request = search_request()
    with ProcessPoolExecutor(max_workers=4, mp_context=get_context("spawn")) as pool:
        results = list(
            pool.map(claim_from_process, [pg_url] * 12, [request.model_dump()] * 12)
        )
    assert len({token for token, _ in results}) == 1
    assert sum(enqueued for _, enqueued in results) == 1


def test_postgres_migrations_match_models_and_round_trip(pg_url, monkeypatch):
    monkeypatch.setattr(settings, "DATABASE_URL", pg_url)
    root = Path(__file__).resolve().parents[1]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "alembic"))
    command.upgrade(config, "head")
    command.check(config)
    command.downgrade(config, "base")
    command.upgrade(config, "head")


@pytest.fixture
def redis_url():
    url = os.getenv("TEST_REDIS_URL")
    if not url:
        pytest.skip("TEST_REDIS_URL is not set")
    return url


def test_shared_redis_provider_budget_across_clients(redis_url, monkeypatch):
    # Isolate the limiter key from other tests and any application using Redis.
    scope = "test-" + uuid4().hex
    monkeypatch.setattr(settings, "REDIS_URL", redis_url)
    monkeypatch.setattr(settings, "AMADEUS_HOSTNAME", scope)
    monkeypatch.setattr(settings, "AMADEUS_REQUESTS_PER_SECOND", 10)
    clients = [redis.Redis.from_url(redis_url) for _ in range(6)]
    calls = []

    def send(index):
        transport = lambda request, timeout: calls.append((time.monotonic(), timeout))
        ProviderHTTP(
            cache=SimpleNamespace(is_connected=True, redis_client=clients[index]),
            transport=transport,
        )("request")

    try:
        with ThreadPoolExecutor(max_workers=6) as pool:
            list(pool.map(send, range(6)))
        timestamps = sorted(t for t, _ in calls)
        assert len(timestamps) == 6 and timestamps[-1] - timestamps[0] >= 0.45
        assert all(timeout == 20 for _, timeout in calls)
    finally:
        clients[0].delete(f"provider_rate:amadeus:{scope}")
        for client in clients:
            client.close()


@pytest.mark.parametrize("retry_once", [False, True])
def test_real_broker_worker_publishes_durable_result(
    pg_sessions, redis_url, monkeypatch, retry_once
):
    monkeypatch.setattr(settings, "ENABLE_DUMMY_FALLBACK", True)
    store = MonthlySearchService(pg_sessions, source="demo")
    monkeypatch.setattr(tasks, "MonthlySearchService", lambda: store)
    search = AmadeusService.search_flight_offers
    retry = tasks.run_monthly_search.retry
    calls, retry_delays = [], []

    async def fail_once(self, **conditions):
        calls.append(conditions)
        if retry_once and len(calls) == 1:
            return {"success": False, "data": []}
        return await search(self, **conditions)

    def retry_immediately(**kwargs):
        retry_delays.append(kwargs["countdown"])
        return retry(**{**kwargs, "countdown": 0})

    monkeypatch.setattr(AmadeusService, "search_flight_offers", fail_once)
    monkeypatch.setattr(tasks.run_monthly_search, "retry", retry_immediately)
    old_broker, old_transport = (
        celery_app.conf.broker_url,
        celery_app.conf.broker_transport_options,
    )
    # A unique Redis prefix keeps this worker's queue isolated from other runs.
    celery_app.conf.broker_url = redis_url
    celery_app.conf.broker_transport_options = {
        "global_keyprefix": "flight_test_" + uuid4().hex + ":",
        "socket_timeout": 2,
        "socket_connect_timeout": 2,
    }
    try:
        with start_worker(
            celery_app,
            pool="solo",
            concurrency=1,
            perform_ping_check=False,
            queues=["monthly_analysis"],
            shutdown_timeout=15,
        ):
            request = search_request(
                currency="USD", adults=2, duration_days=5, non_stop=True
            )
            pending = store.request(request)
            assert pending["status_code"] == 202
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                response = store.request(request)
                if response["data"]["status"] == "ready":
                    break
                time.sleep(0.05)
            assert response["status_code"] == 200
            assert response["data"]["status"] == "ready"
            assert response["data"]["total_regions"] == 6
            assert (
                response["data"]["adults"] == 2
                and response["data"]["duration_days"] == 5
            )
            assert response["data"]["non_stop"] and response["data"]["is_demo"]
            assert retry_delays == ([60] if retry_once else [])
            assert (
                response["data"]["job_id"] != pending["data"]["job_id"]
            ) == retry_once
            assert len(calls) == response["data"]["total_searches"] + int(retry_once)
    finally:
        celery_app.conf.broker_url = old_broker
        celery_app.conf.broker_transport_options = old_transport
