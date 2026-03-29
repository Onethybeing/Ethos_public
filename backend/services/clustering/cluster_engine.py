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

from collections import Counter
import logging
from dataclasses import dataclass

import numpy as np
from qdrant_client.models import FieldCondition, Filter, MatchValue

from backend.config import get_settings
from backend.core.clients import get_qdrant
from backend.core.llm import get_llm

logger = logging.getLogger(__name__)


@dataclass
class NarrativePillar:
    cluster_id: int
    summary: str
    article_count: int
    representative_urls: list[str]
    divergence_score: float  # 0.8 cosine distance + 0.2 normalized tone std dev


@dataclass
class ClusterResult:
    article_id: str
    topic_query: str
    pillars: list[NarrativePillar]
    noise_article_count: int  # HDBSCAN label == -1


def _as_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_rows(vectors: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return vectors / norms


def _payload_entities(payload: dict) -> list[str]:
    raw_entities = payload.get("entities")
    if not isinstance(raw_entities, list):
        return []

    entities: list[str] = []
    for entity in raw_entities:
        text = str(entity).strip()
        if text:
            entities.append(text)
    return entities


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
    target_payload = target.payload or {}
    topic_query = str(target_payload.get("title", ""))
    target_category_raw = target_payload.get("category")
    target_category = str(target_category_raw).strip() if target_category_raw else ""

    # ── 2. Retrieve similar articles ──────────────────────────────────────────
    query_filter = None
    if target_category:
        query_filter = Filter(
            must=[
                FieldCondition(
                    key="category",
                    match=MatchValue(value=target_category),
                )
            ]
        )

    hits = qdrant.query_points(
        collection_name=settings.qdrant_collection,
        query=target_vector.tolist(),
        query_filter=query_filter,
        limit=settings.background_article_limit,
        with_payload=True,
        with_vectors=True,
    ).points

    valid_hits = [hit for hit in hits if hit.vector is not None]

    if len(valid_hits) < 3:
        return ClusterResult(
            article_id=article_id,
            topic_query=topic_query,
            pillars=[],
            noise_article_count=len(valid_hits),
        )

    # ── 3. HDBSCAN clustering ─────────────────────────────────────────────────
    try:
        import hdbscan  # type: ignore[import-untyped]
    except ImportError:
        raise RuntimeError("Install hdbscan: pip install hdbscan")

    hit_vectors = np.array([h.vector for h in valid_hits], dtype="float32")
    hit_payloads = [h.payload or {} for h in valid_hits]

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

        # Divergence score: 0.8 * cosine_distance + 0.2 * normalized tone std dev
        normalized_vectors = _normalize_rows(cluster_vectors)
        centroid = normalized_vectors.mean(axis=0)
        centroid_norm = float(np.linalg.norm(centroid)) or 1.0
        centroid = centroid / centroid_norm
        cosine_distances = 1.0 - np.clip(normalized_vectors @ centroid, -1.0, 1.0)
        cosine_distance = float(cosine_distances.mean())

        tone_values = [
            tone for tone in (_as_float(p.get("avg_tone")) for p in cluster_payloads)
            if tone is not None
        ]
        tone_std_normalized = 0.0
        if len(tone_values) >= 2:
            tone_std_normalized = min(1.0, float(np.std(tone_values)) / 100.0)

        divergence_score = (cosine_distance * 0.8) + (tone_std_normalized * 0.2)

        # Representative URLs: 60% centroid proximity + 40% mention breadth
        max_distance = float(np.max(cosine_distances)) if len(cosine_distances) else 0.0
        mention_scores = [
            _as_float(payload.get("num_mentions")) or 0.0
            for payload in cluster_payloads
        ]
        max_mentions = max(mention_scores) if mention_scores else 0.0

        ranked_candidates: list[tuple[float, str]] = []
        for idx, payload in enumerate(cluster_payloads):
            url = str(payload.get("url") or payload.get("source") or "").strip()
            if not url:
                continue

            if max_distance > 0:
                proximity = 1.0 - (float(cosine_distances[idx]) / max_distance)
            else:
                proximity = 1.0

            coverage = (mention_scores[idx] / max_mentions) if max_mentions > 0 else 0.0
            weighted_score = (proximity * 0.6) + (coverage * 0.4)
            ranked_candidates.append((weighted_score, url))

        ranked_candidates.sort(key=lambda item: item[0], reverse=True)
        rep_urls = list(dict.fromkeys(url for _, url in ranked_candidates))[:3]

        # LLM pillar summary using snippets and entity context from cluster articles
        entity_counter: Counter[str] = Counter()
        for payload in cluster_payloads:
            entity_counter.update(_payload_entities(payload))
        top_entities = [entity for entity, _ in entity_counter.most_common(12)]

        snippets = "\n\n".join(
            (
                f"Source: {p.get('source_name') or p.get('source') or 'unknown'}\n"
                f"Entities: {', '.join(_payload_entities(p)[:8]) or 'none'}\n"
                f"{str(p.get('content', ''))[:300]}"
            )
            for p in cluster_payloads[:5]
        )
        summary = await _summarize_pillar(snippets, topic_query, cluster_id, top_entities)

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


async def _summarize_pillar(
    snippets: str,
    topic: str,
    cluster_id: int,
    top_entities: list[str],
) -> str:
    """Ask the LLM to write a 2-3 sentence summary of a narrative cluster."""
    entities_line = ", ".join(top_entities[:12]) if top_entities else "none"
    messages = [
        {
            "role": "system",
            "content": (
                "You are a senior news analyst. Given several article snippets covering "
                "the same topic from a similar narrative angle, write a 2-3 sentence "
                "summary describing what this narrative perspective argues, emphasises, "
                "or frames differently from mainstream coverage. Use entity context when "
                "available. Be specific and concise."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Topic: {topic}\n"
                f"Key entities: {entities_line}\n\n"
                f"Article snippets from narrative cluster {cluster_id}:\n\n"
                f"{snippets}\n\nSummarise this narrative perspective in 2-3 sentences:"
            ),
        },
    ]
    try:
        return await get_llm().chat(messages=messages, model_tier="strong", temperature=0.3)
    except Exception as e:
        logger.warning("Pillar summary failed for cluster %d: %s", cluster_id, e)
        return f"Cluster {cluster_id}: narrative perspective could not be summarized."
