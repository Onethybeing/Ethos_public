"""Pydantic models for authentication request and response payloads."""
from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    """Request payload for user registration."""

    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)
    email: EmailStr | None = None
    display_name: str | None = Field(default=None, max_length=120)


class LoginRequest(BaseModel):
    """Request payload for user login."""

    identity: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class UserProfileResponse(BaseModel):
    """Public user profile fields returned by auth endpoints."""

    id: str
    username: str
    email: str | None = None
    display_name: str | None = None
    onboarding_completed: bool
    streak_count: int = 0


class AuthResponse(BaseModel):
    """Authentication response with bearer token and profile."""

    access_token: str
    token_type: str = "bearer"
    user: UserProfileResponse
