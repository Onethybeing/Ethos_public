"""
Agentic Fact-Checking Engine.

Pipeline:
  1. extract_claims()      — LLM breaks text into atomic factual claims
  2. _gather_candidates()  — Qdrant corpus search + Tavily web search (parallel per claim)
  3. _batch_rerank()       — Single CrossEncoder call over ALL claim-candidate pairs at once
  4. _classify()           — LLM judges each claim vs its top-4 evidence (semaphore-throttled)
  5. run_full_pipeline()   — orchestrates 1→2→3→4 → FinalFactCheckResult

Fixes vs previous version:
  - Thread-safe singletons: clients.py now uses threading.Lock (double-checked locking)
  - Dedicated _ClassificationResponse model: LLM no longer confuses ClaimEvaluation schema
    with the claim string — it only sees classification/explanation/supporting_urls fields.
  - asyncio.Semaphore(settings.fact_check_max_concurrent): caps parallel LLM calls so
    Groq 6000 TPM limit is not breached; default=3 (configurable via FACT_CHECK_MAX_CONCURRENT).
  - Batched CrossEncoder: all [claim, passage] pairs across all claims are scored in ONE
    ce.predict() call, then results are split back per-claim — ~8× fewer model forward passes.
"""
from __future__ import annotations

import asyncio
import json
import logging
import math
import re
from typing import Literal

from pydantic import BaseModel, Field

from backend.config import get_settings
from backend.core.clients import get_cross_encoder, get_encoder, get_qdrant
from backend.core.llm import get_llm

logger = logging.getLogger(__name__)


# ── Pydantic models ───────────────────────────────────────────────────────────

class ClaimList(BaseModel):
    claims: list[str] = Field(
        description="List of atomic factual claims extracted from the text."
    )


class _ClassificationResponse(BaseModel):
    """Minimal schema sent to the LLM — deliberately excludes `claim` to avoid
    the model echoing back a schema object instead of a string."""
    classification: Literal["Supported", "Contradicted", "Not Mentioned"]
    explanation: str = Field(description="Brief reasoning based strictly on provided evidence.")
    supporting_urls: list[str] = Field(default_factory=list)


class ClaimEvaluation(BaseModel):
    claim: str
    classification: Literal["Supported", "Contradicted", "Not Mentioned"]
    explanation: str = Field(description="Brief reasoning based strictly on provided evidence.")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    supporting_urls: list[str] = Field(default_factory=list)
    source_types: list[str] = Field(default_factory=list)  # "web" | "corpus" per URL


class FinalFactCheckResult(BaseModel):
    evaluations: list[ClaimEvaluation]
    unverifiable_ratio: float = 0.0   # fraction of claims classified "Not Mentioned"
    slop_score: float | None = None   # injected by API layer from article record
    slop_label: str | None = None     # injected by API layer from article record


# ── Helpers ───────────────────────────────────────────────────────────────────

def _sigmoid(x: float) -> float:
    """Normalise a raw cross-encoder logit score to (0, 1)."""
    return 1.0 / (1.0 + math.exp(-x / 3.0))


# ── Engine ────────────────────────────────────────────────────────────────────

