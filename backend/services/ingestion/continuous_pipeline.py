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
from urllib.parse import urljoin, urlparse

import gdelt  # type: ignore[import-untyped]
import httpx
import trafilatura
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


_CAMEO_CATEGORY_MAP: dict[str, str] = {
    "01": "Politics",
    "02": "Politics",
    "03": "Diplomacy",
    "04": "Diplomacy",
    "05": "Diplomacy",
    "06": "Economy",
    "07": "Humanitarian",
    "08": "Diplomacy",
    "09": "Governance",
    "10": "Politics",
    "11": "Politics",
    "12": "Politics",
    "13": "Conflict",
    "14": "Civil Society",
    "15": "Conflict",
    "16": "Conflict",
    "17": "Conflict",
    "18": "Conflict",
    "19": "Conflict",
    "20": "Conflict",
}


def _is_missing(value: object) -> bool:
    if value is None:
        return True
    text = str(value).strip().lower()
    if text in {"nan", "<na>", "none", "nat"}:
        return True
    try:
        return bool(value != value)  # NaN check
    except Exception:
        return False


def _safe_str(value: object) -> str:
    if _is_missing(value):
        return ""
    return str(value).strip()


def _to_float(value: object) -> float | None:
    if _is_missing(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: object) -> int | None:
    if _is_missing(value):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _event_id(value: object) -> str | None:
    raw = _safe_str(value)
    if not raw:
        return None
    try:
        return str(int(float(raw)))
    except (TypeError, ValueError):
        return raw


def _cameo_to_category(event_code: object) -> str | None:
    code = _safe_str(event_code)
    if not code:
        return None
    digits = "".join(ch for ch in code if ch.isdigit())
    if len(digits) < 2:
        return None
    return _CAMEO_CATEGORY_MAP.get(digits[:2])


def _iso_from_gdelt_ts(ts: object) -> str:
    raw = _safe_str(ts)
    if not raw:
        return datetime.now(timezone.utc).isoformat()

    digits = "".join(ch for ch in raw if ch.isdigit())
    if len(digits) >= 14:
        try:
            dt = datetime.strptime(digits[:14], "%Y%m%d%H%M%S")
            return dt.replace(tzinfo=timezone.utc).isoformat()
        except ValueError:
            pass

    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except ValueError:
        return datetime.now(timezone.utc).isoformat()


