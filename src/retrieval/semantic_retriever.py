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
        document: Full EmailDocument
        score: Normalized similarity score (0-1, higher is better)
        distance: Raw L2 distance from FAISS
        rank: Position in results (1-indexed)
        metadata_preview: Quick access to key metadata
    """
    document: EmailDocument
    score: float
    distance: float
    rank: int
    metadata_preview: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (excluding full document for brevity)."""
        return {
            'rank': self.rank,
            'score': round(self.score, 4),
            'distance': round(self.distance, 4),
            'subject': self.document.subject,
            'date': self.document.received_time,
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
        # Format date
        date_str = "Unknown"
        if self.document.metadata and self.document.metadata.article_date:
            date_str = self.document.metadata.article_date.strftime("%Y-%m-%d")
        elif self.document.received_time:
            date_str = self.document.received_time.strftime("%Y-%m-%d")
        
        # Truncate content
        content = self.document.body[:content_length]
        if len(self.document.body) > content_length:
            content += "..."
        
        # Build preview
        preview = f"[{self.rank}] Score: {self.score:.3f} | {self.document.subject}\n"
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
        if vector_store.get_index_size() != metadata_mapper.get_size():
            logger.warning(
                f"Size mismatch: vector store has {vector_store.get_index_size()} vectors, "
                f"metadata mapper has {metadata_mapper.get_size()} documents"
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
        
        Uses inverse normalization: score = 1 / (1 + distance)
        This ensures:
        - distance=0 -> score=1.0 (perfect match)
        - distance=inf -> score=0.0 (no match)
        
        Args:
            distances: Array of L2 distances from FAISS
            
        Returns:
            Array of normalized scores (0-1, higher is better)
        """
        # Inverse normalization
        scores = 1.0 / (1.0 + distances)
        
        logger.debug(
            f"Normalized distances: "
            f"min_dist={distances.min():.3f} -> max_score={scores.max():.3f}, "
            f"max_dist={distances.max():.3f} -> min_score={scores.min():.3f}"
        )
        
        return scores
    
    def _get_metadata_preview(self, document: EmailDocument) -> Dict[str, Any]:
        """
        Extract key metadata for quick preview.
        
        Args:
            document: EmailDocument instance
            
        Returns:
            Dictionary with preview metadata (topics, people, author, category)
        """
        preview = {}
        
        if document.metadata:
            if document.metadata.topics:
                preview['topics'] = document.metadata.topics
            if document.metadata.people:
                preview['people'] = document.metadata.people
            if document.metadata.author:
                preview['author'] = document.metadata.author
            if document.metadata.category:
                preview['category'] = document.metadata.category
        
        return preview
    
    def search(
        self,
        query: str,
        top_k: int = 5
    ) -> List[SearchResult]:
        """
        Perform semantic search for query.
        
        Complete pipeline:
        1. Generate query embedding
        2. Search FAISS for top-K nearest neighbors
        3. Normalize distances to similarity scores
        4. Retrieve document metadata
        5. Format as SearchResult objects
        
        Args:
            query: Search query string
            top_k: Number of results to return (default: 5)
            
        Returns:
            List of SearchResult objects, ordered by score (best first)
            
        Raises:
            ValueError: If query is empty or top_k is invalid
            RuntimeError: If search fails
            
        Example:
            >>> retriever = SemanticRetriever(gen, store, mapper)
            >>> results = retriever.search("tech sector news", top_k=5)
            >>> for result in results:
            ...     print(f"{result.rank}. {result.document.subject} (score: {result.score:.3f})")
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
                - metadata_stats: dict (from MetadataMapper)
        """
        stats = {
            'total_documents': self.vector_store.get_index_size(),
            'embedding_dimension': self.vector_store.dimension,
            'metadata_stats': self.metadata_mapper.get_statistics()
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