class FactChecker:
    """
    Async fact-checking engine. Instantiate once; reuse across requests.
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
        "6. For 'Not Mentioned': include the most relevant evidence source_url(s) for traceability."
    )

    def __init__(self) -> None:
        self._settings = get_settings()
        self._collection = self._settings.qdrant_collection
        logger.info("FactChecker initialized.")

    # ── Step 1: Claim extraction ──────────────────────────────────────────────

    @staticmethod
    def _fallback_extract_claims(text: str, max_claims: int = 8) -> list[str]:
        sentences = [
            s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()
        ]
        return sentences[:max_claims]

    async def extract_claims(self, text: str) -> list[str]:
        try:
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
        except Exception:
            logger.exception("LLM claim extraction failed; using fallback extractor.")
            claims = self._fallback_extract_claims(text)

        claims = [c for c in claims if isinstance(c, str) and c.strip()]
        logger.info("Extracted %d claims.", len(claims))
        return claims

    # ── Step 2: Evidence gathering ────────────────────────────────────────────

    def _corpus_search(self, claim: str, limit: int = 15) -> list[dict]:
        """Semantic search against locally ingested Qdrant corpus."""
        try:
            query_vector = get_encoder().encode(claim).tolist()
            hits = get_qdrant().query_points(
                collection_name=self._collection,
                query=query_vector,
                limit=limit,
            ).points
            return [
                {
                    "source_url": hit.payload.get("source", ""),
                    "content": hit.payload.get("content", "")[:600],
                    "source_type": "corpus",
                }
                for hit in hits
                if hit.payload.get("content", "").strip()
            ]
        except Exception:
            logger.exception("Corpus evidence retrieval failed.")
            return []

    async def _web_search(self, claim: str, max_results: int = 5) -> list[dict]:
        """Live web search via Tavily. Skipped if TAVILY_API_KEY is not set."""
        if not self._settings.tavily_api_key:
            return []
        try:
            from tavily import AsyncTavilyClient
            client = AsyncTavilyClient(api_key=self._settings.tavily_api_key)
            response = await client.search(
                query=claim,
                search_depth="basic",
                max_results=max_results,
            )
            return [
                {
                    "source_url": r.get("url", ""),
                    "content": r.get("content", "")[:600],
                    "source_type": "web",
                }
                for r in response.get("results", [])
                if r.get("content", "").strip()
            ]
        except Exception:
            logger.warning("Tavily web search failed for claim.")
            return []

    async def _gather_candidates(self, claim: str) -> list[dict]:
        """Gather corpus + web candidates for a single claim (parallel)."""
        loop = asyncio.get_running_loop()
        corpus_cands, web_cands = await asyncio.gather(
            loop.run_in_executor(None, self._corpus_search, claim, 15),
            self._web_search(claim, max_results=5),
        )
        return corpus_cands + web_cands

    # ── Step 3: Batched cross-encoder reranking ───────────────────────────────

    async def _batch_rerank(
        self,
        claims: list[str],
        candidate_lists: list[list[dict]],
        top_k: int = 4,
    ) -> list[tuple[list[dict], float]]:
        """
        Score ALL [claim, passage] pairs from all claims in a SINGLE ce.predict() call.
        Returns a list of (top_k_candidates, max_score) per claim.
        """
        # Build flat pair list and track slice boundaries
        all_pairs: list[list[str]] = []
        offsets: list[int] = []
        counts: list[int] = []

        for claim, candidates in zip(claims, candidate_lists):
            offsets.append(len(all_pairs))
            pairs = [[claim, c["content"]] for c in candidates]
            all_pairs.extend(pairs)
            counts.append(len(pairs))

        if not all_pairs:
            return [([], 0.0)] * len(claims)

        loop = asyncio.get_running_loop()
        ce = get_cross_encoder()
        all_scores: list[float] = await loop.run_in_executor(None, ce.predict, all_pairs)

        results: list[tuple[list[dict], float]] = []
        for i, (claim, candidates) in enumerate(zip(claims, candidate_lists)):
            start = offsets[i]
            end = start + counts[i]
            scores = list(all_scores[start:end])

            if not scores:
                results.append(([], 0.0))
                continue

            ranked = sorted(zip(scores, candidates), key=lambda x: x[0], reverse=True)
            top = [c for _, c in ranked[:top_k]]
            max_score = float(ranked[0][0])
            results.append((top, max_score))

        return results

    # ── Step 4: LLM classification (semaphore-throttled) ─────────────────────

    async def _classify(
        self,
        claim: str,
        evidence: list[dict],
        confidence: float,
        sem: asyncio.Semaphore,
    ) -> ClaimEvaluation:
        url_to_type = {e["source_url"]: e["source_type"] for e in evidence}
        evidence_for_llm = [
            {"source_url": e["source_url"], "content": e["content"]}
            for e in evidence
        ]

        async with sem:
            try:
                raw = await get_llm().chat(
                    messages=[
                        {"role": "system", "content": self._CLASSIFICATION_PROMPT},
                        {"role": "user", "content": (
                            f"CLAIM: {claim}\n\n"
                            f"PROVIDED EVIDENCE:\n{json.dumps(evidence_for_llm, indent=2)}"
                        )},
                    ],
                    json_schema=_ClassificationResponse.model_json_schema(),
                    temperature=0.0,
                    model_tier="fast",
                )
                parsed = json.loads(raw)
                evaluation = ClaimEvaluation(
                    claim=claim,
                    classification=parsed.get("classification", "Not Mentioned"),
                    explanation=parsed.get("explanation", ""),
                    confidence=confidence,
                    supporting_urls=parsed.get("supporting_urls", []),
                )
            except Exception:
                logger.exception("Claim classification failed for: %.60s", claim)
                evaluation = ClaimEvaluation(
                    claim=claim,
                    classification="Not Mentioned",
                    explanation="Classification unavailable due to a temporary backend error.",
                    confidence=confidence,
                    supporting_urls=[e["source_url"] for e in evidence[:2]],
                )

        # Tag each supporting URL with its source type
        evaluation.source_types = [
            url_to_type.get(url, "corpus") for url in evaluation.supporting_urls
        ]
        return evaluation

    # ── Orchestration ─────────────────────────────────────────────────────────

    async def run_full_pipeline(self, input_text: str) -> FinalFactCheckResult:
        logger.info("Starting fact-check pipeline…")

        # 1. Extract claims
        claims = await self.extract_claims(input_text)
        if not claims:
            return FinalFactCheckResult(evaluations=[], unverifiable_ratio=0.0)

        # 2. Gather candidates for all claims in parallel (no semaphore needed — these
        #    are search calls, not LLM calls)
        candidate_lists: list[list[dict]] = list(
            await asyncio.gather(*[self._gather_candidates(c) for c in claims])
        )

        # 3. Single batched CrossEncoder call across all claims
        ranked_results = await self._batch_rerank(claims, candidate_lists, top_k=4)

        # 4. LLM classification — throttled by semaphore
        sem = asyncio.Semaphore(self._settings.fact_check_max_concurrent)
        classify_tasks = [
            self._classify(claim, evidence, round(_sigmoid(max_score), 3), sem)
            for claim, (evidence, max_score) in zip(claims, ranked_results)
        ]
        evaluations: list[ClaimEvaluation] = list(await asyncio.gather(*classify_tasks))

        not_mentioned = sum(
            1 for e in evaluations if e.classification == "Not Mentioned"
        )
        unverifiable_ratio = round(not_mentioned / len(evaluations), 3)

        logger.info(
            "Fact-check complete: %d claims, %.0f%% unverifiable.",
            len(evaluations), unverifiable_ratio * 100,
        )
        return FinalFactCheckResult(
            evaluations=evaluations,
            unverifiable_ratio=unverifiable_ratio,
        )