def _extract_domain(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.lower().strip()
    if host.startswith("www."):
        host = host[4:]
    return host


def _normalize_source_name(raw_source: str, url: str) -> str:
    if not raw_source:
        return _extract_domain(url)

    candidate = raw_source.strip().lower()
    if not candidate:
        return _extract_domain(url)

    parsed = urlparse(candidate if "://" in candidate else f"https://{candidate}")
    host = (parsed.netloc or parsed.path).split("/")[0]
    if host.startswith("www."):
        host = host[4:]
    return host or _extract_domain(url)


def _extract_title(soup: BeautifulSoup) -> str:
    title = soup.find("title")
    if title and title.get_text(strip=True):
        return title.get_text(strip=True)
    return "Untitled"


def _extract_image_url(soup: BeautifulSoup, article_url: str) -> str | None:
    meta = (
        soup.find("meta", property="og:image")
        or soup.find("meta", attrs={"name": "og:image"})
        or soup.find("meta", attrs={"name": "twitter:image"})
    )
    if not meta:
        return None
    content = _safe_str(meta.get("content"))
    if not content:
        return None
    return urljoin(article_url, content)


def _lower_key_dict(record: dict[object, object]) -> dict[str, object]:
    return {str(key).lower(): value for key, value in record.items()}


def _build_events_lookup(events_df) -> dict[str, dict[str, object]]:
    lookup: dict[str, dict[str, object]] = {}
    if events_df is None or events_df.empty:
        return lookup

    for _, row in events_df.iterrows():
        raw = _lower_key_dict(row.to_dict())
        global_event_id = _event_id(raw.get("globaleventid"))
        if not global_event_id:
            continue

        lookup[global_event_id] = {
            "avg_tone": _to_float(raw.get("avgtone")),
            "num_mentions": _to_int(raw.get("nummentions")),
            "event_code": _safe_str(raw.get("eventcode")) or None,
            "country_code": _safe_str(raw.get("actor1countrycode")) or None,
        }

    return lookup


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
    Producer: polls GDELT mentions and events tables, joins on GlobalEventID,
    and pushes enriched article items to the queue.
    """
    g = gdelt.gdelt()
    seen_urls: set[str] = set()

    while True:
        logger.info("Polling GDELT mentions/events...")
        try:
            today_str = datetime.now(timezone.utc).strftime("%Y %b %d")
            mentions_df = g.Search([today_str], table="mentions", coverage=True)
            events_df = g.Search([today_str], table="events", coverage=True)
            events_lookup = _build_events_lookup(events_df)

            if mentions_df is not None and not mentions_df.empty:
                new_count = 0
                for _, row in mentions_df.iterrows():
                    raw = _lower_key_dict(row.to_dict())

                    url = _safe_str(raw.get("sourceurl"))
                    if not url or url in seen_urls:
                        continue

                    seen_urls.add(url)
                    global_event_id = _event_id(raw.get("globaleventid"))
                    enrichment = events_lookup.get(global_event_id or "", {})

                    timestamp_raw = (
                        raw.get("mentiontimedate")
                        or raw.get("eventtimedate")
                        or raw.get("dateadded")
                    )
                    await queue.put(
                        {
                            "url": url,
                            "timestamp": _iso_from_gdelt_ts(timestamp_raw),
                            "source_name": _normalize_source_name(
                                _safe_str(raw.get("mentionsourcename")),
                                url,
                            ),
                            "avg_tone": enrichment.get("avg_tone"),
                            "num_mentions": enrichment.get("num_mentions"),
                            "event_code": enrichment.get("event_code"),
                            "country_code": enrichment.get("country_code"),
                        }
                    )
                    new_count += 1

                logger.info("GDELT: queued %d enriched mention URLs.", new_count)
            else:
                logger.info("GDELT mentions: no new rows.")

            if len(seen_urls) > 50_000:
                seen_urls.clear()
                logger.info("Seen URL cache exceeded 50k entries; cache reset.")
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
            url = str(item.get("url", "")).strip()

            try:
                if not url:
                    continue

                # ── 1. Dedup check (UUID5 of URL) ──────────────────────────────
                doc_id = str(uuid.uuid5(uuid.NAMESPACE_URL, url))
                if _already_indexed(settings, doc_id):
                    logger.debug("Skipping already-indexed URL: %s", url[:60])
                    continue

                # ── 2. Scrape with trafilatura (BS4 only for title/image) ─────
                resp = await http.get(url)
                resp.raise_for_status()

                soup = BeautifulSoup(resp.text, "html.parser")
                title_text = _extract_title(soup)
                image_url = _extract_image_url(soup, url)

                extracted_text = trafilatura.extract(
                    resp.text,
                    include_comments=False,
                    include_tables=False,
                    no_fallback=False,
                )
                text = (extracted_text or "").strip()
                if not text:
                    continue

                # ── 3. Min content filter before NLP/embedding ────────────────
                if len(text.split()) < 150:
                    continue

                text_for_processing = text[:char_limit]

                # ── 4. spaCy in executor (non-blocking) ───────────────────────
                loop = asyncio.get_running_loop()
                doc = await loop.run_in_executor(None, nlp, text_for_processing)
                entities = list(dict.fromkeys(
                    ent.text for ent in doc.ents
                    if ent.label_ in {"PERSON", "ORG", "GPE", "LOC"}
                ))

                # ── 5. Embed ───────────────────────────────────────────────────
                vector = encoder.encode(text_for_processing).tolist()

                # ── 6. AI slop detection (L1 uses precomputed doc) ────────────
                slop = slop_l1.analyze(text_for_processing, doc=doc)
                if slop.get("ai_slop_label") == "uncertain":
                    slop = await slop_l2.evaluate_pipeline(text_for_processing, slop)

                slop_score: float | None = slop.get("ai_slop_score")
                slop_label: str | None = slop.get("ai_slop_label")
                category = _cameo_to_category(item.get("event_code"))
                timestamp_iso = str(item.get("timestamp") or datetime.now(timezone.utc).isoformat())
                source_name = str(item.get("source_name") or _extract_domain(url))

                # ── 7. Write to Qdrant with enrichment payload ─────────────────
                qdrant.upsert(
                    collection_name=settings.qdrant_collection,
                    points=[PointStruct(
                        id=doc_id,
                        vector=vector,
                        payload={
                            "title": title_text,
                            "source": url,
                            "source_name": source_name,
                            "url": url,
                            "timestamp": timestamp_iso,
                            "content": text_for_processing,
                            "entities": entities,
                            "category": category,
                            "avg_tone": item.get("avg_tone"),
                            "num_mentions": item.get("num_mentions"),
                            "country_code": item.get("country_code"),
                            "ai_slop_score": slop_score,
                            "ai_slop_label": slop_label,
                        },
                    )],
                )

                # ── 8. Write to Postgres ───────────────────────────────────────
                inserted = await save_article({
                    "id": doc_id,
                    "title": title_text,
                    "content": text,
                    "url": url,
                    "source": source_name,
                    "published_at": timestamp_iso,
                    "image_url": image_url,
                    "category": category,
                    "avg_tone": item.get("avg_tone"),
                    "num_mentions": item.get("num_mentions"),
                    "country_code": item.get("country_code"),
                    "ai_slop_score": slop_score,
                    "ai_slop_label": slop_label,
                })

                if inserted:
                    slop_score_str = f"{slop_score:.2f}" if isinstance(slop_score, (int, float)) else "n/a"
                    logger.info(
                        "Ingested [%s] %s… (slop=%s)",
                        slop_label, url[:60], slop_score_str,
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
