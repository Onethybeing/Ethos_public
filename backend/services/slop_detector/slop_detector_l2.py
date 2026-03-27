"""
Layer 2 AI Slop Detector Module.
Uses a lightweight LLM (via Groq) to evaluate articles that Layer 1 flagged as 'uncertain'.
Supports strict JSON output, truncation, and automatic retries.
"""

import os
import json
from groq import Groq

class SlopDetectorL2:
    """
    Second layer of AI detection for news articles using a Groq LLM.
    Triggered only when local statistical signals fall into the 'uncertain' threshold.
    """

    def __init__(self, api_key: str = None, model: str = "llama-3.1-8b-instant"):
        """
        Initializes the Layer 2 LLM detector.
        
        Args:
            api_key: Optional Groq API key. If None, expects GROQ_API_KEY in environment.
            model: The Groq model to use (default: llama-3.1-8b-instant).
        """
        self.model = model
        # Initialize Groq client (uses env var GROQ_API_KEY by default if api_key is None)
        self.client = Groq(api_key=api_key) if api_key else Groq()

    def analyze(self, text: str) -> dict:
        """
        Calls the LLM to analyze the text and return an AI-generation score.
        Wraps the call in a try/except with exactly one retry.
        
        Args:
            text: The article text to analyze.
            
        Returns:
            dict: Raw evaluation from the LLM containing 'score' and 'reasons'.
                  Returns default score of None on total failure.
        """
        # Truncate to 1500 chars to save tokens and speed up inference
        truncated_text = text[:1500]

        prompt = (
            "You are an AI content detector specialized in news articles.\n"
            "Analyze the article below and score how likely it is to be AI-generated.\n\n"
            "Look for these signals:\n"
            "- Generic phrasing with no original reporting\n"
            "- No specific sources, quotes, or named journalists\n"
            "- Unnaturally smooth and uniform writing style\n"
            "- Filler sentences that add no information\n"
            "- Lacks a specific time, place, or event anchor\n\n"
            "Return JSON only, no explanation:\n"
            '{"score": 0.0, "reasons": ["reason1", "reason2"]}\n\n'
            "Score: 0.0 = definitely human, 1.0 = definitely AI generated.\n\n"
            f"Article:\n{truncated_text}"
        )

        for attempt in range(2):  # 1 initial try + 1 retry
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                    temperature=0.0  # Keep scoring deterministic
                )
                
                result_text = response.choices[0].message.content
                result_json = json.loads(result_text)
                
                # Ensure the JSON has the expected keys, default to safe values if not
                return {
                    "score": float(result_json.get("score", 0.5)),
                    "reasons": result_json.get("reasons", [])
                }
                
            except Exception as e:
                if attempt == 1:
                    # Final failure after retry
                    return None

    def evaluate_pipeline(self, text: str, layer1_result: dict) -> dict:
        """
        The main orchestration method to combine L1 and L2 scores.
        Only invokes the LLM (Layer 2) if Layer 1 returned 'uncertain'.
        
        Args:
            text: The full original article text.
            layer1_result: The dictionary output from utils.slop_detector.SlopDetector.
            
        Returns:
            dict: The final merged results dictionary.
        """
        l1_score = layer1_result.get("ai_slop_score", 0.0)
        l1_label = layer1_result.get("ai_slop_label", "uncertain")

        # Base structure for our return dictionary
        final_output = {
            "ai_slop_score": l1_score,
            "ai_slop_label": l1_label,
            "l1_score": l1_score,
            "l2_score": None,
            "l2_reasons": [],
            "l2_triggered": False
        }

        # Logic: Only run L2 if L1 is 'uncertain'
        if l1_label == "uncertain":
            layer2_result = self.analyze(text)
            
            # If the LLM successfully returned a result
            if layer2_result is not None:
                final_output["l2_triggered"] = True
                final_output["l2_score"] = layer2_result["score"]
                final_output["l2_reasons"] = layer2_result["reasons"]
                
                # Merge Layer 1 (40%) + Layer 2 (60%)
                merged_score = (l1_score * 0.4) + (layer2_result["score"] * 0.6)
                final_output["ai_slop_score"] = round(merged_score, 4)
                
                # Recalculate Label
                if merged_score < 0.35:
                    final_output["ai_slop_label"] = "human"
                elif 0.35 <= merged_score <= 0.65:
                    final_output["ai_slop_label"] = "uncertain"
                else:
                    final_output["ai_slop_label"] = "ai_generated"

        return final_output
