"""
EthosNews API — unified FastAPI application entry point.

Starts all routers, configures CORS, and handles startup/shutdown.

Run:
    uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import get_settings
from backend.core.logging_config import setup_logging
from backend.core.db.postgres import init_db

# API routers
from backend.api.feed import router as feed_router
from backend.api.checker import router as checker_router
from backend.api.auth import router as auth_router
from backend.api.pnc import router as pnc_router
from backend.api.clusters import router as clusters_router
from backend.api.leaderboard import router as leaderboard_router
from backend.api.rephrase import router as rephrase_router
from backend.api.engagement import router as engagement_router
from backend.api.voice import router as voice_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown logic."""
    settings = get_settings()
    setup_logging(settings.log_level)
    logger.info("EthosNews API starting up (env=%s)…", settings.environment)

    # Ensure Postgres tables exist
    await init_db()

    # Warm up shared singletons on first request rather than at boot
    # (encoder/nlp are lazy — they load on first use to keep startup fast)
    logger.info("EthosNews API ready.")
    yield
    logger.info("EthosNews API shutting down.")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="EthosNews API",
        description=(
            "Participatory, intent-driven news ecosystem. "
            "PNC filtering · Narrative clustering · Agentic fact-checking · Leaderboard."
        ),
        version="2.0.0",
        lifespan=lifespan,
    )

    # CORS — restrict to configured origins (not wildcard)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ───────────────────────────────────────────────────────────────
    app.include_router(feed_router)
    app.include_router(checker_router)
    app.include_router(auth_router)
    app.include_router(pnc_router)
    app.include_router(clusters_router)
    app.include_router(leaderboard_router)
    app.include_router(rephrase_router)
    app.include_router(engagement_router)
    app.include_router(voice_router)

    @app.get("/health", tags=["System"])
    async def health():
        return {"status": "ok", "environment": settings.environment}

    return app


app = create_app()
