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
    active_participations = Column(Integer, nullable=False, default=0)
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
    avg_tone = Column(Float, nullable=True)
    num_mentions = Column(Integer, nullable=True)
    country_code = Column(String, nullable=True)
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


class Comment(Base):
    __tablename__ = "comments"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    article_id = Column(String, index=True, nullable=False)
    parent_id = Column(String, index=True, nullable=True)  # For threaded replies
    content = Column(Text, nullable=False)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class ArticleVote(Base):
    __tablename__ = "article_votes"

    user_id = Column(String, primary_key=True, index=True)
    article_id = Column(String, primary_key=True, index=True)
    vote = Column(Integer, nullable=False)  # 1 (up) or -1 (down)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
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
    ("006_backfill_uninitialized_constitutions", (
        "UPDATE user_constitutions "
        "SET constitution = '{"
        "\"epistemic_framework\": {\"primary_mode\": \"empiricist\", \"verification_threshold\": 0.7}, "
        "\"narrative_preferences\": {\"diversity_weight\": 0.5, \"bias_tolerance\": \"medium\"}, "
        "\"topical_constraints\": {\"priority_domains\": [], \"excluded_topics\": []}, "
        "\"complexity_preference\": {\"readability_depth\": \"intermediate\", \"data_density\": \"medium\"}"
        "}'::jsonb, "
        "updated_at = now() "
        "WHERE "
        "(constitution->'epistemic_framework'->>'primary_mode') IS NULL "
        "OR (constitution->'epistemic_framework'->>'verification_threshold') IS NULL "
        "OR (constitution->'narrative_preferences'->>'diversity_weight') IS NULL "
        "OR (constitution->'narrative_preferences'->>'bias_tolerance') IS NULL "
        "OR (constitution->'topical_constraints'->'priority_domains') IS NULL "
        "OR (constitution->'topical_constraints'->'excluded_topics') IS NULL "
        "OR (constitution->'complexity_preference'->>'readability_depth') IS NULL "
        "OR (constitution->'complexity_preference'->>'data_density') IS NULL"
    )),
    ("007_add_active_participations", (
        "ALTER TABLE users "
        "ADD COLUMN IF NOT EXISTS active_participations INTEGER NOT NULL DEFAULT 0"
    )),
    ("008_default_epistemic_mode_all", (
        "UPDATE user_constitutions uc "
        "SET constitution = jsonb_set(uc.constitution, '{epistemic_framework,primary_mode}', '\"all\"'::jsonb, true), "
        "updated_at = now() "
        "FROM users u "
        "WHERE u.id = uc.user_id "
        "AND u.onboarding_completed = FALSE "
        "AND (uc.constitution->'epistemic_framework'->>'primary_mode') = 'empiricist'"
    )),
    ("008_add_gdelt_enrichment_columns", (
        "ALTER TABLE articles "
        "ADD COLUMN IF NOT EXISTS avg_tone FLOAT, "
        "ADD COLUMN IF NOT EXISTS num_mentions INTEGER, "
        "ADD COLUMN IF NOT EXISTS country_code VARCHAR"
    )),
    ("009_add_engagement_tables", (
        "CREATE TABLE IF NOT EXISTS comments ("
        "  id VARCHAR PRIMARY KEY, "
        "  user_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE, "
        "  article_id VARCHAR NOT NULL REFERENCES articles(id) ON DELETE CASCADE, "
        "  parent_id VARCHAR REFERENCES comments(id) ON DELETE SET NULL, "
        "  content TEXT NOT NULL, "
        "  is_deleted BOOLEAN NOT NULL DEFAULT false, "
        "  created_at TIMESTAMPTZ DEFAULT now(), "
        "  updated_at TIMESTAMPTZ DEFAULT now()"
        ");"
        "CREATE INDEX IF NOT EXISTS ix_comments_user_id ON comments (user_id);"
        "CREATE INDEX IF NOT EXISTS ix_comments_article_id ON comments (article_id);"
        "CREATE INDEX IF NOT EXISTS ix_comments_parent_id ON comments (parent_id);"
        "CREATE TABLE IF NOT EXISTS article_votes ("
        "  user_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE, "
        "  article_id VARCHAR NOT NULL REFERENCES articles(id) ON DELETE CASCADE, "
        "  vote INTEGER NOT NULL, "
        "  created_at TIMESTAMPTZ DEFAULT now(), "
        "  updated_at TIMESTAMPTZ DEFAULT now(), "
        "  PRIMARY KEY (user_id, article_id)"
        ");"
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
            avg_tone=article_data.get("avg_tone"),
            num_mentions=article_data.get("num_mentions"),
            country_code=article_data.get("country_code"),
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
