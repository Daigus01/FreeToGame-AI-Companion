"""User library + event tracking (RF-1.4, feeds RF-3.2). STATUS: minimal, untested (P1-05).

POST /api/interactions        body {game_id, interaction_type}
GET  /api/library?type=saved  list latest game ids per interaction type
TODO(P1-05): decide semantics - "saved"/"played"/"disliked" are STATE (upsert/toggle, latest wins),
             "view"/"click" are EVENTS (append). Currently everything is append-only.
DONE(P1-05, partial): 404 if game_id not in `games`; user row created lazily via ensure_user.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id
from app.db.models import Game, UserGameInteraction
from app.db.session import get_session
from app.schemas import InteractionIn, InteractionType
from app.services.users import ensure_user

router = APIRouter(prefix="/api", tags=["library"])


@router.post("/interactions", status_code=201)
async def add_interaction(
    body: InteractionIn,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    if await session.get(Game, body.game_id) is None:  # FK would 500; run catalog sync first (P1-02)
        raise HTTPException(404, "Game not in local catalog (run catalog sync)")
    await ensure_user(session, user_id)  # dev auth stub never creates users (P1-04 replaces this)
    session.add(UserGameInteraction(user_id=user_id, game_id=body.game_id, interaction_type=body.interaction_type))
    await session.commit()
    return {"ok": True}


@router.get("/library")
async def library(
    type: InteractionType = "saved",
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    rows = await session.execute(
        select(UserGameInteraction.game_id)
        .where(UserGameInteraction.user_id == user_id, UserGameInteraction.interaction_type == type)
        .order_by(UserGameInteraction.created_at.desc())
    )
    return {"type": type, "game_ids": list(dict.fromkeys(rows.scalars().all()))}
