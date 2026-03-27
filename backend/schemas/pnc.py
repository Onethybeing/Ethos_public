"""
Personal News Constitution (PNC) Pydantic schema.

These models define the canonical structure for a user's news preferences.
They are shared between the PNC service (LLM extraction) and the PNC API router.

Fields sourced from ethosnews/pnc_onboarding/pnc_onboarding.py and ehoss.md spec.
"""
from __future__ import annotations

import textwrap
from typing import Literal

from pydantic import BaseModel, Field


class EpistemicFramework(BaseModel):
    """The user's preferred epistemic approach to evaluating news."""

    primary_mode: Literal["empiricist", "rationalist", "narrative"]
    verification_threshold: float = Field(
        ge=0.0, le=1.0,
        description="0.0 = accept anything, 1.0 = demand hard evidence.",
    )


class NarrativePreferences(BaseModel):
    """Tolerance for narrative diversity and bias in news consumption."""

    diversity_weight: float = Field(
        ge=0.0, le=1.0,
        description="0.0 = mono-perspective, 1.0 = maximum diversity.",
    )
    bias_tolerance: Literal["low", "medium", "high"]


class TopicalConstraints(BaseModel):
    """Topic domains to prioritise and topics to exclude."""

    priority_domains: list[str] = Field(
        default_factory=list,
        description="Up to 10 topic strings the user cares about.",
    )
    excluded_topics: list[str] = Field(
        default_factory=list,
        description="Topics the user wants filtered out.",
    )


class ComplexityPreference(BaseModel):
    """Controls reading level and data richness of delivered content."""

    readability_depth: Literal["beginner", "intermediate", "expert"]
    data_density: Literal["low", "medium", "high"]


class PersonalNewsConstitution(BaseModel):
    """Top-level PNC aggregating all user preference axes."""

    user_id: str
    epistemic_framework: EpistemicFramework
    narrative_preferences: NarrativePreferences
    topical_constraints: TopicalConstraints
    complexity_preference: ComplexityPreference


# ── LLM extraction prompt ─────────────────────────────────────────────────────

PNC_SYSTEM_PROMPT = textwrap.dedent("""\
    You are an AI assistant for EthosNews. Your sole task is to convert a user's
    natural-language description of their ideal news diet into a structured JSON
    object that conforms *exactly* to the following schema.

    Schema
    ------
    {
      "user_id": "<string — use the provided user_id or 'new_user' if not given>",
      "epistemic_framework": {
        "primary_mode": "<'empiricist' | 'rationalist' | 'narrative'>",
        "verification_threshold": <float 0.0–1.0>
      },
      "narrative_preferences": {
        "diversity_weight": <float 0.0–1.0>,
        "bias_tolerance": "<'low' | 'medium' | 'high'>"
      },
      "topical_constraints": {
        "priority_domains": ["<string>", ...],
        "excluded_topics": ["<string>", ...]
      },
      "complexity_preference": {
        "readability_depth": "<'beginner' | 'intermediate' | 'expert'>",
        "data_density": "<'low' | 'medium' | 'high'>"
      }
    }

    Rules
    -----
    1. Return ONLY the JSON object — no markdown fences, no commentary.
    2. Infer reasonable defaults when the user does not state a preference
       (e.g. diversity_weight = 0.5, bias_tolerance = "medium").
    3. primary_mode must be exactly one of the three allowed values.
    4. All float fields must be between 0.0 and 1.0 inclusive.
    5. priority_domains and excluded_topics should each contain 1–10 items
       derived from the user's description.
""")
