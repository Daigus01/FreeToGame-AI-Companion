"""Client for the public FreeToGame API with Redis cache + stale fallback.

STATUS: skeleton implemented; NOT yet verified against the live API (TODO P1-03).
Requirements: RNF-2 (12h TTL cache), RNF-3 (degraded mode when upstream is down).

FreeToGame endpoints used:
  GET /games?platform=&category=&sort-by=   -> list of game summaries
  GET /game?id=<int>                        -> game detail (description, screenshots, requirements)
Note: the API query param is `sort-by` (hyphen); our public param is `sort_by`.
Upstream rate limit is documented as ~10 req/s; cache makes this a non-issue in normal use.
"""
import logging
from typing import Any

import httpx

from app.core.cache import JsonCache

logger = logging.getLogger(__name__)


class UpstreamUnavailable(Exception):
    """Raised when FreeToGame is down AND no stale cached copy exists."""


class FreeToGameClient:
    def __init__(self, base_url: str, cache: JsonCache, ttl: int, timeout: float = 5.0):
        self._http = httpx.AsyncClient(base_url=base_url, timeout=timeout)
        self._cache = cache
        self._ttl = ttl

    async def aclose(self) -> None:
        await self._http.aclose()

    async def _cached_get(self, key: str, path: str, params: dict[str, Any]) -> Any:
        fresh = await self._cache.get(key)
        if fresh is not None:
            return fresh
        try:
            resp = await self._http.get(path, params=params)
            if resp.status_code == 404:
                # Unknown resource (e.g. bad game id) is NOT an outage: don't use stale, don't cache it.
                return {"status": 0, "status_message": "not found"}
            resp.raise_for_status()
            data = resp.json()
        except (httpx.HTTPError, ValueError):
            logger.warning("FreeToGame request failed: %s %s", path, params, exc_info=True)
            stale = await self._cache.get_stale(key)
            if stale is not None:
                return stale  # RNF-3: degraded mode
            raise UpstreamUnavailable(path) from None
        await self._cache.set(key, data, self._ttl)
        return data

    async def get_games(
        self,
        category: str | None = None,
        platform: str | None = None,
        sort_by: str | None = None,
    ) -> list[dict]:
        params: dict[str, Any] = {}
        if category:
            params["category"] = category.lower()
        if platform:
            params["platform"] = platform
        if sort_by:
            params["sort-by"] = sort_by
        key = f"ftg:games:{params.get('category','-')}:{params.get('platform','-')}:{params.get('sort-by','-')}"
        data = await self._cached_get(key, "/games", params)
        return data if isinstance(data, list) else []

    async def get_game(self, game_id: int) -> dict | None:
        data = await self._cached_get(f"ftg:game:{game_id}", "/game", {"id": game_id})
        # API returns {"status":0,"status_message":"..."} for unknown ids
        if not isinstance(data, dict) or "id" not in data:
            return None
        return data
