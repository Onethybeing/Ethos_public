"""
Narrative Divergence Clustering Engine.

Given an article ID, retrieves semantically similar articles from Qdrant,
clusters them using HDBSCAN, and summarises each cluster into a narrative pillar
using the LLM.

This implements the "[View Narrative Clusters]" button from the ehoss.md spec:
  - DPR retrieval (Qdrant semantic search)
  - Divergence clustering (HDBSCAN on embedding vectors)
  - Pillar summaries (LLM per cluster)

Spec metric: Narrative Entropy H > 2.5 (pillar diversity).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

from backend.config import get_settings
from backend.core.clients import get_encoder, get_qdrant
from backend.core.llm import get_llm

logger = logging.getLogger(__name__)


@dataclass
class NarrativePillar:
    cluster_id: int
    summary: str
    article_count: int
    representative_urls: list[str]
    divergence_score: float  # mean intra-cluster cosine distance from centroid


@dataclass
class ClusterResult:
    article_id: str
    topic_query: str
    pillars: list[NarrativePillar]
    noise_article_count: int  # HDBSCAN label == -1


async def get_narrative_clusters(article_id: str) -> ClusterResult:
    """
    Main entry point: returns narrative pillars for a given article.

    Steps:
      1. Fetch the article's embedding from Qdrant (or re-encode if missing).
      2. Retrieve top-N similar articles.
      3. Run HDBSCAN on their embeddings.
      4. For each cluster, LLM generates a 2-3 sentence pillar summary.

    Args:
        article_id: The UUID of the article to cluster around.

    Returns:
        ClusterResult with a list of NarrativePillar objects.
    """
    settings = get_settings()
    qdrant = get_qdrant()

    # ── 1. Fetch target article ───────────────────────────────────────────────
    results = qdrant.retrieve(
        collection_name=settings.qdrant_collection,
        ids=[article_id],
        with_payload=True,
        with_vectors=True,
    )
    if not results:
        raise ValueError(f"Article {article_id} not found in Qdrant.")

    target = results[0]
    target_vector = np.array(target.vector, dtype="float32")
    topic_query = target.payload.get("title", "")

    # ── 2. Retrieve similar articles ──────────────────────────────────────────
    hits = qdrant.search(
        collection_name=settings.qdrant_collection,
        query_vector=target_vector.tolist(),
        limit=50,
        with_vectors=True,
    )

    if len(hits) < 3:
        return ClusterResult(
            article_id=article_id,
            topic_query=topic_query,
            pillars=[],
            noise_article_count=len(hits),
        )

    # ── 3. HDBSCAN clustering ─────────────────────────────────────────────────
    try:
        import hdbscan  # type: ignore[import-untyped]
    except ImportError:
        raise RuntimeError("Install hdbscan: pip install hdbscan")

    hit_ids = [h.id for h in hits]
    hit_vectors = np.array([h.vector for h in hits], dtype="float32")
    hit_payloads = [h.payload for h in hits]

    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=3,
        metric="euclidean",
        cluster_selection_method="eom",
    )
    labels: np.ndarray = clusterer.fit_predict(hit_vectors)

    unique_labels = set(labels) - {-1}
    noise_count = int(np.sum(labels == -1))
    logger.info(
        "HDBSCAN: %d clusters, %d noise articles for article %s",
        len(unique_labels), noise_count, article_id,
    )

    # ── 4. Build pillars (LLM summary per cluster) ────────────────────────────
    pillars: list[NarrativePillar] = []

    for cluster_id in sorted(unique_labels):
        mask = labels == cluster_id
        cluster_vectors = hit_vectors[mask]
        cluster_payloads = [hit_payloads[i] for i, m in enumerate(mask) if m]
        cluster_urls = [
            hit_payloads[i].get("source", "")
            for i, m in enumerate(mask) if m
        ]

        # Divergence score: mean distance of members from cluster centroid
        centroid = cluster_vectors.mean(axis=0)
        distances = np.linalg.norm(cluster_vectors - centroid, axis=1)
        divergence_score = float(distances.mean())

        # Representative URLs (top 3 closest to centroid)
        closest_idx = np.argsort(distances)[:3]
        rep_urls = [cluster_urls[i] for i in closest_idx if cluster_urls[i]]

        # LLM pillar summary using snippets from cluster articles
        snippets = "\n\n".join(
            f"Source: {p.get('source', 'unknown')}\n{p.get('content', '')[:300]}"
            for p in cluster_payloads[:5]
        )
        summary = await _summarize_pillar(snippets, topic_query, cluster_id)

        pillars.append(NarrativePillar(
            cluster_id=int(cluster_id),
            summary=summary,
            article_count=int(mask.sum()),
            representative_urls=rep_urls,
            divergence_score=round(divergence_score, 4),
        ))

    return ClusterResult(
        article_id=article_id,
        topic_query=topic_query,
        pillars=pillars,
        noise_article_count=noise_count,
    )


async def _summarize_pillar(snippets: str, topic: str, cluster_id: int) -> str:
    """Ask the LLM to write a 2-3 sentence summary of a narrative cluster."""
    messages = [
        {
            "role": "system",
            "content": (
                "You are a senior news analyst. Given several article snippets covering "
                "the same topic from a similar narrative angle, write a 2-3 sentence "
                "summary describing what this narrative perspective argues, emphasises, "
                "or frames differently from mainstream coverage. Be specific and concise."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Topic: {topic}\n\nArticle snippets from narrative cluster {cluster_id}:\n\n"
                f"{snippets}\n\nSummarise this narrative perspective in 2-3 sentences:"
            ),
        },
    ]
    try:
        return await get_llm().chat(messages=messages, model_tier="strong", temperature=0.3)
    except Exception as e:
        logger.warning("Pillar summary failed for cluster %d: %s", cluster_id, e)
        return f"Cluster {cluster_id}: narrative perspective could not be summarized."
