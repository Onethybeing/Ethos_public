"""
Personal News Constitution (PNC) API router.

Endpoints:
  POST  /pnc/generate            — convert natural language → PNC JSON via LLM
  POST  /pnc/{user_id}           — save/upsert a constitution
  GET   /pnc/{user_id}           — fetch a user's constitution
  PATCH /pnc/{user_id}           — partial update (user feedback loop, Stage 11)
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.core.db.postgres import AsyncSessionLocal, UserConstitution
from backend.schemas.pnc import PersonalNewsConstitution
from backend.services.pnc_service import generate_pnc

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/pnc", tags=["PNC"])


# ── Request / response models ─────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    natural_language: str
    user_id: str = "new_user"


class PatchRequest(BaseModel):
    """Partial update — only include fields you want to change."""
    epistemic_framework: dict | None = None
    narrative_preferences: dict | None = None
    topical_constraints: dict | None = None
    complexity_preference: dict | None = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/generate", response_model=PersonalNewsConstitution)
async def generate_constitution(request: GenerateRequest):
    """
    Convert a natural-language description of news preferences into a structured PNC.

    The LLM extracts and validates the constitution. Falls back to sensible defaults
    if the LLM call fails.
    """
    if not request.natural_language.strip():
        raise HTTPException(status_code=400, detail="natural_language cannot be empty.")

    pnc = await generate_pnc(request.natural_language, request.user_id)
    return pnc


@router.post("/{user_id}", response_model=PersonalNewsConstitution)
async def save_constitution(user_id: str, pnc: PersonalNewsConstitution):
    """
    Save or replace a user's Personal News Constitution.

    The request body must be a complete PersonalNewsConstitution JSON.
    """
    pnc.user_id = user_id  # ensure URL param takes precedence

    async with AsyncSessionLocal() as session:
        existing = await session.get(UserConstitution, user_id)
        if existing:
            existing.constitution = pnc.model_dump(exclude={"user_id"})
            existing.updated_at = datetime.now(timezone.utc)
        else:
            session.add(UserConstitution(
                user_id=user_id,
                constitution=pnc.model_dump(exclude={"user_id"}),
            ))
        await session.commit()

    logger.info("Saved PNC for user %s.", user_id)
    return pnc


@router.get("/{user_id}", response_model=PersonalNewsConstitution)
async def get_constitution(user_id: str):
    """Fetch a user's stored Personal News Constitution."""
    async with AsyncSessionLocal() as session:
        record = await session.get(UserConstitution, user_id)

    if not record:
        raise HTTPException(status_code=404, detail="Constitution not found.")

    data = {"user_id": user_id, **record.constitution}
    return PersonalNewsConstitution(**data)


@router.patch("/{user_id}", response_model=PersonalNewsConstitution)
async def update_constitution(user_id: str, patch: PatchRequest):
    """
    Partial update of a user's constitution.

    Supports the user feedback loop (Stage 11 in the spec): only the provided
    fields are merged into the existing constitution.
    """
    async with AsyncSessionLocal() as session:
        record = await session.get(UserConstitution, user_id)
        if not record:
            raise HTTPException(status_code=404, detail="Constitution not found.")

        updates = patch.model_dump(exclude_none=True)
        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update.")

        existing = dict(record.constitution)
        for key, value in updates.items():
            if isinstance(value, dict) and isinstance(existing.get(key), dict):
                existing[key] = {**existing[key], **value}
            else:
                existing[key] = value

        record.constitution = existing
        record.updated_at = datetime.now(timezone.utc)
        await session.commit()

        logger.info("Patched PNC for user %s: %s", user_id, list(updates.keys()))
        return PersonalNewsConstitution(**{"user_id": user_id, **existing})
