"""Authentication security helpers for password hashing and JWT handling."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt

from backend.config import get_settings


def hash_password(password: str) -> str:
    """Return a bcrypt hash for a plaintext password."""
    encoded = password.encode("utf-8")
    return bcrypt.hashpw(encoded, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Validate a plaintext password against a bcrypt hash."""
    return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token(user_id: str) -> str:
    """Create a signed JWT access token for the provided user ID."""
    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_exp_minutes)
    payload = {
        "sub": user_id,
        "exp": expires_at,
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT access token payload."""
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
