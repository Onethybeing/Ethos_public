"""
LLM Service - Narrative extraction using Google Gemini

Extracts:
- Narrative framing
- Causal structure
- Emotional tone
- Actor roles
- Pattern tags
"""

from google import genai
from .. import config as settings
from typing import Dict, Any, List, Optional
import json
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NarrativeExtractor:
    """
    Extracts narrative patterns from text using Google Gemini.
    
    Uses Gemini Flash for cost-effective extraction with rate limiting.
    """
    
    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model_id = settings.GEMINI_MODEL
        self._last_call_time = 0
        self._min_interval = 0.5  # Minimum seconds between API calls
    
    def generate_content(self, prompt: str, max_retries: int = 3) -> Any:
        """Wrapper for direct model calls (used by other agents).
        
        Retries on 429 (rate limit) with exponential backoff.
        """
        for attempt in range(max_retries):
            self._rate_limit()
            try:
                return self.client.models.generate_content(
                    model=self.model_id,
                    contents=prompt
                )
            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                    # Parse retry delay from error if available
                    wait_time = min(60 * (2 ** attempt), 300)  # 60s, 120s, 300s max
                    import re
                    delay_match = re.search(r'retry in ([\d.]+)s', error_str)
                    if delay_match:
                        wait_time = min(float(delay_match.group(1)) + 2, 300)
                    
                    if attempt < max_retries - 1:
                        logger.warning(f"Rate limited (attempt {attempt + 1}/{max_retries}). Waiting {wait_time:.0f}s...")
                        time.sleep(wait_time)
                        continue
                raise
    
    def _rate_limit(self):
        """Simple rate limiting to avoid API throttling."""
        elapsed = time.time() - self._last_call_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_call_time = time.time()
    
    def extract_narrative(self, title: str, text: str) -> Dict[str, Any]:
        """
        Extract narrative components from article content.
        """
        logger.info(f"🔮 Extracting narrative for: {title[:50]}...")
        # Rate limiting handled in generate_content
        truncated_text = text[:1500] if text else ""
        
        prompt = f"""Analyze this content as a NARRATIVE system. Do not just summarize it—deconstruct its hidden story structure.
        
HEADLINE: {title}

TEXT: {truncated_text}

You are an expert media analyst detecting underlying narrative patterns. Return a JSON object with these EXACT fields:

{{
    "narrative_framing": "A short, punchy phrase (3-6 words) capturing the core conflict or theme (e.g., 'Big Tech vs The People', 'Inevitable March of Progress', 'Regulatory Catch-up').",
    
    "causal_structure": "A single sentence explaining the implied logic: 'Because X happened, Y is inevitable, leading to Z.'",
    
    "emotional_tone": "One descriptive word capturing the feeling (e.g., 'Warning', 'Triumphant', 'Skeptical', 'Resigned').",
    
    "actor_roles": {{
        "Hero": "Who is saving the day? (entity/concept)",
        "Villain": "Who is causing the problem? (entity/concept)",
        "Victim": "Who is suffering? (entity/concept)"
    }},
    
    "tags": ["hyphenated-tag-1", "hyphenated-tag-2"]
}}

For tags, use 3-5 tags that describe the *narrative* patterns, NOT just topic keywords.
GOOD tags: "corporate-paternalism", "technological-determinism", "privacy-erosion", "david-vs-goliath"
BAD tags: "iphone", "google", "stock-market"

Return ONLY valid JSON. No markdown formatting."""

        max_retries = 3
        backoff = 2
        
        for attempt in range(max_retries):
            try:
                response = self.generate_content(prompt)
                
                content = response.text.strip()
                content = content.replace("```json", "").replace("```", "").strip()
                result = json.loads(content)
                
                if "tags" in result and isinstance(result["tags"], list):
                    result["tags"] = [str(t).lower().strip() for t in result["tags"]]
                else:
                    result["tags"] = []
                
                return result
                
            except Exception as e:
                if "429" in str(e) or "quota" in str(e).lower():
                    wait_time = backoff ** (attempt + 1)
                    logger.warning(f"Rate limit hit. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"LLM extraction failed: {e}")
                    break
                    
        return self._default_response()
    
    def extract_batch(
        self,
        items: List[Dict[str, str]],
        batch_size: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Extract narratives for multiple items with rate limiting.
        """
        results = []
        for i, item in enumerate(items):
            # Optimization: Skip narrative extraction for very short items or duplicates
            # Only process every 2nd item if under heavy load (optional logic)
            # For now, just robust processing
            
            result = self.extract_narrative(item.get("title", ""), item.get("text", ""))
            results.append(result)
            
            # Simple rate limiting: 1 request every 2 seconds to stay under ~30 RPM
            time.sleep(2.0)
        
        return results
    
    def generate_anchor_narrative(self, theme: str) -> Dict[str, Any]:
        """
        Generate a synthetic narrative anchor for a given theme.
        
        Used to seed the database with prototype narratives.
        """
        # Rate limiting handled in generate_content
        
        prompt = f"""Generate a synthetic news narrative about this theme: "{theme}"

Create a plausible but fictional example of how this theme appears in media.

Return a JSON object:
{{
    "title": "A realistic headline for this narrative",
    "text": "A 2-3 sentence summary of the narrative",
    "narrative_framing": "The core framing in 2-5 words",
    "causal_structure": "What leads to what",
    "emotional_tone": "One word tone",
    "actor_roles": "Key players and roles",
    "tags": ["hyphenated-tag-1", "hyphenated-tag-2", "hyphenated-tag-3"]
}}

Return ONLY valid JSON."""

        try:
            response = self.generate_content(prompt)
            content = response.text.strip()
            content = content.replace("```json", "").replace("```", "").strip()
            return json.loads(content)
        except Exception as e:
            logger.error(f"Anchor generation failed: {e}")
            return {
                "title": theme,
                "text": theme,
                **self._default_response()
            }
    


    def analyze_mutation(self, original_text: str, variant_text: str, shared: str, diff: str) -> Dict[str, Any]:
        """
        Analyze how a narrative has mutated between two versions.
        """
        logger.info("🧬 Analyzing narrative mutation signature...")
        # Rate limiting handled in generate_content
        
        prompt = f"""Compare these two narratives to detect coordinated evolution or manipulation.

ORIGINAL: {original_text}

VARIANT: {variant_text}

CONTEXT:
They share: {shared}
They differ in: {diff}

Explain the mutation in one sentence. What changed and why might it matter?
Classify the mutation type: "Frame shift", "Conclusion flip", "Actor replacement", "Intensification", or "Softening".
Rate severity (1-10) of meaning change.

Return JSON:
{{
    "mutation_type": "Type",
    "explanation": "One sentence explanation...",
    "severity_score": 8
}}
Return ONLY valid JSON."""

        try:
            response = self.generate_content(prompt)
            content = response.text.strip()
            content = content.replace("```json", "").replace("```", "").strip()
            return json.loads(content)
        except Exception as e:
            logger.error(f"Mutation analysis failed: {e}")
            return {
                "mutation_type": "Unknown",
                "explanation": "Failed to analyze mutation.",
                "severity_score": 0
            }

    def _default_response(self) -> Dict[str, Any]:
        """Return default response when extraction fails."""
        return {
            "narrative_framing": "unknown",
            "causal_structure": "unknown",
            "emotional_tone": "neutral",
            "actor_roles": "unknown",
            "tags": []
        }


# Singleton instance
llm_service = NarrativeExtractor()
