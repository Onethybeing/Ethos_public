"""
External Knowledge Agent - Enriches narratives with external context and fact-checks.
"""

import requests
import logging
from typing import Dict, Any, List
from data_pipeline.services.llm import llm_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ExternalKnowledgeAgent:
    def __init__(self):
        self.llm = llm_service
        # Simulate APIs for demo/offline usability
        self.simulate = True

    def enrich_narrative(self, narrative_text: str, entities: List[str]) -> Dict[str, Any]:
        """
        Run enrichment pipeline: Fact Check + Entity Context.
        """
        # 1. Fact Check Integration
        claim_info = self._extract_claim(narrative_text)
        fact_check = self._check_claim(claim_info["claim_text"]) if claim_info["claim_text"] else None
        
        # 2. Entity Context (Wikipedia/Wikidata sim)
        entity_context = {}
        for entity in entities[:3]: # Limit to top 3
            entity_context[entity] = self._get_entity_summary(entity)
            
        return {
            "claim_analysis": claim_info,
            "fact_check": fact_check,
            "entity_context": entity_context
        }

    def _extract_claim(self, text: str) -> Dict[str, str]:
        """Stage 2: Extract central claim using LLM."""
        prompt = f"""Extract the central factual claim from this narrative that could be verified.
        
TEXT: {text[:500]}

Return JSON: {{ "claim_text": "string", "claim_type": "empirical"|"normative"|"predictive" }}"""
        
        try:
            # Reusing the generate_content pattern
            # For brevity in this agent implementation, we Mock extraction or call LLM.
            # Let's call the LLM service we have.
            # But the LLM service method `extract_narrative` is specific.
            # We can use the raw model if exposed or add a method.
            # We will use the model directly via a helper if possible or assume a mocked logical block for speed here.
            # Actually, let's just make a specialized prompt call using available method or assume simulation if LLM service is busy.
            
            # Using LLM Service's model directly
            response = self.llm.generate_content(prompt)
            import json
            content = response.text.replace("```json", "").replace("```", "").strip()
            return json.loads(content)
        except:
            return {"claim_text": "", "claim_type": "unknown"}

    def _check_claim(self, claim: str) -> Dict[str, Any]:
        """Stage 2: Query Fact Check tools (Mocked for this implementation)."""
        if self.simulate:
            return {
                "status": "Unverified (Simulation Mode)",
                "source": "Google Fact Check Tools",
                "url": "https://toolbox.google.com/factcheck/explorer"
            }
        # Real implementation would call Google Fact Check API here
        return {}

    def _get_entity_summary(self, entity: str) -> str:
        """Stage 1: Wikipedia summary (Mocked/Simplified)."""
        if self.simulate:
            return f"Strategic entity context for {entity} would appear here."
        
        # Real impl: requests.get(f"https://en.wikipedia.org/api/rest_v1/page/summary/{entity}")
        return ""

external_agent = ExternalKnowledgeAgent()
