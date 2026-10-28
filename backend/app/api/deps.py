"""FastAPI dependencies.

Auth (D-11): the user is identified by the signed `ftg_session` cookie set after an OAuth login
(app/api/routes/auth.py). The old `X-User-Id` header is accepted ONLY when ALLOW_DEV_AUTH=true (local dev).
"""
from uuid import UUID

from fastapi import Header, HTTPException, Request

from app.auth.session import SESSION_COOKIE, SESSION_MAX_AGE, read_session
from app.config import get_settings
from app.services.freetogame import FreeToGameClient


def get_ftg(request: Request) -> FreeToGameClient:
    return request.app.state.ftg


async def get_current_user_id(request: Request, x_user_id: str | None = Header(default=None)) -> UUID:
    st = get_settings()
    uid = read_session(request.cookies.get(SESSION_COOKIE), st.session_secret, SESSION_MAX_AGE)
    if uid:
        return uid
    if st.allow_dev_auth and x_user_id:
        try:
            return UUID(x_user_id)
        except ValueError:
            raise HTTPException(status_code=401, detail="Invalid X-User-Id") from None
    raise HTTPException(status_code=401, detail="Not authenticated")


def get_llm_provider(request: Request):
    """Lazily build the LLM provider; 503 if not configured (keeps the catalog usable without keys)."""
    from app.llm.providers import get_provider

    if getattr(request.app.state, "provider", None) is None:
        s = get_settings()
        key = {"openai": s.openai_api_key, "anthropic": s.anthropic_api_key, "mock": "n/a"}.get(s.llm_provider, "")
        if not key:
            raise HTTPException(status_code=503, detail="LLM not configured (missing API key)")
        try:
            request.app.state.provider = get_provider(s)
        except NotImplementedError as e:
            raise HTTPException(status_code=503, detail=str(e)) from None
    return request.app.state.provider
