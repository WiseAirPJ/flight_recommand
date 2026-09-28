"""Bound provider traffic across processes using the shared Redis deployment."""

import math
import time
from threading import Lock
from urllib.request import urlopen

from app.config.settings import settings
from app.services.cache_service import CacheService


class ProviderHTTP:
    _local_lock = Lock()
    _next_local_call = 0.0

    def __init__(self, cache=None, transport=None):
        self.cache = cache if cache is not None else CacheService()
        self.transport = transport or urlopen

    def __call__(self, request):
        interval = 1 / settings.AMADEUS_REQUESTS_PER_SECOND
        deadline = time.monotonic() + 10
        # The SDK invokes this inside the quote's worker thread. The socket
        # timeout also covers authentication requests made by the SDK.
        while time.monotonic() < deadline:
            if settings.REDIS_URL or settings.REDIS_HOST:
                if not self.cache.is_connected:
                    raise ConnectionError("Shared provider rate limiter unavailable")
                allowed = self.cache.redis_client.set(
                    f"provider_rate:amadeus:{settings.AMADEUS_HOSTNAME}",
                    "1",
                    nx=True,
                    px=math.ceil(interval * 1000),
                )
            else:
                # Local development only; production requires shared Redis.
                with self._local_lock:
                    now = time.monotonic()
                    allowed = now >= type(self)._next_local_call
                    if allowed:
                        type(self)._next_local_call = now + interval
            if allowed:
                return self.transport(request, timeout=20)
            time.sleep(min(interval, 0.1))
        raise TimeoutError("Provider request budget exhausted; retry later")
