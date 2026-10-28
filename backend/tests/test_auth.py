"""OAuth (D-11) tests: session/state signing, provider normalisation, token exchange (mock HTTP), routes, deps."""
import asyncio
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user_id
from app.auth import session as sess
from app.auth.providers import (OAuthError, OAuthProfile, build_authorize_url, fetch_profile, get_providers,
                                normalize_discord, normalize_google)
from app.config import Settings, get_settings
from app.db.session import get_session
from app.main import app

SECRET = "test-secret"
UID = UUID("11111111-1111-1111-1111-111111111111")


@pytest.fixture(autouse=True)
def env(monkeypatch):
    for k, v in {"SESSION_SECRET": SECRET, "GOOGLE_CLIENT_ID": "gid", "GOOGLE_CLIENT_SECRET": "gsec",
                 "DISCORD_CLIENT_ID": "did", "DISCORD_CLIENT_SECRET": "dsec", "FRONTEND_URL": "http://front.test",
                 "BACKEND_PUBLIC_URL": "http://api.test", "ALLOW_DEV_AUTH": "false"}.items():
        monkeypatch.setenv(k, v)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


# ---------- session / state ----------
def test_session_roundtrip_tamper_and_expiry():
    tok = sess.make_session(UID, SECRET)
    assert sess.read_session(tok, SECRET) == UID
    assert sess.read_session(tok, "other-secret") is None
    assert sess.read_session(tok[:-2] + "xx", SECRET) is None
    assert sess.read_session(tok, SECRET, max_age=-1) is None
    assert sess.read_session(None, SECRET) is None and sess.read_session("garbage", SECRET) is None


def test_state_check():
    c = sess.make_state_cookie("google", "abc", SECRET)
    assert sess.check_state(c, "google", "abc", SECRET)
    assert not sess.check_state(c, "discord", "abc", SECRET)  # provider mismatch
    assert not sess.check_state(c, "google", "zzz", SECRET)
    assert not sess.check_state(None, "google", "abc", SECRET) and not sess.check_state(c, "google", None, SECRET)
    assert not sess.check_state(sess.make_session(UID, SECRET), "google", "abc", SECRET)  # wrong cookie type (salt)


# ---------- providers ----------
def test_only_configured_providers_enabled():
    none = dict(discord_client_id="", discord_client_secret="")
    assert set(get_providers(Settings(google_client_id="a", google_client_secret="b", **none))) == {"google"}
    assert get_providers(Settings(google_client_id="a", google_client_secret="", **none)) == {}  # id without secret -> disabled


def test_authorize_url():
    spec = get_providers(get_settings())["discord"]
    u = httpx.URL(build_authorize_url(spec, "http://api.test/cb", "st8"))
    assert u.host == "discord.com" and u.params["state"] == "st8" and u.params["scope"] == "identify email"
    assert u.params["redirect_uri"] == "http://api.test/cb" and u.params["response_type"] == "code"


def test_normalizers():
    g = normalize_google({"sub": 7, "email": "a@x.com", "email_verified": True, "name": "A", "picture": "p"})
    assert (g.provider, g.provider_user_id, g.email_verified, g.avatar_url) == ("google", "7", True, "p")
    d = normalize_discord({"id": "9", "username": "u", "global_name": "G", "avatar": "h", "email": "d@x.com", "verified": True})
    assert d.name == "G" and d.avatar_url == "https://cdn.discordapp.com/avatars/9/h.png" and d.email_verified
    assert not normalize_discord({"id": "9", "username": "u", "email": "d@x.com", "verified": False}).email_verified
    assert normalize_discord({"id": "9", "username": "u"}).avatar_url is None


def _mock(token_status=200, info_status=200, info=None):
    seen = {}

    def handler(req: httpx.Request):
        if req.url.path.endswith("token"):
            seen["token_form"] = dict(httpx.QueryParams(req.content.decode()))
            return httpx.Response(token_status, json={"access_token": "AT"} if token_status == 200 else {})
        seen["auth"] = req.headers.get("authorization")
        return httpx.Response(info_status, json=info or {"sub": "1", "email": "a@x.com", "email_verified": True})

    return httpx.AsyncClient(transport=httpx.MockTransport(handler)), seen


def test_fetch_profile_ok_sends_form_and_bearer():
    http, seen = _mock()
    spec = get_providers(get_settings())["google"]
    p = asyncio.run(fetch_profile(spec, "CODE", "http://api.test/cb", http))
    assert p.email == "a@x.com" and seen["auth"] == "Bearer AT"
    assert seen["token_form"]["code"] == "CODE" and seen["token_form"]["grant_type"] == "authorization_code"


@pytest.mark.parametrize("kw", [{"token_status": 400}, {"info_status": 401}, {"info": {"weird": 1}}])
def test_fetch_profile_errors(kw):
    http, _ = _mock(**kw)
    with pytest.raises(OAuthError):
        asyncio.run(fetch_profile(get_providers(get_settings())["google"], "C", "http://x/cb", http))


# ---------- routes ----------
class FakeUser:
    id, email, name, avatar_url = UID, "a@x.com", "A", None


