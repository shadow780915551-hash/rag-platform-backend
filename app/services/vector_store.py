"""
Vector Store Service Module

This module handles FAISS vector store for efficient similarity search.
"""

import faiss
import numpy as np
import pickle
import os
from typing import List, Tuple, Optional
from app.core.config import get_settings
from loguru import logger

settings = get_settings()


class VectorStoreService:
    """
    Service for managing FAISS vector stores for similarity search.
    
    This service provides methods to create, update, and search FAISS indexes
    for efficient vector similarity search.
    """
    
    def __init__(self, index_type: str = None, dimension: int = None):
        """
        Initialize the vector store service.
        
        Args:
            index_type: Type of FAISS index (flat, ivf, hnsw)
            dimension: Dimension of the vectors
        """
        self.index_type = index_type or settings.FAISS_INDEX_TYPE
        self.dimension = dimension
        self.index = None
        self.documents = []  # Store document metadata
        self._initialize_index()
    
    def _initialize_index(self):
        """
        Initialize the FAISS index based on the specified type.
        """
        if self.dimension is None:
            raise ValueError("Dimension must be specified to initialize index")
        
        if self.index_type == "flat":
            # Flat index (exact search)
            self.index = faiss.IndexFlatL2(self.dimension)
            logger.info(f"Initialized Flat L2 index with dimension {self.dimension}")
        
        elif self.index_type == "ivf":
            # IVF (Inverted File) index for faster search
            quantizer = faiss.IndexFlatL2(self.dimension)
            nlist = 100  # Number of clusters
            self.index = faiss.IndexIVFFlat(quantizer, self.dimension, nlist)
            logger.info(f"Initialized IVF index with dimension {self.dimension}")
        
        elif self.index_type == "hnsw":
            # HNSW (Hierarchical Navigable Small World) index
            self.index = faiss.IndexHNSWFlat(self.dimension, 32)
            logger.info(f"Initialized HNSW index with dimension {self.dimension}")
        
        else:
            raise ValueError(f"Unsupported index type: {self.index_type}")
    
    def add_vectors(self, vectors: np.ndarray, document_ids: List[int]) -> None:
        """
        Add vectors to the index.
        
        Args:
            vectors: Array of vectors to add
            document_ids: List of document IDs corresponding to vectors
        """
        if self.index is None:
            raise RuntimeError("Index not initialized")
        
        try:
            # Train index if needed (for IVF)
            if self.index_type == "ivf" and not self.index.is_trained:
                self.index.train(vectors)
            
            # Add vectors to index
            self.index.add(vectors.astype('float32'))
            
            # Store document metadata
            for doc_id in document_ids:
                self.documents.append(doc_id)
            
            logger.info(f"Added {len(vectors)} vectors to index")
        except Exception as e:
            logger.error(f"Failed to add vectors to index: {e}")
            raise
    
    def search(
        self,
        query_vector: np.ndarray,
        k: int = 10
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for similar vectors.
        
        Args:
            query_vector: Query vector
            k: Number of results to return
            
        Returns:
            Tuple[np.ndarray, np.ndarray]: (distances, indices)
        """
        if self.index is None:
            raise RuntimeError("Index not initialized")
        
        try:
            # Reshape query vector if needed
            if len(query_vector.shape) == 1:
                query_vector = query_vector.reshape(1, -1)
            
            # Search
            distances, indices = self.index.search(query_vector.astype('float32'), k)
            
            return distances, indices
        except Exception as e:
            logger.error(f"Failed to search index: {e}")
            raise
    
    def save_index(self, filepath: str) -> None:
        """
        Save the index to disk.
        
        Args:
            filepath: Path to save the index
        """
        try:
            # Save index
            faiss.write_index(self.index, filepath)
            
            # Save documents metadata
            metadata_path = filepath.replace('.index', '_metadata.pkl')
            with open(metadata_path, 'wb') as f:
                pickle.dump(self.documents, f)
            
            logger.info(f"Index saved to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save index: {e}")
            raise
    
    def load_index(self, filepath: str) -> None:
        """
        Load an index from disk.
        
        Args:
            filepath: Path to load the index from
        """
        try:
            # Load index
            self.index = faiss.read_index(filepath)
            
            # Load documents metadata
            metadata_path = filepath.replace('.index', '_metadata.pkl')
            if os.path.exists(metadata_path):
                with open(metadata_path, 'rb') as f:
                    self.documents = pickle.load(f)
            
            logger.info(f"Index loaded from {filepath}")
        except Exception as e:
            logger.error(f"Failed to load index: {e}")
            raise
    
    def get_document_id(self, index: int) -> Optional[int]:
        """
        Get document ID for a given index.
        
        Args:
            index: Index in the vector store
            
        Returns:
            Optional[int]: Document ID or None if not found
        """
        if 0 <= index < len(self.documents):
            return self.documents[index]
        return None
    
    def get_size(self) -> int:
        """
        Get the number of vectors in the index.
        
        Returns:
            int: Number of vectors
        """
        if self.index is None:
            return 0
        return self.index.ntotal


# Global vector store instances
_vector_stores = {}


def get_vector_store(document_id: int, dimension: int) -> VectorStoreService:
    """
    Get or create a vector store for a specific document.
    
    Args:
        document_id: Document ID
        dimension: Vector dimension
        
    Returns:
        VectorStoreService: Vector store instance
    """
    global _vector_stores
    
    if document_id not in _vector_stores:
        _vector_stores[document_id] = VectorStoreService(dimension=dimension)
    
    return _vector_stores[document_id]
