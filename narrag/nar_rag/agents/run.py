#!/usr/bin/env python
"""
Run script for Agents service.
Tests agent pipelines independently.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_mutation_agent():
    """Test mutation detection agent."""
    print("🧬 Testing Mutation Agent...")
    from agents.services.mutation import mutation_agent
    
    result = mutation_agent.detect_mutations(text="AI companies face new regulations")
    print(f"  Mutations found: {len(result.get('mutations', []))}")
    print(f"  Hotspot alert: {result.get('hotspot_alert', False)}")
    return True

def test_meta_agent():
    """Test meta-synthesis agent."""
    print("📊 Testing Meta-Synthesis Agent...")
    from agents.services.meta import meta_agent
    
    result = meta_agent.generate_report("Artificial Intelligence", days=30)
    if "error" in result:
        print(f"  Status: {result['error']}")
    else:
        print(f"  Dominance metrics: {len(result.get('dominance_analysis', []))}")
        print(f"  Conflicts: {len(result.get('conflicts', []))}")
    return True

if __name__ == "__main__":
    print("=" * 50)
    print("AGENTS SERVICE TEST")
    print("=" * 50)
    
    # Note: These tests require data in Qdrant
    print("\n⚠️  Note: These tests require data in the memory store.")
    print("Run ingestion first if you see 'No data' errors.\n")
    
    test_mutation_agent()
    print()
    test_meta_agent()
    
    print("\n✅ Tests completed!")
