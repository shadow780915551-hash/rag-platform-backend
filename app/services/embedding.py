"""
Embedding Service Module

This module handles text embedding using Sentence Transformers for semantic search.
"""

from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Union
import pickle
from app.core.config import get_settings
from loguru import logger

settings = get_settings()


class EmbeddingService:
    """
    Service for generating text embeddings using Sentence Transformers.
    
    This service provides methods to encode text into vector embeddings
    for semantic search and similarity matching.
    """
    
    def __init__(self, model_name: str = None):
        """
        Initialize the embedding service.
        
        Args:
            model_name: Name of the Sentence Transformer model to use
        """
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """
        Load the Sentence Transformer model.
        """
        try:
            logger.info(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            logger.info("Embedding model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise
    
    def encode_text(
        self,
        text: Union[str, List[str]],
        batch_size: int = 32,
        show_progress: bool = False
    ) -> np.ndarray:
        """
        Encode text into embeddings.
        
        Args:
            text: Single text string or list of text strings
            batch_size: Batch size for encoding
            show_progress: Whether to show progress bar
            
        Returns:
            np.ndarray: Text embeddings
        """
        if self.model is None:
            raise RuntimeError("Model not loaded")
        
        if isinstance(text, str):
            text = [text]
        
        try:
            embeddings = self.model.encode(
                text,
                batch_size=batch_size,
                show_progress_bar=show_progress,
                convert_to_numpy=True
            )
            return embeddings
        except Exception as e:
            logger.error(f"Failed to encode text: {e}")
            raise
    
    def encode_single(self, text: str) -> np.ndarray:
        """
        Encode a single text string into embedding.
        
        Args:
            text: Text string to encode
            
        Returns:
            np.ndarray: Text embedding
        """
        return self.encode_text(text)[0]
    
    def get_embedding_dimension(self) -> int:
        """
        Get the dimension of the embedding vectors.
        
        Returns:
            int: Embedding dimension
        """
        if self.model is None:
            raise RuntimeError("Model not loaded")
        
        # Get dimension by encoding a dummy text
        dummy_embedding = self.encode_single("test")
        return dummy_embedding.shape[0]
    
    def save_embedding(self, embedding: np.ndarray, filepath: str) -> None:
        """
        Save an embedding to a file.
        
        Args:
            embedding: Embedding to save
            filepath: Path to save the embedding
        """
        try:
            with open(filepath, 'wb') as f:
                pickle.dump(embedding, f)
            logger.info(f"Embedding saved to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save embedding: {e}")
            raise
    
    def load_embedding(self, filepath: str) -> np.ndarray:
        """
        Load an embedding from a file.
        
        Args:
            filepath: Path to load the embedding from
            
        Returns:
            np.ndarray: Loaded embedding
        """
        try:
            with open(filepath, 'rb') as f:
                embedding = pickle.load(f)
            logger.info(f"Embedding loaded from {filepath}")
            return embedding
        except Exception as e:
            logger.error(f"Failed to load embedding: {e}")
            raise


# Global embedding service instance
_embedding_service = None


def get_embedding_service() -> EmbeddingService:
    """
    Get or create the global embedding service instance.
    
    Returns:
        EmbeddingService: Global embedding service instance
    """
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
