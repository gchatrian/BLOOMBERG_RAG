"""
Google ADK Tools for Bloomberg RAG System.

This module provides tool functions that expose retrieval capabilities
to the Google ADK agent. Each tool is a Python function with detailed
docstrings that Google ADK uses to determine when to call the tool.

The RetrievalToolkit class manages the vector store and provides
helper methods for all tools.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

# These imports will be available when integrated with full project
try:
    from src.vectorstore.faiss_store import FAISSVectorStore
    from src.vectorstore.metadata_mapper import MetadataMapper
    from src.retrieval.semantic_retriever import SemanticRetriever
    from src.retrieval.hybrid_retriever import HybridRetriever
    from src.retrieval.temporal_scorer import TemporalScorer
    from src.retrieval.metadata_filter import MetadataFilter
    from src.embedding.generator import EmbeddingGenerator
    from config.settings import (
        get_tool_config, 
        get_vectorstore_config, 
        get_retrieval_config,
        get_embedding_config
    )
except ImportError as e:
    # Placeholder for development
    logging.warning(f"Import error: {e}")
    FAISSVectorStore = None
    MetadataMapper = None
    SemanticRetriever = None
    HybridRetriever = None
    TemporalScorer = None
    MetadataFilter = None
    EmbeddingGenerator = None
    get_tool_config = lambda: None
    get_vectorstore_config = lambda: None
    get_retrieval_config = lambda: None
    get_embedding_config = lambda: None

logger = logging.getLogger(__name__)


class RetrievalToolkit:
    """
    Manages vector store and provides helper methods for Google ADK tools.
    
    This class is instantiated once and shared across all tool functions.
    It loads the FAISS vector store, embedding generator, and retriever
    on initialization.
    
    Initialization chain:
    1. EmbeddingGenerator
    2. FAISSVectorStore
    3. MetadataMapper
    4. SemanticRetriever(embedding_generator, vector_store, metadata_mapper)
    5. HybridRetriever(semantic_retriever, temporal_scorer, metadata_filter)
    """
    
    def __init__(self):
        """Initialize the toolkit by loading vector store and retriever."""
        logger.info("Initializing RetrievalToolkit...")
        
        # Load configurations
        self.tool_config = get_tool_config()
        self.vectorstore_config = get_vectorstore_config()
        self.retrieval_config = get_retrieval_config()
        self.embedding_config = get_embedding_config()
        
        # Initialize components (lazy loaded)
        self._embedding_generator = None
        self._vector_store = None
        self._metadata_mapper = None
        self._semantic_retriever = None
        self._temporal_scorer = None
        self._metadata_filter = None
        self._retriever = None
        
        # Cache for results (if enabled)
        self._cache = {} if self.tool_config and self.tool_config.enable_caching else None
        
        logger.info("RetrievalToolkit initialized (lazy loading enabled)")
    
    @property
    def embedding_generator(self):
        """Lazy load embedding generator."""
        if self._embedding_generator is None:
            logger.info("Loading embedding generator...")
            if EmbeddingGenerator is not None:
                model_name = self.embedding_config.model_name if self.embedding_config else None
                self._embedding_generator = EmbeddingGenerator(model_name)
            else:
                raise RuntimeError("EmbeddingGenerator not available")
        return self._embedding_generator
    
    @property
    def vector_store(self):
        """Lazy load vector store."""
        if self._vector_store is None:
            logger.info("Loading FAISS vector store...")
            if FAISSVectorStore is not None:
                if self.vectorstore_config.index_path.exists():
                    self._vector_store = FAISSVectorStore.load(
                        str(self.vectorstore_config.index_path),
                        self.embedding_config.embedding_dim
                    )
                else:
                    raise RuntimeError(
                        f"Vector store not found at {self.vectorstore_config.index_path}. "
                        "Run sync first to index emails."
                    )
            else:
                raise RuntimeError("FAISSVectorStore not available")
        return self._vector_store
    
    @property
    def metadata_mapper(self):
        """Lazy load metadata mapper."""
        if self._metadata_mapper is None:
            logger.info("Loading metadata mapper...")
            if MetadataMapper is not None:
                if self.vectorstore_config.metadata_path.exists():
                    self._metadata_mapper = MetadataMapper.load(
                        str(self.vectorstore_config.metadata_path)
                    )
                else:
                    raise RuntimeError(
                        f"Metadata mapper not found at {self.vectorstore_config.metadata_path}. "
                        "Run sync first to index emails."
                    )
            else:
                raise RuntimeError("MetadataMapper not available")
        return self._metadata_mapper
    
    @property
    def semantic_retriever(self):
        """Lazy load semantic retriever."""
        if self._semantic_retriever is None:
            logger.info("Loading semantic retriever...")
            if SemanticRetriever is not None:
                self._semantic_retriever = SemanticRetriever(
                    embedding_generator=self.embedding_generator,
                    vector_store=self.vector_store,
                    metadata_mapper=self.metadata_mapper
                )
            else:
                raise RuntimeError("SemanticRetriever not available")
        return self._semantic_retriever
    
    @property
    def temporal_scorer(self):
        """Lazy load temporal scorer."""
        if self._temporal_scorer is None:
            logger.info("Loading temporal scorer...")
            if TemporalScorer is not None:
                halflife = self.retrieval_config.temporal_halflife_days if self.retrieval_config else 30
                self._temporal_scorer = TemporalScorer(halflife_days=halflife)
            else:
                raise RuntimeError("TemporalScorer not available")
        return self._temporal_scorer
    
    @property
    def metadata_filter(self):
        """Lazy load metadata filter."""
        if self._metadata_filter is None:
            logger.info("Loading metadata filter...")
            if MetadataFilter is not None:
                self._metadata_filter = MetadataFilter()
            else:
                raise RuntimeError("MetadataFilter not available")
        return self._metadata_filter
    
    @property
    def retriever(self):
        """Lazy load hybrid retriever."""
        if self._retriever is None:
            logger.info("Loading hybrid retriever...")
            if HybridRetriever is not None:
                recency_weight = self.retrieval_config.recency_weight if self.retrieval_config else 0.3
                self._retriever = HybridRetriever(
                    semantic_retriever=self.semantic_retriever,
                    temporal_scorer=self.temporal_scorer,
                    metadata_filter=self.metadata_filter,
                    default_recency_weight=recency_weight
                )
            else:
                raise RuntimeError("HybridRetriever not available")
        return self._retriever
    
    def format_article(self, article_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format article data for tool response.
        
        Args:
            article_data: Raw article data from retriever
            
        Returns:
            Formatted article dictionary
        """
        max_snippet = self.tool_config.max_snippet_length if self.tool_config else 200
        include_full = self.tool_config.include_full_content if self.tool_config else False
        
        # Handle different input formats
        if hasattr(article_data, 'document'):
            # HybridSearchResult or SearchResult object
            doc = article_data.document
            score = getattr(article_data, 'combined_score', None) or getattr(article_data, 'score', 0.0)
        else:
            # Raw document
            doc = article_data
            score = article_data.get('score', 0.0)
        
        # Extract metadata
        metadata = doc.bloomberg_metadata if hasattr(doc, 'bloomberg_metadata') and doc.bloomberg_metadata else None
        
        # Build formatted article
        formatted = {
            "subject": doc.subject if hasattr(doc, 'subject') else str(doc),
            "date": None,
            "author": None,
            "topics": [],
            "people": [],
            "tickers": [],
            "content": "",
            "score": round(score, 3) if isinstance(score, float) else score
        }
        
        # Extract date
        if metadata and hasattr(metadata, 'article_date') and metadata.article_date:
            formatted["date"] = metadata.article_date.strftime("%Y-%m-%d")
        elif hasattr(doc, 'received_date') and doc.received_date:
            formatted["date"] = doc.received_date.strftime("%Y-%m-%d")
        
        # Extract author
        if metadata and hasattr(metadata, 'author'):
            formatted["author"] = metadata.author
        elif hasattr(doc, 'sender'):
            formatted["author"] = doc.sender
        
        # Extract Bloomberg metadata
        if metadata:
            if hasattr(metadata, 'topics') and metadata.topics:
                formatted["topics"] = metadata.topics
            if hasattr(metadata, 'people') and metadata.people:
                formatted["people"] = metadata.people
            if hasattr(metadata, 'tickers') and metadata.tickers:
                formatted["tickers"] = metadata.tickers
        
        # Extract content
        if hasattr(doc, 'body'):
            if include_full:
                formatted["content"] = doc.body
            else:
                formatted["content"] = doc.body[:max_snippet] + ("..." if len(doc.body) > max_snippet else "")
        
        return formatted
    
    def format_response(
        self,
        articles: List[Any],
        query_info: Dict[str, Any],
        success: bool = True,
        message: str = ""
    ) -> Dict[str, Any]:
        """
        Format complete tool response.
        
        Args:
            articles: List of articles from retriever
            query_info: Query metadata
            success: Whether operation succeeded
            message: Status or error message
            
        Returns:
            Formatted response dictionary
        """
        max_articles = self.tool_config.max_articles_per_call if self.tool_config else 10
        
        # Limit and format articles
        limited_articles = articles[:max_articles] if articles else []
        formatted_articles = [self.format_article(a) for a in limited_articles]
        
        # Add timestamp
        query_info["timestamp"] = datetime.now().isoformat()
        
        return {
            "success": success,
            "articles": formatted_articles,
            "count": len(formatted_articles),
            "total_found": len(articles) if articles else 0,
            "query_info": query_info,
            "message": message
        }
    
    def search_semantic(
        self,
        query: str,
        top_k: Optional[int] = None
    ) -> List[Any]:
        """
        Perform semantic search only.
        
        Args:
            query: Search query
            top_k: Number of results (uses config default if None)
            
        Returns:
            List of SearchResult objects
        """
        top_k = top_k or (self.tool_config.default_top_k if self.tool_config else 20)
        
        # Use semantic retriever directly
        results = self.semantic_retriever.search(query, top_k=top_k)
        
        return results
    
    def search_hybrid(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        top_k: Optional[int] = None
    ) -> List[Any]:
        """
        Perform hybrid search (semantic + temporal + filters).
        
        Args:
            query: Search query
            filters: Optional metadata filters
            top_k: Number of results (uses config default if None)
            
        Returns:
            List of HybridSearchResult objects
        """
        top_k = top_k or (self.tool_config.default_top_k if self.tool_config else 20)
        recency_weight = self.retrieval_config.recency_weight if self.retrieval_config else 0.3
        
        # Handle empty query (filter-only search)
        if not query or not query.strip():
            # For filter-only queries, use a generic query
            query = "*"
        
        # Use hybrid retriever
        results = self.retriever.search(
            query=query,
            top_k=top_k,
            filters=filters,
            recency_weight=recency_weight
        )
        
        return results


# ============================================================================
# GLOBAL TOOLKIT INSTANCE
# ============================================================================

_toolkit_instance: Optional[RetrievalToolkit] = None


def get_toolkit() -> RetrievalToolkit:
    """
    Get or create the global RetrievalToolkit instance.
    
    Returns:
        RetrievalToolkit instance
    """
    global _toolkit_instance
    
    if _toolkit_instance is None:
        _toolkit_instance = RetrievalToolkit()
    
    return _toolkit_instance


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    'RetrievalToolkit',
    'get_toolkit'
]