"""
Enrichment Routes - Trigger batch enrichment of ingested articles

Supports:
- Background enrichment with SSE progress streaming
- Priority queue by topic / recency
- Adaptive rate limiting (backoff on 429, speed up on success)
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List
import asyncio
import json
import queue
import threading

router = APIRouter()


# ================== Request Models ==================

class EnrichRequest(BaseModel):
    batch_size: int = Field(20, description="Articles per LLM call", ge=1, le=50)
    max_articles: Optional[int] = Field(None, description="Max articles to enrich (None = all)")
    priority_topics: Optional[List[str]] = Field(None, description="Topics to prioritize (e.g. ['AI', 'climate'])")


# ================== State ==================

_enrichment_status = {
    "running": False,
    "last_run": None,
    "last_stats": None,
    "progress": []  # Rolling list of recent events
}


# ================== Endpoints ==================

@router.post("/enrich")
async def trigger_enrichment(request: EnrichRequest, background_tasks: BackgroundTasks):
    """
    Trigger batch enrichment of unenriched articles.
    
    Scrapes full text from URLs, batch-summarizes via LLM,
    extracts narrative metadata, and updates Qdrant.
    
    Features:
    - Adaptive rate limiting (backs off on 429, speeds up on success)
    - Skips failed batches and continues to the next
    - Optional priority_topics to process matching articles first
    
    Runs in background - use GET /enrich/stream for real-time SSE progress,
    or GET /enrich/status for polling.
    """
    if _enrichment_status["running"]:
        return {
            "status": "already_running",
            "message": "Enrichment is already in progress"
        }
    
    def run_enrichment():
        _enrichment_status["running"] = True
        _enrichment_status["progress"] = []
        
        def on_progress(event):
            _enrichment_status["progress"].append(event)
            # Keep only the last 50 events
            if len(_enrichment_status["progress"]) > 50:
                _enrichment_status["progress"] = _enrichment_status["progress"][-50:]
        
        try:
            from agents.services.enrichment import enrichment_agent
            stats = enrichment_agent.enrich_unenriched(
                batch_size=request.batch_size,
                max_articles=request.max_articles,
                priority_topics=request.priority_topics,
                on_progress=on_progress,
            )
            _enrichment_status["last_stats"] = stats
            import datetime
            _enrichment_status["last_run"] = datetime.datetime.now().isoformat()
        except Exception as e:
            _enrichment_status["last_stats"] = {"error": str(e)}
        finally:
            _enrichment_status["running"] = False
    
    background_tasks.add_task(run_enrichment)
    
    return {
        "status": "started",
        "message": f"Enrichment started (batch_size={request.batch_size}, max={request.max_articles or 'all'}, priority={request.priority_topics or 'none'})",
        "tip": "Use GET /api/enrich/stream for real-time SSE progress"
    }


@router.get("/enrich/stream")
async def enrichment_stream():
    """
    Server-Sent Events (SSE) stream of enrichment progress.
    
    Connect to this endpoint while enrichment is running to get
    real-time updates on batch progress, delays, and completion.
    
    Events: started, batch_start, batch_done, batch_skipped, complete
    """
    async def event_generator():
        last_index = 0
        
        # If not running and nothing queued, send a status message
        if not _enrichment_status["running"]:
            yield f"data: {json.dumps({'event': 'idle', 'data': {'running': False, 'last_stats': _enrichment_status['last_stats']}})}\n\n"
            return
        
        while _enrichment_status["running"] or last_index < len(_enrichment_status["progress"]):
            progress = _enrichment_status["progress"]
            
            # Send any new events
            while last_index < len(progress):
                event = progress[last_index]
                yield f"data: {json.dumps(event)}\n\n"
                last_index += 1
            
            # Check if done
            if not _enrichment_status["running"] and last_index >= len(progress):
                break
            
            await asyncio.sleep(0.5)
        
        # Final complete event
        yield f"data: {json.dumps({'event': 'stream_end', 'data': _enrichment_status.get('last_stats', {})})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.get("/enrich/status")
async def enrichment_status():
    """Get current enrichment status, last run stats, and recent progress events."""
    return {
        "running": _enrichment_status["running"],
        "last_run": _enrichment_status["last_run"],
        "last_stats": _enrichment_status["last_stats"],
        "recent_events": _enrichment_status["progress"][-10:],
    }


@router.post("/enrich/reset")
async def reset_enrichment():
    """
    Reset all articles back to unenriched state.
    
    Clears enriched flag, enrich_attempts, and all LLM-generated fields
    so articles will be re-processed on the next enrichment run.
    """
    if _enrichment_status["running"]:
        raise HTTPException(status_code=409, detail="Cannot reset while enrichment is running")
    
    try:
        from memory import qdrant_client
        from qdrant_client.http import models
        
        # Scroll ALL points and reset enrichment fields
        reset_count = 0
        for batch in qdrant_client.scroll_all(limit=100):
            point_ids = [p.id for p in batch if p.payload.get("enriched", False)]
            if not point_ids:
                continue
            
            qdrant_client.update_payload(
                point_ids=point_ids,
                payload={
                    "enriched": False,
                    "enrich_attempts": 0,
                    "summary": None,
                    "narrative_framing": None,
                    "causal_structure": None,
                    "emotional_tone": None,
                    "actor_roles": None,
                    "tags": None,
                    "link_alive": None,
                    "enriched_at": None,
                }
            )
            reset_count += len(point_ids)
        
        return {
            "status": "completed",
            "reset_count": reset_count,
            "message": f"Reset {reset_count} articles to unenriched state"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
