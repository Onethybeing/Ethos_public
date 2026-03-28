"""Authentication dependencies for protected API routes."""
from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import select

from backend.core.db.postgres import AsyncSessionLocal, User
from backend.core.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Resolve and return the authenticated user from a bearer token."""
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
    except JWTError as exc:
        raise unauthorized from exc

    user_id = payload.get("sub")
    if not isinstance(user_id, str) or not user_id:
        raise unauthorized

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise unauthorized

    return user
