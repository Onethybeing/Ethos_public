"""
PNC Service — async extraction of Personal News Constitutions via LLM.

Wraps the LLM call and Pydantic validation. No CLI, no Groq import.
"""
from __future__ import annotations

import json
import logging

from backend.core.llm import get_llm
from backend.schemas.pnc import (
    PNC_SYSTEM_PROMPT,
    PersonalNewsConstitution,
)

logger = logging.getLogger(__name__)

_FALLBACK_PNC = {
    "epistemic_framework": {
        "primary_mode": "all",
        "verification_threshold": 0.7,
    },
    "narrative_preferences": {
        "diversity_weight": 0.5,
        "bias_tolerance": "medium",
    },
    "topical_constraints": {
        "priority_domains": ["general news"],
        "excluded_topics": [],
    },
    "complexity_preference": {
        "readability_depth": "intermediate",
        "data_density": "medium",
    },
}


async def generate_pnc(natural_language: str, user_id: str) -> PersonalNewsConstitution:
    """
    Convert a free-text news preference description into a validated PNC.

    Falls back to sensible defaults if the LLM call fails.

    Args:
        natural_language: User's description of their ideal news diet.
        user_id:          The user ID to embed in the constitution.

    Returns:
        A validated PersonalNewsConstitution instance.
    """
    messages = [
        {"role": "system", "content": PNC_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"user_id: {user_id}\n\nDescription: {natural_language}",
        },
    ]

    try:
        raw = await get_llm().chat(
            messages=messages,
            json_schema=PersonalNewsConstitution.model_json_schema(),
            temperature=0.2,
            model_tier="strong",
        )
        data = json.loads(raw)
        data["user_id"] = user_id  # always override with the route param
        pnc = PersonalNewsConstitution(**data)
        logger.info("Generated PNC for user %s.", user_id)
        return pnc

    except Exception as e:
        logger.warning("PNC generation failed for %s (%s), using fallback.", user_id, e)
        fallback = {**_FALLBACK_PNC, "user_id": user_id}
        return PersonalNewsConstitution(**fallback)
