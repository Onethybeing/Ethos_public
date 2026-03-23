"""
Dominance Analysis - Computes dominance metrics efficiently using Qdrant aggregations.
"""

from typing import Dict, List, Any
import time
from memory import qdrant_client
from agents.services.outcome import outcome_agent
from qdrant_client.http import models
from collections import defaultdict

class DominanceAnalyzer:
    def __init__(self, qdrant_client_inst=None):
        self.qdrant = qdrant_client_inst or qdrant_client

    def analyze_dominance(self, narratives: List[Any], total_mentions_in_period: int) -> List[Dict[str, Any]]:
        """
        Analyze narrative dominance metrics properly grouped by narrative family.
        Note: narratives input is a list of points from the search.
        In a real system, we might need broader aggregation.
        Here we analyze the *provided* set of narratives.
        """
        if not narratives:
            return []

        # 1. Group by "Family" (Framing)
        families = defaultdict(list)
        for n in narratives:
            framing = n.payload.get("narrative_framing", "Unknown")
            families[framing].append(n)

        results = []
        now = int(time.time())
        seven_days_ago = now - (7 * 24 * 3600)
        thirty_days_ago = now - (30 * 24 * 3600)

        for framing, points in families.items():
            # Basic stats
            reinforcement_sum = sum([p.payload.get("reinforcement_count", 1) for p in points])
            count = len(points)
            
            # Prevalence: Share of voice in this retrieved set
            prevalence = reinforcement_sum / max(total_mentions_in_period, 1)

            # Velocity: Mentions in last 7 days vs prior 30 days
            # Note: We need timestamps from points
            recent_mentions = 0
            prior_mentions = 0
            
            sources = set()
            has_image = 0
            
            for p in points:
                ts = p.payload.get("timestamp", 0)
                sources.add(p.payload.get("source", "unknown"))
                if p.payload.get("image_url"):
                    has_image += 1
                
                if ts >= seven_days_ago:
                    recent_mentions += 1
                elif ts >= thirty_days_ago:
                    prior_mentions += 1
            
            # Normalize velocity (simple ratio, handle zero)
            # Just count density per day to be fair?
            # 7 days vs 23 days (30-7).
            rate_recent = recent_mentions / 7.0
            rate_prior = prior_mentions / 23.0 if prior_mentions > 0 else 0.001
            
            if rate_prior == 0: rate_prior = 0.001
            velocity = rate_recent / rate_prior

            # Source Diversity
            diversity = len(sources) / max(count, 1) # simple distinct/total
            
            # Outcome Track Record (Sample one point)
            # We don't want to run full tracer for every family in a quick report.
            # Maybe check if we have done it before?
            # For now, just placeholder or lightweight check.
            has_outcomes = False
            
            results.append({
                "framing": framing,
                "metrics": {
                    "prevalence": round(prevalence, 2),
                    "velocity": round(velocity, 2),
                    "source_diversity": round(diversity, 2),
                    "visual_strength": round(has_image / max(count, 1), 2),
                },
                "status": self._classify_status(prevalence, velocity, diversity),
                "point_count": count
            })

        # Sort by prevalence
        return sorted(results, key=lambda x: x["metrics"]["prevalence"], reverse=True)

    def _classify_status(self, prev, vel, div):
        if prev > 0.4: return "Dominant"
        if vel > 2.0: return "Rising"
        if div < 0.3: return "Echo Chamber"
        return "Stable"

dominance_analyzer = DominanceAnalyzer()
