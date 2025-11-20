"""
Orchestration module for Bloomberg RAG system.

Coordinates pipelines for:
- Data ingestion (email extraction and processing)
- Indexing (embedding generation and vector store updates)
"""

from .ingestion_pipeline import IngestionPipeline
from .indexing_pipeline import IndexingPipeline

__all__ = [
    'IngestionPipeline',
    'IndexingPipeline'
]