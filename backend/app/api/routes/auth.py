"""OAuth login routes (D-11): Google + Discord. STATUS: implemented, tested with mocked providers (tests/test_auth.py).
Real-provider check pending (P1-11, needs client ids/secrets; see docs/OAUTH_SETUP.md).

Flow:  browser -> GET /api/auth/{provider}/login  (sets short-lived state cookie, 302 to provider)
       provider -> GET /api/auth/{provider}/callback?code&state  (verify state, exchange code, upsert user,
       set signed session cookie, 302 to FRONTEND_URL). Failures redirect to FRONTEND_URL/?auth_error=<code>.
Security notes: `state` cookie = CSRF defence; only VERIFIED emails accepted; redirect target is fixed
(FRONTEND_URL), never taken from the request (no open redirect); tokens from the provider are never stored or logged.
TODO(P4-02): rate-limit /login and /callback.
"""
import logging
from typing import Literal
from urllib.parse import urlencode
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id
from app.auth import session as sess
from app.auth.providers import OAuthError, build_authorize_url, fetch_profile, get_providers
from app.config import get_settings
from app.db.session import get_session
from app.services import users as users_svc

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])

ProviderName = Literal["google", "discord"]


def _redirect_uri(provider: str) -> str:
    return f"{get_settings().backend_public_url.rstrip('/')}/api/auth/{provider}/callback"


def _home(error: str | None = None) -> RedirectResponse:
    url = get_settings().frontend_url.rstrip("/") + "/"
    if error:
        url += "?" + urlencode({"auth_error": error})
    return RedirectResponse(url, status_code=302)


@router.get("/providers")
async def providers():
    s = get_settings()
    return {"providers": list(get_providers(s)), "dev_auth": s.allow_dev_auth}


@router.get("/{provider}/login")
async def login(provider: ProviderName):
    s = get_settings()
    spec = get_providers(s).get(provider)
    if spec is None:
        raise HTTPException(404, f"{provider} login is not configured")
    state = sess.new_state()
    resp = RedirectResponse(build_authorize_url(spec, _redirect_uri(provider), state), status_code=302)
    resp.set_cookie(sess.STATE_COOKIE, sess.make_state_cookie(provider, state, s.session_secret),
                    max_age=sess.STATE_MAX_AGE, httponly=True, samesite="lax", secure=s.cookie_secure, path="/")
    return resp


@router.get("/{provider}/callback")
async def callback(provider: ProviderName, request: Request, code: str | None = None, state: str | None = None,
                   error: str | None = None, db: AsyncSession = Depends(get_session)):
    s = get_settings()
    spec = get_providers(s).get(provider)
    if spec is None:
        raise HTTPException(404, f"{provider} login is not configured")
    if error:  # user pressed "cancel" or provider rejected the request
        return _clear_state(_home("cancelled" if error == "access_denied" else "provider_error"))
    if not sess.check_state(request.cookies.get(sess.STATE_COOKIE), provider, state, s.session_secret):
        return _clear_state(_home("state"))
    if not code:
        return _clear_state(_home("provider_error"))
    try:
        profile = await fetch_profile(spec, code, _redirect_uri(provider))
    except OAuthError:
        logger.warning("oauth exchange failed for %s", provider, exc_info=True)
        return _clear_state(_home("provider_error"))
    if not profile.email or not profile.email_verified:
        return _clear_state(_home("email_unverified"))
    user_id = await users_svc.upsert_oauth_user(db, profile)
    resp = _home()
    resp.set_cookie(sess.SESSION_COOKIE, sess.make_session(user_id, s.session_secret), max_age=sess.SESSION_MAX_AGE,
                    httponly=True, samesite="lax", secure=s.cookie_secure, path="/")
    return _clear_state(resp)


def _clear_state(resp: RedirectResponse) -> RedirectResponse:
    resp.delete_cookie(sess.STATE_COOKIE, path="/")
    return resp


@router.get("/me")
async def me(user_id: UUID = Depends(get_current_user_id), db: AsyncSession = Depends(get_session)):
    user = await users_svc.get_user(db, user_id)
    if user is None:  # signed cookie for a user that no longer exists
        raise HTTPException(401, "Not authenticated")
    return {"id": str(user.id), "email": user.email, "name": user.name, "avatar_url": user.avatar_url}


@router.post("/logout")
async def logout():
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(sess.SESSION_COOKIE, path="/")
    return resp
