"""SQLAlchemy models mirroring SRS section 6 DDL (+ 1 documented extension).

STATUS: done (skeleton). The SQL files in backend/migrations/ are the CANONICAL schema;
keep these models in sync by hand (no Alembic yet, see docs/HANDOFF.md decision D-04).
EXTENSION (not in SRS): UserPreferenceProfile, needed by RF-3.2 to store LLM-extracted chat preferences.
"""
import uuid
from datetime import date, datetime

from sqlalchemy import ARRAY, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


def _now() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now())


class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = _uuid_pk()
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    created_at: Mapped[datetime] = _now()


class Game(Base):
    __tablename__ = "games"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    thumbnail: Mapped[str | None] = mapped_column(Text)
    short_description: Mapped[str | None] = mapped_column(Text)
    genre: Mapped[str | None] = mapped_column(String(100))
    platform: Mapped[str | None] = mapped_column(String(50))
    publisher: Mapped[str | None] = mapped_column(String(100))
    developer: Mapped[str | None] = mapped_column(String(100))
    release_date: Mapped[date | None] = mapped_column(Date)
    freetogame_profile_url: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = _now()


class UserGameInteraction(Base):
    __tablename__ = "user_game_interactions"
    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"))
    interaction_type: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = _now()


class ChatSession(Base):
    __tablename__ = "chat_sessions"
    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = _now()


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id: Mapped[uuid.UUID] = _uuid_pk()
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chat_sessions.id", ondelete="CASCADE"))
    sender: Mapped[str] = mapped_column(String(20), nullable=False)  # user|assistant|system|tool
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # Convention (D-06): assistant rows -> {"tool_calls":[{id,name,arguments}]}; tool rows -> {"tool_call_id","name"}
    tool_calls: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = _now()


class DailyRecommendation(Base):
    __tablename__ = "daily_recommendations"
    __table_args__ = (UniqueConstraint("user_id", "recommendation_date"),)
    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    recommendation_date: Mapped[date] = mapped_column(Date, nullable=False)
    game_ids: Mapped[list[int]] = mapped_column(ARRAY(Integer), nullable=False)
    created_at: Mapped[datetime] = _now()


class UserPreferenceProfile(Base):
    """EXTENSION: LLM-extracted chat preferences, e.g. {"genres": {"mmorpg": 0.8}, "platform": "pc"}."""
    __tablename__ = "user_preference_profiles"
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    preferences: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    updated_at: Mapped[datetime] = _now()
