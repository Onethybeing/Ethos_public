from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List
from agents.services.meta import meta_agent

router = APIRouter()

class ReportRequest(BaseModel):
    topic: str
    days: int = 30

@router.post("/report", response_model=Dict[str, Any])
async def generate_report_endpoint(request: ReportRequest):
    """
    Generate a strategic intelligence report for a topic.
    """
    try:
        report = meta_agent.generate_report(request.topic, request.days)
        if "error" in report:
            raise HTTPException(status_code=404, detail=report["error"])
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
