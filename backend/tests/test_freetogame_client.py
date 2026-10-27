"""RNF-2 (cache) and RNF-3 (stale fallback) for FreeToGameClient, using httpx.MockTransport + in-memory cache."""
import asyncio

import httpx
import pytest

from app.services.freetogame import FreeToGameClient, UpstreamUnavailable


class MemCache:
    def __init__(self):
        self.fresh, self.stale = {}, {}

    async def get(self, k): return self.fresh.get(k)
    async def get_stale(self, k): return self.stale.get(k)
    async def set(self, k, v, ttl): self.fresh[k] = v; self.stale[k] = v


def make(handler, cache=None):
    c = FreeToGameClient("https://x.test/api", cache or MemCache(), ttl=60)
    c._http = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://x.test/api")
    return c


def test_sort_by_hyphen_param_and_cache_hit():
    seen = []

    def handler(req):
        seen.append(req.url.params)
        return httpx.Response(200, json=[{"id": 1}])

    c = make(handler)
    assert asyncio.run(c.get_games("Shooter", "pc", "popularity")) == [{"id": 1}]
    assert asyncio.run(c.get_games("Shooter", "pc", "popularity")) == [{"id": 1}]
    assert len(seen) == 1  # second call served from cache
    assert seen[0]["sort-by"] == "popularity" and seen[0]["category"] == "shooter"


def test_stale_fallback_when_upstream_down():
    cache = MemCache()
    ok = make(lambda r: httpx.Response(200, json=[{"id": 7}]), cache)
    asyncio.run(ok.get_games("pvp"))
    cache.fresh.clear()  # TTL expired
    down = make(lambda r: httpx.Response(500), cache)
    assert asyncio.run(down.get_games("pvp")) == [{"id": 7}]


def test_raises_when_down_and_no_stale():
    with pytest.raises(UpstreamUnavailable):
        asyncio.run(make(lambda r: httpx.Response(500)).get_games())


def test_unknown_game_returns_none():
    c = make(lambda r: httpx.Response(200, json={"status": 0, "status_message": "no game"}))
    assert asyncio.run(c.get_game(999999)) is None
