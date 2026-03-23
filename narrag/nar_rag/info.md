# Narrative Memory System: Technical & Strategic Architecture

This document providing a comprehensive, high-resolution breakdown of the **Narrative Intelligence Engine**. It serves as an exhaustive technical and operational manual for the repository.

---

## 1. Executive Summary
The **Narrative Memory System** is an advanced AI framework designed to move beyond simple "Semantic Search" (finding text that sounds similar). Instead, it implements **Narrative Analysis**—detecting the structural skeletons of stories, tracking their dominance in the information space, and analyzing their evolution over time.

It combines **Multi-Vector Retrieval**, **Temporal Analysis**, and a **Multi-Agent Orchestration** layer to turn raw news data into strategic intelligence.

---

## 2. Information Ingestion Flow (The "Sensor" Layer)
This layer is responsible for turning "unstructured noise" into "structured memory."

### 2.1 Data Collection (`collector.py`)
*   **What**: Polls multiple high-signal sources including RSS Feeds (BBC Technology, Wired, etc.), Reddit (r/technology), and the Hacker News API.
*   **Why**: Gathers a diverse range of perspectives—from mainstream media to developer-centric discussions.
*   **Mechanism**: Normalizes heterogeneous data formats into a unified `Item` schema (title, text, source, url, timestamp, image).

### 2.2 Extraction Agent (`llm.py`)
*   **What**: A specialized LLM service (Gemini 2.0 Flash) that acts as a "Deconstruction Engine."
*   **Why**: To identify the underlying story structure, not just keywords.
*   **How**: For every article, it extracts:
    *   **Framing**: The core "hook" or perspective (e.g., "AI as a Job Killer").
    *   **Causal Structure**: The "If [A] then [B]" logic found in the text.
    *   **Actor Roles**: Who is the **Hero**, **Villain**, or **Victim** in this specific narrative?
    *   **Narrative Tags**: High-level conceptual tags (e.g., `regulatory-capture`, `techno-optimism`).

### 2.3 Semantic Memory Storage (`qdrant_service.py`)
*   **What**: Persists the data into **Qdrant Cloud** using a specific Multi-Vector architecture.
*   **Why**: To enable "Hybrid Search" that looks at conceptual meaning, keywords, and visuals simultaneously.
*   **Implementation**:
    *   **Dense Vectors (768d)**: Captures the conceptual "vibe" of the narrative.
    *   **Sparse Vectors**: Captures rare keywords and terminology for precision.
    *   **Image Vectors (512d)**: Stores visual context using CLIP embeddings if an image is present.
    *   **Deduplication & Reinforcement**: If a new article is >90% similar to an existing one, the system doesn't create a new record. Instead, it **Reinforces** the existing one, incrementing a count. This allows the system to measure how "loud" a narrative is.

---

## 3. The Retrieval Engine (The "Brain")
Standard search is not enough for intelligence work. This system uses a **4-Stage Pipeline** found in `retrieval.py`.

### Stage 1: Hybrid Multivector Recall
*   **Process**: Executes 3 searches in parallel: Dense, Sparse, and Image.
*   **Fusion**: Uses **Reciprocal Rank Fusion (RRF)** to blend these lists. This ensures that an article that is both conceptually relevant and has exact keyword matches is ranked highest.

### Stage 2: Discovery & Mutation Search
*   **Process**: Uses Qdrant's Recommendation API.
*   **Logic**: Finds articles that share a "Positive" framing (e.g., "Renewable Energy") but may have a "Negative" conclusion. This identifies **Narrative Drift** or contradictions in the media.

### Stage 3: Temporal Reranking
*   **Process**: Applies a mathematical **Decay Function** over time.
*   **Boost**: Narratives that have been "Reinforced" many times get a score boost.
*   **Recency Bonus**: Newer items get a slight multiplier to ensure freshness.

### Stage 4: Outcome Attribution
*   **Process**: Takes a selected narrative and maps it forward in time.
*   **Goal**: To find if this narrative eventually "resolved" into a specific real-world event (e.g., did a prediction about a "Tech Crash" lead to actual market dip articles later?).

---

## 4. Multi-Agent Analysis (The "Analyst Suite")
Each agent is a specialized micro-service that performs one critical analytical task.

### 4.1 Dominance Agent (`dominance.py`)
*   **Goal**: Find what is "Mainstream."
*   **Logic**: It calculates **Volume**, **Frequency**, and **Velocity**.
*   **Insight**: It answers: "Is this story gaining traction or fading away?"

### 4.2 Evolution Agent (`evolution.py`)
*   **Goal**: Track changes over deep time.
*   **Logic**: It captures snapshots of the same topic at T-0 (current), T-1 (1 month ago), and T-2 (6 months ago).
*   **Insight**: It uses an LLM call to compare these snapshots and report: "The discussion used to be about [A], but now it has shifted to [B]."

### 4.3 External Knowledge Agent (`external.py`)
*   **Goal**: Sanity-check the memory.
*   **Logic**: Extracts the central "Factual Claim" from a narrative and attempts to verify it against Wikipedia or Fact-Check APIs.
*   **Insight**: It flags "Villains" or "Heroes" from Phase 2 that might have a controversial real-world history.

### 4.4 Outcome Tracer (`outcome.py`)
*   **Goal**: Historical pattern matching.
*   **Logic**: Queries Qdrant for "Post-Event" articles (articles appearing 30-90 days *after* a narrative window).
*   **Insight**: It summarizes where stories "ended up," allowing users to anticipate the end of current trends.

### 4.5 Meta-Synthesis Agent (`meta.py`)
*   **Goal**: Final Intelligence Briefing.
*   **Logic**: The "Director" agent. It orchestrates calls to all sub-agents, gathers their disparate data, and passes a massive context window to Gemini 2.0.
*   **Style**: It is programmed to write in a "Professional Intelligence Analyst" style—clean, strategic, and focused on "Blind Spots."

---

## 5. API Interface (The "Touchpoint")
The system is controlled via a REST API (`api/main.py`).

*   **POST /api/ingest**: Triggers the collection and narrative extraction of new data.
*   **POST /api/retrieve**: Executes the 4-stage search journey for a user query.
*   **POST /api/report**: Triggers the `MetaSynthesisAgent` to build a full strategic brief.
*   **GET /api/health**: Checks the connection to Qdrant Cloud and verifies the status of your "Memory."

---

## 6. Philosophy: Strategic Narrative RAG
Unlike traditional RAG which retrieves "Chunks" of text to answer a specific question, this system retrieves **Narrative Profiles**. 

**The goal is not to help the user read better, but to help the user THINK better by revealing the patterns that are often hidden in the noise of daily news.**
