"""
Metadata Filter for Bloomberg RAG System.

Provides filtering capabilities based on Bloomberg metadata (dates, topics, people).
"""

import logging
from typing import List, Dict, Any, Optional, Set
from datetime import datetime

logger = logging.getLogger(__name__)


def _get_document_date(doc: Any) -> Optional[datetime]:
    """
    Extract date from document (handles both dict and EmailDocument).
    
    Args:
        doc: Document as dict or EmailDocument object
        
    Returns:
        datetime or None
    """
    article_date = None
    
    if isinstance(doc, dict):
        # Handle dict from JSON
        bloomberg_metadata = doc.get('bloomberg_metadata', {})
        if isinstance(bloomberg_metadata, dict) and bloomberg_metadata.get('article_date'):
            date_val = bloomberg_metadata['article_date']
            if isinstance(date_val, str):
                try:
                    article_date = datetime.fromisoformat(date_val.replace('Z', '+00:00'))
                except:
                    pass
            elif isinstance(date_val, datetime):
                article_date = date_val
        
        if article_date is None and doc.get('received_date'):
            date_val = doc['received_date']
            if isinstance(date_val, str):
                try:
                    article_date = datetime.fromisoformat(date_val.replace('Z', '+00:00'))
                except:
                    pass
            elif isinstance(date_val, datetime):
                article_date = date_val
    else:
        # Handle EmailDocument object
        if hasattr(doc, 'bloomberg_metadata') and doc.bloomberg_metadata:
            if hasattr(doc.bloomberg_metadata, 'article_date') and doc.bloomberg_metadata.article_date:
                article_date = doc.bloomberg_metadata.article_date
        
        if article_date is None and hasattr(doc, 'received_date') and doc.received_date:
            article_date = doc.received_date
    
    return article_date


def _get_document_topics(doc: Any) -> List[str]:
    """
    Extract topics from document (handles both dict and EmailDocument).
    
    Args:
        doc: Document as dict or EmailDocument object
        
    Returns:
        List of topics
    """
    if isinstance(doc, dict):
        bloomberg_metadata = doc.get('bloomberg_metadata', {})
        if isinstance(bloomberg_metadata, dict):
            return bloomberg_metadata.get('topics', []) or []
        return []
    else:
        if hasattr(doc, 'bloomberg_metadata') and doc.bloomberg_metadata:
            if hasattr(doc.bloomberg_metadata, 'topics') and doc.bloomberg_metadata.topics:
                return doc.bloomberg_metadata.topics
        return []


def _get_document_people(doc: Any) -> List[str]:
    """
    Extract people from document (handles both dict and EmailDocument).
    
    Args:
        doc: Document as dict or EmailDocument object
        
    Returns:
        List of people names
    """
    if isinstance(doc, dict):
        bloomberg_metadata = doc.get('bloomberg_metadata', {})
        if isinstance(bloomberg_metadata, dict):
            return bloomberg_metadata.get('people', []) or []
        return []
    else:
        if hasattr(doc, 'bloomberg_metadata') and doc.bloomberg_metadata:
            if hasattr(doc.bloomberg_metadata, 'people') and doc.bloomberg_metadata.people:
                return doc.bloomberg_metadata.people
        return []


def _get_document_tickers(doc: Any) -> List[str]:
    """
    Extract tickers from document (handles both dict and EmailDocument).
    
    Args:
        doc: Document as dict or EmailDocument object
        
    Returns:
        List of tickers
    """
    if isinstance(doc, dict):
        bloomberg_metadata = doc.get('bloomberg_metadata', {})
        if isinstance(bloomberg_metadata, dict):
            return bloomberg_metadata.get('tickers', []) or []
        return []
    else:
        if hasattr(doc, 'bloomberg_metadata') and doc.bloomberg_metadata:
            if hasattr(doc.bloomberg_metadata, 'tickers') and doc.bloomberg_metadata.tickers:
                return doc.bloomberg_metadata.tickers
        return []


