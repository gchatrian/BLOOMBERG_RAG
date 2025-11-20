"""
Indexing Pipeline for Bloomberg RAG System.

Orchestrates the indexing workflow:
1. Take processed EmailDocuments
2. Generate embeddings in batches
3. Add to FAISS vector store
4. Save index to disk
"""

import logging
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class IndexingStats:
    """Statistics for an indexing run."""
    total_documents: int = 0
    documents_indexed: int = 0
    documents_skipped: int = 0
    errors: int = 0
    start_time: datetime = None
    end_time: datetime = None
    index_size_before: int = 0
    index_size_after: int = 0
    
    def duration_seconds(self) -> float:
        """Calculate duration in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0


class IndexingPipeline:
    """
    Coordinates the indexing workflow for processed documents.
    
    This pipeline handles:
    - Batch embedding generation
    - Adding embeddings to FAISS vector store
    - Incremental indexing (skip already indexed documents)
    - Saving updated index to disk
    - Progress tracking and error handling
    """
    
    def __init__(
        self,
        embedding_generator,
        vector_store,
        batch_size: int = 32
    ):
        """
        Initialize indexing pipeline.
        
        Args:
            embedding_generator: EmbeddingGenerator instance
            vector_store: FAISSStore instance
            batch_size: Number of documents to process in each batch
        """
        self.embedding_generator = embedding_generator
        self.vector_store = vector_store
        self.batch_size = batch_size
        
        self.stats = IndexingStats()
    
    def run(self, documents: List) -> IndexingStats:
        """
        Run the indexing pipeline on a list of documents.
        
        Args:
            documents: List of EmailDocument objects to index
            
        Returns:
            IndexingStats with indexing statistics
        """
        logger.info("Starting indexing pipeline...")
        self.stats = IndexingStats(start_time=datetime.now())
        self.stats.total_documents = len(documents)
        self.stats.index_size_before = self.vector_store.size()
        
        try:
            # Process documents in batches
            for i in range(0, len(documents), self.batch_size):
                batch = documents[i:i + self.batch_size]
                self._process_batch(batch)
            
            # Save index to disk
            self._save_index()
            
            # Finalize stats
            self.stats.end_time = datetime.now()
            self.stats.index_size_after = self.vector_store.size()
            self._log_final_report()
            
            return self.stats
            
        except Exception as e:
            logger.error(f"Indexing pipeline failed: {e}", exc_info=True)
            self.stats.end_time = datetime.now()
            raise
    
    def run_incremental(self, documents: List) -> IndexingStats:
        """
        Run incremental indexing, skipping already indexed documents.
        
        Args:
            documents: List of EmailDocument objects to index
            
        Returns:
            IndexingStats with indexing statistics
        """
        logger.info("Starting incremental indexing pipeline...")
        
        # Filter out already indexed documents
        new_documents = self._filter_new_documents(documents)
        
        logger.info(f"Found {len(new_documents)} new documents to index (out of {len(documents)} total)")
        
        # Run normal indexing on new documents only
        return self.run(new_documents)
    
    def _filter_new_documents(self, documents: List) -> List:
        """
        Filter out documents that are already in the vector store.
        
        Args:
            documents: List of EmailDocument objects
            
        Returns:
            List of documents not yet indexed
        """
        new_documents = []
        
        for doc in documents:
            # Check if document is already in vector store
            if not self.vector_store.has_document(doc.outlook_entry_id):
                new_documents.append(doc)
            else:
                self.stats.documents_skipped += 1
        
        return new_documents
    
    def _process_batch(self, batch: List) -> None:
        """
        Process a batch of documents.
        
        Args:
            batch: List of EmailDocument objects
        """
        logger.info(f"Processing batch of {len(batch)} documents...")
        
        try:
            # Extract full text from documents
            texts = [doc.full_text for doc in batch]
            
            # Generate embeddings for batch
            embeddings = self.embedding_generator.encode_batch(texts)
            
            # Add to vector store
            for doc, embedding in zip(batch, embeddings):
                try:
                    self.vector_store.add_document(
                        embedding=embedding,
                        document=doc
                    )
                    self.stats.documents_indexed += 1
                    
                except Exception as e:
                    logger.error(f"Failed to index document {doc.subject}: {e}", exc_info=True)
                    self.stats.errors += 1
            
            logger.info(f"Batch processed: {len(batch)} documents indexed")
            
        except Exception as e:
            logger.error(f"Failed to process batch: {e}", exc_info=True)
            self.stats.errors += len(batch)
    
    def _save_index(self) -> None:
        """Save the vector store index to disk."""
        try:
            logger.info("Saving index to disk...")
            self.vector_store.save()
            logger.info("Index saved successfully")
        except Exception as e:
            logger.error(f"Failed to save index: {e}", exc_info=True)
            raise
    
    def _log_final_report(self) -> None:
        """Log final indexing statistics."""
        duration = self.stats.duration_seconds()
        docs_per_second = self.stats.documents_indexed / duration if duration > 0 else 0
        
        logger.info("="*60)
        logger.info("INDEXING PIPELINE COMPLETED")
        logger.info("="*60)
        logger.info(f"Total documents: {self.stats.total_documents}")
        logger.info(f"Documents indexed: {self.stats.documents_indexed}")
        logger.info(f"Documents skipped: {self.stats.documents_skipped}")
        logger.info(f"Errors: {self.stats.errors}")
        logger.info(f"Index size before: {self.stats.index_size_before}")
        logger.info(f"Index size after: {self.stats.index_size_after}")
        logger.info(f"Duration: {duration:.2f} seconds")
        logger.info(f"Speed: {docs_per_second:.2f} docs/second")
        logger.info("="*60)
    
    def get_stats(self) -> IndexingStats:
        """
        Get current indexing statistics.
        
        Returns:
            IndexingStats object
        """
        return self.stats