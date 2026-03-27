from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Import the FactChecker engine we just built
from backend.services.fact_checker.fact_checker_engine import FactChecker

# Initialize FastAPI App
app = FastAPI(
    title="Ethos Fact-Checking API",
    description="API to break down and verify claims using Qdrant and Llama 3.",
    version="1.0.0"
)

# Allow CORS for easy frontend integration (React, etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins, restrict this in production!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the Fact Checking Engine globally so it only loads models/clients once
try:
    engine = FactChecker()
except Exception as e:
    print(f"Failed to initialize engine. Please check your .env file. Error: {e}")
    engine = None

# Request Model
class FactCheckRequest(BaseModel):
    text: str

# Endpoints
@app.get("/")
def read_root():
    return {"message": "Welcome to the Ethos Fact-Checking API. Go to /docs for testing."}

@app.get("/health")
def health_check():
    return {"status": "ok", "engine_ready": engine is not None}

@app.post("/api/check")
def check_facts(request: FactCheckRequest):
    """
    Takes a block of text, extracts atomic claims, cross-references with Qdrant,
    and returns a structured JSON evaluation of Supported/Contradicted/Not Mentioned.
    """
    if engine is None:
        raise HTTPException(status_code=500, detail="Fact Checker engine failed to initialize (Missing API keys?).")
    
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Input text cannot be empty.")

    try:
        # Run the existing pipeline
        # Our engine already returns a Pydantic FinalFactCheckResult model.
        # FastAPI will automatically serialize it back out as perfect JSON!
        result = engine.run_full_pipeline(request.text)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing fact-check: {str(e)}")


if __name__ == "__main__":
    print("Starting Ethos Fact-Checking API on http://localhost:8000 ...")
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)