"""
Indexing Pipeline for Bloomberg RAG System.

Coordinates the complete indexing process: documents to embeddings to vector store + metadata.
Handles batch processing, progress tracking, and validation.
"""

import logging
import time
from typing import List, Dict, Any, Optional
from tqdm import tqdm

from src.models import EmailDocument
from src.embedding.generator import EmbeddingGenerator
from src.vectorstore import FAISSVectorStore, MetadataMapper

logger = logging.getLogger(__name__)


class IndexingPipeline:
    """
    Orchestrates document indexing pipeline.
    
    Takes EmailDocuments, generates embeddings, adds to vector store,
    and maintains metadata mappings. Supports batch processing and
    progress tracking.
    
    Attributes:
        embedding_generator: EmbeddingGenerator instance
        vector_store: FAISSVectorStore instance
        metadata_mapper: MetadataMapper instance
    """
    
    def __init__(
        self,
        embedding_generator: EmbeddingGenerator,
        vector_store: FAISSVectorStore,
        metadata_mapper: MetadataMapper
    ):
        """
        Initialize indexing pipeline.
        
        Args:
            embedding_generator: Initialized EmbeddingGenerator
            vector_store: Initialized FAISSVectorStore
            metadata_mapper: Initialized MetadataMapper
            
        Raises:
            TypeError: If any component has wrong type
        """
        if not isinstance(embedding_generator, EmbeddingGenerator):
            raise TypeError("embedding_generator must be EmbeddingGenerator instance")
        
        if not isinstance(vector_store, FAISSVectorStore):
            raise TypeError("vector_store must be FAISSVectorStore instance")
        
        if not isinstance(metadata_mapper, MetadataMapper):
            raise TypeError("metadata_mapper must be MetadataMapper instance")
        
        self.embedding_generator = embedding_generator
        self.vector_store = vector_store
        self.metadata_mapper = metadata_mapper
        
        logger.info("IndexingPipeline initialized")
    
    def index_documents(
        self,
        documents: List[EmailDocument],
        batch_size: int = 32,
        show_progress: bool = True
    ) -> Dict[str, Any]:
        """
        Index a list of documents.
        
        Complete pipeline:
        1. Extract text from documents
        2. Generate embeddings (batch)
        3. Add vectors to FAISS
        4. Map vector IDs to document metadata
        5. Validate consistency
        
        Args:
            documents: List of EmailDocument instances to index
            batch_size: Number of documents to process per batch (default: 32)
            show_progress: Whether to show progress bar (default: True)
            
        Returns:
            Dictionary with indexing statistics:
                - total_documents: Number of documents processed
                - successful: Number successfully indexed
                - failed: Number of failures
                - processing_time: Total time in seconds
                - avg_time_per_doc: Average time per document
                - batch_size: Batch size used
                - start_vector_id: First vector ID assigned
                - end_vector_id: Last vector ID assigned
                
        Raises:
            ValueError: If documents list is empty
            RuntimeError: If indexing fails completely
            
        Example:
            >>> pipeline = IndexingPipeline(gen, store, mapper)
            >>> docs = [doc1, doc2, doc3]
            >>> stats = pipeline.index_documents(docs, batch_size=16)
            >>> print(f"Indexed {stats['successful']} documents")
        """
        if not documents:
            raise ValueError("Cannot index empty document list")
        
        logger.info(f"Starting indexing pipeline for {len(documents)} documents")
        start_time = time.time()
        
        # Track statistics
        stats = {
            'total_documents': len(documents),
            'successful': 0,
            'failed': 0,
            'processing_time': 0.0,
            'avg_time_per_doc': 0.0,
            'batch_size': batch_size,
            'start_vector_id': self.vector_store.get_index_size(),
            'end_vector_id': None
        }
        
        try:
            # Step 1: Extract text for embedding
            logger.info("Extracting text from documents...")
            texts = []
            valid_documents = []
            
            for i, doc in enumerate(documents):
                try:
                    # FIX: Changed from doc.full_text to doc.get_full_text()
                    text = doc.get_full_text()
                    
                    if not text or not text.strip():
                        logger.warning(f"Document {i} has empty text, skipping")
                        stats['failed'] += 1
                        continue
                    
                    texts.append(text)
                    valid_documents.append(doc)
                    
                except Exception as e:
                    logger.error(f"Failed to extract text from document {i}: {e}")
                    stats['failed'] += 1
                    continue
            
            if not texts:
                raise RuntimeError("No valid documents to index (all have empty text)")
            
            logger.info(f"Extracted text from {len(texts)}/{len(documents)} documents")
            
            # Step 2: Generate embeddings
            logger.info(f"Generating embeddings (batch_size={batch_size})...")
            try:
                embeddings = self.embedding_generator.generate_embeddings(
                    texts,
                    batch_size=batch_size,
                    show_progress=show_progress
                )
                logger.info(f"Generated {len(embeddings)} embeddings")
            except Exception as e:
                logger.error(f"Embedding generation failed: {e}")
                raise RuntimeError(f"Could not generate embeddings: {e}")
            
            # Step 3: Add vectors to FAISS
            logger.info("Adding vectors to FAISS index...")
            try:
                start_id = self.vector_store.get_index_size()
                n_added = self.vector_store.add_vectors(embeddings)
                logger.info(f"Added {n_added} vectors to index")
            except Exception as e:
                logger.error(f"Failed to add vectors to FAISS: {e}")
                raise RuntimeError(f"Could not add vectors to index: {e}")
            
            # Step 4: Map vector IDs to metadata
            logger.info("Mapping vector IDs to document metadata...")
            try:
                n_mapped = self.metadata_mapper.add_documents(
                    valid_documents,
                    start_id=start_id
                )
                logger.info(f"Mapped {n_mapped} documents")
            except Exception as e:
                logger.error(f"Failed to map metadata: {e}")
                raise RuntimeError(f"Could not map document metadata: {e}")
            
            # Step 5: Validate consistency
            logger.info("Validating index consistency...")
            is_valid = self.validate_index()
            if not is_valid:
                logger.warning("Index validation failed - size mismatch between store and mapper")
            
            # Update statistics
            stats['successful'] = len(valid_documents)
            stats['end_vector_id'] = self.vector_store.get_index_size() - 1
            stats['processing_time'] = time.time() - start_time
            stats['avg_time_per_doc'] = stats['processing_time'] / len(valid_documents)
            
            logger.info(
                f"Indexing complete: {stats['successful']} successful, "
                f"{stats['failed']} failed, "
                f"{stats['processing_time']:.2f}s total "
                f"({stats['avg_time_per_doc']:.3f}s/doc)"
            )
            
            return stats
            
        except Exception as e:
            stats['processing_time'] = time.time() - start_time
            logger.error(f"Indexing pipeline failed: {e}")
            raise
    
    def validate_index(self) -> bool:
        """
        Validate index integrity.
        
        Checks that vector store size matches metadata mapper size,
        ensuring all vectors have corresponding metadata.
        
        Returns:
            True if index is valid (sizes match), False otherwise
        """
        store_size = self.vector_store.get_index_size()
        mapper_size = self.metadata_mapper.get_size()
        
        is_valid = (store_size == mapper_size)
        
        if is_valid:
            logger.info(f"Index validation passed: {store_size} vectors, {mapper_size} metadata entries")
        else:
            logger.error(
                f"Index validation FAILED: "
                f"vector store has {store_size} vectors, "
                f"metadata mapper has {mapper_size} entries"
            )
        
        return is_valid
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get current indexing statistics.
        
        Returns:
            Dictionary with:
                - total_vectors: Number of vectors in store
                - total_documents: Number of documents in mapper
                - index_valid: Whether sizes match
                - embedding_dimension: Vector dimension
                - document_stats: Statistics from metadata mapper
        """
        store_size = self.vector_store.get_index_size()
        mapper_size = self.metadata_mapper.get_size()
        
        stats = {
            'total_vectors': store_size,
            'total_documents': mapper_size,
            'index_valid': store_size == mapper_size,
            'embedding_dimension': self.vector_store.dimension,
            'document_stats': self.metadata_mapper.get_statistics()
        }
        
        return stats
    
    def index_single_document(
        self,
        document: EmailDocument
    ) -> Optional[int]:
        """
        Index a single document.
        
        Convenience method for adding one document at a time.
        For bulk indexing, use index_documents() for better performance.
        
        Args:
            document: EmailDocument to index
            
        Returns:
            Vector ID assigned to document, or None if indexing failed
            
        Raises:
            ValueError: If document has empty text
        """
        try:
            # Use the batch method with single document
            stats = self.index_documents(
                [document],
                batch_size=1,
                show_progress=False
            )
            
            if stats['successful'] == 1:
                return stats['end_vector_id']
            else:
                logger.error("Failed to index single document")
                return None
                
        except Exception as e:
            logger.error(f"Error indexing single document: {e}")
            return None
    
    def reindex_all(
        self,
        documents: List[EmailDocument],
        batch_size: int = 32,
        show_progress: bool = True
    ) -> Dict[str, Any]:
        """
        Clear existing index and reindex all documents.
        
        Warning: This will delete all existing vectors and metadata!
        
        Args:
            documents: List of EmailDocument instances to index
            batch_size: Batch size for processing
            show_progress: Whether to show progress bar
            
        Returns:
            Indexing statistics dictionary
        """
        logger.warning("Clearing existing index for reindexing...")
        
        # Clear both store and mapper
        old_store_size = self.vector_store.get_index_size()
        old_mapper_size = self.metadata_mapper.get_size()
        
        self.vector_store.reset()
        self.metadata_mapper.clear()
        
        logger.info(
            f"Cleared index: removed {old_store_size} vectors "
            f"and {old_mapper_size} metadata entries"
        )
        
        # Reindex
        return self.index_documents(documents, batch_size, show_progress)
    
    def __repr__(self) -> str:
        """String representation of the pipeline."""
        store_size = self.vector_store.get_index_size()
        mapper_size = self.metadata_mapper.get_size()
        return (
            f"IndexingPipeline("
            f"vectors={store_size}, "
            f"documents={mapper_size}, "
            f"valid={store_size == mapper_size})"
        )