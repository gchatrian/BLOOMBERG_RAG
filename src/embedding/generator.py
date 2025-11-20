"""
Embedding Generator for Bloomberg RAG System.

Uses sentence-transformers to generate semantic embeddings from text.
Supports both single and batch processing with automatic optimization.
"""

import logging
import numpy as np
from typing import List, Union, Optional
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """
    Generate semantic embeddings using sentence-transformers.
    
    Uses a multilingual model to support both Italian and English queries.
    Implements lazy loading and batch processing for efficiency.
    
    Attributes:
        model_name: Name of the sentence-transformers model to use
        model: Loaded SentenceTransformer instance (lazy loaded)
        embedding_dim: Dimension of output embeddings (384 for default model)
    """
    
    # Default model: multilingual, good performance, 384 dimensions
    DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    
    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize the embedding generator.
        
        Args:
            model_name: Optional custom model name. If None, uses DEFAULT_MODEL.
                       Must be a valid sentence-transformers model.
        
        Note:
            The model is not loaded until first use (lazy loading) to save memory.
        """
        self.model_name = model_name or self.DEFAULT_MODEL
        self._model: Optional[SentenceTransformer] = None
        self._embedding_dim: Optional[int] = None
        
        logger.info(f"EmbeddingGenerator initialized with model: {self.model_name}")
    
    @property
    def model(self) -> SentenceTransformer:
        """
        Get the loaded model, loading it if necessary (lazy loading).
        
        Returns:
            Loaded SentenceTransformer instance
            
        Raises:
            RuntimeError: If model loading fails
        """
        if self._model is None:
            try:
                logger.info(f"Loading embedding model: {self.model_name}")
                self._model = SentenceTransformer(self.model_name)
                logger.info("Model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load model {self.model_name}: {e}")
                raise RuntimeError(f"Could not load embedding model: {e}")
        
        return self._model
    
    def get_embedding_dimension(self) -> int:
        """
        Get the dimension of embeddings produced by this model.
        
        Returns:
            Embedding dimension (e.g., 384 for default model)
            
        Note:
            This triggers model loading if not already loaded.
        """
        if self._embedding_dim is None:
            # Get dimension from model
            self._embedding_dim = self.model.get_sentence_embedding_dimension()
            logger.debug(f"Embedding dimension: {self._embedding_dim}")
        
        return self._embedding_dim
    
    def generate_embeddings(
        self, 
        texts: List[str],
        batch_size: int = 32,
        show_progress: bool = True
    ) -> np.ndarray:
        """
        Generate embeddings for multiple texts using batch processing.
        
        Args:
            texts: List of text strings to embed
            batch_size: Number of texts to process in each batch (default: 32)
            show_progress: Whether to show progress bar during encoding
            
        Returns:
            numpy array of shape (len(texts), embedding_dim) with float32 dtype
            
        Raises:
            ValueError: If texts list is empty
            RuntimeError: If encoding fails
            
        Example:
            >>> generator = EmbeddingGenerator()
            >>> texts = ["First document", "Second document"]
            >>> embeddings = generator.generate_embeddings(texts)
            >>> embeddings.shape
            (2, 384)
        """
        if not texts:
            raise ValueError("Cannot generate embeddings for empty text list")
        
        # Filter out empty strings and log warning
        valid_texts = [t for t in texts if t and t.strip()]
        if len(valid_texts) < len(texts):
            logger.warning(
                f"Filtered out {len(texts) - len(valid_texts)} empty/whitespace texts"
            )
        
        if not valid_texts:
            raise ValueError("All texts are empty or whitespace")
        
        try:
            logger.info(f"Generating embeddings for {len(valid_texts)} texts (batch_size={batch_size})")
            
            # Generate embeddings with batch processing
            embeddings = self.model.encode(
                valid_texts,
                batch_size=batch_size,
                show_progress_bar=show_progress,
                convert_to_numpy=True,
                normalize_embeddings=False  # We'll normalize manually for consistency
            )
            
            # Ensure float32 dtype for FAISS compatibility
            embeddings = embeddings.astype(np.float32)
            
            # Normalize embeddings (L2 normalization)
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            embeddings = embeddings / (norms + 1e-8)  # Add epsilon to avoid division by zero
            
            logger.info(f"Successfully generated {len(embeddings)} embeddings")
            logger.debug(f"Embedding shape: {embeddings.shape}, dtype: {embeddings.dtype}")
            
            return embeddings
            
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            raise RuntimeError(f"Embedding generation failed: {e}")
    
    def generate_single_embedding(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text string to embed
            
        Returns:
            numpy array of shape (embedding_dim,) with float32 dtype
            
        Raises:
            ValueError: If text is empty or whitespace
            RuntimeError: If encoding fails
            
        Example:
            >>> generator = EmbeddingGenerator()
            >>> query = "What happened in the tech sector?"
            >>> embedding = generator.generate_single_embedding(query)
            >>> embedding.shape
            (384,)
        """
        if not text or not text.strip():
            raise ValueError("Cannot generate embedding for empty text")
        
        try:
            logger.debug(f"Generating embedding for single text (length: {len(text)})")
            
            # Use batch method with single item (more efficient than separate implementation)
            embeddings = self.generate_embeddings(
                [text],
                batch_size=1,
                show_progress=False
            )
            
            # Return first (and only) embedding
            return embeddings[0]
            
        except Exception as e:
            logger.error(f"Failed to generate single embedding: {e}")
            raise RuntimeError(f"Single embedding generation failed: {e}")
    
    def __repr__(self) -> str:
        """String representation of the generator."""
        loaded = "loaded" if self._model is not None else "not loaded"
        return f"EmbeddingGenerator(model={self.model_name}, status={loaded})"