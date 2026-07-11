"""
Re-ranking Service Module

This module handles cross-encoder re-ranking for improved search results.
"""

from sentence_transformers import CrossEncoder
import numpy as np
from typing import List, Tuple, Dict
from app.core.config import get_settings
from loguru import logger

settings = get_settings()


class ReRankerService:
    """
    Service for re-ranking search results using Cross-Encoder models.
    
    This service provides methods to re-rank search results based on
    query-document relevance scores from a cross-encoder model.
    """
    
    def __init__(self, model_name: str = None):
        """
        Initialize the re-ranking service.
        
        Args:
            model_name: Name of the Cross-Encoder model to use
        """
        self.model_name = model_name or settings.CROSS_ENCODER_MODEL
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """
        Load the Cross-Encoder model.
        """
        try:
            logger.info(f"Loading cross-encoder model: {self.model_name}")
            self.model = CrossEncoder(self.model_name)
            logger.info("Cross-encoder model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load cross-encoder model: {e}")
            raise
    
    def rerank(
        self,
        query: str,
        documents: List[str],
        top_k: int = None
    ) -> List[Tuple[int, float]]:
        """
        Re-rank documents based on query relevance.
        
        Args:
            query: Search query
            documents: List of document texts
            top_k: Number of top results to return
            
        Returns:
            List[Tuple[int, float]]: List of (index, score) tuples sorted by score
        """
        if self.model is None:
            raise RuntimeError("Model not loaded")
        
        if not documents:
            return []
        
        try:
            # Create query-document pairs
            pairs = [[query, doc] for doc in documents]
            
            # Predict relevance scores
            scores = self.model.predict(pairs)
            
            # Sort by score
            ranked_indices = np.argsort(scores)[::-1]
            
            # Return top-k results
            if top_k:
                ranked_indices = ranked_indices[:top_k]
            
            results = [(int(idx), float(scores[idx])) for idx in ranked_indices]
            return results
        
        except Exception as e:
            logger.error(f"Failed to re-rank documents: {e}")
            raise
    
    def rerank_with_metadata(
        self,
        query: str,
        documents: List[Dict],
        text_field: str = "text",
        top_k: int = None
    ) -> List[Dict]:
        """
        Re-rank documents with metadata.
        
        Args:
            query: Search query
            documents: List of document dictionaries
            text_field: Field name containing the text
            top_k: Number of top results to return
            
        Returns:
            List[Dict]: Re-ranked documents with relevance scores
        """
        if not documents:
            return []
        
        # Extract texts
        texts = [doc.get(text_field, "") for doc in documents]
        
        # Re-rank
        ranked_results = self.rerank(query, texts, top_k)
        
        # Reconstruct documents with scores
        reranked_docs = []
        for idx, score in ranked_results:
            doc = documents[idx].copy()
            doc["relevance_score"] = score
            reranked_docs.append(doc)
        
        return reranked_docs


# Global re-ranker service instance
_reranker_service = None


def get_reranker_service() -> ReRankerService:
    """
    Get or create the global re-ranker service instance.
    
    Returns:
        ReRankerService: Global re-ranker service instance
    """
    global _reranker_service
    if _reranker_service is None:
        _reranker_service = ReRankerService()
    return _reranker_service
