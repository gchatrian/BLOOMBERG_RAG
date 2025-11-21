"""
FAISS Vector Store for Bloomberg RAG System.

Wrapper around FAISS IndexFlatL2 for efficient semantic search.
Handles vector addition, search, and persistence.
"""

import logging
import numpy as np
import faiss
from typing import Tuple, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class FAISSVectorStore:
    """
    FAISS-based vector store for semantic search.
    
    Uses IndexFlatL2 for exact L2 distance search. Supports incremental
    addition of vectors and persistence to disk.
    
    Attributes:
        dimension: Dimension of vectors (e.g., 384)
        index: FAISS index instance
    """
    
    def __init__(self, dimension: int):
        """
        Initialize FAISS vector store.
        
        Args:
            dimension: Dimension of embedding vectors (must match model output)
            
        Raises:
            ValueError: If dimension is not positive
        """
        if dimension <= 0:
            raise ValueError(f"Dimension must be positive, got {dimension}")
        
        self.dimension = dimension
        self.index: Optional[faiss.IndexFlatL2] = None
        
        # Initialize empty index
        self._initialize_index()
        
        logger.info(f"FAISSVectorStore initialized with dimension {dimension}")
    
    def _initialize_index(self):
        """
        Initialize or reset FAISS index.
        
        Creates a new IndexFlatL2 for exact L2 distance search.
        """
        self.index = faiss.IndexFlatL2(self.dimension)
        logger.debug(f"Created new FAISS IndexFlatL2 (dim={self.dimension})")
    
    def add_vectors(self, embeddings: np.ndarray) -> int:
        """
        Add vectors to the index.
        
        Args:
            embeddings: numpy array of shape (n_vectors, dimension) or (dimension,)
                       Must be float32 dtype and normalized.
            
        Returns:
            Number of vectors added
            
        Raises:
            ValueError: If embeddings shape or dtype is invalid
            RuntimeError: If adding to index fails
            
        Example:
            >>> store = FAISSVectorStore(dimension=384)
            >>> vectors = np.random.randn(10, 384).astype(np.float32)
            >>> count = store.add_vectors(vectors)
            >>> print(count)
            10
        """
        # Handle single vector (1D array)
        if embeddings.ndim == 1:
            embeddings = embeddings.reshape(1, -1)
        
        # Validate shape
        if embeddings.ndim != 2:
            raise ValueError(f"Embeddings must be 2D array, got shape {embeddings.shape}")
        
        if embeddings.shape[1] != self.dimension:
            raise ValueError(
                f"Embedding dimension {embeddings.shape[1]} does not match "
                f"index dimension {self.dimension}"
            )
        
        # Validate dtype
        if embeddings.dtype != np.float32:
            logger.warning(
                f"Converting embeddings from {embeddings.dtype} to float32"
            )
            embeddings = embeddings.astype(np.float32)
        
        # Add to index
        try:
            n_vectors = len(embeddings)
            old_size = self.get_index_size()
            
            self.index.add(embeddings)
            
            new_size = self.get_index_size()
            logger.info(f"Added {n_vectors} vectors to index (size: {old_size} to {new_size})")
            
            return n_vectors
            
        except Exception as e:
            logger.error(f"Failed to add vectors to index: {e}")
            raise RuntimeError(f"Could not add vectors to FAISS index: {e}")
    
    def search(
        self, 
        query_vector: np.ndarray, 
        k: int = 5
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors of query vector.
        
        Args:
            query_vector: Query embedding of shape (dimension,) or (1, dimension)
            k: Number of nearest neighbors to return
            
        Returns:
            Tuple of (distances, indices):
                - distances: numpy array of shape (k,) with L2 distances
                - indices: numpy array of shape (k,) with vector IDs
                
        Raises:
            ValueError: If query_vector shape is invalid or k is invalid
            RuntimeError: If index is empty or search fails
            
        Example:
            >>> distances, indices = store.search(query_vector, k=5)
            >>> print(f"Top result ID: {indices[0]}, distance: {distances[0]}")
        """
        # Validate k
        if k <= 0:
            raise ValueError(f"k must be positive, got {k}")
        
        index_size = self.get_index_size()
        if index_size == 0:
            raise RuntimeError("Cannot search in empty index")
        
        # Limit k to index size
        k = min(k, index_size)
        
        # Handle single vector (1D array)
        if query_vector.ndim == 1:
            query_vector = query_vector.reshape(1, -1)
        
        # Validate shape
        if query_vector.shape != (1, self.dimension):
            raise ValueError(
                f"Query vector must have shape (1, {self.dimension}), "
                f"got {query_vector.shape}"
            )
        
        # Validate dtype
        if query_vector.dtype != np.float32:
            logger.debug("Converting query vector to float32")
            query_vector = query_vector.astype(np.float32)
        
        try:
            # Search returns (distances, indices) each of shape (n_queries, k)
            distances, indices = self.index.search(query_vector, k)
            
            # Return flattened arrays (we only have 1 query)
            distances = distances[0]  # Shape: (k,)
            indices = indices[0]      # Shape: (k,)
            
            logger.debug(f"Search returned {len(indices)} results (k={k})")
            
            return distances, indices
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise RuntimeError(f"FAISS search failed: {e}")
    
    def get_index_size(self) -> int:
        """
        Get the number of vectors currently in the index.
        
        Returns:
            Number of indexed vectors
        """
        return self.index.ntotal
    
    def is_empty(self) -> bool:
        """
        Check if index is empty.
        
        Returns:
            True if index contains no vectors
        """
        return self.get_index_size() == 0
    
    def save(self, path: str):
        """
        Save index to disk.
        
        Args:
            path: File path to save index (will create parent dirs if needed)
            
        Raises:
            RuntimeError: If save fails
            
        Example:
            >>> store.save("data/faiss_index.bin")
        """
        try:
            # Ensure parent directory exists
            path_obj = Path(path)
            path_obj.parent.mkdir(parents=True, exist_ok=True)
            
            # Save index
            faiss.write_index(self.index, str(path))
            
            logger.info(f"Saved FAISS index to {path} ({self.get_index_size()} vectors)")
            
        except Exception as e:
            logger.error(f"Failed to save index to {path}: {e}")
            raise RuntimeError(f"Could not save FAISS index: {e}")
    
    @classmethod
    def load(cls, path: str, dimension: int) -> 'FAISSVectorStore':
        """
        Load index from disk.
        
        Args:
            path: File path to load index from
            dimension: Expected dimension of vectors (for validation)
            
        Returns:
            Loaded FAISSVectorStore instance
            
        Raises:
            FileNotFoundError: If index file doesn't exist
            ValueError: If loaded index dimension doesn't match expected
            RuntimeError: If load fails
            
        Example:
            >>> store = FAISSVectorStore.load("data/faiss_index.bin", dimension=384)
        """
        path_obj = Path(path)
        
        if not path_obj.exists():
            raise FileNotFoundError(f"Index file not found: {path}")
        
        try:
            # Load index
            index = faiss.read_index(str(path))
            
            # Validate dimension
            if index.d != dimension:
                raise ValueError(
                    f"Loaded index dimension {index.d} does not match "
                    f"expected dimension {dimension}"
                )
            
            # Create instance and assign loaded index
            store = cls(dimension)
            store.index = index
            
            logger.info(f"Loaded FAISS index from {path} ({store.get_index_size()} vectors)")
            
            return store
            
        except Exception as e:
            logger.error(f"Failed to load index from {path}: {e}")
            raise RuntimeError(f"Could not load FAISS index: {e}")
    
    def reset(self):
        """
        Reset index to empty state.
        
        Warning: This will delete all vectors from the index!
        """
        old_size = self.get_index_size()
        self._initialize_index()
        logger.warning(f"Reset index (deleted {old_size} vectors)")
    
    def __repr__(self) -> str:
        """String representation of the vector store."""
        size = self.get_index_size()
        return f"FAISSVectorStore(dimension={self.dimension}, size={size})"