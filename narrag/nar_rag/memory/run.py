#!/usr/bin/env python
"""
Run script for Memory service.
Tests Qdrant connectivity and basic operations.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory.services.qdrant_service import NarrativeMemoryClient

def test_connection():
    """Test Qdrant connection."""
    print("🔌 Testing Qdrant Connection...")
    client = NarrativeMemoryClient()
    info = client.get_collection_info()
    print(f"  Collection: {client.collection_name}")
    print(f"  Points: {info.get('points_count', 0)}")
    print(f"  Status: {info.get('status', 'unknown')}")
    return True

def test_search():
    """Test basic search."""
    print("🔍 Testing Search...")
    client = NarrativeMemoryClient()
    
    # Create a dummy vector for testing
    dummy_vector = [0.1] * 768
    results = client.search_dense(dummy_vector, limit=3)
    print(f"  Found: {len(results)} results")
    return True

if __name__ == "__main__":
    print("=" * 50)
    print("MEMORY SERVICE TEST")
    print("=" * 50)
    
    test_connection()
    print()
    test_search()
    
    print("\n✅ All tests passed!")
