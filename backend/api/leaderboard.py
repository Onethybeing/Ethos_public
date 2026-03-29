"""
Gamified Leaderboard API router.

Endpoints:
  POST /leaderboard/event       — record a read event and compute engagement score
  GET  /leaderboard/top         — top N users by cumulative engagement score
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.core.db.postgres import AsyncSessionLocal, UserConstitution
from backend.services.leaderboard.leaderboard_engine import get_top_users, record_engagement

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/leaderboard", tags=["Leaderboard"])


class EngagementEventRequest(BaseModel):
    user_id: str
    article_id: str
    time_spent_secs: int = Field(ge=0, description="Seconds the user spent reading the article.")


@router.post("/event")
async def post_engagement_event(request: EngagementEventRequest):
    """
    Record that a user read an article and compute their engagement score.

    Score formula (from ehoss.md):
        0.40 × PNC alignment  +  0.30 × diversity  +  0.30 × time on verified

    The score is added to the user's running total in the Redis leaderboard.
    The full event is persisted to the engagement_events Postgres table.
    """
    # Fetch user's PNC for alignment computation
    async with AsyncSessionLocal() as session:
        record = await session.get(UserConstitution, request.user_id)

    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"No PNC found for user '{request.user_id}'. Create one first via POST /pnc/generate.",
        )

    result = await record_engagement(
        user_id=request.user_id,
        article_id=request.article_id,
        time_spent_secs=request.time_spent_secs,
        user_constitution=record.constitution,
    )
    return result


@router.get("/top")
async def get_leaderboard(limit: int = 50):
    """
    Fetch the top N users by cumulative engagement score.

    Returns a ranked list of {rank, user_id, score}.
    Scores are cumulative across all recorded engagement events.
    """
    if limit < 1 or limit > 200:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 200.")

    top = await get_top_users(limit=limit)
    return {"count": len(top), "leaderboard": top}
