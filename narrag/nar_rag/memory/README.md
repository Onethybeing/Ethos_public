# Memory

Vector database layer using Qdrant for narrative storage and retrieval.

## Services

| File | Description |
|------|-------------|
| `qdrant_client.py` | Core Qdrant wrapper with named vector support |
| `retrieval.py` | Search logic with hybrid RRF fusion |
| `management.py` | Memory decay, snapshots, health checks |

## Qdrant Features Used

1. **Named Vectors**: Store 3 vectors per point (`text_dense`, `text_sparse`, `image_clip`)
2. **Hybrid Search (RRF)**: Fuse dense + sparse results using Reciprocal Rank Fusion
3. **Discovery API**: Recommendation search for mutation detection
4. **Payload Indexing**: Fast filtering on timestamp, source, tags
5. **Scroll API**: Batch iteration for decay simulation

## Collection Schema

```
narrative_memory
├── text_dense (768-dim, COSINE)
├── text_sparse (sparse vector)
├── image_clip (512-dim, COSINE)
└── Payload:
    ├── timestamp (indexed)
    ├── source (indexed)
    ├── title, text
    ├── narrative_framing
    ├── emotional_tone
    ├── actor_roles
    └── tags (indexed)
```

## Usage

```python
from memory.services.qdrant_client import NarrativeMemoryClient

client = NarrativeMemoryClient()

# Dense search
results = client.search_dense(vector, limit=10)

# Hybrid search with RRF
results = client.hybrid_search_rrf(dense_vec, sparse_vec)

# Discovery search (for mutation detection)
results = client.recommend_narratives([positive_vec], [negative_vec])
```
