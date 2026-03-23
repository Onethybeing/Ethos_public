# Narrative Memory Frontend

A React application for visualizing and interacting with the Narrative Memory System.

## Features

### 1. Article Analyzer
- Paste a headline or text to search the memory.
- Uses **Hybrid Search** (Dense + Sparse + Image) to find matches.
- Shows **Outcome Attribution**: If a narrative led to specific outcomes (e.g., regulations, debunking), they are highlighted.

### 2. Narrative Explorer
- Visualizes **Narrative Families**: Clusters of related stories.
- Shows impact scores based on reinforcement count.
- Identifies **Anchor Points** (foundational narratives).

### 3. Time Travel
- Compare the "state of the world" between different points in time.
- Requires creating **Snapshots** first.
- Search a query and see how the results differ between "Now" and "Then".

### 4. System Dashboard
- Real-time statistics: Total memories, active vs. faded, top sources.
- **Controls**:
  - **Run Ingestion**: Trigger data fetch from RSS/Reddit.
  - **Run Decay**: Simulate memory fading over time.

## Setup

1. Install dependencies:
   ```bash
   npm install
   ```

2. Run development server:
   ```bash
   npm run dev
   ```

3. The app will be available at `http://localhost:5173`.
