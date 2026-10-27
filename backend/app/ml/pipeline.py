"""Daily Top-5 batch (RF-3.1). Scored by app/ml/ranking.py (pure). Scheduled by app/ml/scheduler.py.

STATUS: implemented, UNTESTED against a real Postgres (TODO P3-03). Idempotent: re-running the same
day overwrites that day's row (UNIQUE(user_id, recommendation_date) + upsert).
Known limits: N+1 queries per user (fine for MVP) -> TODO(P3-06) batch queries / swap in `implicit`.
Candidates come from FreeToGame (cached, sort-by=popularity gives popularity_rank); if upstream is down and
no stale copy exists we fall back to the local `games` table (RNF-3), ranked by id.
TODO(P3-01): preferences from chat are READ here (user_preference_profiles) but nothing WRITES them yet.
"""
import logging
from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DailyRecommendation, Game, User, UserGameInteraction, UserPreferenceProfile
from app.ml.ranking import Candidate, build_profile, recommend
from app.services.freetogame import UpstreamUnavailable
from app.services.recs import to_candidates

logger = logging.getLogger(__name__)


async def load_candidates(session: AsyncSession, client) -> list[Candidate]:
    try:
        return to_candidates(await client.get_games(sort_by="popularity"))
    except UpstreamUnavailable:
        rows = (await session.execute(select(Game).order_by(Game.id))).scalars().all()
        return [Candidate(r.id, r.genre, r.platform, i) for i, r in enumerate(rows)]


async def run_daily_pipeline(session: AsyncSession, client, today: date | None = None) -> int:
    """Returns number of users that received a Top 5."""
    today = today or datetime.now(timezone.utc).date()
    candidates = await load_candidates(session, client)
    if not candidates:
        logger.warning("daily pipeline: no candidates, skipping")
        return 0
    by_id = {c.id: c for c in candidates}
    done = 0
    for user_id in (await session.execute(select(User.id))).scalars().all():
        try:
            inter = (
                await session.execute(
                    select(UserGameInteraction.game_id, UserGameInteraction.interaction_type)
                    .where(UserGameInteraction.user_id == user_id)
                    .order_by(UserGameInteraction.created_at)
                )
            ).all()
            prefs_row = await session.get(UserPreferenceProfile, user_id)
            profile = build_profile([(g, t) for g, t in inter], by_id, prefs_row.preferences if prefs_row else None)
            ids = recommend(candidates, profile)
            if not ids:
                continue
            stmt = insert(DailyRecommendation).values(user_id=user_id, recommendation_date=today, game_ids=ids)
            await session.execute(
                stmt.on_conflict_do_update(
                    index_elements=["user_id", "recommendation_date"],
                    set_={"game_ids": stmt.excluded.game_ids, "created_at": func.now()},
                )
            )
            await session.commit()
            done += 1
        except Exception:  # noqa: BLE001 - one bad user must not abort the batch
            await session.rollback()
            logger.exception("daily pipeline failed for user %s", user_id)
    logger.info("daily pipeline: %s users processed for %s", done, today)
    return done
