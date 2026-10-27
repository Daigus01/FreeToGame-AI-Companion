"""GET /api/recommendations/today (RF-3.4). STATUS: implemented, untested against Postgres (P3-04).
Returns the precomputed row when present (source='ml'); otherwise computes the same ranking on the fly
from interactions (source='fallback_popular') so a new user's widget is never empty."""
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id, get_ftg
from app.db.models import DailyRecommendation, UserGameInteraction
from app.db.session import get_session
from app.ml.ranking import build_profile, recommend
from app.schemas import DailyRecommendationsOut
from app.services.freetogame import UpstreamUnavailable
from app.services.recs import to_candidates

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


@router.get("/today", response_model=DailyRecommendationsOut)
async def today(user_id: UUID = Depends(get_current_user_id), session: AsyncSession = Depends(get_session), ftg=Depends(get_ftg)):
    day = datetime.now(timezone.utc).date()
    try:
        games = await ftg.get_games(sort_by="popularity")
    except UpstreamUnavailable:
        raise HTTPException(503, "FreeToGame unavailable and no cached copy") from None
    by_id = {g["id"]: g for g in games if "id" in g}
    row = (await session.execute(
        select(DailyRecommendation).where(DailyRecommendation.user_id == user_id, DailyRecommendation.recommendation_date == day)
    )).scalar_one_or_none()
    if row:
        ids, source = list(row.game_ids), "ml"
    else:
        cands = to_candidates(games)
        inter = (await session.execute(
            select(UserGameInteraction.game_id, UserGameInteraction.interaction_type).where(UserGameInteraction.user_id == user_id)
        )).all()
        profile = build_profile([(g, t) for g, t in inter], {c.id: c for c in cands})
        ids, source = recommend(cands, profile), "fallback_popular"
    return {"date": day.isoformat(), "source": source, "games": [by_id[i] for i in ids if i in by_id]}
