# NARRAG — Narrative Intelligence System

A multi-agent RAG platform that goes beyond semantic search. NARRAG deconstructs news articles into **narrative structures** (framing, actors, causal logic), stores them as multi-modal vector embeddings, and uses 7 specialized AI agents to generate strategic intelligence reports.

Built for a hackathon — collaborative project.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)
![Qdrant](https://img.shields.io/badge/Qdrant-1.12-red)
![Gemini](https://img.shields.io/badge/Gemini_2.0_Flash-LLM-4285F4?logo=google&logoColor=white)

---

## What It Does

```
News Sources (RSS, HN) → Narrative Extraction (LLM) → Multi-Modal Embeddings → Qdrant
                                                                                  ↓
                        Intelligence Report ← Agent Orchestration ← 4-Stage Retrieval
```

1. **Ingests** news from 7+ RSS feeds and Hacker News
2. **Extracts** narrative DNA — framing, actor roles (hero/villain/victim), causal claims, emotional tone
3. **Embeds** each article as 3 vector types: Dense (semantic), Sparse (keyword), and CLIP (visual)
4. **Deduplicates** via cosine similarity — near-duplicates reinforce existing records instead of creating new ones
5. **Retrieves** via a 4-stage pipeline: Hybrid Search → Discovery → Temporal Reranking → Outcome Attribution
6. **Analyzes** via specialized agents that assess dominance, track evolution, and synthesize reports

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      API Layer (FastAPI)                      │
│   /ingest   /retrieve   /report   /memory   /mutation        │
└──────────────────────────────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
 ┌─────────────┐    ┌──────────────┐    ┌─────────────────┐
 │   Data       │    │   Memory     │    │   Agents        │
 │   Pipeline   │    │   Layer      │    │   (Multi-Agent) │
 │              │    │              │    │                 │
 │ • Collectors │    │ • Qdrant     │    │ • Dominance     │
 │ • Embeddings │    │ • Retrieval  │    │ • Enrichment    │
 │ • LLM Extract│    │ • Management │    │ • Evolution ⚗   │
 │ • Ingestion  │    │              │    │ • Mutation  ⚗   │
 │              │    │              │    │ • Outcome   ⚗   │
 │              │    │              │    │ • External  ⚗°  │
 │              │    │              │    │ • Meta-Synth    │
 └─────────────┘    └──────────────┘    └─────────────────┘
        │                    │                    │
        └────────────────────┼────────────────────┘
                             ▼
              ┌──────────────────────────┐
              │    External Services      │
              │  • Qdrant Cloud           │
              │  • Google Gemini 2.0 Flash│
              │  • RSS Feeds / HN API     │
              └──────────────────────────┘

⚗ = Experimental (implemented but not fully tested)
° = Simulated (API integration stubbed)
```

---

## Feature Status

| Feature | Status | Notes |
|---------|--------|-------|
| RSS + HN data collection | ✅ Stable | 7 RSS sources + Hacker News |
| LLM narrative extraction | ✅ Stable | Gemini 2.0 Flash, structured JSON output |
| Dense embeddings (768d) | ✅ Stable | sentence-transformers/all-mpnet-base-v2 |
| Sparse embeddings (TF-IDF) | ✅ Stable | Custom hashed sparse vectors |
| CLIP image embeddings (512d) | ✅ Stable | OpenAI CLIP ViT-B/32 |
| Qdrant storage + deduplication | ✅ Stable | Similarity thresholds + reinforcement |
| Hybrid search (RRF fusion) | ✅ Stable | Dense + Sparse + Image fusion |
| Dominance analysis agent | ✅ Stable | Prevalence, velocity, source diversity |
| React dashboard | ✅ Stable | Search, reports, system monitoring |
| Enrichment agent | ✅ Stable | Batch article scraping, LLM summarization, 44-tag canonical taxonomy |
| Discovery / mutation search | ⚗ Experimental | Implemented, needs more testing |
| Evolution tracking agent | ⚗ Experimental | Temporal snapshots, LLM comparison |
| Outcome attribution agent | ⚗ Experimental | Forward-trace narrative resolution |
| External validation agent | ⚗ Experimental | Claim extraction via LLM, fact-check API stubbed (simulated) |
| Meta-synthesis agent | ⚗ Experimental | Combines all agent outputs into reports |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.10+, FastAPI |
| **Frontend** | React 18, Vite |
| **Vector DB** | Qdrant Cloud (named vectors, hybrid search, discovery API) |
| **LLM** | Google Gemini 2.0 Flash |
| **Dense Embeddings** | sentence-transformers (all-mpnet-base-v2, 768d) |
| **Sparse Embeddings** | Custom TF-IDF with feature hashing |
| **Image Embeddings** | CLIP ViT-B/32 (512d) |
| **Deployment** | Docker Compose |

---

## Setup

### Prerequisites
- Python 3.10+
- Node.js 18+
- Qdrant Cloud account (or local Docker: `docker compose up -d`)
- Google Gemini API key

### Installation

```bash
git clone https://github.com/<your-username>/narrag.git
cd narrag

# Backend
pip install -r requirements.txt

# Frontend
cd frontend && npm install && cd ..
```

### Configuration

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_key_here
QDRANT_URL=https://your-cluster.qdrant.io:6333
QDRANT_API_KEY=your_qdrant_api_key
```

### Run

```bash
python run.py
```

- **Dashboard**: http://localhost:5173
- **API Docs**: http://localhost:8000/docs

---

## API Examples

```bash
# Ingest news from all sources
curl -X POST http://localhost:8000/api/ingest

# Search narratives (4-stage hybrid retrieval)
curl -X POST http://localhost:8000/api/retrieve \
  -H "Content-Type: application/json" \
  -d '{"query": "AI Regulation"}'

# Generate intelligence report
curl -X POST http://localhost:8000/api/report \
  -H "Content-Type: application/json" \
  -d '{"topic": "Technology", "days": 30}'
```

---

## How the 4-Stage Retrieval Works

1. **Hybrid Search (RRF)** — Runs dense, sparse, and image searches in parallel, fuses results via Reciprocal Rank Fusion
2. **Discovery Search** — Finds narrative mutations by comparing vector similarity with semantic filtering and tone contrast
3. **Temporal Reranking** — Applies time-decay scoring with reinforcement boosts for frequently-seen narratives
4. **Outcome Attribution** — Forward-traces narratives to see if predictions resolved into real events

---

## Project Structure

```
nar_rag/
├── api/                  # FastAPI routes and middleware
│   └── routes/           # Endpoint handlers (ingest, retrieve, report, etc.)
├── data_pipeline/        # Ingestion, embedding generation, LLM extraction
│   └── services/         # Collectors, embeddings, LLM, ingestion logic
├── memory/               # Qdrant integration and retrieval pipeline
│   └── services/         # Client, retrieval (4-stage), management
├── agents/               # Multi-agent analysis system
│   └── services/         # Dominance, evolution, mutation, outcome, meta
├── frontend/             # React + Vite dashboard
│   └── src/components/   # NarrativeAnalyzer, IntelligenceReports, SystemDashboard
├── tests/                # Unit tests
├── docker-compose.yml    # Qdrant container
├── requirements.txt      # Python dependencies
└── run.py                # Master launcher (API + frontend)
```

---