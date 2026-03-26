#!/usr/bin/env python3
"""
EthosNews Phase 2 — Personal News Constitution (PNC) Onboarding Prototype
=========================================================================

Architecture
------------
This script implements a terminal‑based onboarding flow that converts a user's
free‑text description of their ideal news diet into a validated, machine‑readable
Personal News Constitution (PNC).

Components:
    1. **Pydantic models** — canonical PNC schema with strict validation.
    2. **LLM extraction** — sends user text to a Groq‑hosted model and
       enforces structured JSON output matching the schema.
    3. **CLI harness** — interactive terminal flow: welcome → prompt → extract →
       validate → confirm → persist.

Security:
    • The Groq API key is accepted **only** via ``--groq_api_key`` at runtime.
    • It is never logged, printed, or written to disk.

Usage::

    python pnc_onboarding.py --groq_api_key YOUR_API_KEY
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import textwrap
import uuid
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError


# ──────────────────────────────────────────────────────────────────────────────
# 1. Pydantic Models (PNC Schema)
# ──────────────────────────────────────────────────────────────────────────────


class EpistemicFramework(BaseModel):
    """Describes the user's preferred epistemic approach to news consumption.

    Attributes:
        primary_mode: One of 'empiricist' (data-driven), 'rationalist'
            (logic-first), or 'narrative' (story-driven).
        verification_threshold: How strict the user wants verification to be
            (0.0 = accept anything → 1.0 = demand hard evidence).
    """

    primary_mode: Literal["empiricist", "rationalist", "narrative"]
    verification_threshold: float = Field(ge=0.0, le=1.0)


class NarrativePreferences(BaseModel):
    """Captures the user's tolerance for narrative diversity and bias.

    Attributes:
        diversity_weight: 0.0 (mono-perspective) → 1.0 (max diversity).
        bias_tolerance: Qualitative label — 'low', 'medium', or 'high'.
    """

    diversity_weight: float = Field(ge=0.0, le=1.0)
    bias_tolerance: str = Field(pattern=r"^(low|medium|high)$")


class TopicalConstraints(BaseModel):
    """Specifies which domains the user prioritises and which they want excluded.

    Attributes:
        priority_domains: List of topic strings the user cares about.
        excluded_topics: List of topic strings the user wants filtered out.
    """

    priority_domains: list[str] = Field(default_factory=list)
    excluded_topics: list[str] = Field(default_factory=list)


class ComplexityPreference(BaseModel):
    """Controls the reading level and data richness of delivered content.

    Attributes:
        readability_depth: One of 'beginner', 'intermediate', or 'expert'.
        data_density: One of 'low', 'medium', or 'high'.
    """

    readability_depth: str = Field(pattern=r"^(beginner|intermediate|expert)$")
    data_density: str = Field(pattern=r"^(low|medium|high)$")


class PersonalNewsConstitution(BaseModel):
    """Top‑level Personal News Constitution aggregating all preference axes.

    This is the canonical schema persisted in ``mock_db_pnc.json`` and
    consumed downstream by the PNC Orchestrator (Layer 1).
    """

    user_id: str
    epistemic_framework: EpistemicFramework
    narrative_preferences: NarrativePreferences
    topical_constraints: TopicalConstraints
    complexity_preference: ComplexityPreference


# ──────────────────────────────────────────────────────────────────────────────
# 2. LLM Extraction Function
# ──────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = textwrap.dedent("""\
    You are an AI assistant for EthosNews. Your sole task is to convert a user's
    natural-language description of their ideal news diet into a structured JSON
    object that conforms *exactly* to the following schema.

    Schema
    ------
    {
      "user_id": "<string — always set to 'prototype_user'>",
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
    1. Return **ONLY** the JSON object — no markdown fences, no commentary.
    2. Infer reasonable defaults when the user does not state a preference
       explicitly (e.g. diversity_weight = 0.5, bias_tolerance = "medium").
    3. primary_mode must be exactly one of the three allowed values.
    4. All float fields must be between 0.0 and 1.0 inclusive.
    5. priority_domains and excluded_topics should each contain 1–10 items
       derived from the user's description.
""")


def _mock_fallback(user_input: str) -> dict:
    """Return a sensible default PNC when the LLM call is unavailable.

    This ensures the prototype remains demonstrable even without network
    connectivity or a valid API key.
    """
    return {
        "user_id": "prototype_user",
        "epistemic_framework": {
            "primary_mode": "empiricist",
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


def extract_pnc_from_text(user_input: str, client: object | None) -> dict:
    """Send *user_input* to a Groq‑hosted LLM and return a PNC‑shaped dict.

    The function instructs the model to reply with strict JSON matching the
    ``PersonalNewsConstitution`` Pydantic schema.  If the LLM call fails for
    any reason a deterministic mock fallback is returned instead, ensuring the
    onboarding flow can still be demonstrated end‑to‑end.

    System prompt used for JSON enforcement
    ----------------------------------------
    (see module‑level ``SYSTEM_PROMPT`` constant)

    Parameters
    ----------
    user_input:
        Free‑text description from the user about their ideal news diet.
    client:
        An initialised ``groq.Groq`` client instance, or ``None`` to trigger
        the mock fallback.

    Returns
    -------
    dict
        A dictionary whose shape is compatible with
        ``PersonalNewsConstitution(**result)``.
    """
    if client is None:
        print("\n⚠  No Groq client available — using mock fallback response.")
        return _mock_fallback(user_input)

    try:
        chat_completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_input},
            ],
            temperature=0.2,
            max_tokens=1024,
            response_format={"type": "json_object"},
        )

        raw_content: str = chat_completion.choices[0].message.content
        parsed: dict = json.loads(raw_content)

        # Ensure user_id is always set for the prototype
        parsed.setdefault("user_id", "prototype_user")

        return parsed

    except Exception as exc:
        print(f"\n⚠  LLM extraction failed ({exc}). Falling back to mock response.")
        return _mock_fallback(user_input)


# ──────────────────────────────────────────────────────────────────────────────
# 3. Persistence Helpers
# ──────────────────────────────────────────────────────────────────────────────

_DB_PATH = Path(__file__).resolve().parent / "mock_db_pnc.json"


def _load_db() -> list[dict]:
    """Load the mock JSON database, returning an empty list if absent."""
    if _DB_PATH.exists():
        with open(_DB_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
            return data if isinstance(data, list) else [data]
    return []


def _save_to_db(pnc: PersonalNewsConstitution) -> None:
    """Append a validated PNC record to the mock JSON database."""
    records = _load_db()
    records.append(pnc.model_dump())
    with open(_DB_PATH, "w", encoding="utf-8") as fh:
        json.dump(records, fh, indent=2, ensure_ascii=False)


# ──────────────────────────────────────────────────────────────────────────────
# 4. Pretty Printing
# ──────────────────────────────────────────────────────────────────────────────

_SEPARATOR = "─" * 60


def _pretty_print_pnc(pnc: PersonalNewsConstitution) -> None:
    """Display a validated PNC in a human‑friendly terminal format."""
    print(f"\n{_SEPARATOR}")
    print("  📜  YOUR PERSONAL NEWS CONSTITUTION")
    print(_SEPARATOR)

    ef = pnc.epistemic_framework
    print(f"\n  🧠  Epistemic Framework")
    print(f"       Primary Mode           : {ef.primary_mode.capitalize()}")
    print(f"       Verification Threshold : {ef.verification_threshold:.2f}")

    np_ = pnc.narrative_preferences
    print(f"\n  📖  Narrative Preferences")
    print(f"       Diversity Weight       : {np_.diversity_weight:.2f}")
    print(f"       Bias Tolerance         : {np_.bias_tolerance.capitalize()}")

    tc = pnc.topical_constraints
    print(f"\n  🎯  Topical Constraints")
    print(f"       Priority Domains       : {', '.join(tc.priority_domains) or '—'}")
    print(f"       Excluded Topics        : {', '.join(tc.excluded_topics) or '—'}")

    cp = pnc.complexity_preference
    print(f"\n  📊  Complexity Preference")
    print(f"       Readability Depth      : {cp.readability_depth.capitalize()}")
    print(f"       Data Density           : {cp.data_density.capitalize()}")

    print(f"\n  🆔  User ID: {pnc.user_id}")
    print(_SEPARATOR)


# ──────────────────────────────────────────────────────────────────────────────
# 5. Terminal Onboarding CLI
# ──────────────────────────────────────────────────────────────────────────────


def _build_groq_client(api_key: str | None):
    """Attempt to instantiate a ``groq.Groq`` client.

    Returns ``None`` (triggering the mock fallback) when the key is missing or
    the ``groq`` package is not installed.
    """
    if not api_key:
        return None
    try:
        from groq import Groq  # type: ignore[import-untyped]

        return Groq(api_key=api_key)
    except ImportError:
        print(
            "\n⚠  'groq' package not installed. "
            "Install with: pip install groq\n"
            "   Continuing with mock fallback.\n"
        )
        return None


def main() -> None:
    """Interactive terminal onboarding flow for EthosNews PNC creation.

    Steps:
        1. Parse CLI args (``--groq_api_key``).
        2. Print welcome banner.
        3. Prompt user for free‑text news diet description.
        4. Extract structured PNC via Groq LLM (or mock fallback).
        5. Validate with Pydantic.
        6. Pretty‑print the constitution.
        7. Ask for confirmation.
        8. Persist to ``mock_db_pnc.json`` on confirmation.
    """

    # ── Step 1: Parse CLI arguments ──────────────────────────────────────
    parser = argparse.ArgumentParser(
        description="EthosNews Phase 2 — PNC Onboarding Prototype",
    )
    parser.add_argument(
        "--groq_api_key",
        type=str,
        default=None,
        help="Groq API key (never stored or logged).",
    )
    args = parser.parse_args()

    client = _build_groq_client(args.groq_api_key)

    # ── Step 2: Welcome message ──────────────────────────────────────────
    print()
    print("=" * 60)
    print("  Welcome to EthosNews Phase 2")
    print("  — Personal News Constitution Builder —")
    print("=" * 60)
    print()
    print(
        "  Your Personal News Constitution (PNC) tells our system\n"
        "  exactly how to curate, verify, and present news for you.\n"
        "  We'll convert your description into a structured profile\n"
        "  in seconds.\n"
    )

    # ── Step 3: Prompt user ──────────────────────────────────────────────
    print(
        "💬  Describe your ideal news diet in a few sentences.\n"
        "    What do you want to see, and what are you tired of?\n"
    )
    try:
        user_input: str = input(">>> ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n\nExiting. No constitution was created.")
        sys.exit(0)

    if not user_input:
        print("\n⚠  Empty input received. Please re‑run and describe your preferences.")
        sys.exit(1)

    # ── Step 4: Extract PNC via LLM ──────────────────────────────────────
    print("\n⏳  Analyzing your preferences …")
    raw_pnc: dict = extract_pnc_from_text(user_input, client)

    # ── Step 5: Validate with Pydantic ───────────────────────────────────
    try:
        pnc = PersonalNewsConstitution(**raw_pnc)
    except ValidationError as ve:
        print("\n❌  Validation failed. The LLM output did not conform to the schema:")
        for err in ve.errors():
            loc = " → ".join(str(l) for l in err["loc"])
            print(f"     • {loc}: {err['msg']}")
        print("\nPlease try again with a more detailed description.")
        sys.exit(1)

    # ── Step 6: Pretty-print ─────────────────────────────────────────────
    _pretty_print_pnc(pnc)

    # ── Step 7: Confirmation ─────────────────────────────────────────────
    print()
    try:
        confirm: str = input(
            "Does this Constitution accurately reflect your intent? (y/n): "
        ).strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\n\nExiting. Constitution was NOT saved.")
        sys.exit(0)

    if confirm not in ("y", "yes"):
        print(
            "\n🔄  No problem! Re‑run the tool and try a different description.\n"
            "    Your constitution was NOT saved."
        )
        sys.exit(0)

    # ── Step 8: Persist ──────────────────────────────────────────────────
    _save_to_db(pnc)
    print(f"\n✅  Constitution saved to {_DB_PATH.name}")
    print("    Your PNC is now active. EthosNews will curate your feed accordingly.\n")


if __name__ == "__main__":
    main()
