"""
Narrative Clustering API router.

Endpoints:
  GET /article/{article_id}/clusters  — narrative divergence clusters for an article
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import update

from backend.core.auth import get_current_user
from backend.core.db import cache
from backend.core.db.postgres import AsyncSessionLocal, User
from backend.services.clustering.cluster_engine import ClusterResult, get_narrative_clusters

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Narrative Clusters"])


@router.get("/article/{article_id}/clusters")
async def get_clusters(article_id: str, current_user: User = Depends(get_current_user)):
    """
    Map alternative narrative perspectives for a given article.

    Retrieves 50 semantically similar articles, clusters them with HDBSCAN,
    and returns LLM-generated pillar summaries for each cluster.

    Cached in Redis for 30 minutes (clusters are stable over that window).
    """
    # Increment counter
    async with AsyncSessionLocal() as session:
        await session.execute(update(User).where(User.id == current_user.id).values(active_participations=User.active_participations + 1))
        await session.commit()

    cached = await cache.get_cached_clusters(article_id)
    if cached:
        return {"source": "redis_cache", **cached}

    try:
        result: ClusterResult = await get_narrative_clusters(article_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    response = {
        "article_id": result.article_id,
        "topic_query": result.topic_query,
        "pillar_count": len(result.pillars),
        "noise_article_count": result.noise_article_count,
        "pillars": [
            {
                "cluster_id": p.cluster_id,
                "summary": p.summary,
                "article_count": p.article_count,
                "representative_urls": p.representative_urls,
                "divergence_score": p.divergence_score,
            }
            for p in result.pillars
        ],
    }

    await cache.set_cached_clusters(article_id, response)
    return {"source": "pipeline", **response}
