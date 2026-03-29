"""
Layer 2 AI Slop Detector — LLM-based fallback.

Triggered only when Layer 1 (statistical) returns "uncertain".
Accepts any BaseLLMClient; does not instantiate its own Groq client.
"""
from __future__ import annotations

import json
import logging

logger = logging.getLogger(__name__)


class SlopDetectorL2:
    """
    LLM-based AI content detector for articles the statistical Layer 1 flagged
    as "uncertain". Uses the fast model tier (low latency, low cost).
    """

    _PROMPT_TEMPLATE = (
        "You are an AI content detector specialized in news articles.\n"
        "Analyze the article below and score how likely it is to be AI-generated.\n\n"
        "Look for these signals:\n"
        "- Generic phrasing with no original reporting\n"
        "- No specific sources, quotes, or named journalists\n"
        "- Unnaturally smooth and uniform writing style\n"
        "- Filler sentences that add no information\n"
        "- Lacks a specific time, place, or event anchor\n\n"
        "Return JSON only: "
        '{{"score": 0.0, "reasons": ["reason1", "reason2"]}}\n\n'
        "Score: 0.0 = definitely human, 1.0 = definitely AI generated.\n\n"
        "Article:\n{text}"
    )

    def __init__(self, llm_client) -> None:
        """
        Args:
            llm_client: Any BaseLLMClient instance (from backend.core.llm).
        """
        self._llm = llm_client

    async def analyze(self, text: str) -> dict | None:
        """Call the LLM; return {score, reasons} or None on failure."""
        truncated = text[:4000]
        messages = [
            {"role": "user", "content": self._PROMPT_TEMPLATE.format(text=truncated)}
        ]

        for attempt in range(2):
            try:
                raw = await self._llm.chat(
                    messages=messages,
                    json_schema={"score": "number", "reasons": ["string"]},
                    temperature=0.0,
                    model_tier="fast",
                )
                result = json.loads(raw)
                return {
                    "score": float(result.get("score", 0.5)),
                    "reasons": result.get("reasons", []),
                }
            except Exception as e:
                if attempt == 1:
                    logger.warning("SlopDetectorL2 failed after retry: %s", e)
                    return None

    async def evaluate_pipeline(self, text: str, layer1_result: dict) -> dict:
        """
        Combine L1 statistical result with L2 LLM result.

        Only invokes the LLM if L1 returned "uncertain".
        Merges scores: L1 × 0.4 + L2 × 0.6.
        """
        l1_score = layer1_result.get("ai_slop_score", 0.0)
        l1_label = layer1_result.get("ai_slop_label", "uncertain")

        final = {
            **layer1_result,
            "l1_score": l1_score,
            "l2_score": None,
            "l2_reasons": [],
            "l2_triggered": False,
        }

        if l1_label != "uncertain":
            return final

        layer2 = await self.analyze(text)
        if layer2 is None:
            return final

        final["l2_triggered"] = True
        final["l2_score"] = layer2["score"]
        final["l2_reasons"] = layer2["reasons"]

        merged = round(l1_score * 0.4 + layer2["score"] * 0.6, 4)
        final["ai_slop_score"] = merged

        if merged < 0.35:
            final["ai_slop_label"] = "human"
        elif merged <= 0.65:
            final["ai_slop_label"] = "uncertain"
        else:
            final["ai_slop_label"] = "ai_generated"

        return final
