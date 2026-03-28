# Ethos

EthosNews — participatory, intent-driven news ecosystem.

## Stack

| Layer    | Tech                                      |
|----------|-------------------------------------------|
| Backend  | Python 3.11+, FastAPI, uv                 |
| Frontend | React 19, Vite 8, framer-motion, Axios    |
| DB       | PostgreSQL (asyncpg), Redis, Qdrant       |
| LLMs     | Groq, OpenAI, Google Generative AI        |

---

## Prerequisites

- [uv](https://docs.astral.sh/uv/getting-started/installation/) — Python toolchain & dependency manager
- [Node.js](https://nodejs.org/) v18+ — for the frontend
- PostgreSQL, Redis, Qdrant — running locally or via Docker

---

## Backend Setup

```bash
# 1. Install Python dependencies (creates .venv automatically)
uv sync

# 2. Copy and fill in environment variables
cp backend/.env.example backend/.env
# edit backend/.env with your DB URLs, API keys, etc.

# 3. Run the FastAPI server
uv run uvicorn backend.main:app --reload --port 8000
```

### Add a new Python dependency

```bash
uv add <package-name>
# commit both pyproject.toml and uv.lock
```

### Run a one-off Python command

```bash
uv run python -c "from backend.config import get_settings; print(get_settings().app_name)"
```

---

## Frontend Setup

```bash
cd frontend

# 1. Install dependencies
npm install

# 2. Start dev server (proxies API to localhost:8000)
npm run dev
```

| Script          | Description              |
|-----------------|--------------------------|
| `npm run dev`   | Dev server at :5173      |
| `npm run build` | Production build → dist/ |
| `npm run lint`  | ESLint                   |

---

## Project Structure

```
ethos/
├── backend/
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # pydantic-settings config
│   ├── api/                 # Route handlers (feed, checker, pnc, clusters, leaderboard)
│   ├── services/            # Business logic (ingestion, slop detector, fact checker, clustering)
│   ├── core/                # DB clients, LLM wrappers, logging
│   └── schemas/             # Pydantic models
├── frontend/
│   ├── src/
│   │   ├── pages/           # Feed, TruthEngine, Constitution, Leaderboard
│   │   ├── components/      # Navbar, FeedCard, ClusterViz, SlopMeter, ...
│   │   └── api/client.js    # Axios base client
│   └── vite.config.js
├── pyproject.toml           # Python deps (uv)
└── uv.lock
```
