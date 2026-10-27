"""Sync the local `games` table from FreeToGame (needed for FK integrity of interactions + ML job).

STATUS: implemented, untested (TODO P1-02). Run manually:  python -m app.services.catalog_sync
TODO(P1-02): also schedule it (e.g. daily, before the 00:00 UTC ML job).
"""
import asyncio
import logging
from datetime import date

from sqlalchemy.dialects.postgresql import insert

from app.config import get_settings
from app.core.cache import JsonCache, make_redis
from app.db.models import Game
from app.db.session import SessionLocal
from app.services.freetogame import FreeToGameClient

logger = logging.getLogger(__name__)


def _parse_date(value: str | None) -> date | None:
    try:
        return date.fromisoformat(value) if value else None
    except ValueError:
        return None


def to_game_row(g: dict) -> dict:
    return {
        "id": g["id"],
        "title": g.get("title", "")[:255],
        "thumbnail": g.get("thumbnail"),
        "short_description": g.get("short_description"),
        "genre": (g.get("genre") or None),
        "platform": g.get("platform"),
        "publisher": g.get("publisher"),
        "developer": g.get("developer"),
        "release_date": _parse_date(g.get("release_date")),
        "freetogame_profile_url": g.get("freetogame_profile_url"),
    }


async def sync_catalog(client: FreeToGameClient) -> int:
    games = await client.get_games()
    rows = [to_game_row(g) for g in games if "id" in g]
    if not rows:
        return 0
    async with SessionLocal() as session:
        stmt = insert(Game).values(rows)
        update_cols = {c: stmt.excluded[c] for c in rows[0] if c != "id"}
        await session.execute(stmt.on_conflict_do_update(index_elements=["id"], set_=update_cols))
        await session.commit()
    return len(rows)


async def _main() -> None:
    s = get_settings()
    redis = make_redis(s.redis_url)
    client = FreeToGameClient(s.freetogame_base_url, JsonCache(redis), s.freetogame_cache_ttl_seconds)
    try:
        n = await sync_catalog(client)
        print(f"synced {n} games")
    finally:
        await client.aclose()
        await redis.aclose()


if __name__ == "__main__":
    asyncio.run(_main())
