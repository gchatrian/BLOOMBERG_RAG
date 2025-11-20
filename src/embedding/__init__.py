"""
Embedding generation module for Bloomberg RAG system.

Provides functionality to generate semantic embeddings from text using
sentence-transformers models and coordinate the indexing pipeline.
"""

from .generator import EmbeddingGenerator
from .batch_processor import IndexingPipeline

__all__ = ['EmbeddingGenerator', 'IndexingPipeline']