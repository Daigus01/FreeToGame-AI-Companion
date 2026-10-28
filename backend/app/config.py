"""Settings from environment (RNF-4: secrets live ONLY in backend env, never in the frontend).
STATUS: done. Rewritten 2026-10-27 after being accidentally overwritten; field names are the ones the
rest of the code uses (see docs/PROGRESS.md, incident I-01)."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://ftg:ftg@localhost:5432/ftg"
    redis_url: str = "redis://localhost:6379/0"
    freetogame_base_url: str = "https://www.freetogame.com/api"
    freetogame_cache_ttl_seconds: int = 12 * 60 * 60  # RNF-2
    cors_origins: str = "http://localhost:3000"

    llm_provider: str = "openai"  # openai | anthropic (D-02)
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-5-5"

    # --- Auth (D-11: OAuth with Google + Discord only; session in a signed HttpOnly cookie) ---
    session_secret: str = "dev-insecure-change-me"  # MUST be changed outside local dev (startup warns)
    cookie_secure: bool = False  # true when served over HTTPS
    frontend_url: str = "http://localhost:3000"  # where the browser lands after login
    backend_public_url: str = "http://localhost:8000"  # base of the OAuth redirect URIs
    allow_dev_auth: bool = False  # accept the X-User-Id header (local dev only, never in production)
    google_client_id: str = ""
    google_client_secret: str = ""
    discord_client_id: str = ""
    discord_client_secret: str = ""

    enable_scheduler: bool = True  # set false in tests / extra replicas (D-08)
    recs_cron_hour: int = 0  # RF-3.1: 00:00 UTC
    recs_cron_minute: int = 0


@lru_cache
def get_settings() -> Settings:
    return Settings()
