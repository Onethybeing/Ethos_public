"""
Continuous news ingestion pipeline.

Polls GDELT every N seconds, scrapes article text, embeds it, runs slop detection,
and writes to both Qdrant (for semantic search) and Postgres (permanent storage).

Architecture: async producer/consumer with configurable worker count.
  - fetch_gdelt_source()  → pushes URLs into asyncio.Queue
  - stream_processor()    → consumes URLs: scrape → embed → detect → persist
"""
from __future__ import annotations

import asyncio
import logging
import os
import uuid
from datetime import datetime, timezone

import gdelt  # type: ignore[import-untyped]
import httpx
from bs4 import BeautifulSoup
from qdrant_client.models import Distance, PointStruct, VectorParams

from backend.config import get_settings
from backend.core.clients import get_encoder, get_nlp, get_qdrant
from backend.core.db.postgres import init_db, save_article
from backend.core.llm import get_llm
from backend.services.slop_detector.slop_detector import SlopDetector
from backend.services.slop_detector.slop_detector_l2 import SlopDetectorL2

logger = logging.getLogger(__name__)

# Suppress MKL duplicate lib warning (Intel + sentence-transformers)
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")


def _ensure_collection(settings) -> None:
    """Create the Qdrant collection if it doesn't exist."""
    qdrant = get_qdrant()
    try:
        qdrant.get_collection(settings.qdrant_collection)
    except Exception:
        qdrant.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE),
        )
        logger.info("Created Qdrant collection: %s", settings.qdrant_collection)


def _already_indexed(settings, doc_id: str) -> bool:
    """Return True if this article UUID already exists in Qdrant (dedup check)."""
    try:
        results = get_qdrant().retrieve(
            collection_name=settings.qdrant_collection,
            ids=[doc_id],
            with_payload=False,
            with_vectors=False,
        )
        return len(results) > 0
    except Exception:
        return False


async def fetch_gdelt_source(queue: asyncio.Queue, settings) -> None:
    """
    Producer: polls GDELT on a fixed interval and pushes new article URLs to queue.
    Tracks seen URLs in-memory to avoid re-processing within a session.
    """
    g = gdelt.gdelt()
    seen_urls: set[str] = set()

    while True:
        logger.info("Polling GDELT…")
        try:
            today_str = datetime.now(timezone.utc).strftime("%Y %b %d")
            df = g.Search([today_str], table="events", coverage=True)
            if df is not None and not df.empty:
                new_count = 0
                for url, ts in zip(df["SOURCEURL"].dropna(), df["DATEADDED"]):
                    if url not in seen_urls:
                        seen_urls.add(url)
                        new_count += 1
                        await queue.put({"url": url, "timestamp": str(ts)})
                logger.info("GDELT: pushed %d new URLs to stream.", new_count)
            else:
                logger.info("GDELT: no new events found.")
        except Exception as e:
            logger.warning("GDELT polling error: %s", e)

        await asyncio.sleep(settings.gdelt_poll_interval_secs)


async def stream_processor(queue: asyncio.Queue, settings) -> None:
    """
    Consumer: scrapes, embeds, detects slop, and persists each article.
    Multiple workers run concurrently to hide I/O latency.
    """
    encoder = get_encoder()
    nlp = get_nlp()
    slop_l1 = SlopDetector(nlp)
    slop_l2 = SlopDetectorL2(get_llm())
    qdrant = get_qdrant()
    char_limit = settings.spacy_char_limit

    async with httpx.AsyncClient(
        timeout=settings.scrape_timeout_secs,
        headers={"User-Agent": "Mozilla/5.0 (compatible; EthosNews/2.0)"},
        follow_redirects=True,
    ) as http:

        while True:
            item = await queue.get()
            url: str = item["url"]

            try:
                # ── 1. Dedup check (UUID5 of URL) ──────────────────────────────
                doc_id = str(uuid.uuid5(uuid.NAMESPACE_URL, url))
                if _already_indexed(settings, doc_id):
                    logger.debug("Skipping already-indexed URL: %s", url[:60])
                    continue

                # ── 2. Scrape ──────────────────────────────────────────────────
                resp = await http.get(url)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")
                text = " ".join(
                    p.get_text() for p in soup.find_all("p") if p.get_text().strip()
                )
                if not text.strip():
                    continue

                title = soup.find("title")
                title_text = title.get_text().strip() if title else "Untitled"

                # ── 3. NER (entities for Qdrant payload) ───────────────────────
                doc = nlp(text[:char_limit])
                entities = list(dict.fromkeys(
                    ent.text for ent in doc.ents
                    if ent.label_ in {"PERSON", "ORG", "GPE", "LOC"}
                ))

                # ── 4. Embed ───────────────────────────────────────────────────
                vector = encoder.encode(text[:char_limit]).tolist()

                # ── 5. AI slop detection (L1 → L2 only if uncertain) ───────────
                slop = slop_l1.analyze(text)
                if slop["ai_slop_label"] == "uncertain":
                    slop = await slop_l2.evaluate_pipeline(text, slop)

                slop_score: float | None = slop.get("ai_slop_score")
                slop_label: str | None = slop.get("ai_slop_label")

                # ── 6. Write to Qdrant ─────────────────────────────────────────
                qdrant.upsert(
                    collection_name=settings.qdrant_collection,
                    points=[PointStruct(
                        id=doc_id,
                        vector=vector,
                        payload={
                            "title": title_text,
                            "source": url,
                            "timestamp": item["timestamp"],
                            "content": text[:char_limit],
                            "entities": entities,
                            "ai_slop_score": slop_score,
                            "ai_slop_label": slop_label,
                        },
                    )],
                )

                # ── 7. Write to Postgres ───────────────────────────────────────
                inserted = await save_article({
                    "id": doc_id,
                    "title": title_text,
                    "content": text,
                    "url": url,
                    "source": url,
                    "published_at": item["timestamp"],
                    "image_url": None,
                    "category": None,
                    "ai_slop_score": slop_score,
                    "ai_slop_label": slop_label,
                })

                if inserted:
                    logger.info(
                        "Ingested [%s] %s… (slop=%s)",
                        slop_label, url[:60], f"{slop_score:.2f}" if slop_score else "n/a",
                    )

            except httpx.HTTPStatusError as e:
                logger.debug("HTTP %s for %s — skipping.", e.response.status_code, url[:60])
            except httpx.RequestError as e:
                logger.debug("Request error for %s: %s", url[:60], e)
            except Exception as e:
                logger.warning("Unexpected error processing %s: %s", url[:60], e)
            finally:
                queue.task_done()


async def main() -> None:
    from backend.core.logging_config import setup_logging
    settings = get_settings()
    setup_logging(settings.log_level)

    logger.info("=" * 50)
    logger.info("  EthosNews Continuous Ingestion Pipeline")
    logger.info("=" * 50)

    await init_db()
    _ensure_collection(settings)

    queue: asyncio.Queue = asyncio.Queue(maxsize=500)

    workers = [
        stream_processor(queue, settings)
        for _ in range(settings.ingestion_workers)
    ]

    await asyncio.gather(
        fetch_gdelt_source(queue, settings),
        *workers,
    )


if __name__ == "__main__":
    if os.name == "nt":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown signal received. Stopping pipeline.")
