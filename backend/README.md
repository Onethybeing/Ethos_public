# Backend

FastAPI app. Python 3.11+, managed with uv.

## Start

```bash
# from repo root
uv sync
cp backend/.env.example backend/.env   # fill in credentials
uv run uvicorn backend.main:app --reload --port 8000
```

API available at `http://localhost:8000`. Docs at `/docs`.

## Key env vars (`backend/.env`)

```dotenv
DATABASE_URL=postgresql+asyncpg://...
REDIS_URL=redis://localhost:6379
QDRANT_URL=http://localhost:6333
JWT_SECRET=<long random string>
GROQ_API_KEY=...
OPENAI_API_KEY=...
```

## Add a dependency

```bash
uv add <package>   # updates pyproject.toml + uv.lock
```
