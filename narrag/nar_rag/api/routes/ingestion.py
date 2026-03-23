"""
Ingestion Routes - Data ingestion endpoints
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List
from data_pipeline.services.ingestion import ingestion_service

router = APIRouter()


# ================== Request Models ==================

class IngestRequest(BaseModel):
    pass  # No parameters needed for basic ingestion


class IngestItemRequest(BaseModel):
    title: str
    text: str
    url: Optional[str] = None
    source: str = "manual"
    image_url: Optional[str] = None


class IngestBatchRequest(BaseModel):
    items: List[IngestItemRequest]


# ================== State ==================

_ingestion_status = {
    "running": False,
    "last_run": None,
    "last_stats": None
}


# ================== Endpoints ==================

@router.post("/ingest")
async def trigger_ingestion(background_tasks: BackgroundTasks):
    """
    Trigger full ingestion from all sources.
    
    Runs in background - check /ingest/status for progress.
    """
    if _ingestion_status["running"]:
        return {
            "status": "already_running",
            "message": "Ingestion is already in progress"
        }
    
    def run_ingestion():
        _ingestion_status["running"] = True
        try:
            stats = ingestion_service.ingest_all()
            _ingestion_status["last_stats"] = stats
            import datetime
            _ingestion_status["last_run"] = datetime.datetime.now().isoformat()
        finally:
            _ingestion_status["running"] = False
    
    background_tasks.add_task(run_ingestion)
    
    return {
        "status": "started",
        "message": "Ingestion started in background (fast mode - no LLM)"
    }


@router.get("/ingest/status")
async def ingestion_status():
    """Get current ingestion status."""
    return _ingestion_status


@router.post("/ingest/single")
async def ingest_single_item(request: IngestItemRequest):
    """
    Ingest a single item manually.
    """
    try:
        item = {
            "title": request.title,
            "text": request.text,
            "url": request.url,
            "source": request.source,
            "image_url": request.image_url,
            "timestamp": None  # Will use current time
        }
        
        stats = ingestion_service.ingest_items([item])
        
        return {
            "status": "completed",
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest/batch")
async def ingest_batch(request: IngestBatchRequest, background_tasks: BackgroundTasks):
    """
    Ingest a batch of items.
    
    Runs in background for large batches.
    """
    items = [
        {
            "title": item.title,
            "text": item.text,
            "url": item.url,
            "source": item.source,
            "image_url": item.image_url,
            "timestamp": None
        }
        for item in request.items
    ]
    
    if len(items) > 10:
        # Run in background for large batches
        def run_batch():
            _ingestion_status["running"] = True
            try:
                stats = ingestion_service.ingest_items(items)
                _ingestion_status["last_stats"] = stats
            finally:
                _ingestion_status["running"] = False
        
        background_tasks.add_task(run_batch)
        
        return {
            "status": "started",
            "message": f"Ingesting {len(items)} items in background"
        }
    else:
        # Run synchronously for small batches
        stats = ingestion_service.ingest_items(items)
        return {
            "status": "completed",
            "stats": stats
        }


@router.post("/anchors/generate")
async def generate_anchors(background_tasks: BackgroundTasks):
    """
    Generate synthetic narrative anchors.
    """
    def run_anchors():
        from scripts.generate_anchors import generate_anchors
        generate_anchors()
    
    background_tasks.add_task(run_anchors)
    
    return {
        "status": "started",
        "message": "Generating 10 narrative anchors in background"
    }
