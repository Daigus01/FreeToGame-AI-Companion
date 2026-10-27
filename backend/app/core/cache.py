"""Thin async Redis JSON cache. Failures never raise: cache is best-effort (RNF-3).

STATUS: done (skeleton), untested against a live Redis (see P1-01).
Two-tier keys support RNF-2 + RNF-3:
  - `<key>`        : fresh copy, expires after TTL (12h)
  - `<key>:stale`  : long-lived copy used only when the upstream API is down
"""
import json
import logging
from typing import Any

from redis.asyncio import Redis

logger = logging.getLogger(__name__)

STALE_TTL_SECONDS = 30 * 24 * 60 * 60


class JsonCache:
    def __init__(self, redis: Redis):
        self._r = redis

    async def get(self, key: str) -> Any | None:
        try:
            raw = await self._r.get(key)
            return json.loads(raw) if raw else None
        except Exception:  # noqa: BLE001 - cache must never break requests
            logger.warning("cache get failed for %s", key, exc_info=True)
            return None

    async def set(self, key: str, value: Any, ttl: int) -> None:
        try:
            payload = json.dumps(value)
            await self._r.set(key, payload, ex=ttl)
            await self._r.set(f"{key}:stale", payload, ex=STALE_TTL_SECONDS)
        except Exception:  # noqa: BLE001
            logger.warning("cache set failed for %s", key, exc_info=True)

    async def get_stale(self, key: str) -> Any | None:
        return await self.get(f"{key}:stale")


def make_redis(url: str) -> Redis:
    return Redis.from_url(url, decode_responses=True)
