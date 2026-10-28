"""OAuth 2.0 authorization-code flow for Google and Discord (D-11), implemented with httpx (no extra OAuth lib).
STATUS: implemented + unit-tested with mocked HTTP. NOT yet run against the real providers (P1-11: needs credentials).
Only providers with BOTH client id and secret configured are enabled. We only trust VERIFIED emails.
"""
from dataclasses import dataclass

import httpx

from app.config import Settings

UA = "FreeToGameAICompanion/0.1 (+https://github.com/Daigus01/FreeToGame-AI-Companion)"


class OAuthError(Exception):
    """Any failure in the code exchange / profile fetch. Message is safe to log, never shown to users."""


@dataclass(frozen=True)
class ProviderSpec:
    name: str
    authorize_url: str
    token_url: str
    userinfo_url: str
    scope: str
    client_id: str
    client_secret: str
    extra_authorize_params: tuple[tuple[str, str], ...] = ()


@dataclass
class OAuthProfile:
    provider: str
    provider_user_id: str
    email: str | None
    email_verified: bool
    name: str | None
    avatar_url: str | None


def get_providers(s: Settings) -> dict[str, ProviderSpec]:
    specs: dict[str, ProviderSpec] = {}
    if s.google_client_id and s.google_client_secret:
        specs["google"] = ProviderSpec(
            "google", "https://accounts.google.com/o/oauth2/v2/auth", "https://oauth2.googleapis.com/token",
            "https://openidconnect.googleapis.com/v1/userinfo", "openid email profile",
            s.google_client_id, s.google_client_secret, (("prompt", "select_account"),),
        )
    if s.discord_client_id and s.discord_client_secret:
        specs["discord"] = ProviderSpec(
            "discord", "https://discord.com/oauth2/authorize", "https://discord.com/api/oauth2/token",
            "https://discord.com/api/users/@me", "identify email",
            s.discord_client_id, s.discord_client_secret, (("prompt", "none"),),
        )
    return specs


def build_authorize_url(spec: ProviderSpec, redirect_uri: str, state: str) -> str:
    params = {
        "client_id": spec.client_id, "redirect_uri": redirect_uri, "response_type": "code",
        "scope": spec.scope, "state": state, **dict(spec.extra_authorize_params),
    }
    return str(httpx.URL(spec.authorize_url, params=params))


def normalize_google(d: dict) -> OAuthProfile:
    return OAuthProfile("google", str(d["sub"]), d.get("email"), bool(d.get("email_verified")), d.get("name"), d.get("picture"))


def normalize_discord(d: dict) -> OAuthProfile:
    avatar = f"https://cdn.discordapp.com/avatars/{d['id']}/{d['avatar']}.png" if d.get("avatar") else None
    return OAuthProfile("discord", str(d["id"]), d.get("email"), bool(d.get("verified")), d.get("global_name") or d.get("username"), avatar)


_NORMALIZERS = {"google": normalize_google, "discord": normalize_discord}


async def fetch_profile(spec: ProviderSpec, code: str, redirect_uri: str, http: httpx.AsyncClient | None = None) -> OAuthProfile:
    owns = http is None
    http = http or httpx.AsyncClient(timeout=10.0)
    try:
        tok = await http.post(
            spec.token_url,
            data={"grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri,
                  "client_id": spec.client_id, "client_secret": spec.client_secret},
            headers={"Accept": "application/json", "User-Agent": UA},
        )
        if tok.status_code != 200:
            raise OAuthError(f"{spec.name} token exchange failed: HTTP {tok.status_code}")
        access = tok.json().get("access_token")
        if not access:
            raise OAuthError(f"{spec.name} token response without access_token")
        info = await http.get(spec.userinfo_url, headers={"Authorization": f"Bearer {access}", "User-Agent": UA})
        if info.status_code != 200:
            raise OAuthError(f"{spec.name} userinfo failed: HTTP {info.status_code}")
        try:
            return _NORMALIZERS[spec.name](info.json())
        except (KeyError, ValueError, TypeError) as e:
            raise OAuthError(f"{spec.name} unexpected userinfo shape") from e
    except httpx.HTTPError as e:
        raise OAuthError(f"{spec.name} network error: {type(e).__name__}") from e
    finally:
        if owns:
            await http.aclose()