@pytest.fixture
def client(monkeypatch):
    async def fake_session():
        yield None

    app.dependency_overrides[get_session] = fake_session
    monkeypatch.setattr("app.api.routes.auth.users_svc.get_user", lambda db, uid: _async(FakeUser() if uid == UID else None))
    yield TestClient(app, follow_redirects=False)
    app.dependency_overrides.pop(get_session, None)


async def _a(v):
    return v


def _async(v):
    return _a(v)


def test_providers_endpoint(client):
    assert client.get("/api/auth/providers").json() == {"providers": ["google", "discord"], "dev_auth": False}


def test_login_redirects_and_sets_state_cookie(client):
    r = client.get("/api/auth/google/login")
    assert r.status_code == 302 and r.headers["location"].startswith("https://accounts.google.com/")
    loc = httpx.URL(r.headers["location"])
    assert loc.params["redirect_uri"] == "http://api.test/api/auth/google/callback"
    assert sess.check_state(r.cookies.get(sess.STATE_COOKIE), "google", loc.params["state"], SECRET)
    assert "httponly" in r.headers["set-cookie"].lower()


def test_unknown_or_unconfigured_provider(client, monkeypatch):
    assert client.get("/api/auth/github/login").status_code == 422  # not in Literal
    monkeypatch.setenv("DISCORD_CLIENT_SECRET", ""); get_settings.cache_clear()
    assert client.get("/api/auth/discord/login").status_code == 404


def _login_state(client):
    r = client.get("/api/auth/google/login")
    return httpx.URL(r.headers["location"]).params["state"]


def test_callback_success_sets_session_and_me_works(client, monkeypatch):
    async def fake_fetch(spec, code, redirect_uri, http=None):
        assert code == "C" and redirect_uri == "http://api.test/api/auth/google/callback"
        return OAuthProfile("google", "1", "a@x.com", True, "A", None)

    monkeypatch.setattr("app.api.routes.auth.fetch_profile", fake_fetch)
    monkeypatch.setattr("app.api.routes.auth.users_svc.upsert_oauth_user", lambda db, p: _async(UID))
    st = _login_state(client)
    r = client.get("/api/auth/google/callback", params={"code": "C", "state": st})
    assert r.status_code == 302 and r.headers["location"] == "http://front.test/"
    assert sess.read_session(client.cookies.get(sess.SESSION_COOKIE), SECRET) == UID
    assert client.get("/api/auth/me").json()["email"] == "a@x.com"
    client.post("/api/auth/logout")
    assert client.get("/api/auth/me").status_code == 401


@pytest.mark.parametrize("params,cookie_state,err", [
    ({"code": "C", "state": "forged"}, True, "state"),
    ({"code": "C"}, True, "state"),
    ({"code": "C", "state": "x"}, False, "state"),
    ({"error": "access_denied"}, True, "cancelled"),
])
def test_callback_rejections(client, params, cookie_state, err):
    if cookie_state:
        _login_state(client)
    r = client.get("/api/auth/google/callback", params=params)
    assert r.status_code == 302 and r.headers["location"] == f"http://front.test/?auth_error={err}"
    assert sess.SESSION_COOKIE not in client.cookies


def test_callback_unverified_email_and_provider_failure(client, monkeypatch):
    async def unverified(*a, **k): return OAuthProfile("google", "1", "a@x.com", False, "A", None)
    async def boom(*a, **k): raise OAuthError("x")
    called = []
    monkeypatch.setattr("app.api.routes.auth.users_svc.upsert_oauth_user", lambda db, p: called.append(p) or _async(UID))
    for fn, err in ((unverified, "email_unverified"), (boom, "provider_error")):
        monkeypatch.setattr("app.api.routes.auth.fetch_profile", fn)
        st = _login_state(client)
        r = client.get("/api/auth/google/callback", params={"code": "C", "state": st})
        assert r.headers["location"].endswith(f"auth_error={err}")
    assert called == []  # never created a user


# ---------- dependency ----------
def _dep_client():
    a = FastAPI()

    @a.get("/whoami")
    async def whoami(uid: UUID = Depends(get_current_user_id)):
        return {"uid": str(uid)}

    return TestClient(a)


def test_dep_cookie_ok_header_rejected_by_default():
    c = _dep_client()
    assert c.get("/whoami").status_code == 401
    assert c.get("/whoami", headers={"X-User-Id": str(uuid4())}).status_code == 401  # dev auth is off
    c.cookies.set(sess.SESSION_COOKIE, sess.make_session(UID, SECRET))
    assert c.get("/whoami").json() == {"uid": str(UID)}


def test_dep_dev_header_only_when_enabled(monkeypatch):
    monkeypatch.setenv("ALLOW_DEV_AUTH", "true"); get_settings.cache_clear()
    c = _dep_client()
    assert c.get("/whoami", headers={"X-User-Id": str(UID)}).json() == {"uid": str(UID)}
    assert c.get("/whoami", headers={"X-User-Id": "nope"}).status_code == 401


def test_forged_cookie_rejected():
    c = _dep_client()
    c.cookies.set(sess.SESSION_COOKIE, sess.make_session(UID, "attacker-secret"))
    assert c.get("/whoami").status_code == 401
