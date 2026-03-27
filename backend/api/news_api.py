from fastapi import FastAPI, APIRouter, HTTPException
from sqlalchemy import select, desc
import json
import os
from dotenv import load_dotenv

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# Local Module Imports
from backend.core.db.postgres import AsyncSessionLocal, Article, UserConstitution
from sqlalchemy import or_, and_
import backend.core.db.cache as cache

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

load_dotenv(r"C:\Users\soura\ethos\Ethos\backend\.env")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
COLLECTION_NAME = "news_articles_streaming"

# Initialize Qdrant globally, but let SentenceTransformer load lazily to avoid MKL Intel abort errors in uvicorn
try:
    qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
except Exception as e:
    qdrant_client = None

# Lazy holder
_encoder = None
def get_encoder():
    global _encoder
    if _encoder is None:
        from sentence_transformers import SentenceTransformer
        _encoder = SentenceTransformer('all-MiniLM-L6-v2')
    return _encoder

app = FastAPI(title="Ethos News API", description="API for serving news articles to the frontend.")


@app.get("/feed")
async def get_feed():
    """
    Fetches the top 50 strictly latest articles.
    [Cache Layer] → hits Redis first (5m TTL).
    [Fallback db] → queries Postgres, transforms it, caches it, and returns.
    """
    # 1. Access high-speed cache
    cached_feed = await cache.get_cached_feed()
    if cached_feed:
        return {"source": "redis_cache", "data": cached_feed}

    # 2. Cache miss: heavy query logic onto strictly permanent Postgres DB
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Article).order_by(desc(Article.published_at)).limit(50)
        )
        articles = result.scalars().all()
        
        # Serialize properly since DateTime objects break pure-JSON conversion
        feed_data = [
            {
                "id": a.id,
                "title": a.title,
                "url": a.url,
                "source": a.source,
                "image_url": a.image_url,
                "published_at": a.published_at.isoformat() if a.published_at else None,
                "category": a.category
            } for a in articles
        ]

    # 3. Reload cache pipeline locally for next 5 mins
    if feed_data:
        await cache.set_cached_feed(feed_data)

    return {"source": "postgres_db", "data": feed_data}


@app.get("/article/{article_id}")
async def get_article(article_id: str):
    """
    Fetches raw heavy content text strictly by ID.
    [Cache Layer] → hits Redis first (1hr TTL).
    [Fallback db] → queries exact UUID row, transforms it, caches it, and returns.
    """
    # 1. Direct hit cache
    cached_article = await cache.get_cached_article(article_id)
    if cached_article:
        return {"source": "redis_cache", "data": cached_article}

    # 2. Revert to Database hit
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Article).where(Article.id == str(article_id))
        )
        article = result.scalar_one_or_none()

        if not article:
            raise HTTPException(status_code=404, detail="Article not logically found globally.")

        article_data = {
            "id": article.id,
            "title": article.title,
            "content": article.content,
            "url": article.url,
            "source": article.source,
            "image_url": article.image_url,
            "published_at": article.published_at.isoformat() if article.published_at else None,
            "category": article.category
        }

    # 3. Store heavy row back into redis to insulate database scaling restrictions
    await cache.set_cached_article(article_id, article_data)

    return {"source": "postgres_db", "data": article_data}
