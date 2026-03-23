from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from agents.services.mutation import mutation_agent

router = APIRouter()

class MutationRequest(BaseModel):
    narrative_id: Optional[str] = None
    text: Optional[str] = None

class MutationResponse(BaseModel):
    original_narrative: Dict[str, Any]
    mutations: List[Dict[str, Any]]
    mutation_timeline: List[Dict[str, Any]]
    hotspot_alert: bool

@router.post("/detect-mutations", response_model=MutationResponse)
async def detect_mutations_endpoint(request: MutationRequest):
    """
    Detect narrative mutations using the intelligent agent.
    Provide either a narrative_id (from stored memory) or raw text to analyze on the fly.
    """
    if not request.narrative_id and not request.text:
        raise HTTPException(status_code=400, detail="Must provide narrative_id or text")
    
    try:
        result = mutation_agent.detect_mutations(
            narrative_id=request.narrative_id, 
            text=request.text
        )
        
        if "error" in result:
            if result["error"] == "Narrative not found":
                raise HTTPException(status_code=404, detail=result["error"])
            else:
                raise HTTPException(status_code=400, detail=result["error"])
            
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
