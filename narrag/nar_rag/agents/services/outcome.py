"""
Outcome Tracer Agent - Temporal causal analysis for narrative predictions.

Purpose:
1. Mine historical instances of a narrative pattern (>90 days old).
2. Trace what happened in the 7-120 day window after those instances.
3. Build a predictive model based on those historical outcomes.
"""

from memory import qdrant_client
from data_pipeline.services.embeddings import embedding_generator
from data_pipeline.services.llm import llm_service
from qdrant_client.http import models
from typing import Dict, List, Any, Optional, Set
import logging
import time
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OutcomeTracerAgent:
    def __init__(self):
        self.qdrant = qdrant_client
        self.embeddings = embedding_generator
        self.llm = llm_service

    def trace_outcomes(self, narrative_id: str = None, text: str = None) -> Dict[str, Any]:
        """
        Main pipeline: specific narrative -> historical matches -> future outcomes.
        """
        # 1. Input Processing
        probe_vector = None
        probe_payload = None
        probe_sparse = None

        if narrative_id:
            points = self.qdrant.client.retrieve(
                collection_name=self.qdrant.collection_name,
                ids=[narrative_id],
                with_vectors=True,
                with_payload=True
            )
            if not points:
                return {"error": "Narrative not found"}
            point = points[0]
            probe_vector = point.vector["text_dense"]
            # Handle sparse vector format from Qdrant/Client
            # Point.vector might be a dict if multiple vectors
            if "text_sparse" in point.vector:
                probe_sparse = point.vector["text_sparse"]
            
            probe_payload = point.payload
        elif text:
            # Generate on fly
            analysis = self.llm.extract_narrative("Input", text) # Simplified call
            probe_vector = self.embeddings.generate_dense(text)
            probe_sparse = self.embeddings.generate_sparse(text)
            probe_payload = analysis
            probe_payload["text"] = text
        else:
            return {"error": "Provide narrative_id or text"}

        # 2. Historical Mining (Phase 1, Stage 1)
        historical_matches = self._find_historical_instances(probe_vector, probe_payload)
        
        # 3. Forward Temporal Search (Phase 1, Stage 2)
        outcome_chains = []
        for match in historical_matches:
            outcomes = self._find_forward_outcomes(match)
            if outcomes:
                outcome_chains.append({
                    "source_narrative": {
                        "id": match.id,
                        "title": match.payload.get("title"),
                        "timestamp": match.payload.get("timestamp"),
                        "framing": match.payload.get("narrative_framing")
                    },
                    "outcomes": [
                        {
                            "id": o.id,
                            "title": o.payload.get("title"),
                            "timestamp": o.payload.get("timestamp"),
                            "text": o.payload.get("text", "")[:100] + "..."
                        }
                        for o in outcomes
                    ]
                })

        # 4. Synthesis
        # Simple prediction summary
        prediction = "No sufficient historical data."
        if outcome_chains:
            count = len(outcome_chains)
            prediction = f"Based on {count} historical precedents, this narrative often leads to related events within 1-4 months."

        return {
            "probe": {
                "framing": probe_payload.get("narrative_framing"),
                "text": probe_payload.get("text", "")[:100]
            },
            "historical_matches_count": len(historical_matches),
            "outcome_chains": outcome_chains,
            "prediction_summary": prediction
        }

    def _find_historical_instances(self, vector: List[float], payload: Dict[str, Any]) -> List[models.ScoredPoint]:
        """Find matches > 90 days old with tag overlap."""
        cutoff_time = int(time.time()) - (90 * 24 * 3600)
        
        # 1. Dense Search with Time Filter
        # We need tags from payload to filter in Python
        search_results = self.qdrant.search_dense(
            query_vector=vector,
            limit=50,
            filter_conditions=models.Filter(
                must=[
                    models.FieldCondition(
                        key="timestamp",
                        range=models.Range(lt=cutoff_time)
                    )
                ]
            )
        )

        # 2. Refine by Tag Overlap and retrieve vectors for next stage
        # We need to fetch vectors for the survivors because search_dense doesn't return them by default 
        # (unless we change qdrant_service, but I'll stick to client.retrieve for specific IDs)
        
        probe_tags = set(payload.get("tags", []))
        candidates = []
        
        for res in search_results:
            match_tags = set(res.payload.get("tags", []))
            # "Overlapping narrative_tags (at least 2 shared)"
            if len(probe_tags.intersection(match_tags)) >= 2:
                candidates.append(res)

        return candidates

    def _find_forward_outcomes(self, historical_point: models.ScoredPoint) -> List[models.ScoredPoint]:
        """Search [T+7, T+120] for sparse-similar items with same actors."""
        base_ts = historical_point.payload.get("timestamp", 0)
        start_ts = base_ts + (7 * 24 * 3600)
        end_ts = base_ts + (120 * 24 * 3600)
        
        # We need the sparse vector of the historical point.
        # Since we didn't fetch it in the search, we must retrieve it now.
        # Optimization: Could have fetched in batch logic, but this is clearer.
        full_point = self.qdrant.client.retrieve(
            collection_name=self.qdrant.collection_name,
            ids=[historical_point.id],
            with_vectors=True
        )[0]
        
        sparse_vec = full_point.vector.get("text_sparse")
        if not sparse_vec:
            return []

        # Convert Qdrant SparseVector object to dict for service call if needed,
        # OR just call client.search directly since qdrant_service uses a dict format.
        # qdrant_service.search_sparse expects {"indices": [], "values": []}
        # The retrieved sparse_vec is a models.SparseVector object.
        sparse_dict = {
            "indices": sparse_vec.indices,
            "values": sparse_vec.values
        }

        # Search
        results = self.qdrant.search_sparse(
            sparse_vector=sparse_dict,
            limit=10,
            filter_conditions=models.Filter(
                must=[
                    models.FieldCondition(
                        key="timestamp",
                        range=models.Range(gte=start_ts, lte=end_ts)
                    )
                ]
            )
        )
        
        # Filter by Actor Roles
        # "Contains same actor_roles (entities)"
        source_actors = self._extract_actors(historical_point.payload)
        valid_outcomes = []
        
        for res in results:
            target_actors = self._extract_actors(res.payload)
            if source_actors.intersection(target_actors):
                valid_outcomes.append(res)
                
        return valid_outcomes

    def _extract_actors(self, payload: Dict[str, Any]) -> Set[str]:
        """Helper to extract standardized actor entity names."""
        roles = payload.get("actor_roles", {})
        actors = set()
        if isinstance(roles, dict):
            for role, entity in roles.items():
                if entity and isinstance(entity, str) and entity.lower() != "unknown":
                    actors.add(entity.lower().strip())
        return actors

outcome_agent = OutcomeTracerAgent()
