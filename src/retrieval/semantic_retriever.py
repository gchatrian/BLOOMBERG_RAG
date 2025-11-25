"""
Semantic Retriever for Bloomberg RAG System.

Provides semantic search over email documents using FAISS vector store.
Handles query embedding, similarity search, score normalization, and result formatting.
"""

import logging
import numpy as np
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

from src.models import EmailDocument
from src.embedding import EmbeddingGenerator
from src.vectorstore import FAISSVectorStore, MetadataMapper

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """
    Represents a single search result.
    
    Attributes:
        document: Full EmailDocument (or dict from JSON)
        score: Normalized similarity score (0-1, higher is better)
        distance: Raw L2 distance from FAISS
        rank: Position in results (1-indexed)
        metadata_preview: Quick access to key metadata
    """
    document: Any  # EmailDocument or dict
    score: float
    distance: float
    rank: int
    metadata_preview: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (excluding full document for brevity)."""
        # Handle both EmailDocument and dict
        if isinstance(self.document, dict):
            subject = self.document.get('subject', 'Unknown')
            date = self.document.get('received_date', 'Unknown')
        else:
            subject = self.document.subject
            date = self.document.received_date
        
        return {
            'rank': self.rank,
            'score': round(self.score, 4),
            'distance': round(self.distance, 4),
            'subject': subject,
            'date': date,
            'metadata': self.metadata_preview
        }
    
    def format_preview(self, content_length: int = 200) -> str:
        """
        Format result as preview string.
        
        Args:
            content_length: Maximum content preview length
            
        Returns:
            Formatted string with rank, score, subject, date, and preview
        """
        # Handle both EmailDocument and dict
        if isinstance(self.document, dict):
            subject = self.document.get('subject', 'Unknown')
            body = self.document.get('body', '')
            bloomberg_metadata = self.document.get('bloomberg_metadata', {})
            received_date = self.document.get('received_date')
            
            # Get article date from bloomberg_metadata
            if isinstance(bloomberg_metadata, dict):
                article_date = bloomberg_metadata.get('article_date')
            else:
                article_date = None
        else:
            subject = self.document.subject
            body = self.document.body
            bloomberg_metadata = self.document.bloomberg_metadata
            received_date = self.document.received_date
            article_date = bloomberg_metadata.article_date if bloomberg_metadata else None
        
        # Format date
        date_str = "Unknown"
        if article_date:
            if isinstance(article_date, str):
                date_str = article_date[:10]  # ISO format YYYY-MM-DD
            else:
                date_str = article_date.strftime("%Y-%m-%d")
        elif received_date:
            if isinstance(received_date, str):
                date_str = received_date[:10]
            else:
                date_str = received_date.strftime("%Y-%m-%d")
        
        # Truncate content
        content = body[:content_length] if body else ''
        if len(body) > content_length:
            content += "..."
        
        # Build preview
        preview = f"[{self.rank}] Score: {self.score:.3f} | {subject}\n"
        preview += f"    Date: {date_str}\n"
        
        # Add topics if available
        if self.metadata_preview.get('topics'):
            topics_str = ", ".join(self.metadata_preview['topics'][:3])
            preview += f"    Topics: {topics_str}\n"
        
        # Add people if available
        if self.metadata_preview.get('people'):
            people_str = ", ".join(self.metadata_preview['people'][:3])
            preview += f"    People: {people_str}\n"
        
        preview += f"    Preview: {content}\n"
        
        return preview


class SemanticRetriever:
    """
    Semantic search over email documents.
    
    Combines embedding generation, FAISS vector search, and metadata retrieval
    to provide ranked search results with normalized scores.
    
    Attributes:
        embedding_generator: EmbeddingGenerator instance
        vector_store: FAISSVectorStore instance
        metadata_mapper: MetadataMapper instance
    """
    
    def __init__(
        self,
        embedding_generator: EmbeddingGenerator,
        vector_store: FAISSVectorStore,
        metadata_mapper: MetadataMapper
    ):
        """
        Initialize semantic retriever.
        
        Args:
            embedding_generator: Initialized EmbeddingGenerator
            vector_store: Initialized FAISSVectorStore with indexed documents
            metadata_mapper: Initialized MetadataMapper with document metadata
            
        Raises:
            TypeError: If any component has wrong type
            RuntimeError: If vector store is empty
        """
        if not isinstance(embedding_generator, EmbeddingGenerator):
            raise TypeError("embedding_generator must be EmbeddingGenerator instance")
        
        if not isinstance(vector_store, FAISSVectorStore):
            raise TypeError("vector_store must be FAISSVectorStore instance")
        
        if not isinstance(metadata_mapper, MetadataMapper):
            raise TypeError("metadata_mapper must be MetadataMapper instance")
        
        if vector_store.is_empty():
            raise RuntimeError("Cannot initialize retriever with empty vector store")
        
        # Check consistency
        if vector_store.get_index_size() != metadata_mapper.size():
            logger.warning(
                f"Size mismatch: vector store has {vector_store.get_index_size()} vectors, "
                f"metadata mapper has {metadata_mapper.size()} documents"
            )
        
        self.embedding_generator = embedding_generator
        self.vector_store = vector_store
        self.metadata_mapper = metadata_mapper
        
        logger.info(
            f"SemanticRetriever initialized with {vector_store.get_index_size()} documents"
        )
    
    def _normalize_distances(self, distances: np.ndarray) -> np.ndarray:
        """
        Convert L2 distances to normalized similarity scores (0-1).
        
        Uses formula: score = 1 / (1 + distance)
        This maps distance 0 -> score 1, and larger distances -> smaller scores.
        
        Args:
            distances: Array of L2 distances from FAISS
            
        Returns:
            Array of similarity scores in [0, 1]
        """
        return 1 / (1 + distances)
    
    def _get_metadata_preview(self, document: Any) -> Dict[str, Any]:
        """
        Extract key metadata from document for quick access.
        
        Args:
            document: EmailDocument or dict
            
        Returns:
            Dictionary with key metadata fields
        """
        # Handle both EmailDocument and dict (from JSON)
        if isinstance(document, dict):
            bloomberg_metadata = document.get('bloomberg_metadata', {})
            if isinstance(bloomberg_metadata, dict):
                return {
                    'author': bloomberg_metadata.get('author'),
                    'category': bloomberg_metadata.get('category'),
                    'topics': bloomberg_metadata.get('topics', []),
                    'people': bloomberg_metadata.get('people', []),
                    'tickers': bloomberg_metadata.get('tickers', []),
                    'story_id': bloomberg_metadata.get('story_id')
                }
            return {}
        else:
            # EmailDocument object
            if document.bloomberg_metadata:
                return {
                    'author': document.bloomberg_metadata.author,
                    'category': document.bloomberg_metadata.category,
                    'topics': document.bloomberg_metadata.topics or [],
                    'people': document.bloomberg_metadata.people or [],
                    'tickers': document.bloomberg_metadata.tickers or [],
                    'story_id': document.bloomberg_metadata.story_id
                }
            return {}
    
    def search(
        self,
        query: str,
        top_k: int = 5
    ) -> List[SearchResult]:
        """
        Perform semantic search.
        
        Args:
            query: Search query string
            top_k: Number of results to return (default: 5)
            
        Returns:
            List of SearchResult objects sorted by score (highest first)
            
        Raises:
            ValueError: If query is empty or top_k <= 0
            RuntimeError: If search fails
            
        Example:
            >>> results = retriever.search("Federal Reserve interest rates", top_k=10)
            >>> for result in results:
            ...     print(f"{result.document.subject} (score: {result.score:.3f})")
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
        
        if top_k <= 0:
            raise ValueError(f"top_k must be positive, got {top_k}")
        
        logger.info(f"Searching for: '{query}' (top_k={top_k})")
        
        try:
            # Step 1: Generate query embedding
            query_embedding = self.embedding_generator.generate_single_embedding(query)
            logger.debug(f"Generated query embedding: shape={query_embedding.shape}")
            
            # Step 2: Search FAISS
            distances, indices = self.vector_store.search(query_embedding, k=top_k)
            logger.debug(f"FAISS search returned {len(indices)} results")
            
            # Step 3: Normalize distances to scores
            scores = self._normalize_distances(distances)
            
            # Step 4: Retrieve documents and format results
            results = []
            for rank, (idx, score, distance) in enumerate(zip(indices, scores, distances), 1):
                # Get document from metadata mapper
                document = self.metadata_mapper.get_document(int(idx))
                
                if document is None:
                    logger.warning(f"No document found for vector ID {idx}, skipping")
                    continue
                
                # Create metadata preview
                metadata_preview = self._get_metadata_preview(document)
                
                # Create SearchResult
                result = SearchResult(
                    document=document,
                    score=float(score),
                    distance=float(distance),
                    rank=rank,
                    metadata_preview=metadata_preview
                )
                
                results.append(result)
            
            logger.info(f"Search complete: returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise RuntimeError(f"Semantic search failed: {e}")
    
    def get_index_stats(self) -> Dict[str, Any]:
        """
        Get statistics about indexed documents.
        
        Returns:
            Dictionary with stats:
                - total_documents: int
                - embedding_dimension: int
        """
        stats = {
            'total_documents': self.vector_store.get_index_size(),
            'embedding_dimension': self.vector_store.dimension
        }
        
        return stats
    
    def format_results(
        self,
        results: List[SearchResult],
        content_length: int = 200
    ) -> str:
        """
        Format search results as readable string.
        
        Args:
            results: List of SearchResult objects
            content_length: Maximum content preview length per result
            
        Returns:
            Formatted string with all results
        """
        if not results:
            return "No results found."
        
        output = f"\nSearch Results ({len(results)} documents):\n"
        output += "=" * 80 + "\n\n"
        
        for result in results:
            output += result.format_preview(content_length)
            output += "\n" + "-" * 80 + "\n\n"
        
        return output
    
    def __repr__(self) -> str:
        """String representation of the retriever."""
        return (
            f"SemanticRetriever("
            f"documents={self.vector_store.get_index_size()}, "
            f"dimension={self.vector_store.dimension})"
        )