from __future__ import annotations

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)
    parent_id: Optional[str] = None


class CommentResponse(BaseModel):
    id: str
    user_id: str
    username: str
    display_name: Optional[str]
    avatar_url: Optional[str]
    article_id: str
    parent_id: Optional[str]
    content: str
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
    replies: List[CommentResponse] = []

    class Config:
        from_attributes = True


class VoteRequest(BaseModel):
    vote: int = Field(..., description="1 for upvote, -1 for downvote, 0 to clear")


class EngagementStatus(BaseModel):
    has_read: bool
    current_vote: Optional[int] = None
    vote_count_up: int = 0
    vote_count_down: int = 0
    comment_count: int = 0
