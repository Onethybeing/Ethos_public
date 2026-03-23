"""
Enrichment Agent - Batch LLM processing for summaries and narrative extraction

Operates AFTER ingestion to add rich metadata to unenriched articles:
- Scrapes full article text from source URLs
- Checks link health (alive/dead)
- Batch summarizes articles via LLM (20 per call)
- Extracts narrative framing, actor roles, tags
- Updates Qdrant payloads with enriched data
"""

import time
import json
import datetime
import requests
from typing import List, Dict, Any, Optional, Tuple
from memory import qdrant_client
from data_pipeline.services.llm import llm_service
from qdrant_client.http import models
from agents import config as settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Canonical Narrative Tags ---
# Fixed taxonomy of ~44 narrative pattern tags.
# LLM must pick 2-5 from this list per article. No freeform tags.

CANONICAL_TAGS = {
    # Power & Control
    "power-consolidation",
    "regulatory-capture",
    "gatekeeping-disrupted",
    "david-vs-goliath",
    "monopoly-entrenchment",
    "accountability-gap",
    # Technology & Progress
    "technological-determinism",
    "innovation-hype",
    "tech-solutionism",
    "automation-anxiety",
    "digital-divide",
    "move-fast-break-things",
    # Privacy & Surveillance
    "privacy-erosion",
    "surveillance-normalization",
    "consent-theater",
    "freedom-vs-security",
    # Economic
    "wealth-concentration",
    "creative-destruction",
    "race-to-bottom",
    "market-disruption",
    "austerity-logic",
    "boom-bust-cycle",
    # Fear & Crisis
    "existential-threat",
    "moral-panic",
    "manufactured-crisis",
    "slow-burn-catastrophe",
    "fear-uncertainty-doubt",
    # Trust & Institutions
    "institutional-failure",
    "expert-distrust",
    "transparency-theater",
    "whistleblower-vindication",
    "revolving-door",
    # Geopolitics
    "us-vs-them",
    "cold-war-redux",
    "sovereignty-erosion",
    "arms-race-escalation",
    # Social & Culture
    "generational-divide",
    "scapegoating",
    "corporate-paternalism",
    "collective-amnesia",
    "victim-narrative",
    "hero-worship",
    # Science & Environment
    "climate-urgency",
    "scientific-consensus-challenged",
    "breakthrough-promise",
    "unintended-consequences",
}


# --- Article Scraping ---

def _scrape_article(url: str, timeout: float = 3.0) -> Tuple[bool, str]:
    """
    Fetch and extract clean article text from a URL.
    
    Returns:
        Tuple of (link_alive: bool, article_text: str)
    """
    if not url or not url.startswith("http"):
        return False, ""
    
    try:
        response = requests.get(url, timeout=timeout, headers={
            "User-Agent": "NarrativeMemoryBot/1.0 (Research Project)"
        })
        
        if response.status_code >= 400:
            return False, ""
        
        html = response.text
        
        # Try trafilatura first (best quality extraction)
        try:
            import trafilatura
            text = trafilatura.extract(html)
            if text and len(text.strip()) > 50:
                return True, text.strip()
        except ImportError:
            pass
        
        # Fallback: basic HTML stripping
        import re
        text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
        text = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Take a reasonable chunk (first ~3000 chars of body text)
        if len(text) > 200:
            return True, text[:3000]
        
        return True, ""
        
    except requests.exceptions.Timeout:
        return False, ""
    except requests.exceptions.ConnectionError:
        return False, ""
    except Exception as e:
        logger.warning(f"Scrape failed for {url[:60]}: {e}")
        return False, ""


# --- Batch LLM Summarization ---

