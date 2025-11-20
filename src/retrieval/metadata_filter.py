"""
Metadata Filter for Bloomberg RAG System.

Provides filtering capabilities based on Bloomberg metadata (dates, topics, people).
"""

import logging
from typing import List, Dict, Any, Optional, Set
from datetime import datetime

from src.models import EmailDocument

logger = logging.getLogger(__name__)


class MetadataFilter:
    """
    Filter documents based on Bloomberg metadata.
    
    Supports filtering by:
    - Date range (article_date)
    - Topics (any match)
    - People (any match)
    
    Filters can be combined using AND logic.
    """
    
    def __init__(self):
        """Initialize metadata filter."""
        logger.info("MetadataFilter initialized")
    
    def filter_by_date_range(
        self,
        documents: List[EmailDocument],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[int]:
        """
        Filter documents by date range.
        
        Args:
            documents: List of EmailDocument instances
            start_date: Start date (inclusive), None for no lower bound
            end_date: End date (inclusive), None for no upper bound
            
        Returns:
            List of indices of documents within date range
            
        Example:
            >>> from datetime import datetime, timedelta
            >>> filter = MetadataFilter()
            >>> # Last 30 days
            >>> start = datetime.now() - timedelta(days=30)
            >>> indices = filter.filter_by_date_range(documents, start_date=start)
        """
        if not documents:
            return []
        
        if start_date is None and end_date is None:
            # No filtering
            return list(range(len(documents)))
        
        matching_indices = []
        
        for idx, doc in enumerate(documents):
            # Get article date
            article_date = None
            if doc.metadata and doc.metadata.article_date:
                article_date = doc.metadata.article_date
            elif doc.received_time:
                article_date = doc.received_time
            
            if article_date is None:
                # Skip documents without date
                continue
            
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
        documents: List[EmailDocument],
        topics: List[str]
    ) -> List[int]:
        """
        Filter documents by topics (any match).
        
        Args:
            documents: List of EmailDocument instances
            topics: List of topics to match (case-insensitive)
            
        Returns:
            List of indices of documents matching any topic
            
        Example:
            >>> filter = MetadataFilter()
            >>> indices = filter.filter_by_topics(documents, ['Technology', 'AI'])
        """
        if not documents or not topics:
            return list(range(len(documents)))
        
        # Normalize topics to lowercase for matching
        topics_lower = set(t.lower() for t in topics)
        
        matching_indices = []
        
        for idx, doc in enumerate(documents):
            # Get document topics
            if not doc.metadata or not doc.metadata.topics:
                continue
            
            # Check for any match (case-insensitive)
            doc_topics_lower = set(t.lower() for t in doc.metadata.topics)
            
            if topics_lower & doc_topics_lower:  # Set intersection
                matching_indices.append(idx)
        
        logger.debug(
            f"Topics filter ({topics}): {len(matching_indices)}/{len(documents)} "
            f"documents match"
        )
        
        return matching_indices
    
    def filter_by_people(
        self,
        documents: List[EmailDocument],
        people: List[str]
    ) -> List[int]:
        """
        Filter documents by people mentioned (any match).
        
        Args:
            documents: List of EmailDocument instances
            people: List of people names to match (case-insensitive)
            
        Returns:
            List of indices of documents mentioning any person
            
        Example:
            >>> filter = MetadataFilter()
            >>> indices = filter.filter_by_people(documents, ['Elon Musk', 'Tim Cook'])
        """
        if not documents or not people:
            return list(range(len(documents)))
        
        # Normalize people names to lowercase for matching
        people_lower = set(p.lower() for p in people)
        
        matching_indices = []
        
        for idx, doc in enumerate(documents):
            # Get document people
            if not doc.metadata or not doc.metadata.people:
                continue
            
            # Check for any match (case-insensitive)
            doc_people_lower = set(p.lower() for p in doc.metadata.people)
            
            if people_lower & doc_people_lower:  # Set intersection
                matching_indices.append(idx)
        
        logger.debug(
            f"People filter ({people}): {len(matching_indices)}/{len(documents)} "
            f"documents match"
        )
        
        return matching_indices
    
    def apply_filters(
        self,
        documents: List[EmailDocument],
        filters: Dict[str, Any]
    ) -> List[int]:
        """
        Apply combined filters using AND logic.
        
        Args:
            documents: List of EmailDocument instances
            filters: Dictionary with filter specifications:
                - 'date_range': tuple of (start_date, end_date) or None
                - 'topics': list of topics or None
                - 'people': list of people or None
            
        Returns:
            List of indices of documents passing ALL filters
            
        Example:
            >>> from datetime import datetime, timedelta
            >>> filter = MetadataFilter()
            >>> filters = {
            ...     'date_range': (datetime.now() - timedelta(days=30), None),
            ...     'topics': ['Technology', 'AI'],
            ...     'people': ['Sam Altman']
            ... }
            >>> indices = filter.apply_filters(documents, filters)
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
        
        # Convert back to sorted list
        result = sorted(list(result_indices))
        
        logger.info(
            f"Combined filters: {len(result)}/{len(documents)} documents pass "
            f"(applied {len(filters)} filter types)"
        )
        
        return result
    
    def get_available_topics(
        self,
        documents: List[EmailDocument]
    ) -> List[str]:
        """
        Get all unique topics from documents.
        
        Args:
            documents: List of EmailDocument instances
            
        Returns:
            Sorted list of unique topics
        """
        topics = set()
        
        for doc in documents:
            if doc.metadata and doc.metadata.topics:
                topics.update(doc.metadata.topics)
        
        return sorted(list(topics))
    
    def get_available_people(
        self,
        documents: List[EmailDocument]
    ) -> List[str]:
        """
        Get all unique people from documents.
        
        Args:
            documents: List of EmailDocument instances
            
        Returns:
            Sorted list of unique people
        """
        people = set()
        
        for doc in documents:
            if doc.metadata and doc.metadata.people:
                people.update(doc.metadata.people)
        
        return sorted(list(people))
    
    def __repr__(self) -> str:
        """String representation of the filter."""
        return "MetadataFilter()"