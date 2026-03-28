"""Onboarding API router for first-time questionnaire and PNC generation."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from backend.core.auth import get_current_user
from backend.core.db.postgres import AsyncSessionLocal, User, UserConstitution
from backend.schemas.onboarding import (
    OnboardingQuestion,
    OnboardingQuestionsResponse,
    OnboardingStatusResponse,
    OnboardingSubmitRequest,
    OnboardingSubmitResponse,
)
from backend.services.pnc_service import generate_pnc

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])

_QUESTIONS: list[OnboardingQuestion] = [
    OnboardingQuestion(
        id="topics",
        question="What topics do you want more of, and what topics do you want to avoid?",
        helper_text="Example: more climate tech and policy, avoid celebrity gossip.",
        required=True,
    ),
    OnboardingQuestion(
        id="trust_style",
        question="What makes a news story feel trustworthy to you?",
        helper_text="You can mention data, sources, expert opinion, lived experience, or anything else.",
        required=True,
    ),
    OnboardingQuestion(
        id="perspective_appetite",
        question="How much do you want to see viewpoints you might disagree with?",
        helper_text="Answer in your own words.",
        required=True,
    ),
    OnboardingQuestion(
        id="verification_appetite",
        question="How strict should we be before showing a claim as credible?",
        helper_text="From quick updates to highly verified-only, choose your comfort.",
        required=True,
    ),
    OnboardingQuestion(
        id="reading_style",
        question="What reading style do you prefer?",
        helper_text="Simple summaries, balanced explainers, or deep technical breakdowns.",
        required=True,
    ),
    OnboardingQuestion(
        id="bias_tolerance",
        question="How much opinionated framing are you okay with in your feed?",
        helper_text="Low, medium, high—or explain in your own words.",
        required=True,
    ),
]


def _answers_to_single_prompt(answers: dict[str, str]) -> str:
    """Convert all questionnaire answers into one LLM input text block."""
    lines: list[str] = [
        "User completed onboarding questionnaire. Infer full Personal News Constitution:",
        "",
    ]
    by_id = {q.id: q for q in _QUESTIONS}
    for question in _QUESTIONS:
        value = answers.get(question.id, "").strip()
        lines.append(f"Q: {question.question}")
        lines.append(f"A: {value}")
        lines.append("")

    extra_ids = [key for key in answers.keys() if key not in by_id]
    if extra_ids:
        lines.append("Additional user inputs:")
        for key in extra_ids:
            lines.append(f"- {key}: {answers.get(key, '')}")

    return "\n".join(lines).strip()


@router.get("/questions", response_model=OnboardingQuestionsResponse)
async def get_questions() -> OnboardingQuestionsResponse:
    """Return onboarding questionnaire prompts."""
    return OnboardingQuestionsResponse(questions=_QUESTIONS)


@router.get("/status", response_model=OnboardingStatusResponse)
async def get_onboarding_status(current_user: User = Depends(get_current_user)) -> OnboardingStatusResponse:
    """Return whether authenticated user has completed onboarding."""
    return OnboardingStatusResponse(onboarding_completed=bool(current_user.onboarding_completed))


@router.post("/submit", response_model=OnboardingSubmitResponse)
async def submit_onboarding(
    request: OnboardingSubmitRequest,
    current_user: User = Depends(get_current_user),
) -> OnboardingSubmitResponse:
    """Submit all questionnaire answers once and generate/save full PNC."""
    required_ids = [q.id for q in _QUESTIONS if q.required]
    missing = [qid for qid in required_ids if not request.answers.get(qid, "").strip()]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required answers: {', '.join(missing)}",
        )

    natural_language = _answers_to_single_prompt(request.answers)
    constitution = await generate_pnc(natural_language, current_user.id)

    async with AsyncSessionLocal() as session:
        db_user = await session.get(User, current_user.id)
        if not db_user:
            raise HTTPException(status_code=404, detail="User not found.")

        record = await session.get(UserConstitution, current_user.id)
        payload = constitution.model_dump(exclude={"user_id"})
        if record:
            record.constitution = payload
            record.updated_at = datetime.now(timezone.utc)
        else:
            session.add(UserConstitution(user_id=current_user.id, constitution=payload))

        db_user.onboarding_completed = True
        db_user.updated_at = datetime.now(timezone.utc)
        await session.commit()

    return OnboardingSubmitResponse(onboarding_completed=True, constitution=constitution)