@app.get("/personalized_feed/{user_id}")
async def get_personalized_feed(user_id: str):
    async with AsyncSessionLocal() as session:
        user = await session.get(UserConstitution, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User Constitution not found.")

        # Parse constraints
        const = user.constitution
        print("CONSTITUTION: ", const)
        priority_domains = const.get('topical_constraints', {}).get('priority_domains', [])
        excluded_topics = const.get('topical_constraints', {}).get('excluded_topics', [])

        feed_data = []
        encoder_local = get_encoder()
        print("PRIORITY: ", priority_domains, "ENCODER:", type(encoder_local), "QDRANT:", type(qdrant_client))


        if encoder_local and qdrant_client and priority_domains:
            # 1. Similarity Search using Qdrant based on User's constitutional priorities
            query_text = " ".join(priority_domains)
            query_vector = encoder_local.encode(query_text).tolist()

            try:
                # Execute semantic search against streaming articles
                raw_results = qdrant_client.search(
                    collection_name=COLLECTION_NAME,
                    query_vector=query_vector,
                    limit=200
                )
                
                # Apply Recency Weighting and Filter
                import datetime
                import math
                
                now = datetime.datetime.now()
                scored_hits = []
                
                for hit in raw_results:
                    # Basic exclusion filtering logic
                    content_str = str(hit.payload.get("content", "")).lower()
                    should_exclude = False
                    for excluded in excluded_topics:
                        if excluded.lower() in content_str:
                            should_exclude = True
                            break
                    
                    if should_exclude:
                        continue
                        
                    # Calculate time penalty
                    # GDELT timestamp format from pipeline: typically 'YYYYMMDDHHMMSS' or parsed string, 
                    # let's try to parse or fallback to 0 penalty.
                    ts_str = hit.payload.get("timestamp", "")
                    days_old = 0
                    try:
                        # try parse YYYYMMDDHHMMSS which gdelt returns sometimes
                        if len(ts_str) == 14 and ts_str.isdigit():
                            pub_date = datetime.datetime.strptime(ts_str, "%Y%m%d%H%M%S")
                            days_old = (now - pub_date).total_seconds() / 86400.0
                        else:
                            # if it's stored as ISO 
                            pub_date = datetime.datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                            days_old = (now.astimezone() - pub_date).total_seconds() / 86400.0
                    except:
                        days_old = 1.0 # default penalty if can't parse
                        
                    # Time decay formula: slightly decay score based on days old
                    # exponential decay: score * (decay_factor ^ days_old)
                    decay_factor = 0.85
                    time_weighted_score = hit.score * math.pow(decay_factor, max(0, days_old))
                    
                    scored_hits.append((time_weighted_score, hit.id))
                
                # Sort by blended score
                scored_hits.sort(key=lambda x: x[0], reverse=True)
                
                # Take top 30 unique IDs
                seen_ids = set()
                matched_ids = []
                for score, doc_id in scored_hits:
                    if doc_id not in seen_ids:
                        seen_ids.add(doc_id)
                        matched_ids.append(doc_id)
                        if len(matched_ids) >= 30:
                            break

                # 2. Re-hydrate full article data from Postgres using matched IDs
                if matched_ids:
                    query = select(Article).where(Article.id.in_(matched_ids))
                    result = await session.execute(query)
                    articles = result.scalars().all()
                    
                    # Sort matching DB articles according exactly to the Recency-Weighted ranking
                    id_to_article = {a.id: a for a in articles}
                    sorted_articles = [id_to_article[doc_id] for doc_id in matched_ids if doc_id in id_to_article]

                    feed_data = [
                        {
                            "id": a.id,
                            "title": a.title,
                            "url": a.url,
                            "source": a.source,
                            "image_url": a.image_url,
                            "published_at": a.published_at.isoformat() if a.published_at else None,
                            "category": a.category,
                            "fact_check_status": "pending" 
                        } for a in sorted_articles
                    ]
            except Exception as e:
                print(f"Qdrant Semantic Search Failed: {e}")
                # Fallback to postgres
                pass

        if not feed_data:
            # Fallback Base Query if Qdrant pipeline fails or returns empty constraint filters
            query = select(Article)
            if priority_domains:
                filters = [Article.category.ilike(f"%{domain}%") for domain in priority_domains]
                query = query.where(or_(*filters))
            if excluded_topics:
                for excluded in excluded_topics:
                    query = query.where(~Article.category.ilike(f"%{excluded}%"))

            query = query.order_by(desc(Article.published_at)).limit(30)
            result = await session.execute(query)
            articles = result.scalars().all()
            
            feed_data = [
                {
                    "id": a.id,
                    "title": a.title,
                    "url": a.url,
                    "source": a.source,
                    "image_url": a.image_url,
                    "published_at": a.published_at.isoformat() if a.published_at else None,
                    "category": a.category,
                    "fact_check_status": "pending" 
                } for a in articles
            ]

    return {"source": "qdrant_semantic_filtered" if feed_data and "pending" in feed_data[0].get("fact_check_status", "") else "postgres_db_filtered", "user_id": user_id, "data": feed_data}

