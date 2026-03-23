"""
Embedding Service - Multi-modal embedding generation

Generates:
- Dense embeddings (768-dim) using sentence-transformers all-mpnet-base-v2
- Sparse embeddings using TF-IDF with hashing trick
- Image embeddings (512-dim) using CLIP ViT-B/32
"""

from sentence_transformers import SentenceTransformer
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import torch
import requests
from collections import Counter
from typing import Dict, List, Optional, Any
import logging
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """
    Multi-modal embedding generator for the Narrative Memory System.
    
    Lazy-loads models on first use to optimize startup time.
    """
    
    def __init__(self):
        self._dense_model = None
        self._clip_model = None
        self._clip_processor = None
        self._device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Using device: {self._device}")
    
    @property
    def dense_model(self) -> SentenceTransformer:
        """Lazy load dense embedding model."""
        if self._dense_model is None:
            logger.info("Loading dense model (all-mpnet-base-v2)...")
            self._dense_model = SentenceTransformer('all-mpnet-base-v2', device=self._device)
        return self._dense_model
    
    @property
    def clip_model(self) -> CLIPModel:
        """Lazy load CLIP model."""
        if self._clip_model is None:
            logger.info("Loading CLIP model...")
            self._clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
            self._clip_model.to(self._device)
        return self._clip_model
    
    @property
    def clip_processor(self) -> CLIPProcessor:
        """Lazy load CLIP processor."""
        if self._clip_processor is None:
            self._clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        return self._clip_processor
    
    def generate_dense(self, text: str) -> List[float]:
        """
        Generate dense 768-dimensional embedding for text.
        
        Args:
            text: Input text to embed
            
        Returns:
            List of 768 floats representing the embedding
        """
        if not text or not text.strip():
            # Return zero vector for empty text
            return [0.0] * 768
        
        embedding = self.dense_model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    
    def generate_dense_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate dense embeddings for a batch of texts.
        
        Args:
            texts: List of input texts
            
        Returns:
            List of embeddings
        """
        # Replace empty strings with placeholder
        processed = [t if t and t.strip() else " " for t in texts]
        embeddings = self.dense_model.encode(processed, convert_to_numpy=True, batch_size=32)
        return [e.tolist() for e in embeddings]
    
    def generate_sparse(self, text: str) -> Dict[str, List]:
        """
        Generate sparse vector using TF-IDF-like approach with hashing trick.
        
        Uses term frequency normalized by document length with 
        feature hashing to create sparse representation.
        
        Args:
            text: Input text
            
        Returns:
            Dict with 'indices' and 'values' keys for Qdrant SparseVector
        """
        if not text or not text.strip():
            return {"indices": [], "values": []}
        
        # Tokenize: lowercase, split on non-alphanumeric
        words = re.findall(r'\b[a-z0-9]+\b', text.lower())
        
        if not words:
            return {"indices": [], "values": []}
        
        counts = Counter(words)
        total_words = len(words)
        
        indices = []
        values = []
        
        # Use feature hashing to map words to indices with collision handling
        hashed_sparse = {}
        for word, count in counts.items():
            # Hash to positive integer in range [0, 100000)
            idx = abs(hash(word)) % 100000
            # Compute TF (term frequency)
            tf = count / total_words
            
            # Aggregate values if indices collide
            if idx in hashed_sparse:
                hashed_sparse[idx] += float(tf)
            else:
                hashed_sparse[idx] = float(tf)
        
        # Sort indices as required by many sparse vector implementations
        sorted_indices = sorted(hashed_sparse.keys())
        return {
            "indices": sorted_indices,
            "values": [hashed_sparse[i] for i in sorted_indices]
        }
    
    def generate_image(self, image_url: str) -> Optional[List[float]]:
        """
        Generate 512-dimensional CLIP embedding for an image.
        
        Args:
            image_url: URL of the image to embed
            
        Returns:
            List of 512 floats, or None if image loading fails
        """
        if not image_url:
            return None
        
        try:
            # Fetch image with timeout
            response = requests.get(image_url, stream=True, timeout=10)
            response.raise_for_status()
            
            # Load and process image
            image = Image.open(response.raw).convert("RGB")
            inputs = self.clip_processor(images=image, return_tensors="pt")
            inputs = {k: v.to(self._device) for k, v in inputs.items()}
            
            # Generate embedding
            with torch.no_grad():
                image_features = self.clip_model.get_image_features(**inputs)
            
            # Normalize embedding
            image_features = image_features / image_features.norm(p=2, dim=-1, keepdim=True)
            
            return image_features.squeeze().cpu().tolist()
            
        except Exception as e:
            logger.warning(f"Failed to generate image embedding for {image_url}: {e}")
            return None
    
    def generate_all(
        self,
        text: str,
        image_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate all embeddings for a piece of content.
        
        Args:
            text: Text content
            image_url: Optional image URL
            
        Returns:
            Dict with 'dense', 'sparse', and 'image' embeddings
        """
        return {
            "dense": self.generate_dense(text),
            "sparse": self.generate_sparse(text),
            "image": self.generate_image(image_url) if image_url else None
        }


# Singleton instance
embedding_generator = EmbeddingGenerator()
