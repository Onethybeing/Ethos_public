"""
Ingestion Service - Smart ingestion with deduplication and reinforcement

Features:
- Automatic duplicate detection via semantic similarity
- Reinforcement: duplicate items increment count instead of creating new points
- Variant tracking: similar items linked as variants
- Batch processing for efficiency
"""

import uuid
import datetime
from typing import List, Dict, Any, Optional
from data_pipeline.services.collectors import collector
from data_pipeline.services.embeddings import embedding_generator
from memory import qdrant_client
from .. import config
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IngestionService:
    """
    Orchestrates the ingestion pipeline from data collection to Qdrant storage.
    
    Pipeline:
    1. Collect data from sources
    2. Generate embeddings (from full text)
    3. Check for duplicates/variants
    4. Upsert to Qdrant (minimal payload)
    
    Note: LLM enrichment (summaries, narratives) is handled separately by EnrichmentAgent.
    """
    
    def __init__(self):
        self.qdrant = qdrant_client
        self._stats = {
            "processed": 0,
            "new": 0,
            "reinforced": 0,
            "variants": 0,
            "skipped": 0
        }
    
    def _ensure_qdrant(self):
        """No longer needed as we use singleton."""
        pass
    
    def ingest_all(self) -> Dict[str, int]:
        """
        Run full ingestion pipeline (fast mode - no LLM calls).
        
        Returns:
            Statistics dict with counts
        """
        self._ensure_qdrant()
        self._reset_stats()
        
        # 1. Collect data
        logger.info("=== Starting Data Collection ===")
        items = collector.fetch_all()
        
        if not items:
            logger.warning("No items collected!")
            return self._stats
        
        logger.info(f"Collected {len(items)} items. Starting ingestion...")
        
        # 2. Process each item
        for i, item in enumerate(items):
            try:
                self._process_item(item)
                
                if (i + 1) % 10 == 0:
                    logger.info(f"Processed {i + 1}/{len(items)} items")
                    
            except Exception as e:
                logger.error(f"Failed to process item '{item.get('title', '')[:30]}': {e}")
                self._stats["skipped"] += 1
        
        logger.info(f"=== Ingestion Complete ===")
        logger.info(f"Stats: {self._stats}")
        return self._stats
    
    def ingest_items(self, items: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Ingest a specific list of items.
        
        Args:
            items: List of item dicts with title, text, url, source, timestamp, image_url
            
        Returns:
            Statistics dict
        """
        self._ensure_qdrant()
        self._reset_stats()
        
        for item in items:
            try:
                self._process_item(item)
            except Exception as e:
                logger.error(f"Failed to process item: {e}")
                self._stats["skipped"] += 1
        
        return self._stats
    
    def _process_item(self, item: Dict[str, Any]):
        """Process a single item through the ingestion pipeline."""
        self._stats["processed"] += 1
        
        title = item.get("title", "") or ""
        text = item.get("text", "") or ""
        
        # Skip empty items
        if not title.strip() and not text.strip():
            self._stats["skipped"] += 1
            return
        
        # Full content for embeddings (NOT stored, only used for vectors)
        full_content = f"{title}. {text}"
        
        # 1. Generate dense embedding for similarity check (from FULL text)
        dense_vector = embedding_generator.generate_dense(full_content)
        
        # 2. Check for duplicates using dense similarity
        duplicate_result = self._check_duplicate(dense_vector)
        
        if duplicate_result:
            existing_point, score = duplicate_result
            
            if score >= config.SIMILARITY_THRESHOLD:
                # Exact duplicate: reinforce existing point
                self._reinforce_point(existing_point)
                self._stats["reinforced"] += 1
                logger.debug(f"Reinforced: '{title[:30]}...' (score: {score:.3f})")
                return
            
            elif score >= config.VARIANT_THRESHOLD:
                # Similar but not identical: create variant
                self._create_variant(item, full_content, dense_vector, existing_point)
                self._stats["variants"] += 1
                logger.debug(f"Created variant: '{title[:30]}...' (score: {score:.3f})")
                return
        
        # 3. New item: full processing
        self._create_new_point(item, full_content, dense_vector)
        self._stats["new"] += 1
        logger.debug(f"New item: '{title[:30]}...'")
    
    def _check_duplicate(self, dense_vector: List[float]) -> Optional[tuple]:
        """
        Check for existing similar items.
        
        Returns:
            Tuple of (point, score) if similar item found, None otherwise
        """
        results = self.qdrant.search_dense(
            query_vector=dense_vector,
            limit=1,
            score_threshold=config.VARIANT_THRESHOLD
        )
        
        if results:
            return (results[0], results[0].score)
        return None
    
    def _reinforce_point(self, existing_point):
        """Increment reinforcement count and update last_seen."""
        old_payload = existing_point.payload
        new_count = old_payload.get("reinforcement_count", 1) + 1
        
        self.qdrant.update_payload(
            point_ids=[existing_point.id],
            payload={
                "reinforcement_count": new_count,
                "last_seen": int(datetime.datetime.now().timestamp())
            }
        )
    
    def _create_variant(
        self,
        item: Dict[str, Any],
        full_content: str,
        dense_vector: List[float],
        parent_point
    ):
        """Create a new point linked as variant to existing point."""
        # Generate remaining embeddings (from FULL text)
        sparse_vector = embedding_generator.generate_sparse(full_content)
        image_vector = embedding_generator.generate_image(item.get("image_url"))
        
        # Build minimal payload (no LLM data, no full text)
        now = int(datetime.datetime.now().timestamp())
        payload = {
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "source": item.get("source", ""),
            "image_url": item.get("image_url"),
            "timestamp": item.get("timestamp", now),
            "first_seen": now,
            "last_seen": now,
            "reinforcement_count": 1,
            "is_variant": True,
            "parent_id": str(parent_point.id),
            "enriched": False  # Flag for enrichment agent
        }
        
        # Upsert
        point_id = str(uuid.uuid4())
        self.qdrant.upsert_point(
            point_id=point_id,
            dense_vector=dense_vector,
            sparse_vector=sparse_vector,
            image_vector=image_vector,
            payload=payload
        )
    
    def _create_new_point(
        self,
        item: Dict[str, Any],
        full_content: str,
        dense_vector: List[float]
    ):
        """Create a completely new point."""
        # Generate remaining embeddings (from FULL text)
        sparse_vector = embedding_generator.generate_sparse(full_content)
        image_vector = embedding_generator.generate_image(item.get("image_url"))
        
        # Build minimal payload (no LLM data, no full text)
        now = int(datetime.datetime.now().timestamp())
        timestamp = item.get("timestamp") or now
        
        payload = {
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "source": item.get("source", ""),
            "image_url": item.get("image_url"),
            "timestamp": timestamp,
            "first_seen": now,
            "last_seen": now,
            "reinforcement_count": 1,
            "is_anchor": False,
            "is_faded": False,
            "is_variant": False,
            "enriched": False  # Flag for enrichment agent
        }
        
        # Upsert
        point_id = str(uuid.uuid4())
        self.qdrant.upsert_point(
            point_id=point_id,
            dense_vector=dense_vector,
            sparse_vector=sparse_vector,
            image_vector=image_vector,
            payload=payload
        )
    
    def _reset_stats(self):
        """Reset ingestion statistics."""
        self._stats = {
            "processed": 0,
            "new": 0,
            "reinforced": 0,
            "variants": 0,
            "skipped": 0
        }


# Singleton instance
ingestion_service = IngestionService()
