"""Pydantic API schemas + shared enums (single source of truth for filter values, RF-1.2)."""
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

Platform = Literal["pc", "browser", "all"]
SortBy = Literal["release-date", "popularity", "alphabetical", "relevance"]
InteractionType = Literal["view", "click", "saved", "played", "disliked"]

# RF-1.2 static genre filter values
CATEGORIES = [
    "mmorpg", "shooter", "pvp", "moba", "anime", "strategy", "fantasy",
    "sci-fi", "card", "racing", "fighting", "social", "sports",
]


class GameSummary(BaseModel):
    """Subset of FreeToGame /games item fields (extra fields ignored)."""
    model_config = ConfigDict(extra="ignore")

    id: int
    title: str
    thumbnail: str | None = None
    short_description: str | None = None
    game_url: str | None = None
    genre: str | None = None
    platform: str | None = None
    publisher: str | None = None
    developer: str | None = None
    release_date: str | None = None
    freetogame_profile_url: str | None = None


class Screenshot(BaseModel):
    id: int
    image: str


class GameDetail(GameSummary):
    """FreeToGame /game?id= response: summary + description, status, requirements, screenshots."""
    status: str | None = None
    description: str | None = None
    minimum_system_requirements: dict | None = None
    screenshots: list[Screenshot] = Field(default_factory=list)


class InteractionIn(BaseModel):
    game_id: int
    interaction_type: InteractionType


class ChatRequest(BaseModel):
    session_id: UUID | None = None
    message: str = Field(min_length=1, max_length=2000)


class DailyRecommendationsOut(BaseModel):
    date: str
    source: Literal["ml", "fallback_popular"]
    games: list[GameSummary]
