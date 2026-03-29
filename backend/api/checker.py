"""
Fact-Checking API router.

Endpoints:
  POST /article/{article_id}/fact-check  — fact-check a stored article by ID
  POST /fact-check                        — fact-check arbitrary text
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import select, update

from backend.core.auth import get_current_user
from backend.core.db import cache
from backend.core.db.postgres import Article, AsyncSessionLocal, User
from backend.services.fact_checker.fact_checker_engine import FactChecker

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Fact Check"])

# Shared engine instance (loads models once)
_engine: FactChecker | None = None


def _get_engine() -> FactChecker:
    global _engine
    if _engine is None:
        _engine = FactChecker()
    return _engine


class FactCheckTextRequest(BaseModel):
    text: str


def _service_error_detail(exc: Exception) -> str:
    message = str(exc).strip() or exc.__class__.__name__
    lowered = message.lower()

    if any(token in lowered for token in ("api key", "authentication", "unauthorized", "forbidden")):
        return "Fact-check model provider is not configured or rejected credentials."
    if any(token in lowered for token in ("qdrant", "connection refused", "timed out", "timeout", "dns")):
        return "Evidence service is unavailable. Check Qdrant connectivity/config."
    return f"Fact-check pipeline unavailable: {message}"


@router.post("/article/{article_id}/fact-check")
async def fact_check_article(article_id: str, current_user: User = Depends(get_current_user)):
    """
    Fact-check a stored article by its UUID.

    Fetches article content from Postgres, runs the parallel agentic pipeline,
    and caches the result in Redis for 1 hour.
    """
    # Increment counter
    async with AsyncSessionLocal() as session:
        await session.execute(update(User).where(User.id == current_user.id).values(active_participations=User.active_participations + 1))
        await session.commit()

    # Redis cache hit
    cached = await cache.get_cached_fact_check(article_id)
    if cached:
        return {"source": "redis_cache", "article_id": article_id, "result": cached}

    # Fetch article content
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Article).where(Article.id == article_id)
        )
        article = result.scalar_one_or_none()

    if not article:
        raise HTTPException(status_code=404, detail="Article not found.")

    if not article.content or not article.content.strip():
        raise HTTPException(status_code=422, detail="Article has no content to fact-check.")

    try:
        fact_result = await _get_engine().run_full_pipeline(article.content)
    except Exception as exc:
        logger.exception("Fact-check pipeline failed for article_id=%s", article_id)
        raise HTTPException(status_code=503, detail=_service_error_detail(exc)) from exc

    result_dict = fact_result.model_dump()
    result_dict["slop_score"] = article.ai_slop_score
    result_dict["slop_label"] = article.ai_slop_label

    try:
        await cache.set_cached_fact_check(article_id, result_dict)
    except Exception:
        logger.exception("Failed to cache fact-check result for article_id=%s", article_id)

    return {"source": "pipeline", "article_id": article_id, "result": result_dict}


@router.post("/fact-check")
async def fact_check_text(request: FactCheckTextRequest, current_user: User = Depends(get_current_user)):
    """
    Fact-check arbitrary text (e.g. a pasted news snippet).
    No caching — text is ephemeral.
    """
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")

    # Increment counter
    async with AsyncSessionLocal() as session:
        await session.execute(update(User).where(User.id == current_user.id).values(active_participations=User.active_participations + 1))
        await session.commit()

    try:
        fact_result = await _get_engine().run_full_pipeline(request.text)
        return {"source": "pipeline", "result": fact_result.model_dump()}
    except Exception as exc:
        logger.exception("Fact-check pipeline failed for ad-hoc text request.")
        raise HTTPException(status_code=503, detail=_service_error_detail(exc)) from exc
