"""
Feed API router.

Endpoints:
  GET /feed                          — top 50 latest articles (Redis → Postgres)
  GET /article/{article_id}          — single article by UUID
  GET /personalized_feed/{user_id}   — PNC-filtered, recency-weighted feed
"""
from __future__ import annotations

import datetime
import logging
import math

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, or_, select

from backend.core.clients import get_encoder, get_qdrant
from backend.core.auth import get_current_user
from backend.core.db import cache
from backend.core.db.postgres import Article, AsyncSessionLocal, User, UserConstitution
from backend.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Feed"])


@router.get("/feed")
async def get_feed():
    """
    Top 50 latest articles.
    Hits Redis cache first (5-min TTL), then falls back to Postgres.
    """
    cached = await cache.get_cached_feed()
    if cached:
        return {"source": "redis_cache", "data": cached}

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Article).order_by(desc(Article.published_at)).limit(50)
        )
        articles = result.scalars().all()
        feed_data = [_serialize_article(a) for a in articles]

    if feed_data:
        await cache.set_cached_feed(feed_data)

    return {"source": "postgres_db", "data": feed_data}


@router.get("/article/{article_id}")
async def get_article(article_id: str):
    """
    Fetch a single article's full content by UUID.
    Cached in Redis for 1 hour.
    """
    cached = await cache.get_cached_article(article_id)
    if cached:
        return {"source": "redis_cache", "data": cached}

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Article).where(Article.id == article_id)
        )
        article = result.scalar_one_or_none()

    if not article:
        raise HTTPException(status_code=404, detail="Article not found.")

    data = _serialize_article(article, include_content=True)
    await cache.set_cached_article(article_id, data)
    return {"source": "postgres_db", "data": data}


@router.get("/personalized_feed/{user_id}")
async def get_personalized_feed(user_id: str, current_user: User = Depends(get_current_user)):
    """
    PNC-filtered, recency-weighted personalized feed.

    Uses Qdrant semantic search against the user's priority_domains,
    applies time-decay scoring, then re-hydrates from Postgres.
    Falls back to simple Postgres category filter if Qdrant is unavailable.

    Cached per-user for 2 minutes.
    """
    if user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to access another user's feed.",
        )

    cached = await cache.get_cached_user_feed(user_id)
    if cached:
        return {"source": "redis_cache", "user_id": user_id, "data": cached}

    async with AsyncSessionLocal() as session:
        user = await session.get(UserConstitution, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User constitution not found.")

        const = user.constitution
        priority_domains: list[str] = const.get("topical_constraints", {}).get("priority_domains", [])
        excluded_topics: list[str] = const.get("topical_constraints", {}).get("excluded_topics", [])

        feed_data: list[dict] = []
        encoder = get_encoder()
        qdrant = get_qdrant()
        settings = get_settings()

        if priority_domains and encoder and qdrant:
            try:
                query_vector = encoder.encode(" ".join(priority_domains)).tolist()
                raw_hits = qdrant.query_points(
                    collection_name=settings.qdrant_collection,
                    query=query_vector,
                    limit=200,
                ).points

                now = datetime.datetime.now(datetime.timezone.utc)
                scored: list[tuple[float, str]] = []

                for hit in raw_hits:
                    content = str(hit.payload.get("content", "")).lower()
                    if any(ex.lower() in content for ex in excluded_topics):
                        continue

                    days_old = _parse_days_old(hit.payload.get("timestamp", ""), now)
                    time_weighted = hit.score * (0.85 ** max(0.0, days_old))
                    scored.append((time_weighted, str(hit.id)))

                scored.sort(reverse=True)
                matched_ids = list(dict.fromkeys(doc_id for _, doc_id in scored))[:30]

                if matched_ids:
                    result = await session.execute(
                        select(Article).where(Article.id.in_(matched_ids))
                    )
                    id_map = {a.id: a for a in result.scalars().all()}
                    sorted_articles = [id_map[did] for did in matched_ids if did in id_map]
                    feed_data = [_serialize_article(a) for a in sorted_articles]

            except Exception as e:
                logger.warning("Qdrant personalized feed failed for %s: %s", user_id, e)

        if not feed_data:
            # Postgres fallback: simple category filter
            query = select(Article)
            if priority_domains:
                query = query.where(or_(*[Article.category.ilike(f"%{d}%") for d in priority_domains]))
            for ex in excluded_topics:
                query = query.where(~Article.category.ilike(f"%{ex}%"))
            query = query.order_by(desc(Article.published_at)).limit(30)
            result = await session.execute(query)
            feed_data = [_serialize_article(a) for a in result.scalars().all()]

    if feed_data:
        await cache.set_cached_user_feed(user_id, feed_data)

    source = "qdrant_semantic" if feed_data else "postgres_fallback"
    return {"source": source, "user_id": user_id, "data": feed_data}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _serialize_article(article: Article, include_content: bool = False) -> dict:
    data = {
        "id": article.id,
        "title": article.title,
        "url": article.url,
        "source": article.source,
        "image_url": article.image_url,
        "published_at": article.published_at.isoformat() if article.published_at else None,
        "category": article.category,
        "ai_slop_score": article.ai_slop_score,
        "ai_slop_label": article.ai_slop_label,
    }
    if include_content:
        data["content"] = article.content
    return data


def _parse_days_old(ts_str: str, now: datetime.datetime) -> float:
    try:
        if len(ts_str) == 14 and ts_str.isdigit():
            pub = datetime.datetime.strptime(ts_str, "%Y%m%d%H%M%S").replace(
                tzinfo=datetime.timezone.utc
            )
        else:
            pub = datetime.datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        return max(0.0, (now - pub).total_seconds() / 86400.0)
    except Exception:
        return 1.0
