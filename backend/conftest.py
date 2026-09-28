"""Isolated test settings must be installed before application imports."""

import os

import pytest

for key, value in {
    "SECRET_KEY": "test-secret-key-minimum-32-characters-only",
    "ENVIRONMENT": "test",
    "DATABASE_URL": "sqlite:///:memory:",
    "INIT_DB_ON_STARTUP": "true",
    "USE_REAL_AMADEUS": "false",
    "ENABLE_DUMMY_FALLBACK": "false",
    "ENABLE_EXPERIMENTAL_FEATURES": "false",
    "CELERY_BROKER_URL": "memory://",
    "CELERY_RESULT_BACKEND": "cache+memory://",
    "REDIS_URL": "",
    "REDIS_HOST": "",
    "OPENAI_API_KEY": "",
    "AZURE_OPENAI_API_KEY": "",
    "ANTHROPIC_API_KEY": "",
    "AMADEUS_CLIENT_ID": "",
    "AMADEUS_CLIENT_SECRET": "",
    "KOREAEXIM_API_KEY": "",
    "ADMIN_API_KEY": "",
}.items():
    os.environ[key] = value


@pytest.fixture(autouse=True)
def isolate_cache_and_database():
    from app.api.v1.flights import get_amadeus_service, get_cache_service
    from app.api.v1.regions import get_monthly_search_service
    from app.core.database import Base, engine, init_db
    from app.services.cache_service import CacheService

    CacheService._shared_memory_cache.clear()
    for provider in (
        get_amadeus_service,
        get_cache_service,
        get_monthly_search_service,
    ):
        provider.cache_clear()
    init_db()
    yield
    Base.metadata.drop_all(engine)
    CacheService._shared_memory_cache.clear()
