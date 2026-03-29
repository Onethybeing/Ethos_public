"""Backfill AI slop scores for already-ingested articles."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from sqlalchemy import and_, or_, select

from backend.config import get_settings
from backend.core.clients import get_nlp, get_qdrant
from backend.core.db.postgres import Article, AsyncSessionLocal
from backend.core.llm import get_llm
from backend.services.slop_detector.slop_detector import SlopDetector
from backend.services.slop_detector.slop_detector_l2 import SlopDetectorL2

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SlopBackfillStats:
    """Counters collected while backfilling AI slop fields."""

    targeted: int = 0
    processed: int = 0
    updated: int = 0
    skipped: int = 0
    errors: int = 0
    qdrant_updated: int = 0
    qdrant_errors: int = 0


def _chunked(items: list[str], size: int) -> list[list[str]]:
    """Split a list into equally sized chunks."""
    return [items[i:i + size] for i in range(0, len(items), size)]


async def _target_article_ids(*, limit: int | None, only_missing: bool) -> list[str]:
    """Return article IDs that should be processed by the backfill job."""
    async with AsyncSessionLocal() as session:
        stmt = select(Article.id).order_by(Article.id)
        if only_missing:
            stmt = stmt.where(
                or_(
                    Article.ai_slop_label.is_(None),
                    and_(
                        Article.ai_slop_score.is_(None),
                        Article.ai_slop_label.is_not(None),
                        Article.ai_slop_label != "insufficient_content",
                    ),
                )
            )
        if limit is not None and limit > 0:
            stmt = stmt.limit(limit)
        result = await session.execute(stmt)
        return [row[0] for row in result.all()]


async def backfill_ai_slop_scores(
    *,
    limit: int | None = None,
    only_missing: bool = True,
    batch_size: int = 50,
    use_l2: bool = False,
    update_qdrant: bool = False,
) -> SlopBackfillStats:
    """
    Recompute and persist AI slop fields for existing articles.

    Args:
        limit: Max number of articles to process. None means no limit.
        only_missing: If True, process only rows where slop fields are missing.
        batch_size: Number of articles to process per DB transaction.
        use_l2: If True, run LLM layer-2 fallback for uncertain layer-1 results.
        update_qdrant: If True, patch ai_slop payload fields in Qdrant too.

    Returns:
        SlopBackfillStats with processing counters.
    """
    if batch_size <= 0:
        raise ValueError("batch_size must be greater than zero")

    settings = get_settings()
    ids = await _target_article_ids(limit=limit, only_missing=only_missing)
    stats = SlopBackfillStats(targeted=len(ids))
    if not ids:
        return stats

    nlp = get_nlp()
    slop_l1 = SlopDetector(nlp)

    slop_l2: SlopDetectorL2 | None = None
    if use_l2:
        try:
            slop_l2 = SlopDetectorL2(get_llm())
        except Exception as exc:
            logger.warning("L2 disabled (LLM init failed): %s", exc)

    qdrant = None
    if update_qdrant:
        try:
            qdrant = get_qdrant()
        except Exception as exc:
            logger.warning("Qdrant sync disabled (client init failed): %s", exc)

    loop = asyncio.get_running_loop()

    for id_chunk in _chunked(ids, batch_size):
        chunk_updates: list[tuple[str, float | None, str | None]] = []
        chunk_errors = 0

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Article).where(Article.id.in_(id_chunk))
            )
            articles = {article.id: article for article in result.scalars().all()}

            for article_id in id_chunk:
                article = articles.get(article_id)
                if article is None:
                    stats.skipped += 1
                    continue

                try:
                    content = (article.content or "").strip()
                    if not content:
                        slop_result = {
                            "ai_slop_score": None,
                            "ai_slop_label": "insufficient_content",
                        }
                    else:
                        text_for_processing = content[: settings.spacy_char_limit]
                        doc = await loop.run_in_executor(None, nlp, text_for_processing)
                        slop_result = slop_l1.analyze(text_for_processing, doc=doc)

                        if slop_l2 is not None and slop_result.get("ai_slop_label") == "uncertain":
                            slop_result = await slop_l2.evaluate_pipeline(
                                text_for_processing,
                                slop_result,
                            )

                    score = slop_result.get("ai_slop_score")
                    label = slop_result.get("ai_slop_label")

                    article.ai_slop_score = score
                    article.ai_slop_label = label

                    chunk_updates.append((article.id, score, label))
                    stats.processed += 1
                except Exception:
                    chunk_errors += 1
                    logger.exception("Failed slop backfill for article_id=%s", article_id)

            try:
                await session.commit()
                stats.updated += len(chunk_updates)
            except Exception:
                await session.rollback()
                chunk_errors += len(chunk_updates)
                logger.exception("DB commit failed for slop backfill chunk")
                chunk_updates.clear()

        stats.errors += chunk_errors

        if qdrant is not None:
            for article_id, score, label in chunk_updates:
                try:
                    qdrant.set_payload(
                        collection_name=settings.qdrant_collection,
                        payload={
                            "ai_slop_score": score,
                            "ai_slop_label": label,
                        },
                        points=[article_id],
                    )
                    stats.qdrant_updated += 1
                except Exception:
                    stats.qdrant_errors += 1
                    logger.debug(
                        "Qdrant payload update failed for article_id=%s",
                        article_id,
                        exc_info=True,
                    )

    return stats
