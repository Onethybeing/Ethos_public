"""
Memory Service - Temporal memory management

Features:
- Decay simulation (exponential time-based decay)
- Snapshot management (create/restore)
- Centroid computation and drift detection
- Narrative family clustering
"""

from typing import List, Dict, Any, Optional, Generator
from memory import qdrant_client
from data_pipeline.services.embeddings import embedding_generator
from qdrant_client.http import models
from .. import config as settings
import datetime
import math
import logging
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MemoryService:
    """
    Manages the temporal aspects of narrative memory.
    
    Demonstrates Qdrant's power as a memory substrate:
    - Decay simulation via scroll + batch update
    - Snapshot API for time-travel queries
    - Centroid computation for cluster analysis
    """
    
    def __init__(self):
        self.qdrant = qdrant_client
    
    def _ensure_qdrant(self):
        pass
    
    # ================== Decay Simulation ==================
    
    def run_decay(
        self,
        decay_lambda: float = None,
        fade_threshold: float = None
    ) -> Dict[str, Any]:
        """
        Run decay simulation on all memories.
        
        Computes decay_score = reinforcement_count * exp(-lambda * days_since_last_seen)
        Marks items below threshold as 'faded'.
        
        Args:
            decay_lambda: Decay rate per day (default from settings)
            fade_threshold: Score below which items are marked faded
            
        Returns:
            Statistics about the decay run
        """
        self._ensure_qdrant()
        
        decay_lambda = decay_lambda or settings.DECAY_LAMBDA
        fade_threshold = fade_threshold or settings.FADE_THRESHOLD
        
        now = int(datetime.datetime.now().timestamp())
        
        stats = {
            "total_processed": 0,
            "already_faded": 0,
            "newly_faded": 0,
            "still_active": 0,
            "anchors_skipped": 0
        }
        
        # Use scroll API to process all points in batches
        for batch in self.qdrant.scroll_all(limit=100):
            points_to_fade = []
            
            for point in batch:
                stats["total_processed"] += 1
                payload = point.payload
                
                # Skip anchors
                if payload.get("is_anchor"):
                    stats["anchors_skipped"] += 1
                    continue
                
                # Skip already faded
                if payload.get("is_faded"):
                    stats["already_faded"] += 1
                    continue
                
                # Calculate decay score
                reinforcement = payload.get("reinforcement_count", 1)
                last_seen = payload.get("last_seen", now)
                days_since = (now - last_seen) / 86400
                
                decay_score = reinforcement * math.exp(-decay_lambda * days_since)
                
                if decay_score < fade_threshold:
                    points_to_fade.append(str(point.id))
                    stats["newly_faded"] += 1
                else:
                    stats["still_active"] += 1
            
            # Batch update faded points
            if points_to_fade:
                self.qdrant.update_payload(
                    point_ids=points_to_fade,
                    payload={
                        "is_faded": True,
                        "faded_at": now
                    }
                )
        
        logger.info(f"Decay simulation complete: {stats}")
        return stats
    
    def get_decay_preview(self, sample_size: int = 20) -> List[Dict[str, Any]]:
        """
        Preview decay scores for a sample of memories.
        
        Useful for visualizing the decay curve.
        """
        self._ensure_qdrant()
        now = int(datetime.datetime.now().timestamp())
        
        previews = []
        count = 0
        
        for batch in self.qdrant.scroll_all(limit=sample_size):
            for point in batch:
                if count >= sample_size:
                    break
                    
                payload = point.payload
                if payload.get("is_anchor"):
                    continue
                
                reinforcement = payload.get("reinforcement_count", 1)
                last_seen = payload.get("last_seen", now)
                days_since = (now - last_seen) / 86400
                
                decay_score = reinforcement * math.exp(-settings.DECAY_LAMBDA * days_since)
                
                previews.append({
                    "id": str(point.id),
                    "title": payload.get("title", "")[:50],
                    "reinforcement_count": reinforcement,
                    "days_since_last_seen": round(days_since, 1),
                    "decay_score": round(decay_score, 3),
                    "is_faded": payload.get("is_faded", False),
                    "would_fade": decay_score < settings.FADE_THRESHOLD
                })
                count += 1
            
            if count >= sample_size:
                break
        
        return previews
    
    # ================== Snapshot Management ==================
    
    def create_snapshot(self, snapshot_name: str) -> Dict[str, Any]:
        """
        Create a named snapshot of the current collection state.
        
        Note: This requires Qdrant Cloud or self-hosted with snapshot enabled.
        """
        self._ensure_qdrant()
        
        try:
            result = self.qdrant.client.create_snapshot(
                collection_name=self.qdrant.collection_name
            )
            
            logger.info(f"Created snapshot: {result.name}")
            return {
                "success": True,
                "snapshot_name": result.name,
                "custom_name": snapshot_name,
                "created_at": datetime.datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Snapshot creation failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def list_snapshots(self) -> List[Dict[str, Any]]:
        """List all available snapshots."""
        self._ensure_qdrant()
        
        try:
            snapshots = self.qdrant.client.list_snapshots(
                collection_name=self.qdrant.collection_name
            )
            return [{"name": s.name, "size": s.size} for s in snapshots]
        except Exception as e:
            logger.error(f"Failed to list snapshots: {e}")
            return []
    
    def restore_snapshot(self, snapshot_name: str) -> Dict[str, Any]:
        """
        Restore a snapshot to a temporary collection for comparison.
        
        Creates a new collection with suffix '_snapshot' for time-travel queries.
        """
        self._ensure_qdrant()
        
        temp_collection = f"{self.qdrant.collection_name}_snapshot"
        
        try:
            # This is a simplified version - full implementation would
            # download and restore the snapshot
            return {
                "success": True,
                "message": f"Snapshot {snapshot_name} would be restored to {temp_collection}",
                "note": "Full snapshot restore requires Qdrant Cloud or local file access"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    # ================== Centroid Computation ==================
    
    def compute_centroids(self, min_reinforcement: int = 5) -> Dict[str, Any]:
        """
        Compute centroids for high-reinforcement narrative clusters.
        
        For each narrative with reinforcement > min_reinforcement:
        1. Find all variants linked to it
        2. Compute average embedding
        3. Store as centroid point
        
        Returns:
            Statistics about centroids created
        """
        self._ensure_qdrant()
        
        stats = {
            "narratives_analyzed": 0,
            "centroids_created": 0,
            "variants_processed": 0
        }
        
        # Find high-reinforcement narratives
        filter_conditions = models.Filter(
            must=[
                models.FieldCondition(
                    key="reinforcement_count",
                    range=models.Range(gte=min_reinforcement)
                ),
                models.FieldCondition(
                    key="is_anchor",
                    match=models.MatchValue(value=False)
                )
            ]
        )
        
        for batch in self.qdrant.scroll_all(limit=50, filter_conditions=filter_conditions):
            for point in batch:
                stats["narratives_analyzed"] += 1
                
                payload = point.payload
                parent_id = str(point.id)
                
                # Find variants of this narrative
                variant_filter = models.Filter(
                    must=[
                        models.FieldCondition(
                            key="parent_id",
                            match=models.MatchValue(value=parent_id)
                        )
                    ]
                )
                
                variants = []
                for var_batch in self.qdrant.scroll_all(
                    limit=100,
                    filter_conditions=variant_filter,
                    with_vectors=True
                ):
                    variants.extend(var_batch)
                
                if not variants:
                    continue
                
                stats["variants_processed"] += len(variants)
                
                # Compute centroid from variant embeddings
                # Note: scroll with vectors returns vectors in .vector
                dense_vectors = []
                for v in variants:
                    if hasattr(v, 'vector') and v.vector:
                        if isinstance(v.vector, dict) and 'text_dense' in v.vector:
                            dense_vectors.append(v.vector['text_dense'])
                
                if dense_vectors:
                    centroid = self._compute_centroid(dense_vectors)
                    
                    # Store centroid as special point
                    centroid_payload = {
                        "is_centroid": True,
                        "parent_narrative_id": parent_id,
                        "parent_title": payload.get("title"),
                        "variant_count": len(variants),
                        "created_at": int(datetime.datetime.now().timestamp()),
                        "tags": payload.get("tags", [])
                    }
                    
                    self.qdrant.upsert_point(
                        point_id=str(uuid.uuid4()),
                        dense_vector=centroid,
                        sparse_vector={"indices": [], "values": []},
                        image_vector=None,
                        payload=centroid_payload
                    )
                    
                    stats["centroids_created"] += 1
        
        logger.info(f"Centroid computation complete: {stats}")
        return stats
    
    def detect_drift(self, threshold: float = 0.85) -> List[Dict[str, Any]]:
        """
        Detect narratives drifting from their centroids.
        
        Finds items that are variants but have low similarity to centroid.
        These indicate narrative mutation.
        """
        self._ensure_qdrant()
        
        drifters = []
        
        # Get all centroids
        centroid_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="is_centroid",
                    match=models.MatchValue(value=True)
                )
            ]
        )
        
        for batch in self.qdrant.scroll_all(limit=50, filter_conditions=centroid_filter, with_vectors=True):
            for centroid in batch:
                parent_id = centroid.payload.get("parent_narrative_id")
                if not parent_id:
                    continue
                
                # Get centroid vector
                if not hasattr(centroid, 'vector') or not centroid.vector:
                    continue
                    
                centroid_vec = centroid.vector.get('text_dense') if isinstance(centroid.vector, dict) else None
                if not centroid_vec:
                    continue
                
                # Search for variants
                variant_filter = models.Filter(
                    must=[
                        models.FieldCondition(
                            key="parent_id",
                            match=models.MatchValue(value=parent_id)
                        )
                    ]
                )
                
                # Check each variant's similarity to centroid
                results = self.qdrant.search_dense(
                    query_vector=centroid_vec,
                    limit=20,
                    filter_conditions=variant_filter
                )
                
                for result in results:
                    if result.score < threshold:
                        drifters.append({
                            "variant_id": str(result.id),
                            "variant_title": result.payload.get("title"),
                            "parent_narrative": centroid.payload.get("parent_title"),
                            "similarity_to_centroid": result.score,
                            "drift_amount": 1 - result.score
                        })
        
        return sorted(drifters, key=lambda x: x["drift_amount"], reverse=True)
    
    # ================== Narrative Families ==================
    
    def get_narrative_families(
        self,
        min_size: int = 2,
        include_faded: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get clustered narrative families based on tags and variants.
        
        Returns groups of related narratives for visualization.
        """
        self._ensure_qdrant()
        
        families = {}
        
        # Build filter
        must_conditions = []
        if not include_faded:
            must_conditions.append(
                models.FieldCondition(
                    key="is_faded",
                    match=models.MatchValue(value=False)
                )
            )
        
        filter_conditions = models.Filter(must=must_conditions) if must_conditions else None
        
        # Collect all narratives and group by primary tag
        for batch in self.qdrant.scroll_all(limit=100, filter_conditions=filter_conditions):
            for point in batch:
                payload = point.payload
                
                # Skip centroids
                if payload.get("is_centroid"):
                    continue
                
                tags = payload.get("tags", [])
                primary_tag = tags[0] if tags else "untagged"
                
                if primary_tag not in families:
                    families[primary_tag] = {
                        "tag": primary_tag,
                        "members": [],
                        "total_reinforcement": 0,
                        "anchor_count": 0
                    }
                
                families[primary_tag]["members"].append({
                    "id": str(point.id),
                    "title": payload.get("title", "")[:50],
                    "reinforcement": payload.get("reinforcement_count", 1),
                    "is_anchor": payload.get("is_anchor", False)
                })
                
                families[primary_tag]["total_reinforcement"] += payload.get("reinforcement_count", 1)
                if payload.get("is_anchor"):
                    families[primary_tag]["anchor_count"] += 1
        
        # Filter and sort
        result = []
        for tag, data in families.items():
            if len(data["members"]) >= min_size:
                data["size"] = len(data["members"])
                data["avg_reinforcement"] = data["total_reinforcement"] / data["size"]
                result.append(data)
        
        return sorted(result, key=lambda x: x["total_reinforcement"], reverse=True)
    
    # ================== Statistics ==================
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive memory statistics.
        """
        self._ensure_qdrant()
        
        stats = {
            "total_points": 0,
            "active": 0,
            "faded": 0,
            "anchors": 0,
            "variants": 0,
            "centroids": 0,
            "avg_reinforcement": 0,
            "sources": {},
            "top_tags": {}
        }
        
        reinforcement_sum = 0
        
        for batch in self.qdrant.scroll_all(limit=100):
            for point in batch:
                stats["total_points"] += 1
                payload = point.payload
                
                if payload.get("is_faded"):
                    stats["faded"] += 1
                else:
                    stats["active"] += 1
                
                if payload.get("is_anchor"):
                    stats["anchors"] += 1
                
                if payload.get("is_variant"):
                    stats["variants"] += 1
                
                if payload.get("is_centroid"):
                    stats["centroids"] += 1
                
                reinforcement_sum += payload.get("reinforcement_count", 1)
                
                # Source distribution
                source = payload.get("source", "unknown")
                stats["sources"][source] = stats["sources"].get(source, 0) + 1
                
                # Tag distribution
                for tag in payload.get("tags", []):
                    stats["top_tags"][tag] = stats["top_tags"].get(tag, 0) + 1
        
        if stats["total_points"] > 0:
            stats["avg_reinforcement"] = round(reinforcement_sum / stats["total_points"], 2)
        
        # Sort and limit tags
        stats["top_tags"] = dict(
            sorted(stats["top_tags"].items(), key=lambda x: x[1], reverse=True)[:10]
        )
        
        return stats
    
    # ================== Helpers ==================
    
    def _compute_centroid(self, vectors: List[List[float]]) -> List[float]:
        """Compute centroid of vectors."""
        if not vectors:
            return [0.0] * settings.DENSE_VECTOR_SIZE
        
        n = len(vectors)
        dim = len(vectors[0])
        centroid = [0.0] * dim
        
        for vec in vectors:
            for i, v in enumerate(vec):
                centroid[i] += v
        
        return [v / n for v in centroid]


# Singleton instance
memory_service = MemoryService()
