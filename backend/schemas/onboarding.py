"""Pydantic schemas for onboarding questionnaire APIs."""
from __future__ import annotations

from pydantic import BaseModel, Field

from backend.schemas.pnc import PersonalNewsConstitution


class OnboardingQuestion(BaseModel):
    """A user-friendly onboarding question."""

    id: str
    question: str
    helper_text: str
    required: bool = True


class OnboardingQuestionsResponse(BaseModel):
    """List of onboarding questions for first-time setup."""

    questions: list[OnboardingQuestion]


class OnboardingSubmitRequest(BaseModel):
    """All questionnaire answers collected in one payload."""

    answers: dict[str, str] = Field(default_factory=dict)


class OnboardingStatusResponse(BaseModel):
    """Whether user has completed onboarding."""

    onboarding_completed: bool


class OnboardingSubmitResponse(BaseModel):
    """Result after onboarding submission and constitution generation."""

    onboarding_completed: bool
    constitution: PersonalNewsConstitution
