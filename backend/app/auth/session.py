"""Signed session + OAuth-state cookies (itsdangerous). STATUS: done + tested (tests/test_auth.py).
Cookies are HttpOnly + SameSite=Lax. The session value only carries the user id; it is NOT encrypted
(not secret), it is signed so it cannot be forged without SESSION_SECRET."""
import hmac
import secrets
from uuid import UUID

from itsdangerous import BadSignature, URLSafeTimedSerializer

SESSION_COOKIE = "ftg_session"
STATE_COOKIE = "ftg_oauth_state"
SESSION_MAX_AGE = 30 * 24 * 3600
STATE_MAX_AGE = 10 * 60


def _ser(secret: str, salt: str) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(secret, salt=salt)


def make_session(user_id: UUID, secret: str) -> str:
    return _ser(secret, "session").dumps({"uid": str(user_id)})


def read_session(token: str | None, secret: str, max_age: int = SESSION_MAX_AGE) -> UUID | None:
    if not token:
        return None
    try:
        return UUID(_ser(secret, "session").loads(token, max_age=max_age)["uid"])
    except (BadSignature, KeyError, ValueError, TypeError):
        return None


def new_state() -> str:
    return secrets.token_urlsafe(24)


def make_state_cookie(provider: str, state: str, secret: str) -> str:
    return _ser(secret, "oauth-state").dumps({"p": provider, "s": state})


def check_state(cookie: str | None, provider: str, state: str | None, secret: str, max_age: int = STATE_MAX_AGE) -> bool:
    """CSRF check: the `state` echoed by the provider must match the one we put in the browser's cookie."""
    if not cookie or not state:
        return False
    try:
        data = _ser(secret, "oauth-state").loads(cookie, max_age=max_age)
    except BadSignature:
        return False
    return data.get("p") == provider and hmac.compare_digest(str(data.get("s", "")), state)