class MetadataFilter:
    """
    Filter documents based on Bloomberg metadata.
    
    Supports filtering by:
    - Date range (article_date)
    - Topics (any match)
    - People (any match)
    - Tickers (any match)
    
    Filters can be combined using AND logic.
    """
    
    def __init__(self):
        """Initialize metadata filter."""
        logger.info("MetadataFilter initialized")
    
    def filter_by_date_range(
        self,
        documents: List[Any],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[int]:
        """
        Filter documents by date range.
        
        Args:
            documents: List of documents (dict or EmailDocument)
            start_date: Start date (inclusive), None for no lower bound
            end_date: End date (inclusive), None for no upper bound
            
        Returns:
            List of indices of documents within date range
        """
        if not documents:
            return []
        
        if start_date is None and end_date is None:
            # No filtering
            return list(range(len(documents)))
        
        # Make dates timezone-naive for comparison
        if start_date and hasattr(start_date, 'tzinfo') and start_date.tzinfo:
            start_date = start_date.replace(tzinfo=None)
        if end_date and hasattr(end_date, 'tzinfo') and end_date.tzinfo:
            end_date = end_date.replace(tzinfo=None)
        
        matching_indices = []
        
        for idx, doc in enumerate(documents):
            article_date = _get_document_date(doc)
            
            if article_date is None:
                # Skip documents without date
                continue
            
            # Make timezone-naive for comparison
            if hasattr(article_date, 'tzinfo') and article_date.tzinfo:
                article_date = article_date.replace(tzinfo=None)
            
            # Check bounds
            if start_date and article_date < start_date:
                continue
            if end_date and article_date > end_date:
                continue
            
            matching_indices.append(idx)
        
        logger.debug(
            f"Date filter: {len(matching_indices)}/{len(documents)} documents match "
            f"(start={start_date}, end={end_date})"
        )
        
        return matching_indices
    
    def filter_by_topics(
        self,
        documents: List[Any],
        topics: List[str]
    ) -> List[int]:
        """
        Filter documents by topics (any match).
        
        Args:
            documents: List of documents (dict or EmailDocument)
            topics: List of topics to match (case-insensitive)
            
        Returns:
            List of indices of documents matching any topic
        """
        if not documents or not topics:
            return list(range(len(documents)))
        
        # Normalize topics to lowercase for matching
        topics_lower = set(t.lower() for t in topics)
        
        matching_indices = []
        
        for idx, doc in enumerate(documents):
            doc_topics = _get_document_topics(doc)
            
            if not doc_topics:
                continue
            
            # Check for any match (case-insensitive)
            doc_topics_lower = set(t.lower() for t in doc_topics)
            
            if topics_lower & doc_topics_lower:  # Set intersection
                matching_indices.append(idx)
        
        logger.debug(
            f"Topics filter ({topics}): {len(matching_indices)}/{len(documents)} "
            f"documents match"
        )
        
        return matching_indices
    
    def filter_by_people(
        self,
        documents: List[Any],
        people: List[str]
    ) -> List[int]:
        """
        Filter documents by people mentioned (any match).
        
        Args:
            documents: List of documents (dict or EmailDocument)
            people: List of people names to match (case-insensitive)
            
        Returns:
            List of indices of documents mentioning any person
        """
        if not documents or not people:
            return list(range(len(documents)))
        
        # Normalize people names to lowercase for matching
        people_lower = set(p.lower() for p in people)
        
        matching_indices = []
        
        for idx, doc in enumerate(documents):
            doc_people = _get_document_people(doc)
            
            if not doc_people:
                continue
            
            # Check for any match (case-insensitive)
            doc_people_lower = set(p.lower() for p in doc_people)
            
            if people_lower & doc_people_lower:  # Set intersection
                matching_indices.append(idx)
        
        logger.debug(
            f"People filter ({people}): {len(matching_indices)}/{len(documents)} "
            f"documents match"
        )
        
        return matching_indices
    
    def filter_by_tickers(
        self,
        documents: List[Any],
        tickers: List[str]
    ) -> List[int]:
        """
        Filter documents by tickers (any match).
        
        Args:
            documents: List of documents (dict or EmailDocument)
            tickers: List of tickers to match (case-insensitive)
            
        Returns:
            List of indices of documents mentioning any ticker
        """
        if not documents or not tickers:
            return list(range(len(documents)))
        
        # Normalize tickers to uppercase for matching
        tickers_upper = set(t.upper() for t in tickers)
        
        matching_indices = []
        
        for idx, doc in enumerate(documents):
            doc_tickers = _get_document_tickers(doc)
            
            if not doc_tickers:
                continue
            
            # Check for any match (case-insensitive)
            doc_tickers_upper = set(t.upper() for t in doc_tickers)
            
            if tickers_upper & doc_tickers_upper:  # Set intersection
                matching_indices.append(idx)
        
        logger.debug(
            f"Tickers filter ({tickers}): {len(matching_indices)}/{len(documents)} "
            f"documents match"
        )
        
        return matching_indices
    
    def apply_filters(
        self,
        documents: List[Any],
        filters: Dict[str, Any]
    ) -> List[int]:
        """
        Apply combined filters using AND logic.
        
        Args:
            documents: List of documents (dict or EmailDocument)
            filters: Dictionary with filter specifications:
                - 'date_range': tuple of (start_date, end_date) or None
                - 'topics': list of topics or None
                - 'people': list of people or None
                - 'tickers': list of tickers or None
            
        Returns:
            List of indices of documents passing ALL filters
        """
        if not documents:
            return []
        
        if not filters:
            # No filters, return all indices
            return list(range(len(documents)))
        
        # Start with all documents
        result_indices = set(range(len(documents)))
        
        # Apply date range filter
        if 'date_range' in filters and filters['date_range']:
            start_date, end_date = filters['date_range']
            date_indices = self.filter_by_date_range(documents, start_date, end_date)
            result_indices &= set(date_indices)  # AND operation
        
        # Apply topics filter
        if 'topics' in filters and filters['topics']:
            topic_indices = self.filter_by_topics(documents, filters['topics'])
            result_indices &= set(topic_indices)  # AND operation
        
        # Apply people filter
        if 'people' in filters and filters['people']:
            people_indices = self.filter_by_people(documents, filters['people'])
            result_indices &= set(people_indices)  # AND operation
        
        # Apply tickers filter
        if 'tickers' in filters and filters['tickers']:
            ticker_indices = self.filter_by_tickers(documents, filters['tickers'])
            result_indices &= set(ticker_indices)  # AND operation
        
        # Convert back to sorted list
        result = sorted(list(result_indices))
        
        logger.info(
            f"Combined filters: {len(result)}/{len(documents)} documents pass "
            f"(applied {len(filters)} filter types)"
        )
        
        return result
    
    def get_available_topics(self, documents: List[Any]) -> List[str]:
        """Get all unique topics from documents."""
        topics = set()
        for doc in documents:
            doc_topics = _get_document_topics(doc)
            topics.update(doc_topics)
        return sorted(list(topics))
    
    def get_available_people(self, documents: List[Any]) -> List[str]:
        """Get all unique people from documents."""
        people = set()
        for doc in documents:
            doc_people = _get_document_people(doc)
            people.update(doc_people)
        return sorted(list(people))
    
    def get_available_tickers(self, documents: List[Any]) -> List[str]:
        """Get all unique tickers from documents."""
        tickers = set()
        for doc in documents:
            doc_tickers = _get_document_tickers(doc)
            tickers.update(doc_tickers)
        return sorted(list(tickers))
    
    def __repr__(self) -> str:
        """String representation of the filter."""
        return "MetadataFilter()"