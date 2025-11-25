"""
Temporal Scorer for Bloomberg RAG System.

Implements exponential decay scoring based on article date to boost recent documents.
"""

import logging
import math
from typing import List, Optional, Any, Union
from datetime import datetime, timedelta

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


class TemporalScorer:
    """
    Calculate recency scores using exponential decay.
    
    Scores recent documents higher using formula:
        score = exp(-ln(2) * days_ago / halflife)
    
    This ensures:
    - Recent articles (days_ago=0) → score=1.0
    - Articles at halflife age → score=0.5
    - Old articles → score→0.0
    
    Attributes:
        halflife_days: Number of days for score to decay to 0.5
        default_score: Score for documents without date (default: 0.5)
    """
    
    def __init__(
        self, 
        halflife_days: int = 30,
        default_score: float = 0.5
    ):
        """
        Initialize temporal scorer.
        
        Args:
            halflife_days: Days for score to halve (default: 30)
            default_score: Score for documents without date (default: 0.5)
            
        Raises:
            ValueError: If halflife_days is not positive
        """
        if halflife_days <= 0:
            raise ValueError(f"halflife_days must be positive, got {halflife_days}")
        
        if not 0 <= default_score <= 1:
            raise ValueError(f"default_score must be in [0, 1], got {default_score}")
        
        self.halflife_days = halflife_days
        self.default_score = default_score
        
        # Precompute decay constant for efficiency
        self._decay_constant = math.log(2) / halflife_days
        
        logger.info(
            f"TemporalScorer initialized: halflife={halflife_days} days, "
            f"default_score={default_score}"
        )
    
    def calculate_recency_score(
        self, 
        article_date: Optional[datetime],
        reference_date: Optional[datetime] = None
    ) -> float:
        """
        Calculate recency score for an article date.
        
        Args:
            article_date: Date of the article (or None if unknown)
            reference_date: Reference date for calculation (default: now)
            
        Returns:
            Recency score between 0 and 1 (higher = more recent)
        """
        # Handle missing date
        if article_date is None:
            logger.debug("No article date, using default score")
            return self.default_score
        
        # Use current time as reference if not provided
        if reference_date is None:
            reference_date = datetime.now()
        
        # Make both timezone-naive for comparison
        if hasattr(article_date, 'tzinfo') and article_date.tzinfo is not None:
            article_date = article_date.replace(tzinfo=None)
        if hasattr(reference_date, 'tzinfo') and reference_date.tzinfo is not None:
            reference_date = reference_date.replace(tzinfo=None)
        
        # Calculate days difference
        days_ago = (reference_date - article_date).total_seconds() / 86400.0
        
        # Handle future dates (should not happen, but be defensive)
        if days_ago < 0:
            logger.warning(f"Article date {article_date} is in the future")
            return 1.0
        
        # Exponential decay: score = exp(-ln(2) * days_ago / halflife)
        score = math.exp(-self._decay_constant * days_ago)
        
        # Clamp to [0, 1]
        score = max(0.0, min(1.0, score))
        
        logger.debug(
            f"Article from {days_ago:.1f} days ago → recency score: {score:.3f}"
        )
        
        return score
    
    def calculate_scores(
        self,
        documents: List[Any],
        reference_date: Optional[datetime] = None
    ) -> List[float]:
        """
        Calculate recency scores for multiple documents.
        
        Args:
            documents: List of documents (dict or EmailDocument)
            reference_date: Reference date for calculation (default: now)
            
        Returns:
            List of recency scores (same order as input documents)
        """
        if not documents:
            return []
        
        scores = []
        
        for doc in documents:
            article_date = _get_document_date(doc)
            score = self.calculate_recency_score(article_date, reference_date)
            scores.append(score)
        
        if scores:
            logger.debug(
                f"Calculated recency scores for {len(documents)} documents: "
                f"mean={sum(scores)/len(scores):.3f}, "
                f"min={min(scores):.3f}, max={max(scores):.3f}"
            )
        
        return scores
    
    def get_score_at_age(self, days_ago: float) -> float:
        """
        Get theoretical score for document of given age.
        
        Args:
            days_ago: Age in days
            
        Returns:
            Expected recency score
        """
        if days_ago < 0:
            return 1.0
        
        score = math.exp(-self._decay_constant * days_ago)
        return max(0.0, min(1.0, score))
    
    def __repr__(self) -> str:
        """String representation of the scorer."""
        return (
            f"TemporalScorer("
            f"halflife={self.halflife_days} days, "
            f"default={self.default_score})"
        )