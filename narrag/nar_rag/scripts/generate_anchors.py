"""
Anchor Generation Script

Creates synthetic narrative anchors - prototype narratives that serve as
reference points for discovery search and clustering.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uuid
import datetime
from data_pipeline.services.llm import llm_service
from data_pipeline.services.embeddings import embedding_generator
from memory.services.qdrant_service import NarrativeMemoryClient
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Prototype narrative themes to seed the database
ANCHOR_THEMES = [
    "Technological utopianism: AI and automation will solve humanity's biggest problems",
    "Dystopian surveillance: Privacy erosion through corporate and state monitoring",
    "Corporate monopoly: Big tech companies stifling competition and innovation",
    "AI alignment risk: Artificial intelligence poses existential threat to humanity",
    "Green tech revolution: Renewable energy inevitably replacing fossil fuels",
    "Crypto disruption: Decentralized finance revolutionizing traditional banking",
    "Misinformation crisis: Social media spreading false narratives at scale",
    "Remote work transformation: Permanent shift in how knowledge work is done",
    "Quantum computing breakthrough: New computing paradigm changing everything",
    "Biotech ethics: Gene editing and enhancement raising moral questions",
]


def generate_anchors():
    """Generate and insert synthetic narrative anchors."""
    logger.info("=== Generating Narrative Anchors ===")
    
    qdrant = NarrativeMemoryClient()
    
    for i, theme in enumerate(ANCHOR_THEMES):
        logger.info(f"[{i+1}/{len(ANCHOR_THEMES)}] Creating anchor: {theme[:50]}...")
        
        try:
            # Generate anchor content via LLM
            anchor_data = llm_service.generate_anchor_narrative(theme)
            
            # Combine title and text for embedding
            full_text = f"{anchor_data.get('title', theme)}. {anchor_data.get('text', theme)}"
            
            # Generate embeddings
            dense_vector = embedding_generator.generate_dense(full_text)
            sparse_vector = embedding_generator.generate_sparse(full_text)
            
            # Build payload
            now = int(datetime.datetime.now().timestamp())
            payload = {
                "title": anchor_data.get("title", theme),
                "text": anchor_data.get("text", theme),
                "source": "synthetic_anchor",
                "url": None,
                "image_url": None,
                "timestamp": now,
                "first_seen": now,
                "last_seen": now,
                "reinforcement_count": 100,  # High initial weight
                "is_anchor": True,
                "is_faded": False,
                "is_variant": False,
                "narrative_framing": anchor_data.get("narrative_framing", "unknown"),
                "causal_structure": anchor_data.get("causal_structure", "unknown"),
                "emotional_tone": anchor_data.get("emotional_tone", "neutral"),
                "actor_roles": anchor_data.get("actor_roles", "unknown"),
                "tags": anchor_data.get("tags", []),
            }
            
            # Upsert to Qdrant
            point_id = str(uuid.uuid4())
            qdrant.upsert_point(
                point_id=point_id,
                dense_vector=dense_vector,
                sparse_vector=sparse_vector,
                image_vector=None,
                payload=payload
            )
            
            logger.info(f"  Created anchor: '{payload['title'][:40]}...'")
            
        except Exception as e:
            logger.error(f"  Failed to create anchor for theme '{theme[:30]}': {e}")
    
    logger.info("=== Anchor Generation Complete ===")


if __name__ == "__main__":
    generate_anchors()
