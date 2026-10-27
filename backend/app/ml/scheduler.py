"""APScheduler wiring for the daily job at 00:00 UTC (RF-3.1). STATUS: implemented, untested (P3-03).

NOTE (D-08): in-process scheduler is fine for a single backend instance. With >1 replicas, either run
the scheduler in a dedicated worker container or switch to Celery beat (SRS allows both).
"""
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import Settings
from app.db.session import SessionLocal
from app.ml.pipeline import run_daily_pipeline
from app.services.freetogame import FreeToGameClient

logger = logging.getLogger(__name__)


def build_scheduler(settings: Settings, client: FreeToGameClient) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="UTC")

    async def job() -> None:
        async with SessionLocal() as session:
            await run_daily_pipeline(session, client)

    scheduler.add_job(
        job,
        CronTrigger(hour=settings.recs_cron_hour, minute=settings.recs_cron_minute, timezone="UTC"),
        id="daily_recommendations",
        replace_existing=True,
    )
    return scheduler
