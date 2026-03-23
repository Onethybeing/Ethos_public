# EthosNews Phase 2 Prototype Submission

**Economic Times GenAI Hackathon 2026**  
**Phase 2: Prototype Submission**  
**Senior GenAI Product Architecture Team**  
**March 24, 2026** [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/52208921/48fd359d-92fa-4bb4-b379-fdb4ca176573/ethos.pdf)

## Executive Summary
EthosNews delivers a participatory, intent-driven news ecosystem addressing 2026's core media pathologies: algorithmic echo chambers, narrative overload without perspective, and AI-generated misinformation. Through Personal News Constitutions (PNC), narrative divergence clustering, agentic fact-checking, and gamified engagement leaderboards, users gain unprecedented agency, literacy, and trust. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/52208921/48fd359d-92fa-4bb4-b379-fdb4ca176573/ethos.pdf)

**Current Prototype Status**: Internal MVP processing 50K articles/day with full PNC filtering, clustering, verification pipeline. Phase 2 closed beta ready for 500 power users (journalists/researchers). [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/52208921/48fd359d-92fa-4bb4-b379-fdb4ca176573/ethos.pdf)

India TAM: 450M digital news consumers. Year 1 SOM: 200-500K quality-seeking users. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/52208921/48fd359d-92fa-4bb4-b379-fdb4ca176573/ethos.pdf)

## 1. Problem Statement (2026 Context)

### Three Core Pathologies
1. **Cognitive Capture**: Engagement algorithms create 60-70% narrative monoculture from 3-5 viewpoints. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/52208921/48fd359d-92fa-4bb4-b379-fdb4ca176573/ethos.pdf)
2. **Information Overload**: 350K daily articles globally vs. 8-12 articles/user comprehension window (98.4% waste). [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/52208921/48fd359d-92fa-4bb4-b379-fdb4ca176573/ethos.pdf)
3. **Truth Decay**: Orphaned claims, verification lag (days vs. hours viralization), AI deepfakes with provenance opacity. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/52208921/48fd359d-92fa-4bb4-b379-fdb4ca176573/ethos.pdf)

### 2026 User Psychology
- Demand explicit agency over algorithmic feeds
- Aspiration for news literacy (substantive claim evaluation)
- Human authenticity preference (vs. AI generation)
- Verification fatigue from traditional + AI misinformation [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/52208921/48fd359d-92fa-4bb4-b379-fdb4ca176573/ethos.pdf)

**Primary Users**:
| Segment | Core Need | 2026 Pain Point |
|---------|-----------|----------------|
| General Consumers | Agency, literacy | Overwhelm, fake content burden |
| Journalists | Trust, speed | Fact-check lag, source verification |
| Fact-Checkers | Scalability | Manual workflows, AI falsehoods |
| Content Creators | Attribution | AI impersonation, credit loss |  [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/52208921/48fd359d-92fa-4bb4-b379-fdb4ca176573/ethos.pdf)

## 2. GenAI Technical Unlock

**Why Now? Pre-2025 Limitations**:
- Pre-LLM: Keyword matching only
- 2022-24: Single-model, siloed fact-checking
- **2025+ Multi-agent**: Integrated intent→narrative→verification [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/52208921/48fd359d-92fa-4bb4-b379-fdb4ca176573/ethos.pdf)

**Core Capabilities**:
- **A. Semantic Intent Parsing**: Natural language constitutions → vector constraints
- **B. Narrative Divergence Clustering**: `Divergenceij = ||embAi - embAj||²` + HDBSCAN
- **C. Agentic Fact-Checking**: 4-agent parallel workflow (4x latency reduction)
- **D. Gamified Leaderboard Engine**: Incentivizing news consumption alignment with user's PNC. *(Note: "LLM-as-Judge" for evaluating comment contributions vs. gossip is planned for future iterations).* [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/52208921/48fd359d-92fa-4bb4-b379-fdb4ca176573/ethos.pdf)

## 3. System Architecture (Prototype)

```
Stage 1: Ingestion (GDELT/NewsAPI/PTI)
↓
Stage 2: Parse/Validate/Deduplicate 
↓
Stage 3: FAISS Embedding/Indexing
↓
Stage 4: PNC Constitutional Filter
↓
Stage 5: Metadata Enrichment
↓
Stage 6: Narrative Clustering (Divergence)
↓
Stage 7: Agentic Verification (4 agents)
↓
Stage 8: Pillar Summarization
↓
Stage 9: Gamified Leaderboard (PNC Alignment)
↓
Stage 10: UI Payload
↓
Stage 11: User Feedback → PNC Update
```

### Layer Details

**Layer 1: PNC Orchestrator**
```json
{
  "userid": "researcher001",
  "constitution": {
    "epistemicframework": "empiricist",
    "narrativepreferences": "balance",
    "diversityweight": 0.8,
    "verificationthreshold": "strict"
  }
}
```

**Layer 2: Narrative RAG**
- DPR retrieval → MPNet re-ranking → Divergence clustering → Pillar summaries [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/52208921/48fd359d-92fa-4bb4-b379-fdb4ca176573/ethos.pdf)

**Layer 3: Verification Engine**
```
Article → Agent1(Claim Extract) → Agent2(Evidence) → Agent3(Logic) → Agent4(Ledger)
Veracity: 0.9 (3+ high-cred sources), 0.6-0.8 (mixed), 0.0-0.2 (contradicted)
```

