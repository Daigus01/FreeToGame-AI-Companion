"""STATUS: done (dev-auth helper). Needed until real auth exists (P1-04): creates the user row lazily."""
from uuid import UUID

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User


async def ensure_user(db: AsyncSession, user_id: UUID) -> None:
    await db.execute(insert(User).values(id=user_id, email=f"{user_id}@dev.local").on_conflict_do_nothing())
