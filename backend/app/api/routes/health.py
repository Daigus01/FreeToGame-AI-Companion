"""STATUS: done. Reports dependency state; always 200 so the frontend can show 'degraded mode' (RNF-3)."""
from fastapi import APIRouter, Request
from sqlalchemy import text

from app.db.session import SessionLocal

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(request: Request):
    redis_ok = db_ok = False
    try:
        redis_ok = bool(await request.app.state.redis.ping())
    except Exception:  # noqa: BLE001
        pass
    try:
        async with SessionLocal() as s:
            await s.execute(text("SELECT 1"))
        db_ok = True
    except Exception:  # noqa: BLE001
        pass
    return {"status": "ok" if redis_ok and db_ok else "degraded", "redis": redis_ok, "db": db_ok}