def _build_batch_prompt(articles: List[Dict[str, str]]) -> str:
    """
    Build a single LLM prompt that summarizes and extracts narratives
    for a batch of articles.
    """
    articles_block = ""
    for i, article in enumerate(articles):
        title = article.get("title", "Untitled")
        text = article.get("text", "")[:2000]  # Cap per article
        articles_block += f"""
---
ARTICLE {i + 1}:
TITLE: {title}
TEXT: {text}
"""
    
    # Build canonical tag list for the prompt
    tags_list = ", ".join(f'"{t}"' for t in sorted(CANONICAL_TAGS))
    
    prompt = f"""You are a narrative intelligence analyst. For each article below, produce:
1. A concise summary (2-3 sentences, factual + perspective)
2. The narrative framing (3-6 word phrase capturing the core angle/conflict)
3. Causal structure (one sentence: "Because X, Y is happening, leading to Z")
4. Emotional tone (one word: Warning, Triumphant, Skeptical, Resigned, Alarming, Hopeful, etc.)
5. Actor roles (hero, villain, victim - entities or concepts)
6. Narrative pattern tags: Pick 2-5 tags from the CANONICAL LIST below. Do NOT invent new tags.

CANONICAL TAG LIST (pick ONLY from these):
{tags_list}

{articles_block}

Return a JSON array with one object per article, in the same order.
Each object must have these exact fields:
[
  {{
    "article_index": 1,
    "summary": "2-3 sentence summary...",
    "narrative_framing": "Core Angle In Few Words",
    "causal_structure": "Because X happened, Y is occurring, leading to Z.",
    "emotional_tone": "Warning",
    "actor_roles": {{
      "hero": "entity or concept",
      "villain": "entity or concept",
      "victim": "entity or concept"
    }},
    "tags": ["canonical-tag-1", "canonical-tag-2", "canonical-tag-3"]
  }}
]

Return ONLY valid JSON. No markdown formatting. No extra text."""
    
    return prompt


def _parse_batch_response(response_text: str, expected_count: int) -> List[Dict[str, Any]]:
    """
    Parse the LLM batch response into a list of enrichment dicts.
    Falls back gracefully if parsing fails.
    """
    try:
        content = response_text.strip()
        content = content.replace("```json", "").replace("```", "").strip()
        results = json.loads(content)
        
        if isinstance(results, list):
            # Validate tags against canonical list, strip invalid ones
            for r in results:
                if "tags" in r and isinstance(r["tags"], list):
                    raw = [str(t).lower().strip() for t in r["tags"]]
                    r["tags"] = [t for t in raw if t in CANONICAL_TAGS]
                    dropped = [t for t in raw if t not in CANONICAL_TAGS]
                    if dropped:
                        logger.debug(f"Dropped non-canonical tags: {dropped}")
                else:
                    r["tags"] = []
                    
                # Ensure actor_roles is a dict
                if not isinstance(r.get("actor_roles"), dict):
                    r["actor_roles"] = {
                        "hero": "unknown",
                        "villain": "unknown",
                        "victim": "unknown"
                    }
                
                # Ensure emotional_tone is a string
                if not isinstance(r.get("emotional_tone"), str):
                    r["emotional_tone"] = "neutral"
                
                # Ensure causal_structure is a string
                if not isinstance(r.get("causal_structure"), str):
                    r["causal_structure"] = ""
                    
            return results
        
    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"Failed to parse batch LLM response: {e}")
    
    # Return empty enrichments as fallback
    return [_empty_enrichment() for _ in range(expected_count)]


def _empty_enrichment() -> Dict[str, Any]:
    """Return an empty enrichment dict for failed articles."""
    return {
        "summary": "",
        "narrative_framing": "unknown",
        "causal_structure": "",
        "emotional_tone": "neutral",
        "actor_roles": {
            "hero": "unknown",
            "villain": "unknown",
            "victim": "unknown"
        },
        "tags": []
    }


def _is_valid_enrichment(enrichment: Dict[str, Any]) -> bool:
    """
    Check if an enrichment result contains real data (not just defaults).
    Returns False if the LLM returned garbage that parsed into empty defaults.
    """
    summary = enrichment.get("summary", "").strip()
    framing = enrichment.get("narrative_framing", "unknown").strip().lower()
    tags = enrichment.get("tags", [])
    # Must have a non-empty summary AND a real framing AND at least 1 tag
    return bool(summary) and framing != "unknown" and len(tags) > 0


