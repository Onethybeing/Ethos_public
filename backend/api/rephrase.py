"""
Rephrase API router.

Endpoints:
  GET /article/{article_id}/rephrase  — return a rephrased version of the article body
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from backend.core.db import cache
from backend.core.db.postgres import Article, AsyncSessionLocal
from backend.core.llm import get_llm

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Rephrase"])

_REPHRASE_SYSTEM = (
    "You are a professional copy editor. "
    "Rephrase the article below using entirely different words and sentence structures "
    "while preserving the exact same length, all factual claims, every named person, "
    "every date, every quoted statement, and all numerical figures. "
    "Do not add commentary, analysis, opinions, or any text that was not in the original. "
    "Return only the rephrased article body — no headings, no preamble."
)


@router.get("/article/{article_id}/rephrase")
async def rephrase_article(article_id: str):
    """
    Return a rephrased version of an article's body text.

    Checks Redis (TTL 24 h) first. On miss: fetches content from Postgres,
    calls the fast LLM tier with a strict fidelity prompt, caches, and returns
    { rephrased_content, source_url }.
    """
    cached = await cache.get_cached_rephrase(article_id)
    if cached:
        return {"source": "redis_cache", **cached}

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Article).where(Article.id == article_id)
        )
        article = result.scalar_one_or_none()

    if not article:
        raise HTTPException(status_code=404, detail="Article not found.")

    if not article.content or not article.content.strip():
        raise HTTPException(status_code=422, detail="Article has no content to rephrase.")

    try:
        rephrased = await get_llm().chat(
            messages=[
                {"role": "system", "content": _REPHRASE_SYSTEM},
                {"role": "user",   "content": article.content},
            ],
            model_tier="fast",
            temperature=0.4,
        )
    except Exception as exc:
        logger.exception("Rephrase LLM call failed for article_id=%s", article_id)
        raise HTTPException(
            status_code=503,
            detail=f"Rephrase service unavailable: {exc}",
        ) from exc

    payload = {
        "article_id": article_id,
        "rephrased_content": rephrased.strip(),
        "source_url": article.url,
    }

    try:
        await cache.set_cached_rephrase(article_id, payload)
    except Exception:
        logger.exception("Failed to cache rephrase result for article_id=%s", article_id)

    return {"source": "pipeline", **payload}