**Layer 4: Gamified Engagement Leaderboard**
```
Engagement Score = 0.40*PNC Alignment + 0.30*Diversity of Viewpoints Read + 0.30*Time Spent on Verified Claims
- Goal: Gamify the system to incentivize users to engage with platforms and align consumption with their personal news constitution.
Target: High user retention and >80% PNC alignment metric [file:1]
```

### Tech Stack (Prototype)
| Component | Technology |
|-----------|------------|
| LLM | Llama-2-13B quantized + Claude API |
| Embeddings | Sentence-Transformers all-MiniLM-L6 |
| Vector DB | FAISS (CPU, 500M capacity) |
| Backend | FastAPI + PostgreSQL |
| Queue | Celery + Redis |
| Frontend | React + TypeScript |  [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/52208921/48fd359d-92fa-4bb4-b379-fdb4ca176573/ethos.pdf)

## 4. Prototype Implementation Status

**Phase 2 Deliverables (Current)**:
- ✅ 50K articles/day ingestion (GDELT + India sources)
- ✅ PNC filtering (95% constitutional compliance)
- ✅ Narrative clustering (H>2.5 entropy target)
- ✅ Agentic verification (sample-based, 85% faithfulness)
- ✅ Web dashboard MVP
- ✅ API endpoints (verification, claim priority queue) [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/52208921/48fd359d-92fa-4bb4-b379-fdb4ca176573/ethos.pdf)

**Phase 2 Beta Plan**:
- 500 power users (journalists, researchers, fact-checkers)
- A/B testing: PNC vs. baseline feeds
- Metrics: TCT<3min, satisfaction>4.25/5 [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/52208921/48fd359d-92fa-4bb4-b379-fdb4ca176573/ethos.pdf)

**Infra**: Rs. 690K/month (AWS/GCP g5.12xlarge cluster) [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/52208921/48fd359d-92fa-4bb4-b379-fdb4ca176573/ethos.pdf)

## 5. Data Sources

| Corpus | Volume | Usage |
|--------|--------|-------|
| GDELT | 500K/day | Primary narrative |
| NewsAPI | 200K/day | Cross-validation |
| PTI/Hindu | 50K/day | India-specific |
| FEVER/SciFact | 185K claims | Verification tuning |
| RBI/SEBI | Real-time | Ground truth |  [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/52208921/48fd359d-92fa-4bb4-b379-fdb4ca176573/ethos.pdf)

## 6. Phase 2 Evaluation Framework

| Metric | Target | Method |
|--------|--------|--------|
| Narrative Entropy | H>2.5 | Pillar diversity |
| Constitutional Compliance | 95% | A/B user testing |
| Faithfulness (RAGAS) | 0.85 | Expert alignment |
| Pillar Coherence | 0.75 | Within-cluster similarity |
| Veracity Calibration | ECE<0.05 | Binned accuracy |
| PNC Alignment Gamification | Mean Score > 80 | Leaderboard metrics |  [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/52208921/48fd359d-92fa-4bb4-b379-fdb4ca176573/ethos.pdf)

## 7. User Workflows (Prototype)

### Core App Experience (Daily Use)
1. **"Your Feed" (Default View)**: Upon opening the app, the user is automatically presented with their personalized feed, featuring articles strictly filtered and aligned with their Personal News Constitution (PNC).
2. **Article View**: When a user clicks to read a specific article, they are provided with two primary action buttons:
   - **[View Narrative Clusters]**: Triggers the narrative divergence engine to instantly map out and summarize alternative perspectives (pillars) regarding the story.
   - **[Verify Claims]**: Activates the agentic fact-checking pipeline to run a real-time verification overlay, assessing the veracity and extracting evidence for the article's claims.

### General Consumer
```
Input: "Show balanced climate policy views, peer-reviewed only"
Output: 4 narrative pillars + veracity overlays + AI flags
```

### Journalist
```
Input: "Electoral commission context"
Output: Historical arc + real-time pillars + claim veracity + provenance
```

### Fact-Checker
```
Dashboard: Top 50 trending claims (AI-flagged priority)
→ Auto-evidence → Expert validate → API distribution
```

### Content Creator
```
Register article → Crypto authorship cert → Attribution tracking → Deepfake alerts
```

## 8. Phase 2 → Phase 3 Roadmap
- **Q2 2026**: Public alpha (50K users), Hindi support
- **Q3 2026**: Mobile app, browser extension, LLM-as-Judge comment moderation (evaluation of real contribution vs. gossip)
- **Q4 2026**: 500K articles/day, regional expansion [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/52208921/48fd359d-92fa-4bb4-b379-fdb4ca176573/ethos.pdf)

## 9. Competitive Moats
1. **PNC Semantic Steering**: User intent as first-class architecture
2. **Divergence Clustering**: Narrative landscapes vs. monoculture
3. **Real-time Agentic Verification**: 4x faster than manual
4. **Gamified Engagement Leaderboards**: Incentivized alignment of consumption with personal constitutions [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/52208921/48fd359d-92fa-4bb4-b379-fdb4ca176573/ethos.pdf)

## 10. Impact Quantification
- **User**: 6hr/week time savings, 30% perspective diversity gain
- **Economic**: Rs. 15Cr value (50K users × Rs. 5K/user/year utility)
- **Societal**: Media literacy improvement, polarization reduction [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/52208921/48fd359d-92fa-4bb4-b379-fdb4ca176573/ethos.pdf)

***

**Phase 2 Prototype Ready for Closed Beta Testing**  
**Contact: Senior GenAI Product Architecture Team** [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/52208921/48fd359d-92fa-4bb4-b379-fdb4ca176573/ethos.pdf)