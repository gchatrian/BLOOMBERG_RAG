"""
Vector store module for Bloomberg RAG system.

Provides FAISS-based vector storage and metadata mapping functionality
for semantic search over email documents.
"""

from .faiss_store import FAISSVectorStore
from .metadata_mapper import MetadataMapper

__all__ = ['FAISSVectorStore', 'MetadataMapper']