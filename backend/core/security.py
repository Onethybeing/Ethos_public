"""Authentication security helpers for password hashing and JWT handling."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt

from backend.config import get_settings


def _jwt_config() -> tuple[str, str, int]:
    """Load and validate JWT settings from centralized config."""
    settings = get_settings()
    secret = settings.jwt_secret.strip()
    algorithm = settings.jwt_algorithm.strip()
    exp_minutes = settings.access_token_exp_minutes

    if not secret:
        raise RuntimeError("JWT_SECRET is not configured. Set it in backend/.env.")
    if not algorithm:
        raise RuntimeError("JWT_ALGORITHM is not configured. Set it in backend/.env.")
    if exp_minutes <= 0:
        raise RuntimeError("ACCESS_TOKEN_EXP_MINUTES must be greater than 0.")

    return secret, algorithm, exp_minutes


def hash_password(password: str) -> str:
    """Return a bcrypt hash for a plaintext password."""
    encoded = password.encode("utf-8")
    return bcrypt.hashpw(encoded, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Validate a plaintext password against a bcrypt hash."""
    return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token(user_id: str) -> str:
    """Create a signed JWT access token for the provided user ID."""
    secret, algorithm, exp_minutes = _jwt_config()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=exp_minutes)
    payload = {
        "sub": user_id,
        "exp": expires_at,
        "type": "access",
    }
    return jwt.encode(payload, secret, algorithm=algorithm)


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT access token payload."""
    secret, algorithm, _ = _jwt_config()
    return jwt.decode(token, secret, algorithms=[algorithm])
