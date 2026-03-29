# Ethos

Participatory, intent-driven news platform.

**Stack:** FastAPI · PostgreSQL · Redis · Qdrant · React 19 · Vite

## Prerequisites

- [uv](https://docs.astral.sh/uv/) — Python deps
- Node.js v18+
- PostgreSQL, Redis, Qdrant running locally or via Docker

## Start

**Backend**
```bash
uv sync
cp backend/.env.example backend/.env   # fill in credentials
uv run uvicorn backend.main:app --reload --port 8000
```

**Frontend**
```bash
cd frontend
npm install
npm run dev   # → http://localhost:5173
```

## Add a dependency

```bash
# Python
uv add <package>          # commits pyproject.toml + uv.lock

# JS
cd frontend && npm install <package>
```
