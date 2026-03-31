"""
NüMe API — main FastAPI application.
"""
from __future__ import annotations

from runtime_env import configure_runtime_env

configure_runtime_env()

import logging
from contextlib import asynccontextmanager
from datetime import timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from database import engine
from settings import settings

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Nume API (env=%s)", settings.app_env)

    # Initialize Garmin client if enabled
    if settings.garmin_enabled:
        from garmin_sync import init_garmin_clients
        await init_garmin_clients()
        logger.info("Garmin client initialization complete")

        # Start background sync scheduler
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from garmin_sync import run_scheduled_sync

        scheduler = AsyncIOScheduler(timezone=timezone.utc)
        scheduler.add_job(
            run_scheduled_sync,
            "interval",
            minutes=settings.garmin_sync_interval_min,
            id="garmin_sync",
            replace_existing=True,
        )
        scheduler.start()
        logger.info("Garmin sync scheduler started (interval=%dmin)", settings.garmin_sync_interval_min)
        app.state.scheduler = scheduler

    yield

    # Shutdown
    if hasattr(app.state, "scheduler"):
        app.state.scheduler.shutdown(wait=False)
    await engine.dispose()


app = FastAPI(
    title="NüMe API",
    version="0.1.0",
    description="NüMe health coordination platform API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
from routers.auth import router as auth_router
from routers.profile import router as profile_router
from routers.events import router as events_router
from routers.runs import router as runs_router
from routers.cases import router as cases_router
from routers.interventions import router as interventions_router
from routers.notifications import router as notifications_router
from routers.resources import router as resources_router
from routers.health import router as health_router
from routers.recipes import router as recipes_router
from routers.scenarios import router as scenarios_router
from routers.audit import router as audit_router
from routers.demo import router as demo_router

app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(events_router)
app.include_router(runs_router)
app.include_router(cases_router)
app.include_router(interventions_router)
app.include_router(notifications_router)
app.include_router(resources_router)
app.include_router(health_router)
app.include_router(recipes_router)
app.include_router(scenarios_router)
app.include_router(audit_router)
app.include_router(demo_router)


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "nume-api"}


@app.get("/readyz")
async def readiness_check():
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))

    return {"status": "ok", "service": "nume-api", "database": "ok"}


@app.get("/")
async def root():
    return {"service": "NüMe API", "docs": "/docs"}
