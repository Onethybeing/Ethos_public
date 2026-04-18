from __future__ import annotations

import json

from backend.config import get_settings

_redis_client = None
_GLOBAL_FEED_CACHE_KEY = "feed:global:v2"
_USER_FEED_CACHE_PREFIX = "feed:user:v2:"


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
    data = await _get_client().get(_GLOBAL_FEED_CACHE_KEY)
    return json.loads(data) if data else None


async def set_cached_feed(feed_data: list, ttl: int = 300) -> None:
    await _get_client().setex(_GLOBAL_FEED_CACHE_KEY, ttl, json.dumps(feed_data))


# ── Per-user personalized feed ─────────────────────────────────────────────

async def get_cached_user_feed(user_id: str) -> list | None:
    data = await _get_client().get(f"{_USER_FEED_CACHE_PREFIX}{user_id}")
    return json.loads(data) if data else None


async def set_cached_user_feed(user_id: str, feed_data: list, ttl: int = 120) -> None:
    await _get_client().setex(f"{_USER_FEED_CACHE_PREFIX}{user_id}", ttl, json.dumps(feed_data))


async def get_user_dynamic_profile(user_id: str) -> dict:
    """Fetch real-time dynamic recommendation profile populated by Kafka Streams."""
    data = await _get_client().get(f"user_profile:{user_id}")
    return json.loads(data) if data else {}


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
    limit = get_settings().background_article_limit
    data = await _get_client().get(f"clusters:{limit}:{article_id}")
    return json.loads(data) if data else None


async def set_cached_clusters(article_id: str, result: dict, ttl: int = 1800) -> None:
    limit = get_settings().background_article_limit
    await _get_client().setex(f"clusters:{limit}:{article_id}", ttl, json.dumps(result))


# ── Rephrase results ───────────────────────────────────────────────────────

async def get_cached_rephrase(article_id: str) -> dict | None:
    data = await _get_client().get(f"rephrase:{article_id}")
    return json.loads(data) if data else None


async def set_cached_rephrase(article_id: str, result: dict, ttl: int = 86400) -> None:
    await _get_client().setex(f"rephrase:{article_id}", ttl, json.dumps(result))
