"""User helpers. STATUS: done (OAuth upsert tested against Postgres in session 6; unit tests mock it)."""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.providers import OAuthProfile
from app.db.models import User, UserIdentity


async def ensure_user(db: AsyncSession, user_id: UUID) -> None:
    """Dev-auth only (ALLOW_DEV_AUTH): creates a placeholder row for an X-User-Id that has no user yet."""
    await db.execute(insert(User).values(id=user_id, email=f"{user_id}@dev.local").on_conflict_do_nothing())


async def get_user(db: AsyncSession, user_id: UUID) -> User | None:
    return await db.get(User, user_id)


async def upsert_oauth_user(db: AsyncSession, p: OAuthProfile, _retry: bool = True) -> UUID:
    """Resolve an OAuth login to a user id.
    1) known (provider, provider_user_id) -> that user (refresh name/avatar);
    2) else a user with the same VERIFIED email -> link this identity to it (caller guarantees email_verified);
    3) else create user + identity. The caller must have checked that p.email is present and verified."""
    assert p.email and p.email_verified, "caller must reject unverified/missing emails"
    email = p.email.strip().lower()
    try:
        ident = await db.get(UserIdentity, (p.provider, p.provider_user_id))
        if ident:
            user = await db.get(User, ident.user_id)
        else:
            user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
            if user is None:
                user = User(email=email, name=p.name, avatar_url=p.avatar_url)
                db.add(user)
                await db.flush()
            db.add(UserIdentity(provider=p.provider, provider_user_id=p.provider_user_id, user_id=user.id))
        if p.name and user.name != p.name:
            user.name = p.name
        if p.avatar_url and user.avatar_url != p.avatar_url:
            user.avatar_url = p.avatar_url
        await db.commit()
        return user.id
    except IntegrityError:  # two first-logins racing: retry once, the winner's rows now exist
        await db.rollback()
        if not _retry:
            raise
        return await upsert_oauth_user(db, p, _retry=False)
