import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_pipeline.services.embeddings import embedding_generator
from memory.services.qdrant_client import NarrativeMemoryClient

class TestNarrativeMemory(unittest.TestCase):
    
    def test_embedding_generation(self):
        """Test that embeddings are generated with correct dimensions."""
        text = "Test narrative about AI."
        
        dense = embedding_generator.generate_dense(text)
        self.assertEqual(len(dense), 768, "Dense vector should be 768-dim")
        
        sparse = embedding_generator.generate_sparse(text)
        self.assertTrue("indices" in sparse and "values" in sparse)
        
    @patch('services.qdrant_service.QdrantClient')
    def test_qdrant_connection(self, mock_client):
        """Test Qdrant client initialization."""
        client = NarrativeMemoryClient()
        self.assertIsNotNone(client.client)
        
    def test_sparse_generation_logic(self):
        """Test TF-IDF logic."""
        text = "apple apple banana"
        sparse = embedding_generator.generate_sparse(text)
        
        # apple appears twice, banana once. total 3.
        # apple tf = 2/3 = 0.66
        # banana tf = 1/3 = 0.33
        
        self.assertEqual(len(sparse['indices']), 2)
        self.assertAlmostEqual(sum(sparse['values']), 1.0, places=1)

if __name__ == '__main__':
    unittest.main()
