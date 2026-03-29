"""
Gamified Engagement Leaderboard Engine.

Computes per-read engagement scores and maintains a real-time leaderboard.

Scoring formula (from ehoss.md spec):
    score = 0.40 × pnc_alignment
          + 0.30 × diversity_of_viewpoints
          + 0.30 × time_on_verified

Where:
    pnc_alignment         — cosine similarity of article embedding vs. user's PNC topics
    diversity_of_viewpoints — 1.0 if article belongs to ≥2 clusters, else 0.5
    time_on_verified      — normalized read time (cap 10 min = 1.0), down-weighted
                            when ai_slop_score is high (content may not be trustworthy)

Storage:
    - Postgres: engagement_events table (full history)
    - Redis sorted set "leaderboard": rolling cumulative score per user
"""
from __future__ import annotations

import logging
import math
import uuid
from datetime import datetime, timezone

import numpy as np
from sqlalchemy import text

from backend.core.clients import get_encoder, get_qdrant
from backend.core.db import cache as _cache
from backend.core.db.postgres import AsyncSessionLocal, EngagementEvent, User
from backend.config import get_settings

logger = logging.getLogger(__name__)

_LEADERBOARD_KEY = "leaderboard"
_MAX_READ_SECS = 600  # 10 minutes = full time score


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two 1-D numpy arrays."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


async def _get_pnc_alignment(article_id: str, user_constitution: dict) -> float:
    """
    Compute cosine similarity between the article's embedding and the user's
    PNC priority_domains query vector.
    """
    settings = get_settings()
    qdrant = get_qdrant()
    encoder = get_encoder()

    # Fetch article vector from Qdrant
    results = qdrant.retrieve(
        collection_name=settings.qdrant_collection,
        ids=[article_id],
        with_vectors=True,
        with_payload=False,
    )
    if not results:
        return 0.0

    article_vec = np.array(results[0].vector, dtype="float32")

    # Encode PNC priority domains as a single query vector
    priority_domains = (
        user_constitution
        .get("topical_constraints", {})
        .get("priority_domains", ["general news"])
    )
    pnc_query = " ".join(priority_domains)
    pnc_vec = encoder.encode(pnc_query).astype("float32")

    similarity = _cosine_similarity(article_vec, pnc_vec)
    # Shift from [-1, 1] to [0, 1]
    return float(max(0.0, (similarity + 1.0) / 2.0))


def _diversity_score(article_id: str) -> float:
    """
    Return 1.0 if the article appears in multiple narrative clusters, else 0.5.

    Simplified heuristic: we check the Qdrant payload for a cluster_count field
    written by the clustering engine, or default to 0.5 (single perspective).
    """
    settings = get_settings()
    try:
        results = get_qdrant().retrieve(
            collection_name=settings.qdrant_collection,
            ids=[article_id],
            with_payload=True,
            with_vectors=False,
        )
        if results:
            cluster_count = results[0].payload.get("cluster_count", 1)
            return 1.0 if cluster_count >= 2 else 0.5
    except Exception:
        pass
    return 0.5


def _time_score(time_spent_secs: int, ai_slop_score: float | None) -> float:
    """
    Normalize read time to [0, 1] (capped at 10 min).
    Down-weight by (1 - slop_score) so AI-generated content yields lower scores.
    """
    raw = min(time_spent_secs, _MAX_READ_SECS) / _MAX_READ_SECS
    trust_weight = 1.0 - (ai_slop_score or 0.0)
    return round(raw * trust_weight, 4)


async def record_engagement(
    user_id: str,
    article_id: str,
    time_spent_secs: int,
    user_constitution: dict,
) -> dict:
    """
    Compute and persist an engagement event, then update the Redis leaderboard.

    Args:
        user_id:           The user who read the article.
        article_id:        UUID of the article.
        time_spent_secs:   How long the user spent reading (seconds).
        user_constitution: The user's PNC dict (from DB).

    Returns:
        Dict with computed score components and total_score.
    """
    settings = get_settings()

    # Fetch slop score from Qdrant payload for trust weighting
    ai_slop_score: float | None = None
    try:
        hits = get_qdrant().retrieve(
            collection_name=settings.qdrant_collection,
            ids=[article_id],
            with_payload=True,
            with_vectors=False,
        )
        if hits:
            ai_slop_score = hits[0].payload.get("ai_slop_score")
    except Exception:
        pass

    # ── Compute score components ──────────────────────────────────────────────
    pnc_alignment = await _get_pnc_alignment(article_id, user_constitution)
    diversity = _diversity_score(article_id)
    time_sc = _time_score(time_spent_secs, ai_slop_score)

    total = round(
        0.40 * pnc_alignment +
        0.30 * diversity +
        0.30 * time_sc,
        4,
    )

    # ── Persist to Postgres ───────────────────────────────────────────────────
    event = EngagementEvent(
        id=str(uuid.uuid4()),
        user_id=user_id,
        article_id=article_id,
        pnc_alignment=round(pnc_alignment, 4),
        diversity_score=round(diversity, 4),
        time_score=time_sc,
        total_score=total,
        created_at=datetime.now(timezone.utc),
    )
    async with AsyncSessionLocal() as session:
        session.add(event)
        await session.commit()

    # ── Update Redis leaderboard (sorted set) ─────────────────────────────────
    redis = _cache._get_client()
    await redis.zadd(_LEADERBOARD_KEY, {user_id: total}, incr=True)
    logger.info(
        "Engagement recorded: user=%s article=%s total=%.3f",
        user_id, article_id, total,
    )

    return {
        "user_id": user_id,
        "article_id": article_id,
        "pnc_alignment": round(pnc_alignment, 4),
        "diversity_score": round(diversity, 4),
        "time_score": time_sc,
        "total_score": total,
    }


async def get_top_users(limit: int = 50) -> list[dict]:
    import math
    from sqlalchemy import select, func
    from datetime import datetime, timedelta, timezone
    from backend.config import get_settings
    
    settings = get_settings()
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    
    # Subquery for articles read in the past week
    article_counts = (
        select(
            EngagementEvent.user_id,
            func.count(EngagementEvent.id).label("weekly_reads")
        )
        .where(EngagementEvent.created_at >= seven_days_ago)
        .group_by(EngagementEvent.user_id)
        .subquery()
    )
    
    query = (
        select(
            User,
            func.coalesce(article_counts.c.weekly_reads, 0).label("weekly_reads")
        )
        .outerjoin(article_counts, User.id == article_counts.c.user_id)
        .where(User.is_active == True)
    )
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(query)
        rows = result.all()
        
    scored_users = []
    for user, weekly_reads in rows:
        streak = getattr(user, 'streak_count', 0)
        active_parts = getattr(user, 'active_participations', 0)
        
        base_points = (weekly_reads * settings.weight_read) + (active_parts * settings.weight_active)
        streak_multiplier = 1.0 + (math.log10(streak + 1) * settings.weight_streak)
        score = base_points * streak_multiplier
        
        scored_users.append({
            "user_id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "avatar_url": user.avatar_url,
            "streak": streak,
            "active_participations": active_parts,
            "weekly_reads": weekly_reads,
            "score": score,
        })
        
    # Sort by score descending
    scored_users.sort(key=lambda x: x["score"], reverse=True)
    
    # Apply limit and assign ranks
    top_users = scored_users[:limit]
    for i, u in enumerate(top_users):
        u["rank"] = i + 1
        
    return top_users
