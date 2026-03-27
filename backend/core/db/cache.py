from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from backend.config import get_settings

if TYPE_CHECKING:
    import redis.asyncio as redis_type

logger = logging.getLogger(__name__)

_redis_client = None


def _get_client():
    global _redis_client
    if _redis_client is None:
        import redis.asyncio as redis
        _redis_client = redis.from_url(
            get_settings().redis_url,
            decode_responses=True,
        )
    return _redis_client


# ── Global feed (all users) ────────────────────────────────────────────────

async def get_cached_feed() -> list | None:
    data = await _get_client().get("feed:global")
    return json.loads(data) if data else None


async def set_cached_feed(feed_data: list, ttl: int = 300) -> None:
    await _get_client().setex("feed:global", ttl, json.dumps(feed_data))


# ── Per-user personalized feed ─────────────────────────────────────────────

async def get_cached_user_feed(user_id: str) -> list | None:
    data = await _get_client().get(f"feed:user:{user_id}")
    return json.loads(data) if data else None


async def set_cached_user_feed(user_id: str, feed_data: list, ttl: int = 120) -> None:
    await _get_client().setex(f"feed:user:{user_id}", ttl, json.dumps(feed_data))


# ── Individual article ─────────────────────────────────────────────────────

async def get_cached_article(article_id: str) -> dict | None:
    data = await _get_client().get(f"article:{article_id}")
    return json.loads(data) if data else None


async def set_cached_article(article_id: str, article_data: dict, ttl: int = 3600) -> None:
    await _get_client().setex(f"article:{article_id}", ttl, json.dumps(article_data))


# ── Fact-check results ─────────────────────────────────────────────────────

async def get_cached_fact_check(article_id: str) -> dict | None:
    data = await _get_client().get(f"factcheck:{article_id}")
    return json.loads(data) if data else None


async def set_cached_fact_check(article_id: str, result: dict, ttl: int = 3600) -> None:
    await _get_client().setex(f"factcheck:{article_id}", ttl, json.dumps(result))


# ── Cluster results ────────────────────────────────────────────────────────

async def get_cached_clusters(article_id: str) -> dict | None:
    data = await _get_client().get(f"clusters:{article_id}")
    return json.loads(data) if data else None


async def set_cached_clusters(article_id: str, result: dict, ttl: int = 1800) -> None:
    await _get_client().setex(f"clusters:{article_id}", ttl, json.dumps(result))
