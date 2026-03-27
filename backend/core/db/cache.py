import os
import json
import redis.asyncio as redis
from dotenv import load_dotenv

load_dotenv(r"C:\Users\soura\ethos\factchecker\.env")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Setup robust pure-async Redis connection pool
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

async def get_cached_feed():
    """Gets the main dashboard feed if cached."""
    data = await redis_client.get("news_feed")
    return json.loads(data) if data else None

async def set_cached_feed(feed_data: list):
    """Caches the completely formatted feed list for 5 minutes."""
    await redis_client.setex("news_feed", 300, json.dumps(feed_data)) # 300 secs = 5 mins

async def get_cached_article(article_id: str):
    """Retrieves an exact explicit article from cache instantly."""
    data = await redis_client.get(f"article:{article_id}")
    return json.loads(data) if data else None

async def set_cached_article(article_id: str, article_data: dict):
    """Caches individually viewed articles for a whole hour to prevent spam hits."""
    await redis_client.setex(f"article:{article_id}", 3600, json.dumps(article_data)) # 3600 secs = 1 hr