# --- Enrichment Agent ---

class EnrichmentAgent:
    """
    Batch enrichment agent that adds LLM-generated metadata to unenriched articles.
    
    Pipeline:
    1. Scroll Qdrant for articles with enriched=False
    2. Sort by priority (topic match / recency)
    3. For each batch:
       a. Scrape full text from URLs (check link health)
       b. Send batch to LLM for summarization + narrative extraction
       c. Update Qdrant payloads
    4. Adaptive delay between batches (backs off on 429, speeds up on success)
    5. On batch failure: skip and continue to next batch
    """
    
    def __init__(self):
        self.qdrant = qdrant_client
        self.batch_size = getattr(settings, "ENRICHMENT_BATCH_SIZE", 20)
        # Adaptive rate limiting state
        self._current_delay = getattr(settings, "ENRICHMENT_BASE_DELAY", 4)
        self._base_delay = self._current_delay
        self._max_delay = getattr(settings, "ENRICHMENT_MAX_DELAY", 120)
        self._backoff_factor = getattr(settings, "ENRICHMENT_BACKOFF_FACTOR", 2.0)
        self._cooldown_factor = getattr(settings, "ENRICHMENT_COOLDOWN_FACTOR", 0.7)
    
    def enrich_unenriched(
        self,
        batch_size: Optional[int] = None,
        max_articles: Optional[int] = None,
        priority_topics: Optional[List[str]] = None,
        on_progress: Optional[callable] = None,
    ) -> Dict[str, Any]:
        """
        Find and enrich all unenriched articles in Qdrant.
        
        Args:
            batch_size: Number of articles per LLM call (default: 20)
            max_articles: Max total articles to enrich (None = all)
            priority_topics: Topics to prioritize (enriched first)
            on_progress: Callback(event_dict) for real-time progress streaming
            
        Returns:
            Statistics dict
        """
        batch_size = batch_size or self.batch_size
        self._current_delay = self._base_delay  # Reset delay each run
        
        stats = {
            "total_found": 0,
            "enriched": 0,
            "links_alive": 0,
            "links_dead": 0,
            "llm_calls": 0,
            "failed": 0,
            "batches_skipped": 0,
        }
        
        # 1. Fetch all unenriched articles
        unenriched = self._fetch_unenriched(max_articles)
        stats["total_found"] = len(unenriched)
        
        if not unenriched:
            logger.info("No unenriched articles found.")
            self._emit(on_progress, "complete", stats)
            return stats
        
        # 2. Sort by priority (topic match / recency first)
        topics = priority_topics or getattr(settings, "ENRICHMENT_PRIORITY_TOPICS", [])
        if topics:
            unenriched = self._prioritize(unenriched, topics)
        
        total_batches = (len(unenriched) + batch_size - 1) // batch_size
        logger.info(f"Found {len(unenriched)} unenriched articles. Processing in {total_batches} batches of {batch_size}...")
        self._emit(on_progress, "started", {
            "total_found": len(unenriched),
            "total_batches": total_batches,
            "batch_size": batch_size,
        })
        
        # 3. Process in batches with adaptive delay
        for i in range(0, len(unenriched), batch_size):
            batch = unenriched[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            
            logger.info(f"=== Batch {batch_num}/{total_batches} ({len(batch)} articles) ===")
            self._emit(on_progress, "batch_start", {
                "batch": batch_num,
                "total_batches": total_batches,
                "articles": len(batch),
                "current_delay": round(self._current_delay, 1),
            })
            
            try:
                batch_stats = self._process_batch(batch)
                stats["enriched"] += batch_stats["enriched"]
                stats["links_alive"] += batch_stats["links_alive"]
                stats["links_dead"] += batch_stats["links_dead"]
                stats["llm_calls"] += 1
                stats["failed"] += batch_stats["failed"]
                
                # Success: cool down the delay
                self._adapt_delay(success=True)
                
                self._emit(on_progress, "batch_done", {
                    "batch": batch_num,
                    "enriched": batch_stats["enriched"],
                    "failed": batch_stats["failed"],
                    "next_delay": round(self._current_delay, 1),
                })
                
            except Exception as e:
                error_str = str(e)
                is_rate_limit = "429" in error_str or "RESOURCE_EXHAUSTED" in error_str
                
                if is_rate_limit:
                    self._adapt_delay(success=False)
                    logger.warning(
                        f"⚠ Batch {batch_num} rate-limited. "
                        f"Skipping, will retry later. Delay now {self._current_delay:.0f}s"
                    )
                else:
                    logger.error(f"✗ Batch {batch_num} failed: {e}")
                
                stats["batches_skipped"] += 1
                stats["failed"] += len(batch)
                
                self._emit(on_progress, "batch_skipped", {
                    "batch": batch_num,
                    "reason": "rate_limited" if is_rate_limit else "error",
                    "error": error_str[:200],
                    "next_delay": round(self._current_delay, 1),
                })
            
            # Adaptive delay between batches (skip after last batch)
            if i + batch_size < len(unenriched):
                logger.info(f"⏳ Waiting {self._current_delay:.1f}s before next batch...")
                time.sleep(self._current_delay)
        
        logger.info(f"=== Enrichment Complete === Stats: {stats}")
        self._emit(on_progress, "complete", stats)
        return stats
    
    def _adapt_delay(self, success: bool):
        """Adjust delay based on success/failure (adaptive backoff)."""
        if success:
            self._current_delay = max(
                self._base_delay,
                self._current_delay * self._cooldown_factor
            )
        else:
            self._current_delay = min(
                self._max_delay,
                self._current_delay * self._backoff_factor
            )
    
    def _emit(self, callback: Optional[callable], event: str, data: dict):
        """Fire a progress event if a callback is registered."""
        if callback:
            try:
                callback({"event": event, "data": data})
            except Exception as e:
                logger.debug(f"Progress callback error: {e}")
    
    def _prioritize(self, articles: List[Dict[str, Any]], topics: List[str]) -> List[Dict[str, Any]]:
        """
        Sort articles so that topic-matching and recent articles come first.
        """
        recency_hours = getattr(settings, "ENRICHMENT_PRIORITY_RECENCY_HOURS", 24)
        cutoff = time.time() - (recency_hours * 3600)
        topic_lower = [t.lower() for t in topics]
        
        def priority_score(article):
            title = article.get("title", "").lower()
            score = 0
            # Topic match
            if any(t in title for t in topic_lower):
                score += 2
            # Recency (ingested_at if available, else no boost)
            if article.get("ingested_at", 0) > cutoff:
                score += 1
            return -score  # Negative for ascending sort (highest priority first)
        
        return sorted(articles, key=priority_score)
    
    def _fetch_unenriched(self, max_articles: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Scroll Qdrant for articles where enriched=False.
        
        Returns list of dicts with point_id, title, url.
        """
        max_attempts = getattr(settings, "ENRICHMENT_MAX_ATTEMPTS", 3)
        
        filter_conditions = models.Filter(
            must_not=[
                models.FieldCondition(
                    key="enriched",
                    match=models.MatchValue(value=True)
                )
            ]
        )
        
        unenriched = []
        
        for batch in self.qdrant.scroll_all(limit=100, filter_conditions=filter_conditions):
            for point in batch:
                attempts = point.payload.get("enrich_attempts", 0)
                if attempts >= max_attempts:
                    continue  # Skip articles that hit retry limit
                    
                unenriched.append({
                    "point_id": point.id,
                    "title": point.payload.get("title", ""),
                    "url": point.payload.get("url", ""),
                    "enrich_attempts": attempts,
                    "ingested_at": point.payload.get("ingested_at", 0),
                })
        
        return unenriched
    
    def _process_batch(self, batch: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Process a single batch of articles:
        1. Scrape text from URLs
        2. Call LLM for batch summarization
        3. Update Qdrant
        """
        batch_stats = {
            "enriched": 0,
            "links_alive": 0,
            "links_dead": 0,
            "failed": 0
        }
        
        # Step 1: Scrape articles and check link health
        articles_with_text = []
        link_status = {}  # point_id -> bool
        
        for item in batch:
            url = item.get("url", "")
            point_id = item["point_id"]
            
            logger.info(f"  Scraping: {item.get('title', '')[:50]}...")
            link_alive, full_text = _scrape_article(url)
            
            link_status[point_id] = link_alive
            
            if link_alive:
                batch_stats["links_alive"] += 1
            else:
                batch_stats["links_dead"] += 1
            
            articles_with_text.append({
                "point_id": point_id,
                "title": item.get("title", ""),
                "text": full_text if full_text else item.get("title", ""),
                "link_alive": link_alive,
                "enrich_attempts": item.get("enrich_attempts", 0),
            })
        
        # Step 2: Batch LLM call for summarization + narrative extraction
        prompt_articles = [
            {"title": a["title"], "text": a["text"]}
            for a in articles_with_text
        ]
        
        logger.info(f"  Calling LLM for {len(prompt_articles)} articles...")
        prompt = _build_batch_prompt(prompt_articles)
        
        llm_succeeded = False
        try:
            response = llm_service.generate_content(prompt)
            enrichments = _parse_batch_response(response.text, len(prompt_articles))
            # Check if we got real data or just parsed garbage into defaults
            valid_count = sum(1 for e in enrichments if _is_valid_enrichment(e))
            if valid_count > 0:
                llm_succeeded = True
            else:
                logger.warning(f"  LLM returned parseable but empty/garbage data for all {len(enrichments)} articles")
        except Exception as e:
            logger.error(f"  LLM batch call failed: {e}")
            enrichments = [_empty_enrichment() for _ in prompt_articles]
        
        # Step 3: Update Qdrant payloads
        now = int(datetime.datetime.now().timestamp())
        
        for idx, article in enumerate(articles_with_text):
            point_id = article["point_id"]
            enrichment = enrichments[idx] if idx < len(enrichments) else _empty_enrichment()
            link_alive = link_status.get(point_id, False)
            
            enrichment_valid = _is_valid_enrichment(enrichment)
            
            # If LLM failed (or this specific enrichment is garbage), bump attempts and skip.
            # Dead-link articles with no text get marked enriched (nothing to retry).
            if (not llm_succeeded or not enrichment_valid) and link_alive:
                try:
                    self.qdrant.update_payload(
                        point_ids=[point_id],
                        payload={
                            "link_alive": True,
                            "enrich_attempts": (article.get("enrich_attempts", 0) + 1)
                        }
                    )
                except Exception:
                    pass
                batch_stats["failed"] += 1
                logger.warning(f"  ⟳ Skipped (will retry): {article['title'][:40]}")
                continue
            
            try:
                payload_update = {
                    "summary": enrichment.get("summary", ""),
                    "narrative_framing": enrichment.get("narrative_framing", "unknown"),
                    "causal_structure": enrichment.get("causal_structure", ""),
                    "emotional_tone": enrichment.get("emotional_tone", "neutral"),
                    "actor_roles": enrichment.get("actor_roles", {}),
                    "tags": enrichment.get("tags", []),
                    "link_alive": link_alive,
                    "enriched": True,
                    "enriched_at": now
                }
                
                self.qdrant.update_payload(
                    point_ids=[point_id],
                    payload=payload_update
                )
                
                batch_stats["enriched"] += 1
                logger.debug(f"  ✓ Enriched: {article['title'][:40]}")
                
            except Exception as e:
                logger.error(f"  ✗ Failed to update {point_id}: {e}")
                batch_stats["failed"] += 1
        
        return batch_stats


# Singleton instance
enrichment_agent = EnrichmentAgent()
