"""
Data models for Bloomberg RAG system.
Defines EmailDocument and BloombergMetadata dataclasses.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
import numpy as np


@dataclass
class BloombergMetadata:
    """
    Metadata extracted from Bloomberg emails.
    
    Attributes:
        author: Article author(s) extracted from "By [Name]"
        article_date: Date article was written (priority over email received date)
        topics: List of Bloomberg topics from "Topics:" section
        people: List of people mentioned from "People:" section
        tickers: List of stock tickers from "Tickers:" section
        category: Bloomberg category (BFW, BI, BBF, etc.) from subject
        story_id: Unique Bloomberg story ID extracted from article URL
    """
    
    author: Optional[str] = None
    article_date: Optional[datetime] = None
    topics: List[str] = field(default_factory=list)
    people: List[str] = field(default_factory=list)
    tickers: List[str] = field(default_factory=list)
    category: Optional[str] = None
    story_id: Optional[str] = None
    
    def __repr__(self) -> str:
        """Human-readable representation."""
        parts = []
        if self.category:
            parts.append(f"Category: {self.category}")
        if self.author:
            parts.append(f"Author: {self.author}")
        if self.article_date:
            parts.append(f"Date: {self.article_date.strftime('%Y-%m-%d')}")
        if self.tickers:
            parts.append(f"Tickers: {', '.join(self.tickers[:3])}")
        if self.topics:
            parts.append(f"Topics: {', '.join(self.topics[:3])}")
        if self.people:
            parts.append(f"People: {', '.join(self.people[:3])}")
        if self.story_id:
            parts.append(f"Story ID: {self.story_id}")
        
        return f"BloombergMetadata({' | '.join(parts)})"
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "author": self.author,
            "article_date": self.article_date.isoformat() if self.article_date else None,
            "topics": self.topics,
            "people": self.people,
            "tickers": self.tickers,
            "category": self.category,
            "story_id": self.story_id
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "BloombergMetadata":
        """Create from dictionary."""
        if data.get("article_date"):
            data["article_date"] = datetime.fromisoformat(data["article_date"])
        return cls(**data)


@dataclass
class EmailDocument:
    """
    Represents a processed email document.
    
    This is the main data structure used throughout the pipeline:
    - Extracted from Outlook
    - Cleaned and processed
    - Embedded into vector space
    - Stored in FAISS index
    
    Attributes:
        outlook_entry_id: Unique Outlook identifier (used for folder operations)
        subject: Email subject line
        body: Cleaned email body text
        raw_body: Original unprocessed body (backup for debugging)
        sender: Email sender address
        received_date: Date email was received in Outlook
        bloomberg_metadata: Extracted Bloomberg-specific metadata
        status: Processing status ("complete", "stub", "processed")
        is_stub: Whether this is a stub email (incomplete content)
        embedding: 768-dim vector representation (populated after embedding generation)
        processed_at: Timestamp when document was processed
    """
    
    # Identifiers
    outlook_entry_id: str
    
    # Content
    subject: str
    body: str
    raw_body: str
    
    # Email metadata
    sender: str
    received_date: datetime
    
    # Bloomberg metadata
    bloomberg_metadata: BloombergMetadata
    
    # Processing status
    status: str  # "complete", "stub", "processed"
    is_stub: bool = False
    
    # Embedding (populated later by embedding pipeline)
    embedding: Optional[np.ndarray] = None
    
    # Processing timestamp
    processed_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Set processing timestamp if not provided."""
        if self.processed_at is None:
            self.processed_at = datetime.now()
    
    def __repr__(self) -> str:
        """Human-readable representation."""
        date_str = self.received_date.strftime("%Y-%m-%d")
        status_emoji = "OK" if self.status == "complete" else "⏳" if self.status == "stub" else "📦"
        
        return (
            f"EmailDocument({status_emoji} {self.subject[:50]}... | "
            f"{date_str} | {self.bloomberg_metadata.category or 'Unknown'})"
        )
    
    def get_full_text(self) -> str:
        """
        Get full text for embedding.
        Combines subject, metadata, and body in a structured way.
        """
        parts = [
            f"Subject: {self.subject}",
            f"Date: {self.received_date.strftime('%Y-%m-%d')}"
        ]
        
        # Add Bloomberg metadata
        if self.bloomberg_metadata.category:
            parts.append(f"Category: {self.bloomberg_metadata.category}")
        
        if self.bloomberg_metadata.author:
            parts.append(f"Author: {self.bloomberg_metadata.author}")
        
        if self.bloomberg_metadata.tickers:
            parts.append(f"Tickers: {', '.join(self.bloomberg_metadata.tickers)}")
        
        if self.bloomberg_metadata.topics:
            parts.append(f"Topics: {', '.join(self.bloomberg_metadata.topics)}")
        
        if self.bloomberg_metadata.people:
            parts.append(f"People: {', '.join(self.bloomberg_metadata.people)}")
        
        # Add body
        parts.append(f"\n{self.body}")
        
        return "\n".join(parts)
    
    def get_preview(self, max_length: int = 200) -> str:
        """Get a short preview of the document content."""
        preview = self.body[:max_length]
        if len(self.body) > max_length:
            preview += "..."
        return preview
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "outlook_entry_id": self.outlook_entry_id,
            "subject": self.subject,
            "body": self.body,
            "raw_body": self.raw_body,
            "sender": self.sender,
            "received_date": self.received_date.isoformat(),
            "bloomberg_metadata": self.bloomberg_metadata.to_dict(),
            "status": self.status,
            "is_stub": self.is_stub,
            "embedding": self.embedding.tolist() if self.embedding is not None else None,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "EmailDocument":
        """Create from dictionary."""
        # Parse dates
        data["received_date"] = datetime.fromisoformat(data["received_date"])
        if data.get("processed_at"):
            data["processed_at"] = datetime.fromisoformat(data["processed_at"])
        
        # Parse metadata
        data["bloomberg_metadata"] = BloombergMetadata.from_dict(data["bloomberg_metadata"])
        
        # Parse embedding
        if data.get("embedding"):
            data["embedding"] = np.array(data["embedding"], dtype=np.float32)
        
        return cls(**data)
    
    def get_fingerprint(self) -> str:
        """
        Generate a fingerprint for stub matching.
        Combines subject + normalized date.
        Used as fallback when story_id is not available.
        """
        date_str = self.received_date.strftime("%Y%m%d")
        subject_clean = self.subject.lower().strip()
        return f"{subject_clean}_{date_str}"


