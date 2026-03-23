"""
FastAPI Backend - Narrative Memory System API

Main application with CORS configuration for frontend.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import retrieval, ingestion, memory, mutation, report, enrichment
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Narrative Memory System",
    description="Multi-vector narrative memory with advanced Qdrant features",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(retrieval.router, prefix="/api", tags=["Retrieval"])
app.include_router(ingestion.router, prefix="/api", tags=["Ingestion"])
app.include_router(memory.router, prefix="/api", tags=["Memory"])
app.include_router(mutation.router, prefix="/api", tags=["Mutation Analysis"])
app.include_router(report.router, prefix="/api", tags=["Intelligence Reports"])
app.include_router(enrichment.router, prefix="/api", tags=["Enrichment"])


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "Narrative Memory System",
        "version": "1.0.0"
    }


@app.get("/api/health")
async def health():
    """Detailed health check."""
    from memory.services.qdrant_service import NarrativeMemoryClient
    
    try:
        client = NarrativeMemoryClient()
        info = client.get_collection_info()
        return {
            "status": "healthy",
            "qdrant": {
                "connected": True,
                "collection": client.collection_name,
                "points_count": info.get("points_count", 0)
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
