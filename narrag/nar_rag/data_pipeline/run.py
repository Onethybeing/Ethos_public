#!/usr/bin/env python
"""
Run script for Data Pipeline service.
Standalone mode for testing embeddings and LLM extraction.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_pipeline.services.embeddings import embedding_generator
from data_pipeline.services.llm import llm_service

def test_embeddings():
    """Test embedding generation."""
    print("📐 Testing Embeddings...")
    text = "OpenAI releases new model amid regulatory concerns"
    
    dense = embedding_generator.generate_dense(text)
    sparse = embedding_generator.generate_sparse(text)
    
    print(f"  Dense: {len(dense)} dimensions")
    print(f"  Sparse: {len(sparse['indices'])} non-zero terms")
    return True

def test_llm():
    """Test LLM narrative extraction."""
    print("🧠 Testing LLM Extraction...")
    title = "Tech Giants Face New AI Regulations"
    text = "Major technology companies are facing increased scrutiny as governments around the world move to regulate artificial intelligence development."
    
    result = llm_service.extract_narrative(title, text)
    print(f"  Framing: {result.get('narrative_framing')}")
    print(f"  Tone: {result.get('emotional_tone')}")
    print(f"  Tags: {result.get('tags')}")
    return True

if __name__ == "__main__":
    print("=" * 50)
    print("DATA PIPELINE SERVICE TEST")
    print("=" * 50)
    
    test_embeddings()
    print()
    test_llm()
    
    print("\n✅ All tests passed!")
