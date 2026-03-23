# Data Pipeline

Handles all data ingestion and processing for the Narrative Intelligence Platform.

## Services

| File | Description |
|------|-------------|
| `embeddings.py` | Multi-modal embedding generation (Dense, Sparse, Image) |
| `llm.py` | Google Gemini integration for narrative extraction |
| `collectors.py` | RSS, Reddit, Hacker News data collection |
| `ingestion.py` | Full ingestion pipeline with deduplication |

## Embedding Types

1. **Dense (768-dim)**: Semantic similarity using `all-mpnet-base-v2`
2. **Sparse**: TF-IDF-style feature hashing for keyword matching
3. **Image (512-dim)**: CLIP embeddings for visual content

## LLM Extraction

The LLM extracts structured narrative components:
- `narrative_framing`: The story's core lens
- `causal_structure`: Implied cause-effect logic
- `emotional_tone`: Dominant emotional register
- `actor_roles`: Heroes, Villains, Victims
- `tags`: Narrative pattern tags

## Usage

```python
from data_pipeline.services.embeddings import embedding_generator
from data_pipeline.services.llm import llm_service

# Generate embeddings
dense = embedding_generator.generate_dense("Some text")
sparse = embedding_generator.generate_sparse("Some text")

# Extract narrative
narrative = llm_service.extract_narrative("Title", "Article text...")
```
