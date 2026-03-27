"""
Fact-Checking API router.

Endpoints:
  POST /article/{article_id}/fact-check  — fact-check a stored article by ID
  POST /fact-check                        — fact-check arbitrary text
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from backend.core.db import cache
from backend.core.db.postgres import Article, AsyncSessionLocal
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


@router.post("/article/{article_id}/fact-check")
async def fact_check_article(article_id: str):
    """
    Fact-check a stored article by its UUID.

    Fetches article content from Postgres, runs the parallel agentic pipeline,
    and caches the result in Redis for 1 hour.
    """
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

    fact_result = await _get_engine().run_full_pipeline(article.content)
    result_dict = fact_result.model_dump()

    await cache.set_cached_fact_check(article_id, result_dict)
    return {"source": "pipeline", "article_id": article_id, "result": result_dict}


@router.post("/fact-check")
async def fact_check_text(request: FactCheckTextRequest):
    """
    Fact-check arbitrary text (e.g. a pasted news snippet).
    No caching — text is ephemeral.
    """
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")

    fact_result = await _get_engine().run_full_pipeline(request.text)
    return {"source": "pipeline", "result": fact_result.model_dump()}
