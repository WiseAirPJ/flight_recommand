"""Redis or bounded process-local cache storage used by application services."""

import fnmatch
import json
import logging
from copy import deepcopy
from datetime import datetime, timedelta
from threading import RLock
from typing import Any, Optional

import redis

from app.config.settings import settings

logger = logging.getLogger(__name__)


class CacheService:
    _shared_memory_cache = {}
    _memory_lock = RLock()
    MEMORY_LIMIT = 1000

    def __init__(self, *, clock=None):
        """캐시 서비스 초기화"""
        self._clock = clock or datetime.now
        self._memory_cache = self._shared_memory_cache
        self.redis_client = None
        self.is_connected = False
        try:
            options = dict(
                decode_responses=True, socket_timeout=2, socket_connect_timeout=2
            )
            if settings.REDIS_URL:
                self.redis_client = redis.Redis.from_url(settings.REDIS_URL, **options)
            elif settings.REDIS_HOST:
                self.redis_client = redis.Redis(
                    host=settings.REDIS_HOST,
                    port=settings.REDIS_PORT,
                    username=settings.REDIS_USERNAME,
                    password=settings.REDIS_PASSWORD,
                    **options,
                )
            if self.redis_client is not None:
                self.redis_client.ping()
                self.is_connected = True
        except redis.RedisError:
            logger.warning("Redis unavailable; using process-local memory cache")
            self.redis_client = None

    def _prune_memory(self):
        """Called with the shared lock held; expiry belongs to the envelope only."""
        now = self._clock()
        expired = []
        for key, entry in self._memory_cache.items():
            try:
                if datetime.fromisoformat(entry["expires_at"]) <= now:
                    expired.append(key)
            except KeyError, TypeError, ValueError:
                expired.append(key)
        for key in expired:
            del self._memory_cache[key]
        return len(expired)

    def cleanup_expired(self) -> int:
        # Redis expires keys itself. Never delete by examining the cached value.
        if self.is_connected:
            return 0
        with self._memory_lock:
            return self._prune_memory()

    def memory_snapshot(self) -> dict:
        with self._memory_lock:
            self._prune_memory()
            return deepcopy(self._memory_cache)

    def set_cache(self, key: str, value: Any, ttl_seconds: int = 3600) -> bool:
        try:
            if ttl_seconds <= 0:
                if self.is_connected:
                    self.redis_client.delete(key)
                else:
                    with self._memory_lock:
                        self._memory_cache.pop(key, None)
                return True
            if self.is_connected:
                return bool(
                    self.redis_client.setex(
                        key, ttl_seconds, json.dumps(value, default=str)
                    )
                )
            # Copy before mutation so a failed copy cannot evict another entry.
            entry = {
                "data": deepcopy(value),
                "expires_at": (
                    self._clock() + timedelta(seconds=ttl_seconds)
                ).isoformat(),
            }
            with self._memory_lock:
                self._prune_memory()
                if (
                    key not in self._memory_cache
                    and len(self._memory_cache) >= self.MEMORY_LIMIT
                ):
                    del self._memory_cache[next(iter(self._memory_cache))]
                self._memory_cache[key] = entry
            return True
        except Exception as exc:
            logger.warning("Cache write failed for %s: %s", key, exc)
            return False

    def get_cache(self, key: str) -> Optional[Any]:
        try:
            if self.is_connected:
                value = self.redis_client.get(key)
                if value is None:
                    return None
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
            with self._memory_lock:
                self._prune_memory()
                entry = self._memory_cache.get(key)
                return deepcopy(entry["data"]) if entry is not None else None
        except Exception as exc:
            logger.warning("Cache read failed for %s: %s", key, exc)
            return None

    def delete_cache(self, key: str) -> bool:
        try:
            if self.is_connected:
                return self.redis_client.delete(key) > 0
            with self._memory_lock:
                self._prune_memory()
                return self._memory_cache.pop(key, None) is not None
        except Exception as exc:
            logger.warning("Cache deletion failed for %s: %s", key, exc)
            return False

    def is_cache_valid(self, key: str) -> bool:
        try:
            if self.is_connected:
                # TTL 0 means a live key with less than one second remaining.
                ttl = self.redis_client.ttl(key)
                return ttl >= 0 or ttl == -1
            with self._memory_lock:
                self._prune_memory()
                return key in self._memory_cache
        except Exception as exc:
            logger.warning("Cache validity check failed for %s: %s", key, exc)
            return False

    def clear_cache_pattern(self, pattern: str) -> int:
        try:
            if self.is_connected:
                count = 0
                cursor = 0
                while True:
                    cursor, keys = self.redis_client.scan(
                        cursor=cursor, match=pattern, count=100
                    )
                    if keys:
                        count += self.redis_client.delete(*keys)
                    if cursor == 0:
                        return count
            with self._memory_lock:
                self._prune_memory()
                keys = [
                    key
                    for key in self._memory_cache
                    if fnmatch.fnmatchcase(key, pattern)
                ]
                for key in keys:
                    del self._memory_cache[key]
                return len(keys)
        except Exception as exc:
            logger.warning("Cache pattern deletion failed for %s: %s", pattern, exc)
            return 0
