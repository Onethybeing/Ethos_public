from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import Column, Float, String, Text, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from backend.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()
engine = create_async_engine(settings.postgres_url, echo=False, pool_pre_ping=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()


class Article(Base):
    __tablename__ = "articles"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, index=True)
    content = Column(Text)
    url = Column(String, unique=True, index=True)
    source = Column(String, index=True)
    image_url = Column(String, nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    category = Column(String, nullable=True)
    # AI slop detection results (populated by ingestion pipeline)
    ai_slop_score = Column(Float, nullable=True)
    ai_slop_label = Column(String, nullable=True)


class UserConstitution(Base):
    __tablename__ = "user_constitutions"

    user_id = Column(String, primary_key=True, index=True)
    constitution = Column(JSONB, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class EngagementEvent(Base):
    __tablename__ = "engagement_events"

    id = Column(String, primary_key=True, index=True)  # UUID
    user_id = Column(String, index=True, nullable=False)
    article_id = Column(String, index=True, nullable=False)
    pnc_alignment = Column(Float, nullable=False, default=0.0)
    diversity_score = Column(Float, nullable=False, default=0.0)
    time_score = Column(Float, nullable=False, default=0.0)
    total_score = Column(Float, nullable=False, default=0.0)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


async def init_db() -> None:
    """Create all tables if they don't exist yet."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables initialized.")


async def save_article(article_data: dict) -> bool:
    """
    Persist an article to Postgres.

    Returns True if inserted, False if the URL already existed (duplicate).
    Raises on any other database error.
    """
    async with AsyncSessionLocal() as session:
        pub_date = article_data.get("published_at")
        if isinstance(pub_date, str):
            try:
                pub_date = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
            except ValueError:
                pub_date = datetime.now(timezone.utc)
        elif not pub_date:
            pub_date = datetime.now(timezone.utc)

        new_article = Article(
            id=str(article_data["id"]),
            title=article_data.get("title", "Untitled"),
            content=article_data.get("content", ""),
            url=article_data["url"],
            source=article_data.get("source", ""),
            image_url=article_data.get("image_url"),
            published_at=pub_date,
            category=article_data.get("category"),
            ai_slop_score=article_data.get("ai_slop_score"),
            ai_slop_label=article_data.get("ai_slop_label"),
        )
        session.add(new_article)
        try:
            await session.commit()
            return True
        except IntegrityError:
            # Duplicate URL — expected during continuous ingestion
            await session.rollback()
            return False
        except Exception:
            await session.rollback()
            logger.exception("Unexpected error saving article %s", article_data.get("url"))
            raise