@dataclass
class SearchResult:
    """
    Represents a single search result.
    
    Attributes:
        document: The EmailDocument that was retrieved
        score: Combined relevance score (0-1)
        semantic_score: Pure semantic similarity score
        temporal_score: Recency-based score
        distance: Raw L2 distance from FAISS
    """
    
    document: EmailDocument
    score: float
    semantic_score: float
    temporal_score: float
    distance: float
    
    def __repr__(self) -> str:
        """Human-readable representation."""
        return (
            f"SearchResult(score={self.score:.3f} | "
            f"semantic={self.semantic_score:.3f} | "
            f"temporal={self.temporal_score:.3f} | "
            f"{self.document.subject[:40]}...)"
        )


@dataclass
class StubEntry:
    """
    Represents a stub email in the registry.
    Used for tracking incomplete emails waiting for manual completion.
    
    Attributes:
        outlook_entry_id: Unique Outlook identifier
        story_id: Bloomberg story ID (if available)
        fingerprint: Subject + date fingerprint for matching
        subject: Email subject
        received_time: When stub was received
        status: "pending" or "completed"
        completed_at: When matching complete email was found
    """
    
    outlook_entry_id: str
    story_id: Optional[str]
    fingerprint: str
    subject: str
    received_time: datetime
    status: str = "pending"  # "pending" or "completed"
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "outlook_entry_id": self.outlook_entry_id,
            "story_id": self.story_id,
            "fingerprint": self.fingerprint,
            "subject": self.subject,
            "received_time": self.received_time.isoformat(),
            "status": self.status,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "StubEntry":
        """Create from dictionary."""
        data["received_time"] = datetime.fromisoformat(data["received_time"])
        if data.get("completed_at"):
            data["completed_at"] = datetime.fromisoformat(data["completed_at"])
        return cls(**data)
    
    def __repr__(self) -> str:
        """Human-readable representation."""
        status_emoji = "⏳" if self.status == "pending" else "OK"
        return f"StubEntry({status_emoji} {self.subject[:40]}... | {self.story_id or 'no ID'})"


if __name__ == "__main__":
    # Example usage
    print("Creating sample EmailDocument...")
    
    metadata = BloombergMetadata(
        author="John Doe",
        article_date=datetime.now(),
        topics=["AI", "Tech", "Regulation"],
        people=["Elon Musk", "Sam Altman"],
        tickers=["AAPL US", "MSFT US", "GOOGL US"],
        category="BFW",
        story_id="L123ABC456"
    )
    
    doc = EmailDocument(
        outlook_entry_id="ABC123",
        subject="AI Regulation Update",
        body="The latest developments in AI regulation...",
        raw_body="<html>The latest developments...</html>",
        sender="bloomberg@bloomberg.com",
        received_date=datetime.now(),
        bloomberg_metadata=metadata,
        status="complete",
        is_stub=False
    )
    
    print(doc)
    print("\nMetadata:")
    print(doc.bloomberg_metadata)
    print("\nFull text preview:")
    print(doc.get_full_text()[:200])