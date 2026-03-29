from __future__ import annotations

import uuid
from typing import List, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func, delete, update
from sqlalchemy.orm import selectinload

from backend.core.auth import get_current_user
from backend.core.db.postgres import (
    AsyncSessionLocal,
    User,
    Comment,
    ArticleVote,
    EngagementEvent,
    Article
)
from backend.schemas.engagement import (
    CommentCreate,
    CommentResponse,
    VoteRequest,
    EngagementStatus
)

router = APIRouter(prefix="/articles", tags=["Engagement"])


async def _get_engagement_status(session, user_id: str, article_id: str) -> EngagementStatus:
    # Check if user has read the article
    read_result = await session.execute(
        select(EngagementEvent).where(
            EngagementEvent.user_id == user_id,
            EngagementEvent.article_id == article_id
        ).limit(1)
    )
    has_read = read_result.scalar_one_or_none() is not None

    # Get current vote
    vote_result = await session.execute(
        select(ArticleVote).where(
            ArticleVote.user_id == user_id,
            ArticleVote.article_id == article_id
        )
    )
    vote_obj = vote_result.scalar_one_or_none()
    current_vote = vote_obj.vote if vote_obj else None

    # Get aggregate vote counts
    up_result = await session.execute(
        select(func.count()).select_from(ArticleVote).where(
            ArticleVote.article_id == article_id,
            ArticleVote.vote == 1
        )
    )
    up_count = up_result.scalar_one()

    down_result = await session.execute(
        select(func.count()).select_from(ArticleVote).where(
            ArticleVote.article_id == article_id,
            ArticleVote.vote == -1
        )
    )
    down_count = down_result.scalar_one()

    # Get comment count
    comment_result = await session.execute(
        select(func.count()).select_from(Comment).where(
            Comment.article_id == article_id,
            Comment.is_deleted == False
        )
    )
    comment_count = comment_result.scalar_one()

    return EngagementStatus(
        has_read=has_read,
        current_vote=current_vote,
        vote_count_up=up_count,
        vote_count_down=down_count,
        comment_count=comment_count
    )


async def _increment_user_participation(session, user_id: str):
    await session.execute(
        update(User)
        .where(User.id == user_id)
        .values(active_participations=User.active_participations + 1)
    )


@router.get("/{article_id}/engagement", response_model=EngagementStatus)
async def get_article_engagement(
    article_id: str,
    current_user: User = Depends(get_current_user)
) -> EngagementStatus:
    """Check if the current user has read the article and get vote/comment counts."""
    async with AsyncSessionLocal() as session:
        return await _get_engagement_status(session, current_user.id, article_id)


@router.post("/{article_id}/vote")
async def vote_article(
    article_id: str,
    request: VoteRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Cast an upvote or downvote. 
    ENFORCEMENT: Only allowed if the user has an EngagementEvent for this article.
    """
    async with AsyncSessionLocal() as session:
        if request.vote == 0:
            # Clear vote
            await session.execute(
                delete(ArticleVote).where(
                    ArticleVote.user_id == current_user.id,
                    ArticleVote.article_id == article_id
                )
            )
        else:
            # Upsert vote
            vote_result = await session.execute(
                select(ArticleVote).where(
                    ArticleVote.user_id == current_user.id,
                    ArticleVote.article_id == article_id
                )
            )
            existing_vote = vote_result.scalar_one_or_none()
            
            if existing_vote:
                existing_vote.vote = request.vote
                existing_vote.updated_at = datetime.now(timezone.utc)
            else:
                new_vote = ArticleVote(
                    user_id=current_user.id,
                    article_id=article_id,
                    vote=request.vote
                )
                session.add(new_vote)
                # Participation bonus for first-time vote on an article
                await _increment_user_participation(session, current_user.id)

        await session.commit()
        return {"status": "ok", "vote": request.vote}


@router.post("/{article_id}/comments", response_model=CommentResponse)
async def post_comment(
    article_id: str,
    request: CommentCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Post a comment or a reply.
    ENFORCEMENT: Only allowed if the user has an EngagementEvent for this article.
    """
    async with AsyncSessionLocal() as session:
        # 2. Check parent if it exists
        if request.parent_id:
            parent_check = await session.execute(
                select(Comment).where(Comment.id == request.parent_id)
            )
            if not parent_check.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Parent comment not found."
                )

        # 3. Create comment
        comment = Comment(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            article_id=article_id,
            parent_id=request.parent_id,
            content=request.content.strip()
        )
        session.add(comment)
        
        # 4. Participation impact
        await _increment_user_participation(session, current_user.id)
        
        await session.commit()
        
        return CommentResponse(
            id=comment.id,
            user_id=comment.user_id,
            username=current_user.username,
            display_name=current_user.display_name,
            avatar_url=current_user.avatar_url,
            article_id=comment.article_id,
            parent_id=comment.parent_id,
            content=comment.content,
            is_deleted=comment.is_deleted,
            created_at=comment.created_at or datetime.now(timezone.utc),
            updated_at=comment.updated_at or datetime.now(timezone.utc),
            replies=[]
        )


@router.get("/{article_id}/comments", response_model=List[CommentResponse])
async def get_comments(article_id: str):
    """Fetch all comments for an article and return them as a threaded tree."""
    async with AsyncSessionLocal() as session:
        # Fetch all comments for this article including user info
        # Using a simple join to get username/display_name
        stmt = (
            select(Comment, User.username, User.display_name, User.avatar_url)
            .join(User, Comment.user_id == User.id)
            .where(Comment.article_id == article_id)
            .order_by(Comment.created_at.asc())
        )
        result = await session.execute(stmt)
        rows = result.all()

        # Build threads
        comment_map = {}
        roots = []

        for comment, username, display_name, avatar_url in rows:
            resp = CommentResponse(
                id=comment.id,
                user_id=comment.user_id,
                username=username,
                display_name=display_name,
                avatar_url=avatar_url,
                article_id=comment.article_id,
                parent_id=comment.parent_id,
                content=comment.content if not comment.is_deleted else "[Deleted]",
                is_deleted=comment.is_deleted,
                created_at=comment.created_at,
                updated_at=comment.updated_at,
                replies=[]
            )
            comment_map[resp.id] = resp
            
            if resp.parent_id and resp.parent_id in comment_map:
                comment_map[resp.parent_id].replies.append(resp)
            else:
                roots.append(resp)

        return roots
