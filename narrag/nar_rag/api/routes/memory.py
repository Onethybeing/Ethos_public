"""
Memory Routes - Memory management endpoints
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from memory.services.management import memory_service

router = APIRouter()


# ================== Request Models ==================

class DecayRequest(BaseModel):
    decay_lambda: Optional[float] = Field(None, description="Decay rate per day")
    fade_threshold: Optional[float] = Field(None, description="Score below which items are faded")


class SnapshotCreateRequest(BaseModel):
    name: str = Field(..., description="Name for the snapshot")


class SnapshotRestoreRequest(BaseModel):
    snapshot_name: str = Field(..., description="Snapshot to restore")


class CentroidRequest(BaseModel):
    min_reinforcement: int = Field(5, ge=1, description="Minimum reinforcement for centroid computation")


class DriftRequest(BaseModel):
    threshold: float = Field(0.85, ge=0.5, le=1.0, description="Similarity threshold for drift detection")


class FamiliesRequest(BaseModel):
    min_size: int = Field(2, ge=1, description="Minimum family size to include")
    include_faded: bool = Field(False, description="Include faded memories")


# ================== Endpoints ==================

@router.post("/decay")
async def run_decay(request: DecayRequest):
    """
    Run decay simulation on all memories.
    
    Computes decay scores and marks items below threshold as 'faded'.
    """
    try:
        stats = memory_service.run_decay(
            decay_lambda=request.decay_lambda,
            fade_threshold=request.fade_threshold
        )
        return {
            "status": "completed",
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/decay/preview")
async def preview_decay(sample_size: int = 20):
    """
    Preview decay scores for a sample of memories.
    """
    try:
        preview = memory_service.get_decay_preview(sample_size=sample_size)
        return {
            "sample_size": len(preview),
            "memories": preview
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/snapshot/create")
async def create_snapshot(request: SnapshotCreateRequest):
    """
    Create a named snapshot of current state.
    """
    try:
        result = memory_service.create_snapshot(request.name)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/snapshot/list")
async def list_snapshots():
    """
    List all available snapshots.
    """
    try:
        snapshots = memory_service.list_snapshots()
        return {
            "count": len(snapshots),
            "snapshots": snapshots
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/snapshot/restore")
async def restore_snapshot(request: SnapshotRestoreRequest):
    """
    Restore a snapshot for time-travel queries.
    """
    try:
        result = memory_service.restore_snapshot(request.snapshot_name)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/centroids/compute")
async def compute_centroids(request: CentroidRequest):
    """
    Compute centroids for high-reinforcement narrative clusters.
    """
    try:
        stats = memory_service.compute_centroids(
            min_reinforcement=request.min_reinforcement
        )
        return {
            "status": "completed",
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/drift/detect")
async def detect_drift(request: DriftRequest):
    """
    Detect narratives drifting from their centroids.
    """
    try:
        drifters = memory_service.detect_drift(threshold=request.threshold)
        return {
            "count": len(drifters),
            "drifters": drifters
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/families")
async def get_families(request: FamiliesRequest):
    """
    Get narrative families clustered by tags.
    """
    try:
        families = memory_service.get_narrative_families(
            min_size=request.min_size,
            include_faded=request.include_faded
        )
        return {
            "count": len(families),
            "families": families
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/families")
async def get_families_simple(min_size: int = 2, include_faded: bool = False):
    """
    Get narrative families (GET version).
    """
    try:
        families = memory_service.get_narrative_families(
            min_size=min_size,
            include_faded=include_faded
        )
        return {
            "count": len(families),
            "families": families
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_memory_stats():
    """
    Get comprehensive memory statistics.
    """
    try:
        stats = memory_service.get_memory_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
