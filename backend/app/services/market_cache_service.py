from __future__ import annotations

import json
import time
from typing import Any

from app.config import settings

try:
    import redis
except Exception:  # pragma: no cover - optional runtime dependency
    redis = None


class MarketCacheService:
    """Small Redis-first cache with in-memory fallback for market data.

    The cache is deliberately conservative: quotes have short TTLs, candles have a
    longer TTL, and every value is JSON serialised so the service can be swapped
    without changing the market provider implementation.
    """

    def __init__(self) -> None:
        self._memory: dict[str, tuple[float, Any]] = {}
        self._redis = None
        if redis is not None and settings.redis_url:
            try:
                self._redis = redis.Redis.from_url(settings.redis_url, decode_responses=True)
                self._redis.ping()
            except Exception:
                self._redis = None

    @property
    def backend(self) -> str:
        return 'redis' if self._redis is not None else 'memory'

    def get(self, key: str) -> Any | None:
        if self._redis is not None:
            raw = self._redis.get(key)
            if raw is None:
                return None
            return json.loads(raw)
        item = self._memory.get(key)
        if not item:
            return None
        expires_at, value = item
        if expires_at < time.time():
            self._memory.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        if self._redis is not None:
            self._redis.setex(key, ttl_seconds, json.dumps(value, default=str))
            return
        self._memory[key] = (time.time() + ttl_seconds, value)

    def status(self) -> dict[str, Any]:
        return {
            'backend': self.backend,
            'memory_entries': len(self._memory),
            'redis_configured': bool(settings.redis_url),
            'redis_reachable': self._redis is not None,
        }


market_cache_service = MarketCacheService()
