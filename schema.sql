-- ============================================================
-- EthosNews — Postgres schema (Neon)
-- Source of truth: backend/core/db/postgres.py
--
-- To sync with live DB: uv run python scripts/pull_schema.py
-- ============================================================

-- ── users ───────────────────────────────────────────────────
-- Managed by backend auth routes.
-- user_constitutions and engagement_events both reference this table.
CREATE TABLE IF NOT EXISTS users (
    id              VARCHAR         PRIMARY KEY,        -- UUID user ID
    username        VARCHAR         UNIQUE NOT NULL,
    display_name    VARCHAR,
    email           VARCHAR         UNIQUE,
    password_hash   VARCHAR,
    avatar_url      VARCHAR,
    onboarding_completed BOOLEAN    NOT NULL DEFAULT false,
    is_active       BOOLEAN         NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ     DEFAULT now(),
    updated_at      TIMESTAMPTZ     DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_users_username ON users (username);
CREATE INDEX IF NOT EXISTS ix_users_email    ON users (email);

-- ── articles ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS articles (
    id              VARCHAR         PRIMARY KEY,
    title           VARCHAR,
    content         TEXT,
    url             VARCHAR         UNIQUE NOT NULL,
    source          VARCHAR,
    image_url       VARCHAR,
    published_at    TIMESTAMPTZ,
    category        VARCHAR,

    -- populated by the ingestion pipeline slop detector
    ai_slop_score   FLOAT,
    ai_slop_label   VARCHAR
);

CREATE INDEX IF NOT EXISTS ix_articles_title  ON articles (title);
CREATE INDEX IF NOT EXISTS ix_articles_source ON articles (source);

-- ── user_constitutions ──────────────────────────────────────
-- Stores each user's Personal News Constitution (PNC) as JSONB.
-- One row per user; upserted whenever the user updates their preferences.
CREATE TABLE IF NOT EXISTS user_constitutions (
    user_id         VARCHAR         PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    constitution    JSONB           NOT NULL,
    updated_at      TIMESTAMPTZ     DEFAULT now()
);

-- ── engagement_events ───────────────────────────────────────
-- Immutable log of every user<>article read interaction with score breakdown.
-- Redis sorted set "leaderboard" holds the cumulative total per user for fast reads.
CREATE TABLE IF NOT EXISTS engagement_events (
    id              VARCHAR         PRIMARY KEY,        -- UUID
    user_id         VARCHAR         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    article_id      VARCHAR         NOT NULL REFERENCES articles(id) ON DELETE CASCADE,

    -- Score components (formula: 0.40×pnc + 0.30×diversity + 0.30×time)
    pnc_alignment   FLOAT           NOT NULL DEFAULT 0.0,
    diversity_score FLOAT           NOT NULL DEFAULT 0.0,
    time_score      FLOAT           NOT NULL DEFAULT 0.0,
    total_score     FLOAT           NOT NULL DEFAULT 0.0,

    created_at      TIMESTAMPTZ     DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_engagement_events_user_id    ON engagement_events (user_id);
CREATE INDEX IF NOT EXISTS ix_engagement_events_article_id ON engagement_events (article_id);
