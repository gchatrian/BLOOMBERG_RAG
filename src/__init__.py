"""
Bloomberg RAG System - Source Package

This package contains the core functionality for the Bloomberg email RAG system.
"""

__version__ = "0.1.0"
__author__ = "Bloomberg RAG Team"

# Import main models for convenience
from .models import (
    EmailDocument,
    BloombergMetadata,
    SearchResult,
    StubEntry
)

__all__ = [
    "EmailDocument",
    "BloombergMetadata",
    "SearchResult",
    "StubEntry"
]