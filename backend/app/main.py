"""FastAPI entry point. STATUS: done (wiring only). Run: uvicorn app.main:app --reload"""
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, chat, games, health, interactions, recommendations
from app.config import get_settings
from app.core.cache import JsonCache, make_redis
from app.db.session import engine
from app.ml.scheduler import build_scheduler
from app.services.freetogame import FreeToGameClient


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    if s.session_secret == "dev-insecure-change-me":
        if s.cookie_secure:
            raise RuntimeError("SESSION_SECRET must be set when COOKIE_SECURE=true")
        logging.getLogger(__name__).warning("SESSION_SECRET is the insecure dev default: set it in .env")
    if s.allow_dev_auth:
        logging.getLogger(__name__).warning("ALLOW_DEV_AUTH=true: X-User-Id header is trusted. Never in production.")
    app.state.redis = make_redis(s.redis_url)
    app.state.ftg = FreeToGameClient(s.freetogame_base_url, JsonCache(app.state.redis), s.freetogame_cache_ttl_seconds)
    app.state.provider = None  # lazy, see api/deps.get_llm_provider
    scheduler = None
    if s.enable_scheduler:
        scheduler = build_scheduler(s, app.state.ftg)  # RF-3.1
        scheduler.start()
    yield
    if scheduler:
        scheduler.shutdown(wait=False)
    await app.state.ftg.aclose()
    await app.state.redis.aclose()
    await engine.dispose()


app = FastAPI(title="FreeToGame AI Companion", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=get_settings().cors_origins.split(","), allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])
for r in (health.router, auth.router, games.router, interactions.router, chat.router, recommendations.router):
    app.include_router(r)
