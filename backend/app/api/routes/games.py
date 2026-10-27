"""Catalog endpoints (RF-1.1, RF-1.2, RF-1.3). STATUS: done + tested with a fake client; not yet verified
against the live FreeToGame API (P1-03). TODO(P1-09): server-side pagination (API returns ~400 items)."""
from typing import get_args

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_ftg
from app.schemas import CATEGORIES, GameDetail, GameSummary, Platform, SortBy
from app.services.freetogame import FreeToGameClient, UpstreamUnavailable

router = APIRouter(prefix="/api", tags=["games"])


@router.get("/filters")
async def filters():
    return {"platforms": list(get_args(Platform)), "categories": CATEGORIES, "sort_options": list(get_args(SortBy))}


@router.get("/games", response_model=list[GameSummary])
async def list_games(
    category: str | None = None,
    platform: Platform | None = None,
    sort_by: SortBy | None = None,
    ftg: FreeToGameClient = Depends(get_ftg),
):
    try:
        return await ftg.get_games(category, platform, sort_by)
    except UpstreamUnavailable:
        raise HTTPException(503, "FreeToGame unavailable and no cached copy") from None


@router.get("/games/{game_id}", response_model=GameDetail)
async def get_game(game_id: int, ftg: FreeToGameClient = Depends(get_ftg)):
    try:
        game = await ftg.get_game(game_id)
    except UpstreamUnavailable:
        raise HTTPException(503, "FreeToGame unavailable and no cached copy") from None
    if game is None:
        raise HTTPException(404, "Game not found")
    return game
