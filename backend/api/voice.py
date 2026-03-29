"""
Voice API router.

Endpoints:
  GET /article/{article_id}/voice?mode=anchor|podcast|drama
    — Generate a ~50s narrated MP3 for an article in the chosen style.
      Step 1: LLM produces a ~100-word script (mode sets system prompt).
      Step 2: Groq TTS (playai-tts) synthesises the script to MP3.
      Returns JSON: { script, audio_b64, mode, label }
"""
from __future__ import annotations

import asyncio
import base64
import logging

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from backend.config import get_settings
from backend.core.db.postgres import Article, AsyncSessionLocal
from backend.core.llm import get_llm

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Voice"])

# ──────────────────────────────────────────────────────────────────────────────
# Mode definitions — each has a label, TTS voice, and LLM system prompt
# ──────────────────────────────────────────────────────────────────────────────

VOICE_MODES: dict[str, dict] = {
    "anchor": {
        "label": "News Anchor",
        "voice": "Fritz-PlayAI",
        "system": (
            "You are a professional TV news anchor delivering a live broadcast segment. "
            "Write a tight, authoritative 100-word spoken script that summarises the key facts "
            "from the article below. Lead with the single most important fact, give 2–3 supporting "
            "details, then close with a brief forward-looking line. "
            "Use clear, formal broadcast English. No headlines, stage directions, or bylines — "
            "output only the spoken words."
        ),
    },
    "podcast": {
        "label": "Casual Podcast",
        "voice": "Nova-PlayAI",
        "system": (
            "You are an engaging podcast host giving a quick, friendly news recap. "
            "Write a conversational 100-word segment about the article below. "
            "Use natural spoken language: contractions, a rhetorical question, a brief personal reaction. "
            "Keep it warm, accessible, and energetic — like explaining to a smart friend. "
            "No stage directions or music cues — output only the spoken words."
        ),
    },
    "drama": {
        "label": "Breaking Drama",
        "voice": "Thunder-PlayAI",
        "system": (
            "You are a cinematic documentary narrator building high-stakes tension. "
            "Write an intense 100-word narration of the article below. "
            "Use vivid, urgent language with short punchy sentences and rhetorical weight. "
            "Open with the stakes, escalate through the key details, land a gut-punch closing line. "
            "No stage directions — output only the narration."
        ),
    },
}


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

async def _generate_script(content: str, mode: str) -> str:
    """Call LLM to produce a voiced script for the given mode."""
    return await get_llm().chat(
        messages=[
            {"role": "system", "content": VOICE_MODES[mode]["system"]},
            {"role": "user",   "content": content},
        ],
        model_tier="fast",
        temperature=0.75,
    )


def _tts_blocking(script: str, voice: str) -> bytes:
    """Blocking Groq TTS call — run this inside asyncio.to_thread."""
    from groq import Groq  # type: ignore[import-untyped]

    settings = get_settings()
    client = Groq(api_key=settings.groq_api_key)
    response = client.audio.speech.create(
        model="playai-tts",
        voice=voice,
        input=script,
        response_format="mp3",
    )
    return response.read()


# ──────────────────────────────────────────────────────────────────────────────
# Endpoint
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/article/{article_id}/voice")
async def get_voice(
    article_id: str,
    mode: str = Query("anchor", pattern="^(anchor|podcast|drama)$"),
):
    """
    Generate a narrated MP3 for an article.

    Returns:
        {
          "script":    "The spoken script text...",
          "audio_b64": "<base64-encoded MP3>",
          "mode":      "anchor",
          "label":     "News Anchor",
        }
    """
    if mode not in VOICE_MODES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown mode '{mode}'. Valid options: {list(VOICE_MODES)}",
        )

    # Fetch article from Postgres
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Article).where(Article.id == article_id))
        article = result.scalar_one_or_none()

    if not article:
        raise HTTPException(status_code=404, detail="Article not found.")
    if not article.content or not article.content.strip():
        raise HTTPException(status_code=422, detail="Article has no content to narrate.")

    # Step 1 — generate script via LLM
    try:
        script = (await _generate_script(article.content, mode)).strip()
    except Exception as exc:
        logger.exception("Voice script LLM failed for article_id=%s mode=%s", article_id, mode)
        raise HTTPException(status_code=503, detail=f"Script generation failed: {exc}") from exc

    # Step 2 — synthesise speech via Groq TTS (blocking SDK → thread pool)
    voice = VOICE_MODES[mode]["voice"]
    try:
        audio_bytes = await asyncio.to_thread(_tts_blocking, script, voice)
    except Exception as exc:
        logger.exception("Groq TTS failed for article_id=%s mode=%s", article_id, mode)
        raise HTTPException(status_code=503, detail=f"TTS synthesis failed: {exc}") from exc

    return {
        "script":    script,
        "audio_b64": base64.b64encode(audio_bytes).decode(),
        "mode":      mode,
        "label":     VOICE_MODES[mode]["label"],
    }
