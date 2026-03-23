"""
Meta-Synthesis Agent - Generates strategic intelligence reports.

Core Capabilities:
1. Pattern Discovery: Comprehensive retrieval & multi-dimensional clustering.
2. Conflict Detection: Identifying competing narratives.
3. Landscape Mapping: Visualizing the information space.
"""

from memory import qdrant_client
from data_pipeline.services.embeddings import embedding_generator
from data_pipeline.services.llm import llm_service
from qdrant_client.http import models
from typing import Dict, List, Any, Optional
from collections import defaultdict
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from agents.services.dominance import dominance_analyzer
from agents.services.external import external_agent
from agents.services.evolution import evolution_agent
from agents.services.outcome import outcome_agent

class MetaSynthesisAgent:
    def __init__(self):
        self.qdrant = qdrant_client
        self.embeddings = embedding_generator
        self.llm = llm_service
        self.dominance = dominance_analyzer
        self.external = external_agent
        self.evolution = evolution_agent
        self.outcomes = outcome_agent

    def generate_report(self, topic: str, days: int = 30) -> Dict[str, Any]:
        """
        Generate a comprehensive narrative intelligence report (Phase 4).
        """
        logger.info(f"📊 Starting Strategic Intelligence Report for topic: {topic}")
        
        # 1. Internal Analysis (Landscape & Dominance)
        logger.info("📡 Gathering narratives and computing dominance metrics...")
        narratives = self._gather_narratives(topic, days)
        if not narratives:
            return {"error": "No data found for this topic/time range."}
            
        dominance_metrics = self.dominance.analyze_dominance(narratives, len(narratives))
        conflicts = self._detect_conflicts(topic, narratives)
        
        # 2. External Context
        logger.info("🌐 Fetching external context and fact-checks...")
        enrichment = {}
        if dominance_metrics:
            top_framing = dominance_metrics[0]["framing"]
            rep_text = next((n.payload.get("text") for n in narratives if n.payload.get("narrative_framing") == top_framing), "")
            rep_narrative = next((n for n in narratives if n.payload.get("narrative_framing") == top_framing), None)
            if rep_narrative:
                roles = rep_narrative.payload.get("actor_roles", {})
                # Handle case where actor_roles is a string (from skip_llm mode)
                if isinstance(roles, dict):
                    entities = [v for k,v in roles.items() if v and v != "unknown"]
                else:
                    entities = []
                enrichment = self.external.enrich_narrative(rep_text, entities) if entities else {}

        # 3. Evolution Analysis (Phase 3)
        logger.info("⏳ Analyzing multi-temporal narrative evolution...")
        evolution_data = self.evolution.analyze_evolution(topic)

        # 4. Outcome Tracer Integration
        # Check historical outcomes for the TOP narrative
        logger.info("🔮 Tracing historical outcomes and future trajectories...")
        outcome_data = {}
        if rep_text:
             try:
                 outcome_data = self.outcomes.trace_outcomes(text=rep_text)
             except Exception as e:
                 logger.error(f"Outcome trace failed: {e}")

        # 5. Final Report Synthesis (Phase 4)
        logger.info("📝 Synthesizing final intelligence briefing...")
        full_report_md = self._generate_final_report_md(
            topic=topic,
            dominance=dominance_metrics,
            conflicts=conflicts,
            enrichment=enrichment,
            evolution=evolution_data,
            outcomes=outcome_data
        )
        
        return {
            "topic": topic,
            "period": f"Last {days} days",
            "dominance_analysis": dominance_metrics,
            "conflicts": conflicts,
            "enrichment": enrichment,
            "evolution": evolution_data,
            "outcomes": outcome_data,
            "final_report_markdown": full_report_md
        }

    def _generate_final_report_md(self, topic, dominance, conflicts, enrichment, evolution, outcomes):
        """Generate final Markdown report using the comprehensive prompt."""
        
        # Prepare data strings
        families_str = "\n".join([f"- {d['framing']}: {d['status']} (Prevalence: {d['metrics']['prevalence']})" for d in dominance[:5]])
        conflicts_str = str(conflicts)
        evolution_summ = evolution.get("summary", "N/A")
        outcome_summ = outcomes.get("prediction_summary", "No historical data.")
        
        prompt = f"""You are generating a Strategic Narrative Intelligence Report on the topic: {topic}

INTERNAL ANALYSIS:
Dominant Narratives:
{families_str}

Conflicts:
{conflicts_str}

Evolution:
{evolution_summ}

Outcome Patterns:
{outcome_summ}

EXTERNAL CONTEXT:
Fact Check: {enrichment.get('fact_check', {}).get('status', 'Unverified')}
Claim Analysis: {enrichment.get('claim_analysis', {})}

Generate a detailed markdown report with these sections:
1. EXECUTIVE SUMMARY (4-5 sentences)
2. DOMINANT NARRATIVES (Analyze top 3)
3. NARRATIVE CONFLICTS
4. EXTERNAL CONTEXT & VERIFICATION
5. EVOLUTION ANALYSIS
6. IMPLICATIONS & PREDICTIONS
7. BLIND SPOTS

Write in a professional intelligence analyst style.
"""
        try:
            return self.llm.generate_content(prompt).text
        except:
            return "Report generation failed."

    def _gather_narratives(self, topic: str, days: int) -> List[Any]:
        """Gather relevant narratives using hybrid search."""
        # vector search for topic
        cutoff = int(time.time()) - (days * 24 * 3600)
        vector = self.embeddings.generate_dense(topic)
        
        # Initial broad search - INCREASE LIMIT for better analysis
        results = self.qdrant.search_dense(
            query_vector=vector,
            limit=200, 
            score_threshold=0.25,
            filter_conditions=models.Filter(
                must=[
                    models.FieldCondition(
                        key="timestamp",
                        range=models.Range(gte=cutoff)
                    )
                ]
            )
        )
        return results

    def _detect_conflicts(self, topic: str, narratives: List[Any]) -> List[Dict[str, Any]]:
        """
        Identify competing narratives.
        """
        if not narratives:
            return []
            
        # Simple Logic: Check if we have clusters with opposing sentiment/tone.
        # e.g. One cluster is "Optimistic", another "Pessimistic".
        
        tones = defaultdict(list)
        for n in narratives:
            tones[n.payload.get("emotional_tone", "neutral").lower()].append(n)
            
        conflicts = []
        # Check specific pairs
        pairs = [("optimistic", "pessimistic"), ("supportive", "critical"), ("trusting", "skeptical"), ("hopeful", "fearful")]
        for tone_a, tone_b in pairs:
            if tones.get(tone_a) and tones.get(tone_b):
                conflicts.append({
                    "type": "Tone Conflict",
                    "side_a": f"{tone_a} ({len(tones[tone_a])} items)",
                    "side_b": f"{tone_b} ({len(tones[tone_b])} items)",
                    "example_a": tones[tone_a][0].payload.get("title"),
                    "example_b": tones[tone_b][0].payload.get("title")
                })
                
        return conflicts

    def _synthesize_insights(self, topic: str, dominance: List[Dict], conflicts: List[Dict], enrichment: Dict) -> str:
        """
        Use LLM to generate the executive summary.
        """
        # Simplify data for prompt
        top_narratives = [f"{d['framing']} ({d['status']})" for d in dominance[:5]]
        
        prompt = f"""Generate a strategic intelligence brief on: "{topic}"

DATA:
Dominant Narratives: {top_narratives}
Detected Conflicts: {str(conflicts)}
Fact Check Status (Top Narrative): {enrichment.get('fact_check', {}).get('status', 'N/A')}

TASK:
Write a 3-bullet executive summary answering "What is really happening?".
Focus on the battle between narratives and the validity of claims.
"""
        try:
            response = self.llm.generate_content(prompt)
            content = response.text.replace("```", "").strip()
            return content
        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            return "Synthesis failed."

meta_agent = MetaSynthesisAgent()
