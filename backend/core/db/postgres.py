from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, Float, String, Text, DateTime, Integer, text
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


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    display_name = Column(String, nullable=True)
    email = Column(String, unique=True, nullable=True, index=True)
    password_hash = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    onboarding_completed = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    streak_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


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
    ai_slop_score = Column(Float, nullable=True)
    ai_slop_label = Column(String, nullable=True)


class UserConstitution(Base):
    __tablename__ = "user_constitutions"

    user_id = Column(String, primary_key=True, index=True)  # FK → users.id
    constitution = Column(JSONB, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class EngagementEvent(Base):
    __tablename__ = "engagement_events"

    id = Column(String, primary_key=True, index=True)  # UUID
    user_id = Column(String, index=True, nullable=False)  # FK → users.id
    article_id = Column(String, index=True, nullable=False)
    pnc_alignment = Column(Float, nullable=False, default=0.0)
    diversity_score = Column(Float, nullable=False, default=0.0)
    time_score = Column(Float, nullable=False, default=0.0)
    total_score = Column(Float, nullable=False, default=0.0)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


# One-time migrations: (name, sql) — only run once, tracked in _migrations table
_MIGRATIONS: list[tuple[str, str]] = [
    ("001_add_slop_columns", (
        "ALTER TABLE articles "
        "ADD COLUMN IF NOT EXISTS ai_slop_score FLOAT, "
        "ADD COLUMN IF NOT EXISTS ai_slop_label VARCHAR"
    )),
    ("002_fix_timestamptz", (
        "ALTER TABLE articles "
        "ALTER COLUMN published_at TYPE TIMESTAMPTZ "
        "USING published_at AT TIME ZONE 'UTC';"
        "ALTER TABLE user_constitutions "
        "ALTER COLUMN updated_at TYPE TIMESTAMPTZ "
        "USING updated_at AT TIME ZONE 'UTC'"
    )),
    ("003_constitution_not_null", (
        "UPDATE user_constitutions SET constitution = '{}' WHERE constitution IS NULL;"
        "ALTER TABLE user_constitutions ALTER COLUMN constitution SET NOT NULL"
    )),
    ("004_add_user_auth_columns", (
        "ALTER TABLE users "
        "ADD COLUMN IF NOT EXISTS password_hash VARCHAR, "
        "ADD COLUMN IF NOT EXISTS onboarding_completed BOOLEAN NOT NULL DEFAULT FALSE"
    )),
    ("005_add_streak", (
        "ALTER TABLE users "
        "ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMPTZ, "
        "ADD COLUMN IF NOT EXISTS streak_count INTEGER NOT NULL DEFAULT 0"
    )),
]


async def init_db() -> None:
    """Create all tables, then run any pending one-time migrations."""
    async with engine.begin() as conn:
        # Always safe — no-op if tables already exist
        await conn.run_sync(Base.metadata.create_all)

        # Migration tracking table
        await conn.execute(text(
            "CREATE TABLE IF NOT EXISTS _migrations ("
            "  name VARCHAR PRIMARY KEY, "
            "  applied_at TIMESTAMPTZ DEFAULT now()"
            ")"
        ))

        result = await conn.execute(text("SELECT name FROM _migrations"))
        applied = {row[0] for row in result}

        for name, sql in _MIGRATIONS:
            if name in applied:
                continue
            for statement in sql.split(";"):
                stmt = statement.strip()
                if stmt:
                    await conn.execute(text(stmt))
            await conn.execute(text("INSERT INTO _migrations (name) VALUES (:n)"), {"n": name})
            logger.info("Applied migration: %s", name)

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
            await session.rollback()
            return False
        except Exception:
            await session.rollback()
            logger.exception("Unexpected error saving article %s", article_data.get("url"))
            raise
