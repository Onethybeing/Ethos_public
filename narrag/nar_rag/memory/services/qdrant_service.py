"""
Qdrant Service - Multi-Vector Narrative Memory Client (Refactored)

This module provides the core Qdrant client wrapper with:
- Multi-vector support (dense, sparse, image)
- Qdrant Cloud and local storage support
- Hybrid search with RRF fusion
- Batch operations
"""

from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.models import SparseVector
from .. import config
from typing import List, Dict, Any, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NarrativeMemoryClient:
    """
    Qdrant client wrapper for the Narrative Memory System.
    Uses the modern query_points API for maximum compatibility.
    """
    
    def __init__(self):
        self.client = self._create_client()
        self.collection_name = config.COLLECTION_NAME
        self._ensure_collection()
    
    def _create_client(self) -> QdrantClient:
        """Create Qdrant client based on configuration."""
        if config.QDRANT_URL:
            logger.info(f"Connecting to Qdrant Cloud: {config.QDRANT_URL}")
            return QdrantClient(
                url=config.QDRANT_URL,
                api_key=config.QDRANT_API_KEY,
            )
        else:
            logger.info(f"Using local Qdrant storage: {config.QDRANT_PATH}")
            return QdrantClient(path=config.QDRANT_PATH)
    
    def _ensure_collection(self):
        """Create collection if it doesn't exist."""
        collections = self.client.get_collections().collections
        exists = any(c.name == self.collection_name for c in collections)
        
        if not exists:
            logger.info(f"Creating collection '{self.collection_name}'...")
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config={
                    "text_dense": models.VectorParams(
                        size=config.DENSE_VECTOR_SIZE,
                        distance=models.Distance.COSINE
                    ),
                    "image_clip": models.VectorParams(
                        size=config.IMAGE_VECTOR_SIZE,
                        distance=models.Distance.COSINE
                    ),
                },
                sparse_vectors_config={
                    "text_sparse": models.SparseVectorParams()
                },
                optimizers_config=models.OptimizersConfigDiff(
                    indexing_threshold=20000,
                ),
            )
            self._create_payload_indexes()
            logger.info("Collection created successfully.")
        else:
            logger.info(f"Collection '{self.collection_name}' already exists.")
    
    def _create_payload_indexes(self):
        """Create indexes on frequently filtered payload fields."""
        indexes = [
            ("timestamp", models.PayloadSchemaType.INTEGER),
            ("source", models.PayloadSchemaType.KEYWORD),
            ("tags", models.PayloadSchemaType.KEYWORD),
            ("is_anchor", models.PayloadSchemaType.BOOL),
            ("is_faded", models.PayloadSchemaType.BOOL),
            ("enriched", models.PayloadSchemaType.BOOL),
        ]
        for field, schema_type in indexes:
            try:
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name=field,
                    field_schema=schema_type
                )
            except Exception as e:
                logger.warning(f"Index creation for '{field}' failed: {e}")
    
    def upsert_point(self, point_id: str, dense_vector: List[float], sparse_vector: Dict[str, Any], image_vector: Optional[List[float]], payload: Dict[str, Any]):
        """Upsert a single point with all vector types."""
        vectors = {
            "text_dense": dense_vector,
            "text_sparse": SparseVector(indices=sparse_vector["indices"], values=sparse_vector["values"])
        }
        if image_vector:
            vectors["image_clip"] = image_vector
        else:
            vectors["image_clip"] = [0.0] * config.IMAGE_VECTOR_SIZE
        
        self.client.upsert(
            collection_name=self.collection_name,
            points=[models.PointStruct(id=point_id, vector=vectors, payload=payload)]
        )
    
    def batch_upsert(self, points: List[Dict[str, Any]]):
        """Batch upsert multiple points."""
        point_structs = []
        for p in points:
            vectors = {
                "text_dense": p["dense_vector"],
                "text_sparse": SparseVector(indices=p["sparse_vector"]["indices"], values=p["sparse_vector"]["values"]),
                "image_clip": p.get("image_vector") or [0.0] * config.IMAGE_VECTOR_SIZE
            }
            point_structs.append(models.PointStruct(id=p["id"], vector=vectors, payload=p["payload"]))
        
        self.client.upsert(collection_name=self.collection_name, points=point_structs)
    
    def search_dense(self, query_vector: List[float], limit: int = 10, score_threshold: float = 0.0, filter_conditions: Optional[models.Filter] = None) -> List[models.ScoredPoint]:
        """Search using dense text embedding via modern query API."""
        logger.info(f"🔍 Performing dense vector search (limit={limit})...")
        return self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            using="text_dense",
            limit=limit,
            score_threshold=score_threshold,
            query_filter=filter_conditions
        ).points
    
    def search_sparse(self, sparse_vector: Dict[str, Any], limit: int = 10, filter_conditions: Optional[models.Filter] = None) -> List[models.ScoredPoint]:
        """Search using sparse text vector via modern query API."""
        return self.client.query_points(
            collection_name=self.collection_name,
            query=SparseVector(indices=sparse_vector["indices"], values=sparse_vector["values"]),
            using="text_sparse",
            limit=limit,
            query_filter=filter_conditions
        ).points
    
    def hybrid_search_rrf(self, dense_vector: List[float], sparse_vector: Dict[str, Any], image_vector: Optional[List[float]] = None, limit: int = 10, filter_conditions: Optional[models.Filter] = None) -> List[models.ScoredPoint]:
        """Hybrid search using Reciprocal Rank Fusion."""
        logger.info(f"🧠 Performing hybrid RRF search (limit={limit})...")
        prefetch = [
            models.Prefetch(query=dense_vector, using="text_dense", limit=limit * 2),
            models.Prefetch(query=SparseVector(indices=sparse_vector["indices"], values=sparse_vector["values"]), using="text_sparse", limit=limit * 2),
        ]
        if image_vector:
            prefetch.append(models.Prefetch(query=image_vector, using="image_clip", limit=limit * 2))
        
        return self.client.query_points(
            collection_name=self.collection_name,
            prefetch=prefetch,
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=limit,
            query_filter=filter_conditions
        ).points

    def discover(self, target: List[float], context: List[Dict[str, Any]], limit: int = 10, filter_conditions: Optional[models.Filter] = None) -> List[models.ScoredPoint]:
        """
        Use Qdrant Discovery API to find narratives relative to a context.
        context: List of {"positive": vector, "negative": vector} pairs.
        """
        return self.client.discover(
            collection_name=self.collection_name,
            target=target,
            context=context,
            using="text_dense",
            limit=limit,
            query_filter=filter_conditions
        )

    def recommend(self, positive: List[str], negative: Optional[List[str]] = None, limit: int = 10, filter_conditions: Optional[models.Filter] = None) -> List[models.ScoredPoint]:
        """Find narratives similar to internal IDs."""
        return self.client.recommend(
            collection_name=self.collection_name,
            positive=positive,
            negative=negative or [],
            using="text_dense",
            limit=limit,
            query_filter=filter_conditions
        )

    def get_point(self, point_id: str) -> Optional[models.Record]:
        """Retrieve a single point by ID."""
        results = self.client.retrieve(
            collection_name=self.collection_name,
            ids=[point_id],
            with_payload=True,
            with_vectors=True
        )
        return results[0] if results else None

    def update_payload(self, point_ids: List[str], payload: Dict[str, Any]):
        """Update payload for specified points."""
        self.client.set_payload(collection_name=self.collection_name, payload=payload, points=point_ids)
    
    def get_collection_info(self) -> Dict[str, Any]:
        """Get collection statistics with robust attribute access."""
        info = self.client.get_collection(self.collection_name)
        return {
            "points_count": getattr(info, "points_count", 0),
            "status": getattr(info, "status", "unknown"),
            "config": str(getattr(info, "config", ""))
        }

    def scroll_all(self, limit: int = 100, filter_conditions: Optional[models.Filter] = None, with_vectors: bool = False):
        """Generator to scroll through all points in the collection."""
        offset = None
        while True:
            results, next_offset = self.client.scroll(
                collection_name=self.collection_name,
                limit=limit,
                offset=offset,
                with_payload=True,
                with_vectors=with_vectors,
                scroll_filter=filter_conditions
            )
            if not results:
                break
            yield results
            offset = next_offset
            if offset is None:
                break

    def delete_collection(self):
        """Delete the collection. Use with caution!"""
        self.client.delete_collection(self.collection_name)
        logger.warning(f"Deleted collection '{self.collection_name}'.")

# Singleton instance
qdrant_client = NarrativeMemoryClient()
