"""Authentication API router with JWT signup/login for EthosNews."""
from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select

from backend.core.auth import get_current_user
from backend.core.db.postgres import AsyncSessionLocal, User, UserConstitution
from backend.core.security import create_access_token, hash_password, verify_password
from backend.schemas.auth import AuthResponse, LoginRequest, SignupRequest, UserProfileResponse

router = APIRouter(prefix="/auth", tags=["Auth"])


def _user_profile(user: User) -> UserProfileResponse:
    return UserProfileResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        display_name=user.display_name,
        onboarding_completed=bool(user.onboarding_completed),
    )


def _empty_constitution() -> dict:
    """Return a null-initialized PNC structure for first-time users."""
    return {
        "epistemic_framework": {
            "primary_mode": None,
            "verification_threshold": None,
        },
        "narrative_preferences": {
            "diversity_weight": None,
            "bias_tolerance": None,
        },
        "topical_constraints": {
            "priority_domains": None,
            "excluded_topics": None,
        },
        "complexity_preference": {
            "readability_depth": None,
            "data_density": None,
        },
    }


@router.post("/signup", response_model=AuthResponse)
async def signup(request: SignupRequest) -> AuthResponse:
    """Register a new user and return a JWT access token."""
    username = request.username.strip()
    email = request.email.lower().strip() if request.email else None

    async with AsyncSessionLocal() as session:
        conflict_conditions = [User.username == username]
        if email:
            conflict_conditions.append(User.email == email)

        existing_result = await session.execute(
            select(User).where(or_(*conflict_conditions))
        )
        if existing_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username or email already exists.",
            )

        user = User(
            id=str(uuid4()),
            username=username,
            email=email,
            display_name=request.display_name,
            password_hash=hash_password(request.password),
            onboarding_completed=False,
            is_active=True,
        )
        session.add(user)
        session.add(
            UserConstitution(
                user_id=user.id,
                constitution=_empty_constitution(),
            )
        )
        await session.commit()

    token = create_access_token(user.id)
    return AuthResponse(access_token=token, user=_user_profile(user))


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest) -> AuthResponse:
    """Authenticate a user using username/email and password."""
    identity = request.identity.strip()
    email_candidate = identity.lower()

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(or_(User.username == identity, User.email == email_candidate))
        )
        user = result.scalar_one_or_none()

    if not user or not user.password_hash or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive.")

    token = create_access_token(user.id)
    return AuthResponse(access_token=token, user=_user_profile(user))


@router.get("/me", response_model=UserProfileResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> UserProfileResponse:
    """Return the current authenticated user's profile."""
    return _user_profile(current_user)
