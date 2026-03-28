"""
Agentic Fact-Checking Engine.

Pipeline (fully async, claims evaluated in parallel):
  1. extract_claims()   — LLM breaks article into atomic factual claims
  2. retrieve_evidence()— for each claim, semantic search in Qdrant
  3. classify_claim()   — LLM judges claim vs evidence: Supported / Contradicted / Not Mentioned
  4. run_full_pipeline()— orchestrates 1 → parallel(2+3) → returns FinalFactCheckResult

Latency: sequential was O(n_claims × LLM_latency). Parallel is O(1 × LLM_latency).
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Literal

from pydantic import BaseModel, Field

from backend.config import get_settings
from backend.core.clients import get_encoder, get_qdrant
from backend.core.llm import get_llm

logger = logging.getLogger(__name__)


# ── Pydantic response models ──────────────────────────────────────────────────

class ClaimList(BaseModel):
    claims: list[str] = Field(
        description="List of atomic factual claims extracted from the text."
    )


class ClaimEvaluation(BaseModel):
    claim: str
    classification: Literal["Supported", "Contradicted", "Not Mentioned"]
    explanation: str = Field(description="Brief reasoning based strictly on provided evidence.")
    supporting_urls: list[str] = Field(default_factory=list)


class FinalFactCheckResult(BaseModel):
    evaluations: list[ClaimEvaluation]


# ── Engine ────────────────────────────────────────────────────────────────────

class FactChecker:
    """
    Async fact-checking engine. Instantiate once; reuse across requests.
    Uses shared LLM client, Qdrant client, and encoder from core.clients.
    """

    _CLAIM_EXTRACTION_PROMPT = (
        "You are a meticulous fact-checking assistant. Break the provided text into "
        "distinct, atomic factual claims. Each claim must represent one singular, "
        "verifiable fact without compound conjunctions.\n"
        "RULES:\n"
        "- Extract numerical and statistical statements as separate claims.\n"
        "- Ignore opinions and rhetorical questions.\n"
        "- Return at most 8 claims (focus on the most important ones)."
    )

    _CLASSIFICATION_PROMPT = (
        "You are an impartial Fact-Checking Judge. Evaluate the CLAIM using ONLY the "
        "PROVIDED EVIDENCE.\n"
        "Rules:\n"
        "1. 'Supported' — evidence directly validates the claim.\n"
        "2. 'Contradicted' — evidence directly contradicts the claim.\n"
        "3. 'Not Mentioned' — evidence does not prove or disprove the claim; "
        "   do NOT use outside knowledge.\n"
        "4. For numbers: if evidence states a DIFFERENT number, label 'Contradicted'.\n"
        "5. For 'Supported'/'Contradicted': include exact source_url(s) in supporting_urls.\n"
        "6. For 'Not Mentioned': leave supporting_urls empty."
    )

    def __init__(self) -> None:
        settings = get_settings()
        self._collection = settings.qdrant_collection
        logger.info("FactChecker initialized.")

    async def extract_claims(self, text: str) -> list[str]:
        """Step 1: Break article into atomic factual claims."""
        logger.debug("Extracting claims…")
        raw = await get_llm().chat(
            messages=[
                {"role": "system", "content": self._CLAIM_EXTRACTION_PROMPT},
                {"role": "user", "content": f"TEXT:\n{text}"},
            ],
            json_schema=ClaimList.model_json_schema(),
            temperature=0.0,
            model_tier="fast",
        )
        claims = json.loads(raw).get("claims", [])
        logger.info("Extracted %d claims.", len(claims))
        return claims

    def retrieve_evidence(self, claim: str, limit: int = 4) -> list[dict]:
        """Step 2: Semantic search in Qdrant for articles relevant to the claim."""
        query_vector = get_encoder().encode(claim).tolist()
        hits = get_qdrant().query_points(
            collection_name=self._collection,
            query=query_vector,
            limit=limit,
        ).points
        return [
            {
                "source_url": hit.payload.get("source", ""),
                "content": hit.payload.get("content", "")[:500],
            }
            for hit in hits
        ]

    async def classify_claim(self, claim: str, evidence: list[dict]) -> ClaimEvaluation:
        """Step 3: LLM judges claim vs evidence."""
        user_prompt = (
            f"CLAIM: {claim}\n\nPROVIDED EVIDENCE:\n{json.dumps(evidence, indent=2)}"
        )
        raw = await get_llm().chat(
            messages=[
                {"role": "system", "content": self._CLASSIFICATION_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            json_schema=ClaimEvaluation.model_json_schema(),
            temperature=0.0,
            model_tier="fast",
        )
        return ClaimEvaluation(**json.loads(raw))

    async def _evaluate_claim(self, claim: str) -> ClaimEvaluation:
        """Retrieve evidence and classify a single claim (used for parallel execution)."""
        evidence = self.retrieve_evidence(claim)  # sync Qdrant call — fast
        return await self.classify_claim(claim, evidence)

    async def run_full_pipeline(self, input_text: str) -> FinalFactCheckResult:
        """
        Full fact-check: extract claims → evaluate all in parallel → return result.

        Parallel evaluation reduces latency from O(n × llm_latency) to O(llm_latency).
        """
        logger.info("Starting fact-check pipeline…")

        claims = await self.extract_claims(input_text)
        if not claims:
            return FinalFactCheckResult(evaluations=[])

        # Evaluate all claims concurrently
        evaluations = await asyncio.gather(
            *[self._evaluate_claim(claim) for claim in claims]
        )

        logger.info("Fact-check complete: %d claims evaluated.", len(evaluations))
        return FinalFactCheckResult(evaluations=list(evaluations))
