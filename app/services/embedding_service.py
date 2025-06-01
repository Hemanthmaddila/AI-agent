"""
Embedding Service for AI Job Application Agent
Provides semantic text embeddings using sentence-transformers for advanced job matching.

Phase 5.1: Semantic Embeddings Foundation
"""

import logging
import numpy as np
from typing import List, Optional, Union, Dict, Any
import json
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    raise ImportError("sentence-transformers is required. Install with: pip install sentence-transformers")

from config import settings

logger = logging.getLogger(__name__)

class EmbeddingService:
    """
    Service for generating and managing text embeddings using sentence-transformers.
    
    Capabilities:
    - Generate semantic embeddings for job descriptions, resumes, and user profiles
    - Support for multiple embedding models
    - Efficient batch processing
    - Async-compatible operations
    - Embedding storage and retrieval
    """
    
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        """
        Initialize the embedding service with a specific model.
        
        Args:
            model_name: Name of the sentence-transformers model to use
                       'all-MiniLM-L6-v2' - Fast, good quality, 384 dimensions
                       'all-mpnet-base-v2' - Best quality, 768 dimensions, slower
                       'all-distilroberta-v1' - Good balance, 768 dimensions
        """
        self.model_name = model_name
        self.model: Optional[SentenceTransformer] = None
        self.embedding_dimension: Optional[int] = None
        self._executor = ThreadPoolExecutor(max_workers=2)
        
        logger.info(f"EmbeddingService initialized with model: {model_name}")
    
    def _load_model(self) -> None:
        """Load the sentence-transformers model (lazy loading)."""
        if self.model is None:
            logger.info(f"Loading sentence-transformers model: {self.model_name}")
            try:
                self.model = SentenceTransformer(self.model_name)
                # Get embedding dimension by encoding a test string
                test_embedding = self.model.encode("test")
                self.embedding_dimension = len(test_embedding)
                logger.info(f"Model loaded successfully. Embedding dimension: {self.embedding_dimension}")
            except Exception as e:
                logger.error(f"Failed to load model {self.model_name}: {e}")
                raise
    
    def encode_text(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text.
        
        Args:
            text: Input text to encode
            
        Returns:
            numpy array representing the text embedding
        """
        if not text or not text.strip():
            logger.warning("Empty or whitespace-only text provided for encoding")
            # Return zero embedding for empty text
            self._load_model()
            return np.zeros(self.embedding_dimension)
        
        self._load_model()
        
        try:
            # Clean and normalize text
            clean_text = self._preprocess_text(text)
            embedding = self.model.encode(clean_text, convert_to_numpy=True)
            return embedding
        except Exception as e:
            logger.error(f"Error encoding text: {e}")
            # Return zero embedding on error
            return np.zeros(self.embedding_dimension)
    
    def encode_texts(self, texts: List[str]) -> List[np.ndarray]:
        """
        Generate embeddings for multiple texts (batch processing).
        
        Args:
            texts: List of texts to encode
            
        Returns:
            List of numpy arrays representing text embeddings
        """
        if not texts:
            return []
        
        self._load_model()
        
        try:
            # Clean and normalize all texts
            clean_texts = [self._preprocess_text(text) for text in texts]
            embeddings = self.model.encode(clean_texts, convert_to_numpy=True)
            return [embedding for embedding in embeddings]
        except Exception as e:
            logger.error(f"Error encoding texts batch: {e}")
            # Return zero embeddings on error
            return [np.zeros(self.embedding_dimension) for _ in texts]
    
    async def encode_text_async(self, text: str) -> np.ndarray:
        """
        Asynchronously generate embedding for a single text.
        
        Args:
            text: Input text to encode
            
        Returns:
            numpy array representing the text embedding
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, self.encode_text, text)
    
    async def encode_texts_async(self, texts: List[str]) -> List[np.ndarray]:
        """
        Asynchronously generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to encode
            
        Returns:
            List of numpy arrays representing text embeddings
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, self.encode_texts, texts)
    
    def _preprocess_text(self, text: str) -> str:
        """
        Preprocess text before embedding generation.
        
        Args:
            text: Raw input text
            
        Returns:
            Cleaned and normalized text
        """
        if not text:
            return ""
        
        # Basic text cleaning
        cleaned = text.strip()
        
        # Remove excessive whitespace
        cleaned = ' '.join(cleaned.split())
        
        # Truncate if too long (most models have token limits)
        max_length = 8000  # Conservative limit for most sentence-transformers
        if len(cleaned) > max_length:
            cleaned = cleaned[:max_length]
            logger.debug(f"Text truncated to {max_length} characters")
        
        return cleaned
    
    def calculate_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Cosine similarity score between -1 and 1 (higher = more similar)
        """
        try:
            # Ensure embeddings are numpy arrays
            emb1 = np.array(embedding1)
            emb2 = np.array(embedding2)
            
            # Calculate cosine similarity
            dot_product = np.dot(emb1, emb2)
            norm1 = np.linalg.norm(emb1)
            norm2 = np.linalg.norm(emb2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = dot_product / (norm1 * norm2)
            return float(similarity)
        except Exception as e:
            logger.error(f"Error calculating similarity: {e}")
            return 0.0
    
    def embedding_to_json(self, embedding: np.ndarray) -> str:
        """
        Convert numpy embedding to JSON string for database storage.
        
        Args:
            embedding: Numpy array embedding
            
        Returns:
            JSON string representation of the embedding
        """
        try:
            return json.dumps(embedding.tolist())
        except Exception as e:
            logger.error(f"Error converting embedding to JSON: {e}")
            return "[]"
    
    def embedding_from_json(self, json_str: str) -> np.ndarray:
        """
        Convert JSON string back to numpy embedding.
        
        Args:
            json_str: JSON string representation of embedding
            
        Returns:
            Numpy array embedding
        """
        try:
            embedding_list = json.loads(json_str)
            return np.array(embedding_list)
        except Exception as e:
            logger.error(f"Error converting JSON to embedding: {e}")
            self._load_model()
            return np.zeros(self.embedding_dimension)
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current embedding model.
        
        Returns:
            Dictionary with model information
        """
        self._load_model()
        return {
            "model_name": self.model_name,
            "embedding_dimension": self.embedding_dimension,
            "max_seq_length": getattr(self.model, 'max_seq_length', 'Unknown'),
            "loaded": self.model is not None
        }
    
    def cleanup(self):
        """Clean up resources."""
        if self._executor:
            self._executor.shutdown(wait=True)
        logger.info("EmbeddingService cleaned up")

# Global instance for easy access
_embedding_service = None

def get_embedding_service(model_name: str = 'all-MiniLM-L6-v2') -> EmbeddingService:
    """
    Get or create the global embedding service instance.
    
    Args:
        model_name: Name of the sentence-transformers model to use
        
    Returns:
        EmbeddingService instance
    """
    global _embedding_service
    if _embedding_service is None or _embedding_service.model_name != model_name:
        _embedding_service = EmbeddingService(model_name)
    return _embedding_service

# Example usage and testing
if __name__ == '__main__':
    async def test_embedding_service():
        """Test the embedding service functionality."""
        import time
        
        print("🧪 Testing EmbeddingService...")
        
        # Initialize service
        service = EmbeddingService()
        
        # Test single text encoding
        print("\n1. Single text encoding:")
        job_description = """
        Senior Python Developer - Remote
        We are looking for an experienced Python developer to join our AI team.
        Requirements: 5+ years Python experience, machine learning background,
        experience with FastAPI, Docker, and cloud deployment.
        """
        
        start_time = time.time()
        embedding = service.encode_text(job_description)
        encode_time = time.time() - start_time
        
        print(f"   ✅ Generated embedding: shape {embedding.shape}")
        print(f"   ⏱️ Encoding time: {encode_time:.3f}s")
        
        # Test batch encoding
        print("\n2. Batch text encoding:")
        texts = [
            "Python developer with machine learning experience",
            "Frontend React developer needed",
            "Data scientist with Python and SQL skills"
        ]
        
        start_time = time.time()
        embeddings = service.encode_texts(texts)
        batch_time = time.time() - start_time
        
        print(f"   ✅ Generated {len(embeddings)} embeddings")
        print(f"   ⏱️ Batch time: {batch_time:.3f}s")
        
        # Test similarity calculation
        print("\n3. Similarity calculation:")
        resume_text = "Experienced Python developer with 6 years in machine learning and AI"
        resume_embedding = service.encode_text(resume_text)
        
        similarity = service.calculate_similarity(embedding, resume_embedding)
        print(f"   ✅ Job-Resume similarity: {similarity:.3f}")
        
        # Test JSON serialization
        print("\n4. JSON serialization:")
        json_embedding = service.embedding_to_json(embedding)
        restored_embedding = service.embedding_from_json(json_embedding)
        
        restoration_similarity = service.calculate_similarity(embedding, restored_embedding)
        print(f"   ✅ Serialization preservation: {restoration_similarity:.6f}")
        
        # Test async operations
        print("\n5. Async operations:")
        start_time = time.time()
        async_embedding = await service.encode_text_async(job_description)
        async_time = time.time() - start_time
        
        async_similarity = service.calculate_similarity(embedding, async_embedding)
        print(f"   ✅ Async vs sync similarity: {async_similarity:.6f}")
        print(f"   ⏱️ Async time: {async_time:.3f}s")
        
        # Model info
        print("\n6. Model information:")
        model_info = service.get_model_info()
        for key, value in model_info.items():
            print(f"   {key}: {value}")
        
        service.cleanup()
        print("\n🎉 All tests completed successfully!")
    
    # Run tests
    asyncio.run(test_embedding_service()) 