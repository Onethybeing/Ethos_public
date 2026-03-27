"""
Central LLM abstraction for EthosNews.

One file. Three providers (Groq, OpenAI, Gemini). One factory.

To switch providers: set LLM_PROVIDER=openai (or gemini) in .env.
Zero code changes required anywhere else.

Usage:
    from backend.core.llm import get_llm

    response_text = await get_llm().chat(
        messages=[{"role": "user", "content": "Hello"}],
        model_tier="fast",          # or "strong"
        json_schema=MyModel.model_json_schema(),  # optional
        temperature=0.0,
    )
"""
from __future__ import annotations

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import Any

from backend.config import Settings, get_settings

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Base interface
# ──────────────────────────────────────────────────────────────────────────────

class BaseLLMClient(ABC):
    """Common interface for all LLM providers. All calls are async."""

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, str]],
        json_schema: dict | None = None,
        temperature: float = 0.0,
        model_tier: str = "fast",
    ) -> str:
        """
        Send a chat request and return the response text.

        Args:
            messages:    OpenAI-style list of {"role": ..., "content": ...}.
            json_schema: If provided, append schema to system prompt and enable
                         JSON mode. The model is instructed to return raw JSON.
            temperature: 0.0 = deterministic; higher = more creative.
            model_tier:  "fast" uses the lighter/cheaper model,
                         "strong" uses the more capable one.
        Returns:
            Raw response string (may be JSON if json_schema was passed).
        """

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _inject_schema(
        messages: list[dict[str, str]], json_schema: dict
    ) -> list[dict[str, str]]:
        """Append JSON schema instruction to the first system message (or prepend one)."""
        hint = (
            f"\n\nYou MUST return ONLY raw JSON matching this schema "
            f"(no markdown fences, no commentary):\n"
            f"{json.dumps(json_schema, indent=2)}"
        )
        msgs = list(messages)
        if msgs and msgs[0]["role"] == "system":
            msgs[0] = {**msgs[0], "content": msgs[0]["content"] + hint}
        else:
            msgs.insert(0, {"role": "system", "content": hint})
        return msgs


# ──────────────────────────────────────────────────────────────────────────────
# Groq provider
# ──────────────────────────────────────────────────────────────────────────────

class GroqClient(BaseLLMClient):
    def __init__(self, settings: Settings) -> None:
        from groq import AsyncGroq  # type: ignore[import-untyped]
        self._client = AsyncGroq(api_key=settings.groq_api_key)
        self._models: dict[str, str] = {
            "fast": settings.groq_model_fast,
            "strong": settings.groq_model_strong,
        }

    async def chat(
        self,
        messages: list[dict[str, str]],
        json_schema: dict | None = None,
        temperature: float = 0.0,
        model_tier: str = "fast",
    ) -> str:
        model = self._models.get(model_tier, self._models["fast"])
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        if json_schema is not None:
            kwargs["messages"] = self._inject_schema(messages, json_schema)
            kwargs["response_format"] = {"type": "json_object"}

        response = await self._client.chat.completions.create(**kwargs)
        return response.choices[0].message.content


# ──────────────────────────────────────────────────────────────────────────────
# OpenAI provider
# ──────────────────────────────────────────────────────────────────────────────

class OpenAIClient(BaseLLMClient):
    def __init__(self, settings: Settings) -> None:
        from openai import AsyncOpenAI  # type: ignore[import-untyped]
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._models: dict[str, str] = {
            "fast": settings.openai_model_fast,
            "strong": settings.openai_model_strong,
        }

    async def chat(
        self,
        messages: list[dict[str, str]],
        json_schema: dict | None = None,
        temperature: float = 0.0,
        model_tier: str = "fast",
    ) -> str:
        model = self._models.get(model_tier, self._models["fast"])
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        if json_schema is not None:
            kwargs["messages"] = self._inject_schema(messages, json_schema)
            kwargs["response_format"] = {"type": "json_object"}

        response = await self._client.chat.completions.create(**kwargs)
        return response.choices[0].message.content


# ──────────────────────────────────────────────────────────────────────────────
# Gemini provider
# ──────────────────────────────────────────────────────────────────────────────

class GeminiClient(BaseLLMClient):
    """Wraps google-generativeai. The SDK is synchronous so calls run in a thread."""

    def __init__(self, settings: Settings) -> None:
        import google.generativeai as genai  # type: ignore[import-untyped]
        genai.configure(api_key=settings.gemini_api_key)
        self._genai = genai
        self._models: dict[str, str] = {
            "fast": settings.gemini_model_fast,
            "strong": settings.gemini_model_strong,
        }

    async def chat(
        self,
        messages: list[dict[str, str]],
        json_schema: dict | None = None,
        temperature: float = 0.0,
        model_tier: str = "fast",
    ) -> str:
        model_name = self._models.get(model_tier, self._models["fast"])

        # Separate system messages from user/assistant turns
        system_parts = [m["content"] for m in messages if m["role"] == "system"]
        turns = [m for m in messages if m["role"] != "system"]

        if json_schema is not None:
            hint = (
                f"\n\nReturn ONLY raw JSON matching this schema "
                f"(no markdown fences):\n{json.dumps(json_schema, indent=2)}"
            )
            system_parts.append(hint)

        system_instruction = "\n\n".join(system_parts) if system_parts else None
        prompt = "\n\n".join(t["content"] for t in turns)

        generation_config: dict[str, Any] = {"temperature": temperature}
        if json_schema is not None:
            generation_config["response_mime_type"] = "application/json"

        genai_model = self._genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_instruction,
            generation_config=generation_config,
        )

        # Run blocking Gemini call in thread pool so we don't block the event loop
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, lambda: genai_model.generate_content(prompt)
        )
        return response.text


# ──────────────────────────────────────────────────────────────────────────────
# Module-level singleton — the only entry point callers should use
# ──────────────────────────────────────────────────────────────────────────────

_llm_instance: BaseLLMClient | None = None


def get_llm() -> BaseLLMClient:
    """Return the singleton LLM client for the currently configured provider.

    Provider is determined by the LLM_PROVIDER env var (default: groq).
    The instance is created once and reused for the lifetime of the process.
    """
    global _llm_instance
    if _llm_instance is None:
        s = get_settings()
        logger.info("Initializing LLM provider: %s", s.llm_provider)
        match s.llm_provider:
            case "openai":
                _llm_instance = OpenAIClient(s)
            case "gemini":
                _llm_instance = GeminiClient(s)
            case _:
                _llm_instance = GroqClient(s)
    return _llm_instance
