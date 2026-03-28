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
    jwt_secret: str = ""
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
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    qdrant_collection: str = "news_articles_streaming"

    postgres_url: str = "postgresql+asyncpg://ethos:ethos@localhost:5432/ethos"
    redis_url: str = "redis://localhost:6379/0"

    # Comma-separated allowed CORS origins (e.g. "http://localhost:3000,https://app.ethosnews.com")
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    # ── Ingestion tuning ───────────────────────────────────────────────────
    gdelt_poll_interval_secs: int = 60
    ingestion_workers: int = 3
    scrape_timeout_secs: int = 10
    spacy_char_limit: int = 20_000

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
