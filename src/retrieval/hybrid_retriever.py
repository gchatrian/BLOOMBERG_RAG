"""
Hybrid Retriever for Bloomberg RAG System.

Combines semantic search, temporal scoring, and metadata filtering
for comprehensive document retrieval.
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from src.retrieval.semantic_retriever import SemanticRetriever, SearchResult
from src.retrieval.temporal_scorer import TemporalScorer
from src.retrieval.metadata_filter import MetadataFilter

logger = logging.getLogger(__name__)


def _get_document_subject(doc: Any) -> str:
    """Extract subject from document (handles both dict and EmailDocument)."""
    if isinstance(doc, dict):
        return doc.get('subject', 'Unknown')
    return doc.subject if hasattr(doc, 'subject') else str(doc)


def _get_document_date_str(doc: Any) -> str:
    """Extract date string from document (handles both dict and EmailDocument)."""
    from datetime import datetime
    
    if isinstance(doc, dict):
        bloomberg_metadata = doc.get('bloomberg_metadata', {})
        if isinstance(bloomberg_metadata, dict):
            article_date = bloomberg_metadata.get('article_date')
            if article_date:
                if isinstance(article_date, str):
                    return article_date[:10]
                elif isinstance(article_date, datetime):
                    return article_date.strftime("%Y-%m-%d")
        
        received_date = doc.get('received_date')
        if received_date:
            if isinstance(received_date, str):
                return received_date[:10]
            elif isinstance(received_date, datetime):
                return received_date.strftime("%Y-%m-%d")
        return "Unknown"
    else:
        # EmailDocument object
        if hasattr(doc, 'bloomberg_metadata') and doc.bloomberg_metadata:
            if hasattr(doc.bloomberg_metadata, 'article_date') and doc.bloomberg_metadata.article_date:
                return doc.bloomberg_metadata.article_date.strftime("%Y-%m-%d")
        if hasattr(doc, 'received_date') and doc.received_date:
            return doc.received_date.strftime("%Y-%m-%d")
        return "Unknown"


@dataclass
class HybridSearchResult(SearchResult):
    """
    Extended search result with temporal and combined scores.
    
    Attributes:
        All from SearchResult, plus:
        recency_score: Temporal score (0-1)
        combined_score: Final weighted combination
        recency_weight: Weight used for combination
    """
    recency_score: float = 0.0
    combined_score: float = 0.0
    recency_weight: float = 0.0
    
    def get_score_breakdown(self) -> Dict[str, float]:
        """
        Get detailed score breakdown.
        
        Returns:
            Dictionary with all score components
        """
        return {
            'semantic_score': self.score,
            'recency_score': self.recency_score,
            'combined_score': self.combined_score,
            'recency_weight': self.recency_weight,
            'semantic_weight': 1.0 - self.recency_weight
        }
    
    def format_preview(self, content_length: int = 200) -> str:
        """
        Format result with score breakdown.
        
        Args:
            content_length: Maximum content preview length
            
        Returns:
            Formatted string with all scores
        """
        # Get base preview
        base = super().format_preview(content_length)
        
        # Add score breakdown
        breakdown = (
            f"    Scores: semantic={self.score:.3f}, "
            f"recency={self.recency_score:.3f}, "
            f"combined={self.combined_score:.3f}\n"
        )
        
        # Insert breakdown after first line
        lines = base.split('\n')
        lines.insert(1, breakdown)
        
        return '\n'.join(lines)


class HybridRetriever:
    """
    Hybrid retrieval combining semantic, temporal, and metadata filtering.
    
    Pipeline:
    1. Semantic search (get top-K candidates)
    2. Apply metadata filters (optional)
    3. Calculate recency scores
    4. Combine scores: final = (semantic * (1-w)) + (recency * w)
    5. Re-rank by combined score
    
    Attributes:
        semantic_retriever: SemanticRetriever instance
        temporal_scorer: TemporalScorer instance
        metadata_filter: MetadataFilter instance
        default_recency_weight: Default weight for recency (0-1)
    """
    
    def __init__(
        self,
        semantic_retriever: SemanticRetriever,
        temporal_scorer: Optional[TemporalScorer] = None,
        metadata_filter: Optional[MetadataFilter] = None,
        default_recency_weight: float = 0.3
    ):
        """
        Initialize hybrid retriever.
        
        Args:
            semantic_retriever: Initialized SemanticRetriever
            temporal_scorer: Optional TemporalScorer (default: 30-day halflife)
            metadata_filter: Optional MetadataFilter (default: new instance)
            default_recency_weight: Default weight for recency (default: 0.3)
            
        Raises:
            TypeError: If semantic_retriever has wrong type
            ValueError: If default_recency_weight not in [0, 1]
        """
        if not isinstance(semantic_retriever, SemanticRetriever):
            raise TypeError("semantic_retriever must be SemanticRetriever instance")
        
        if not 0 <= default_recency_weight <= 1:
            raise ValueError(
                f"default_recency_weight must be in [0, 1], got {default_recency_weight}"
            )
        
        self.semantic_retriever = semantic_retriever
        
        # Use provided or create default components
        self.temporal_scorer = temporal_scorer or TemporalScorer(halflife_days=30)
        self.metadata_filter = metadata_filter or MetadataFilter()
        
        self.default_recency_weight = default_recency_weight
        
        logger.info(
            f"HybridRetriever initialized: "
            f"recency_weight={default_recency_weight}, "
            f"halflife={self.temporal_scorer.halflife_days} days"
        )
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        recency_weight: Optional[float] = None
    ) -> List[HybridSearchResult]:
        """
        Perform hybrid search with semantic, temporal, and metadata components.
        
        Args:
            query: Search query string
            top_k: Number of results to return (default: 5)
            filters: Optional metadata filters dict:
                - 'date_range': tuple of (start_date, end_date)
                - 'topics': list of topics
                - 'people': list of people
                - 'tickers': list of tickers
            recency_weight: Weight for recency score (default: use default_recency_weight)
                           0.0 = pure semantic, 1.0 = pure recency
            
        Returns:
            List of HybridSearchResult objects, ordered by combined score
            
        Raises:
            ValueError: If query is empty or parameters are invalid
            RuntimeError: If search fails
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
        
        if top_k <= 0:
            raise ValueError(f"top_k must be positive, got {top_k}")
        
        # Use default recency weight if not specified
        if recency_weight is None:
            recency_weight = self.default_recency_weight
        
        if not 0 <= recency_weight <= 1:
            raise ValueError(f"recency_weight must be in [0, 1], got {recency_weight}")
        
        logger.info(
            f"Hybrid search: query='{query}', top_k={top_k}, "
            f"recency_weight={recency_weight}, filters={bool(filters)}"
        )
        
        try:
            # Step 1: Semantic search (get more candidates for filtering)
            # Request 2x top_k to have buffer after filtering
            search_k = top_k * 2 if filters else top_k
            
            semantic_results = self.semantic_retriever.search(
                query=query,
                top_k=search_k
            )
            
            logger.debug(f"Semantic search returned {len(semantic_results)} results")
            
            if not semantic_results:
                logger.warning("No semantic results found")
                return []
            
            # Step 2: Apply metadata filters (if specified)
            if filters:
                documents = [r.document for r in semantic_results]
                matching_indices = self.metadata_filter.apply_filters(documents, filters)
                
                # Filter semantic results
                semantic_results = [
                    semantic_results[i] for i in matching_indices
                ]
                
                logger.debug(
                    f"After filtering: {len(semantic_results)} results remain"
                )
                
                if not semantic_results:
                    logger.warning("No results after filtering")
                    return []
            
            # Step 3: Calculate recency scores
            documents = [r.document for r in semantic_results]
            recency_scores = self.temporal_scorer.calculate_scores(documents)
            
            # Step 4: Combine scores
            hybrid_results = []
            
            for semantic_result, recency_score in zip(semantic_results, recency_scores):
                # Combined score = (semantic * (1-w)) + (recency * w)
                semantic_score = semantic_result.score
                combined_score = (
                    semantic_score * (1.0 - recency_weight) +
                    recency_score * recency_weight
                )
                
                # Create HybridSearchResult
                hybrid_result = HybridSearchResult(
                    document=semantic_result.document,
                    score=semantic_score,
                    distance=semantic_result.distance,
                    rank=0,  # Will be set after re-ranking
                    metadata_preview=semantic_result.metadata_preview,
                    recency_score=recency_score,
                    combined_score=combined_score,
                    recency_weight=recency_weight
                )
                
                hybrid_results.append(hybrid_result)
            
            # Step 5: Re-rank by combined score
            hybrid_results.sort(key=lambda x: x.combined_score, reverse=True)
            
            # Limit to top_k and update ranks
            hybrid_results = hybrid_results[:top_k]
            for rank, result in enumerate(hybrid_results, 1):
                result.rank = rank
            
            logger.info(
                f"Hybrid search complete: {len(hybrid_results)} results "
                f"(mean_combined={sum(r.combined_score for r in hybrid_results)/len(hybrid_results):.3f})"
            )
            
            return hybrid_results
            
        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            raise RuntimeError(f"Hybrid search failed: {e}")
    
    def search_with_breakdown(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        recency_weight: Optional[float] = None
    ) -> str:
        """
        Run search and explain ranking with score breakdown.
        
        Args:
            Same as search()
            
        Returns:
            Formatted string with detailed score breakdown
        """
        results = self.search(query, top_k, filters, recency_weight)
        
        if not results:
            return "No results found."
        
        output = f"\nHybrid Search Results ({len(results)} documents):\n"
        output += f"Recency Weight: {results[0].recency_weight:.2f} "
        output += f"(Semantic: {1-results[0].recency_weight:.2f}, Recency: {results[0].recency_weight:.2f})\n"
        output += "=" * 80 + "\n\n"
        
        for result in results:
            breakdown = result.get_score_breakdown()
            
            # Use helper function to get subject
            subject = _get_document_subject(result.document)
            output += f"[{result.rank}] {subject}\n"
            output += f"    Semantic: {breakdown['semantic_score']:.3f} | "
            output += f"Recency: {breakdown['recency_score']:.3f} | "
            output += f"Combined: {breakdown['combined_score']:.3f}\n"
            
            # Date info using helper function
            date_str = _get_document_date_str(result.document)
            if date_str != "Unknown":
                output += f"    Date: {date_str}\n"
            
            # Topics
            if result.metadata_preview.get('topics'):
                topics_str = ", ".join(result.metadata_preview['topics'][:3])
                output += f"    Topics: {topics_str}\n"
            
            output += "\n" + "-" * 80 + "\n\n"
        
        return output
    
    def __repr__(self) -> str:
        """String representation of the retriever."""
        return (
            f"HybridRetriever("
            f"recency_weight={self.default_recency_weight}, "
            f"halflife={self.temporal_scorer.halflife_days} days)"
        )