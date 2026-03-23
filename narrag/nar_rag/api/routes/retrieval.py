from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

class RetrievalRequest(BaseModel):
    query: str
    image_url: Optional[str] = None
    counter_narrative: Optional[str] = None
    time_filter_days: int = 30
    top_k: int = 10

@router.post("/retrieve")
async def retrieve_endpoint(request: RetrievalRequest):
    """
    Execute the full multi-stage retrieval pipeline:
    1. Hybrid Search (Dense + Sparse + Image)
    2. Discovery (Drift & Mutation detection)
    3. Temporal Reranking
    4. Outcome Attribution
    """
    from memory.services.retrieval import retrieval_service
    
    try:
        results = retrieval_service.full_retrieval_pipeline(
            query_text=request.query,
            image_url=request.image_url,
            counter_narrative=request.counter_narrative,
            time_filter_days=request.time_filter_days,
            top_k=request.top_k
        )
        return results
    except Exception as e:
        logger.error(f"Retrieval pipeline failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
