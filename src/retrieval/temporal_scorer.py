"""
Temporal Scorer for Bloomberg RAG System.

Implements exponential decay scoring based on article date to boost recent documents.
"""

import logging
import math
from typing import List, Optional
from datetime import datetime, timedelta

from src.models import EmailDocument

logger = logging.getLogger(__name__)


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
            
        Example:
            >>> scorer = TemporalScorer(halflife_days=30)
            >>> # Article from today
            >>> score_today = scorer.calculate_recency_score(datetime.now())
            >>> print(score_today)
            1.0
            >>> # Article from 30 days ago
            >>> old_date = datetime.now() - timedelta(days=30)
            >>> score_old = scorer.calculate_recency_score(old_date)
            >>> print(score_old)
            0.5
        """
        # Handle missing date
        if article_date is None:
            logger.debug("No article date, using default score")
            return self.default_score
        
        # Use current time as reference if not provided
        if reference_date is None:
            reference_date = datetime.now()
        
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
        documents: List[EmailDocument],
        reference_date: Optional[datetime] = None
    ) -> List[float]:
        """
        Calculate recency scores for multiple documents.
        
        Args:
            documents: List of EmailDocument instances
            reference_date: Reference date for calculation (default: now)
            
        Returns:
            List of recency scores (same order as input documents)
            
        Example:
            >>> scorer = TemporalScorer(halflife_days=30)
            >>> scores = scorer.calculate_scores([doc1, doc2, doc3])
            >>> for doc, score in zip(documents, scores):
            ...     print(f"{doc.subject}: {score:.3f}")
        """
        if not documents:
            return []
        
        scores = []
        
        for doc in documents:
            # Try to get article date from metadata first
            article_date = None
            if doc.metadata and doc.metadata.article_date:
                article_date = doc.metadata.article_date
            elif doc.received_time:
                # Fallback to received time
                article_date = doc.received_time
            
            score = self.calculate_recency_score(article_date, reference_date)
            scores.append(score)
        
        logger.debug(
            f"Calculated recency scores for {len(documents)} documents: "
            f"mean={sum(scores)/len(scores):.3f}, "
            f"min={min(scores):.3f}, max={max(scores):.3f}"
        )
        
        return scores
    
    def get_score_at_age(self, days_ago: float) -> float:
        """
        Get theoretical score for document of given age.
        
        Useful for understanding decay curve.
        
        Args:
            days_ago: Age in days
            
        Returns:
            Expected recency score
            
        Example:
            >>> scorer = TemporalScorer(halflife_days=30)
            >>> print(f"Score at 0 days: {scorer.get_score_at_age(0):.3f}")
            Score at 0 days: 1.000
            >>> print(f"Score at 30 days: {scorer.get_score_at_age(30):.3f}")
            Score at 30 days: 0.500
            >>> print(f"Score at 90 days: {scorer.get_score_at_age(90):.3f}")
            Score at 90 days: 0.125
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