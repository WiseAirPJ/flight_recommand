from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.config.settings import settings
from app.services.provider_http import ProviderHTTP


def test_configured_redis_failure_never_bypasses_shared_limit(monkeypatch):
    monkeypatch.setattr(settings, "REDIS_URL", "redis://unavailable")
    transport = Mock()
    with pytest.raises(ConnectionError):
        ProviderHTTP(SimpleNamespace(is_connected=False), transport)("request")
    transport.assert_not_called()


def test_local_transport_also_has_timeout():
    transport = Mock(return_value="response")
    assert ProviderHTTP(transport=transport)("request") == "response"
    transport.assert_called_once_with("request", timeout=20)


def test_budget_wait_is_bounded(monkeypatch):
    from app.services import provider_http

    monkeypatch.setattr(settings, "REDIS_URL", "redis://configured")
    cache = SimpleNamespace(is_connected=True, redis_client=Mock())
    cache.redis_client.set.return_value = False
    clock = iter([0, 0, 11])
    monkeypatch.setattr(provider_http.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(provider_http.time, "sleep", lambda _: None)
    transport = Mock()
    with pytest.raises(TimeoutError):
        ProviderHTTP(cache, transport)("request")
    transport.assert_not_called()
