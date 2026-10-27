"""FastAPI dependencies.

TODO(P1-04): REAL AUTH. `get_current_user_id` is a DEV STUB that trusts an `X-User-Id` header.
It MUST be replaced (JWT / session cookie / magic link) before any deployment. Auth method is an
open decision (docs/HANDOFF.md, Q-01). The SRS lists an "Auth & User Service" but gives no requirements.
"""
from uuid import UUID

from fastapi import Header, HTTPException, Request

from app.services.freetogame import FreeToGameClient


def get_ftg(request: Request) -> FreeToGameClient:
    return request.app.state.ftg


async def get_current_user_id(x_user_id: str | None = Header(default=None)) -> UUID:
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Missing X-User-Id (dev auth stub)")
    try:
        return UUID(x_user_id)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid X-User-Id") from None


def get_llm_provider(request: Request):
    """Lazily build the LLM provider; 503 if not configured (keeps the catalog usable without keys)."""
    from app.config import get_settings
    from app.llm.providers import get_provider

    if getattr(request.app.state, "provider", None) is None:
        s = get_settings()
        key = s.openai_api_key if s.llm_provider == "openai" else s.anthropic_api_key
        if not key:
            raise HTTPException(status_code=503, detail="LLM not configured (missing API key)")
        try:
            request.app.state.provider = get_provider(s)
        except NotImplementedError as e:
            raise HTTPException(status_code=503, detail=str(e)) from None
    return request.app.state.provider
