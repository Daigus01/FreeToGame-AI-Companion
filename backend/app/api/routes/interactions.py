"""User library + event tracking (RF-1.4, feeds RF-3.2). STATUS: minimal, untested (P1-05).

POST /api/interactions        body {game_id, interaction_type}
GET  /api/library?type=saved  list latest game ids per interaction type
TODO(P1-05): decide semantics - "saved"/"played"/"disliked" are STATE (upsert/toggle, latest wins),
             "view"/"click" are EVENTS (append). Currently everything is append-only.
TODO(P1-05): return 404/409 cleanly if game_id is not in `games` (FK) -> run catalog sync first.
TODO(P1-05): ensure the user row exists (dev stub does not create users).
"""
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id
from app.db.models import UserGameInteraction
from app.db.session import get_session
from app.schemas import InteractionIn, InteractionType

router = APIRouter(prefix="/api", tags=["library"])


@router.post("/interactions", status_code=201)
async def add_interaction(
    body: InteractionIn,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
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
