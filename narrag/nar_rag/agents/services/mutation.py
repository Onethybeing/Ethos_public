"""
Mutation Detector Agent - Identifies narrative evolution and manipulation.

Detects:
1. Siblings: Similar framing but different conclusions/spin.
2. Descendants: Temporal evolution of the same narrative structure.
3. Mutation Signatures: Classifies how the narrative changed (Frame shift, Conclusion flip, etc).
"""

from memory import qdrant_client
from data_pipeline.services.embeddings import embedding_generator
from data_pipeline.services.llm import llm_service
from qdrant_client.http import models
from typing import Dict, List, Any, Optional
import logging
import time
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MutationDetectorAgent:
    def __init__(self):
        self.qdrant = qdrant_client
        self.embeddings = embedding_generator
        self.llm = llm_service

    def _get_opposite_tone(self, tone: str) -> str:
        """Simple heuristic to find opposite emotion."""
        opposites = {
            "optimistic": "pessimistic",
            "pessimistic": "optimistic",
            "skeptical": "trusting",
            "trusting": "skeptical",
            "fearful": "hopeful",
            "hopeful": "fearful",
            "neutral": "emotional",
            "emotional": "neutral",
            # Add general fallback
            "positive": "negative",
            "negative": "positive"
        }
        return opposites.get(tone.lower(), "neutral")

    def _get_vector_for_tone(self, tone: str) -> Optional[List[float]]:
        """Find a representative vector for a given tone from existing memories."""
        # Try to find a point with this emotional_tone in payload
        results = self.qdrant.client.scroll(
            collection_name=self.qdrant.collection_name,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="payload.emotional_tone",  # Assuming structure
                        match=models.MatchValue(value=tone)
                    )
                ]
            ),
            limit=1,
            with_vectors=True
        )
        points, _ = results
        if points:
            # Return the dense vector
            return points[0].vector["text_dense"]
        return None

    def detect_mutations(self, narrative_id: str = None, text: str = None) -> Dict[str, Any]:
        """
        Main pipeline: Detect mutations for a given narrative (ID or text).
        """
        # 1. Load/Process Input
        target_point = None
        target_embedding = None
        target_payload = None

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
            target_point = point
            target_embedding = point.vector["text_dense"]
            target_payload = point.payload
        elif text:
            # Extract and embed on the fly
            analysis = self.llm.extract_narrative("Input Text", text)
            dense = self.embeddings.generate_dense(text)
            target_embedding = dense
            target_payload = analysis
            target_payload["text"] = text
            target_payload["timestamp"] = int(time.time())
        else:
            return {"error": "Must provide narrative_id or text"}

        # 2. Run Pipelines
        siblings = self._find_siblings(target_embedding, target_payload)
        descendants = self._find_descendants(target_embedding, target_payload)
        
        # 3. Analyze Mutations
        all_variants = siblings + descendants
        analyzed_mutations = []
        
        for variant in all_variants:
            mutation_info = self._analyze_single_mutation(target_payload, variant.payload)
            if mutation_info:
                analyzed_mutations.append({
                    "variant_id": variant.id,
                    "variant_text": variant.payload.get("text", "")[:200] + "...",
                    "timestamp": variant.payload.get("timestamp"),
                    "score": variant.score,
                    **mutation_info
                })

        # 4. Construct Timeline
        timeline = self._build_timeline(analyzed_mutations)
        
        return {
            "original_narrative": {
                "framing": target_payload.get("narrative_framing"),
                "tone": target_payload.get("emotional_tone"),
                "text": target_payload.get("text", "")[:200]
            },
            "mutations": analyzed_mutations,
            "mutation_timeline": timeline,
            "hotspot_alert": len(analyzed_mutations) > 5
        }

    def _find_siblings(self, embedding: List[float], payload: Dict[str, Any]) -> List[models.ScoredPoint]:
        """Step 1: Find 'same story, different spin' using Discovery API."""
        current_tone = payload.get("emotional_tone", "neutral")
        opposite_tone = self._get_opposite_tone(current_tone)
        
        negative_vector = self._get_vector_for_tone(opposite_tone)
        negatives = [negative_vector] if negative_vector else []
        
        # If we can't find an opposite tone vector, maybe we shouldn't use negatives?
        # Or we use the recommendation to steer AWAY from the current tone?
        # "Negative examples: Narratives with opposite emotional_tone" -> user logic.
        # Actually usually finding siblings means "different spin". 
        # If I am "Hopeful", siblings might be "Fearful".
        # So "Positive: My Frame (Hopeful)". "Negative: Opposite (Fearful)" -> This searches for MORE Hopeful?
        # Wait, if I want to FIND the sibling (the Fearful one), I should search for:
        # Positive: My Topic (embedding)
        # Context: I want results CLOSE to "Fearful".
        # User instruction: "Positive: input narrative's framing vector. Negative: Narratives with opposite emotional_tone".
        # Interpreted literally: Search for things like INPUT but unlike OPPOSITE.
        # This reinforces the CURRENT tone. That sounds like finding duplicates, not mutated siblings?
        # BUT, if the user means: "Find things that share the framing (Positive) but..."
        # Maybe I should just trust the user's specific instruction or adapt for "Sibling" definition.
        # Sibling = "Similar framing, different conclusion".
        # Let's search for: Positive=[Input]. Filter=[Tone != Input Tone].
        # That ensures "Same Topic/Frame" but "Different Tone".
        # The Discovery API usage requested might be for refining the "Framing" vector?
        # I will execute the literal instruction but also add the filter which is crucial.
        
        results = self.qdrant.recommend_narratives(
            positive_vectors=[embedding],
            negative_vectors=negatives,
            limit=5,
            filter_conditions=models.Filter(
                must_not=[
                    models.FieldCondition(
                        key="emotional_tone",
                        match=models.MatchValue(value=current_tone) # Must differ in tone
                    )
                ]
            )
        )
        return results

    def _find_descendants(self, embedding: List[float], payload: Dict[str, Any]) -> List[models.ScoredPoint]:
        """Step 2: Find temporal evolution."""
        if "timestamp" not in payload:
            return []
            
        timestamp = payload["timestamp"]
        
        # Search for similar content that appeared AFTER
        results = self.qdrant.search_dense(
            query_vector=embedding,
            limit=10,
            filter_conditions=models.Filter(
                must=[
                    models.FieldCondition(
                        key="timestamp",
                        range=models.Range(gt=timestamp)
                    )
                ]
            )
        )
        
        # Post-process for Actor overlap
        # Check if they share at least one actor
        my_actors = self._extract_actors(payload)
        filtered = []
        for res in results:
            their_actors = self._extract_actors(res.payload)
            # Intersection
            if my_actors.intersection(their_actors):
                filtered.append(res)
                
        return filtered

    def _extract_actors(self, payload: Dict[str, Any]) -> set:
        """Helper to get a set of actors from payload."""
        roles = payload.get("actor_roles", {})
        if isinstance(roles, str):
            # Sometimes it might be a string if json parsing failed?
            return set()
        actors = set()
        for role, entity in roles.items():
            if entity and entity != "unknown":
                actors.add(entity.lower().strip())
        return actors

    def _analyze_single_mutation(self, original: Dict[str, Any], variant: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Step 3 + LLM: Compute signature and explain."""
        # Calculate scores
        # 1. Jaccard for actors
        actors_a = self._extract_actors(original)
        actors_b = self._extract_actors(variant)
        union = len(actors_a.union(actors_b))
        jaccard = len(actors_a.intersection(actors_b)) / union if union > 0 else 0
        
        # If very low similarity in all aspects, maybe it's not a mutation but unrelated.
        # But we found it via vector search, so it shares topic.
        
        diff_summary = f"Tone: {original.get('emotional_tone')} -> {variant.get('emotional_tone')}. "
        diff_summary += f"Framing: {variant.get('narrative_framing')}"
        
        shared_summary = f"Actors: {', '.join(actors_a.intersection(actors_b))}"
        
        # LLM Call
        llm_result = self.llm.analyze_mutation(
            original_text=original.get("text", "")[:300],
            variant_text=variant.get("text", "")[:300],
            shared=shared_summary,
            diff=diff_summary
        )
        
        return {
            "type": llm_result.get("mutation_type", "Unknown"),
            "explanation": llm_result.get("explanation", ""),
            "severity": llm_result.get("severity_score", 0),
            "actor_overlap": jaccard
        }

    def _build_timeline(self, mutations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Step 4: Cluster by time."""
        # Simple clustering by day
        timeline = {}
        for m in mutations:
            ts = m["timestamp"]
            date = datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
            if date not in timeline:
                timeline[date] = {"date": date, "count": 0, "types": []}
            timeline[date]["count"] += 1
            timeline[date]["types"].append(m["type"])
            
        # Determine dominant type
        sorted_timeline = []
        for date, data in timeline.items():
            # Find most common type
            dominant = max(set(data["types"]), key=data["types"].count) if data["types"] else "None"
            data["dominant_type"] = dominant
            del data["types"]
            sorted_timeline.append(data)
            
        return sorted(sorted_timeline, key=lambda x: x["date"])

mutation_agent = MutationDetectorAgent()
