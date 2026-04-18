from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).parent / ".env"


class Settings(BaseSettings):
    environment: str = "development"
    log_level: str = "INFO"

    # ── Auth ───────────────────────────────────────────────────────────────
    jwt_secret: str = "hello_bhai_sourav_hoon2222"
    jwt_algorithm: str = "HS256"
    access_token_exp_minutes: int = 60 * 24

    # ── LLM — single toggle to switch providers ────────────────────────────
    llm_provider: Literal["groq", "openai", "gemini"] = "groq"

    # Groq
    groq_api_key: str = ""
    groq_model_fast: str = "llama-3.1-8b-instant"
    groq_model_strong: str = "llama-3.3-70b-versatile"

    # OpenAI
    openai_api_key: str = ""
    openai_model_fast: str = "gpt-4o-mini"
    openai_model_strong: str = "gpt-4o"

    # Gemini
    gemini_api_key: str = ""
    gemini_model_fast: str = "gemini-1.5-flash"
    gemini_model_strong: str = "gemini-1.5-pro"

    # ── Infrastructure ─────────────────────────────────────────────────────
    qdrant_url: str = "https://ef25fb4f-5ac1-42ab-b034-4efa9b4d1020.eu-central-1-0.aws.cloud.qdrant.io"
    qdrant_api_key: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.iLqajO84otUonJ-z2oxy8N2yTOg9s7BspQriaXHUcIQ"
    qdrant_collection: str = "news_articles_streaming"

    postgres_url: str = "postgresql+asyncpg://neondb_owner:npg_dJ87MzoyqmZf@ep-young-mountain-amxoo9os-pooler.c-5.us-east-1.aws.neon.tech/neondb?ssl=require"
    redis_url: str = "rediss://default:gQAAAAAAAU2vAAIncDI5MDMxNjc4YzhhNTY0YWQyODBmN2NjNzlmMmJiNzNlMnAyODU0MjM@stirred-gelding-85423.upstash.io:6379"

    kafka_broker_url: str = "localhost:9092"
    rabbitmq_url: str = "amqps://kvrxnlwn:Jr5sJRFGD32hq2i6VDY-DGXrx6X1o-NE@fuji.lmq.cloudamqp.com/kvrxnlwn"

    # Comma-separated allowed CORS origins (e.g. "http://localhost:3000,https://app.ethosnews.com")
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    # ── Fact-checking ─────────────────────────────────────────────────────
    tavily_api_key: str = "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"
    # Max LLM classify calls running concurrently (throttles Groq TPM usage)
    fact_check_max_concurrent: int = 3

    # ── Ingestion tuning ───────────────────────────────────────────────────
    gdelt_poll_interval_secs: int = 900
    ingestion_workers: int = 3
    scrape_timeout_secs: int = 10
    spacy_char_limit: int = 20_000
    feed_article_limit: int = 50
    background_article_limit: int = 200

    # ── Leaderboard Weights ───────────────────────────────────────────────
    weight_read: float = 1.0
    weight_active: float = 2.5
    weight_streak: float = 0.5

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
