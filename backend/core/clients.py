"""
Shared singleton registry for heavy infrastructure clients.

Every module should import from here — never instantiate QdrantClient,
SentenceTransformer, or spaCy models directly. This ensures:
  - Models load exactly once per process (not 3×).
  - Easy to swap implementations or mock in tests.

Usage:
    from backend.core.clients import get_qdrant, get_encoder, get_nlp
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_qdrant = None
_encoder = None
_nlp = None


def get_qdrant():
    """Return the singleton synchronous QdrantClient."""
    global _qdrant
    if _qdrant is None:
        from qdrant_client import QdrantClient
        from backend.config import get_settings
        s = get_settings()
        logger.info("Connecting to Qdrant at %s", s.qdrant_url)
        _qdrant = QdrantClient(
            url=s.qdrant_url,
            api_key=s.qdrant_api_key or None,
        )
    return _qdrant


def get_encoder():
    """Return the singleton SentenceTransformer (lazy-loaded on first call)."""
    global _encoder
    if _encoder is None:
        from sentence_transformers import SentenceTransformer
        logger.info("Loading SentenceTransformer (all-MiniLM-L6-v2)…")
        _encoder = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("SentenceTransformer ready.")
    return _encoder


def get_nlp():
    """Return the singleton spaCy en_core_web_sm model (lazy-loaded on first call)."""
    global _nlp
    if _nlp is None:
        import spacy
        logger.info("Loading spaCy model (en_core_web_sm)…")
        try:
            _nlp = spacy.load("en_core_web_sm")
        except OSError:
            logger.warning("en_core_web_sm not found — downloading now…")
            from spacy.cli import download
            download("en_core_web_sm")
            _nlp = spacy.load("en_core_web_sm")
        logger.info("spaCy model ready.")
    return _nlp
