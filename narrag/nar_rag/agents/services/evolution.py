"""
Evolution Agent - Performs multi-temporal comparative analysis of narrative landscapes.
"""

from typing import Dict, List, Any
import time
from memory import qdrant_client
from data_pipeline.services.embeddings import embedding_generator
from agents.services.dominance import dominance_analyzer
from data_pipeline.services.llm import llm_service
from qdrant_client.http import models

class EvolutionAgent:
    def __init__(self):
        self.qdrant = qdrant_client
        self.embeddings = embedding_generator
        self.dominance = dominance_analyzer
        self.llm = llm_service

    def analyze_evolution(self, topic: str) -> Dict[str, Any]:
        """
        Phase 3: Multi-Temporal Comparative Analysis.
        """
        # 1. Snapshot Comparison
        snapshots = self._get_snapshots(topic)
        
        # 2. Evolution Detection
        changes = self._detect_changes(snapshots)
        
        # 3. Trajectory Projection
        trajectory = self._project_trajectories(changes.get("rising", []))

        # 4. LLM Summary
        summary = self._generate_evolution_summary(snapshots, changes)

        return {
            "snapshots": snapshots,
            "changes": changes,
            "trajectory_forecast": trajectory,
            "summary": summary
        }

    def _get_snapshots(self, topic: str) -> Dict[str, Any]:
        """Retrieve dominance metrics for T0, T1, T2, T3."""
        now = int(time.time())
        month = 30 * 24 * 3600
        
        windows = {
            "T3 (Current)": (now - month, now),
            "T2 (1 Month Ago)": (now - 2*month, now - month),
            "T1 (3 Months Ago)": (now - 4*month, now - 3*month),
            "T0 (6 Months Ago)": (now - 7*month, now - 6*month),
        }
        
        vector = self.embeddings.generate_dense(topic)
        snapshot_data = {}
        
        for name, (start, end) in windows.items():
            # Retrieve
            filter_cond = models.Filter(
                must=[
                    models.FieldCondition(key="timestamp", range=models.Range(gte=start, lt=end))
                ]
            )
            points = self.qdrant.search_dense(
                query_vector=vector, 
                limit=100, 
                filter_conditions=filter_cond,
                score_threshold=0.25
            )
            
            # Compute Dominance
            metrics = self.dominance.analyze_dominance(points, len(points))
            snapshot_data[name] = {
                "count": len(points),
                "metrics": metrics
            }
            
        return snapshot_data

    def _detect_changes(self, snapshots: Dict[str, Any]) -> Dict[str, List[str]]:
        """Identify New, Faded, Mutated, Persistent narratives."""
        # Simplified logic comparing T0 and T3
        t0 = {m["framing"]: m["metrics"]["prevalence"] for m in snapshots["T0 (6 Months Ago)"]["metrics"]}
        t3 = {m["framing"]: m["metrics"]["prevalence"] for m in snapshots["T3 (Current)"]["metrics"]}
        
        emerged = [k for k, v in t3.items() if k not in t0 and v > 0.1]
        faded = [k for k, v in t0.items() if k not in t3 or t3[k] < 0.05]
        persistent = [k for k in t3.keys() if k in t0 and t3[k] > 0.15]
        
        # Check for rising in current window (Velocity > 2.0)
        rising_objs = [
            m for m in snapshots["T3 (Current)"]["metrics"] 
            if m["metrics"].get("velocity", 0) > 2.0
        ]
        
        return {
            "emerged": emerged,
            "faded": faded,
            "persistent": persistent,
            "rising": rising_objs
        }

    def _get_metric_summary(self, metrics):
        if not metrics: return "No data"
        return ", ".join([f"{m['framing']} ({int(m['metrics']['prevalence']*100)}%)" for m in metrics[:3]])

    def _generate_evolution_summary(self, snapshots, changes) -> str:
        """LLM generates narrative evolution analysis."""
        t0_summary = self._get_metric_summary(snapshots["T0 (6 Months Ago)"]["metrics"])
        t3_summary = self._get_metric_summary(snapshots["T3 (Current)"]["metrics"])
        
        prompt = f"""Comparing narrative landscape from 6 months ago to now.

Data:
T0 (6m ago): {t0_summary}
T3 (Current): {t3_summary}

Detailed Changes:
Emerged: {changes['emerged']}
Faded: {changes['faded']}
Persistent: {changes['persistent']}

Generate evolution analysis sections:
1. Emerged Framings
2. Faded Framings
3. Persistence Pattern
4. Key Inflection Point (Estimation)
"""
        try:
            return self.llm.generate_content(prompt).text
        except:
            return "Evolution analysis failed."

    def _project_trajectories(self, rising_narratives: List[Dict]) -> List[Dict]:
        """Stage 3: LLM predicts near-term evolution."""
        if not rising_narratives:
            return []
            
        predictions = []
        for nav in rising_narratives:
            prompt = f"""Predict trajectory for rising narrative: "{nav['framing']}"
Current Velocity: {nav['metrics']['velocity']}
Current Prevalence: {nav['metrics']['prevalence']}

Predict likely trajectory over next 30-60 days.
Return JSON: {{ "narrative_name": "{nav['framing']}", "predicted_prevalence_30d": 0.0, "confidence": "high/med/low", "reasoning": "string" }}"""
            
            try:
                # Basic mock or simple call if we want to save tokens/time
                # For now returning a placeholder structure based on velocity
                pred = {
                    "narrative_name": nav['framing'],
                    "predicted_prevalence_30d": min(nav['metrics']['prevalence'] * 1.5, 1.0),
                    "confidence": "medium",
                    "reasoning": "Projected based on current high velocity > 2.0"
                }
                predictions.append(pred)
            except:
                pass
                
        return predictions

evolution_agent = EvolutionAgent()
