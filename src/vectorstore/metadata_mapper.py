"""
Metadata Mapper for Bloomberg RAG System.

Maintains bidirectional mapping between FAISS vector IDs and EmailDocument metadata.
Handles serialization and retrieval of document metadata.
"""

import logging
import pickle
from typing import Dict, List, Optional
from pathlib import Path

from src.models import EmailDocument

logger = logging.getLogger(__name__)


class MetadataMapper:
    """
    Maps FAISS vector IDs to EmailDocument metadata.
    
    Maintains a dictionary that associates each vector ID (integer) with
    its corresponding EmailDocument. Supports serialization for persistence.
    
    Attributes:
        id_to_document: Dictionary mapping vector_id (int) to EmailDocument
    """
    
    def __init__(self):
        """Initialize empty metadata mapper."""
        self.id_to_document: Dict[int, EmailDocument] = {}
        logger.info("MetadataMapper initialized")
    
    def add_document(self, vector_id: int, email_doc: EmailDocument):
        """
        Add document metadata for a vector ID.
        
        Args:
            vector_id: FAISS vector ID (integer index)
            email_doc: EmailDocument instance with all metadata
            
        Raises:
            ValueError: If vector_id is negative
            TypeError: If email_doc is not an EmailDocument
            
        Example:
            >>> mapper = MetadataMapper()
            >>> doc = EmailDocument(subject="Test", body="Content", ...)
            >>> mapper.add_document(0, doc)
        """
        if vector_id < 0:
            raise ValueError(f"Vector ID must be non-negative, got {vector_id}")
        
        if not isinstance(email_doc, EmailDocument):
            raise TypeError(
                f"email_doc must be EmailDocument, got {type(email_doc)}"
            )
        
        if vector_id in self.id_to_document:
            logger.warning(f"Overwriting existing document for vector ID {vector_id}")
        
        self.id_to_document[vector_id] = email_doc
        logger.debug(f"Added document for vector ID {vector_id}")
    
    def add_documents(self, documents: List[EmailDocument], start_id: int = 0):
        """
        Add multiple documents starting from a given ID.
        
        Args:
            documents: List of EmailDocument instances
            start_id: Starting vector ID (default: 0)
            
        Returns:
            Number of documents added
            
        Example:
            >>> docs = [doc1, doc2, doc3]
            >>> mapper.add_documents(docs, start_id=10)
            3
        """
        for i, doc in enumerate(documents):
            vector_id = start_id + i
            self.add_document(vector_id, doc)
        
        logger.info(f"Added {len(documents)} documents (IDs {start_id}-{start_id + len(documents) - 1})")
        return len(documents)
    
    def get_document(self, vector_id: int) -> Optional[EmailDocument]:
        """
        Retrieve document metadata for a vector ID.
        
        Args:
            vector_id: FAISS vector ID
            
        Returns:
            EmailDocument if found, None otherwise
            
        Example:
            >>> doc = mapper.get_document(5)
            >>> if doc:
            ...     print(doc.subject)
        """
        doc = self.id_to_document.get(vector_id)
        
        if doc is None:
            logger.debug(f"No document found for vector ID {vector_id}")
        
        return doc
    
    def get_documents(self, vector_ids: List[int]) -> List[Optional[EmailDocument]]:
        """
        Retrieve multiple documents by vector IDs.
        
        Args:
            vector_ids: List of FAISS vector IDs
            
        Returns:
            List of EmailDocuments (or None for missing IDs), in same order as input
            
        Example:
            >>> docs = mapper.get_documents([0, 5, 10])
            >>> valid_docs = [d for d in docs if d is not None]
        """
        documents = [self.get_document(vid) for vid in vector_ids]
        
        found = sum(1 for d in documents if d is not None)
        logger.debug(f"Retrieved {found}/{len(vector_ids)} documents")
        
        return documents
    
    def get_all_documents(self) -> List[EmailDocument]:
        """
        Get all documents in the mapper.
        
        Returns:
            List of all EmailDocument instances (unsorted)
        """
        return list(self.id_to_document.values())
    
    def get_all_metadata(self) -> Dict[int, EmailDocument]:
        """
        Get complete mapping dictionary.
        
        Returns:
            Dictionary of vector_id to EmailDocument
            
        Warning:
            Returns reference to internal dict. Do not modify directly.
        """
        return self.id_to_document
    
    def has_document(self, vector_id: int) -> bool:
        """
        Check if document exists for vector ID.
        
        Args:
            vector_id: FAISS vector ID
            
        Returns:
            True if document exists
        """
        return vector_id in self.id_to_document
    
    def get_size(self) -> int:
        """
        Get number of documents in mapper.
        
        Returns:
            Number of mapped documents
        """
        return len(self.id_to_document)
    
    def is_empty(self) -> bool:
        """
        Check if mapper is empty.
        
        Returns:
            True if no documents are mapped
        """
        return len(self.id_to_document) == 0
    
    def remove_document(self, vector_id: int) -> bool:
        """
        Remove document from mapper.
        
        Args:
            vector_id: FAISS vector ID to remove
            
        Returns:
            True if document was removed, False if not found
        """
        if vector_id in self.id_to_document:
            del self.id_to_document[vector_id]
            logger.debug(f"Removed document for vector ID {vector_id}")
            return True
        else:
            logger.debug(f"No document to remove for vector ID {vector_id}")
            return False
    
    def clear(self):
        """
        Remove all documents from mapper.
        
        Warning: This will delete all mappings!
        """
        old_size = self.get_size()
        self.id_to_document.clear()
        logger.warning(f"Cleared mapper (removed {old_size} documents)")
    
    def save(self, path: str):
        """
        Save mapper to disk using pickle.
        
        Args:
            path: File path to save mapper (will create parent dirs if needed)
            
        Raises:
            RuntimeError: If save fails
            
        Example:
            >>> mapper.save("data/documents_metadata.pkl")
        """
        try:
            # Ensure parent directory exists
            path_obj = Path(path)
            path_obj.parent.mkdir(parents=True, exist_ok=True)
            
            # Save with pickle
            with open(path, 'wb') as f:
                pickle.dump(self.id_to_document, f, protocol=pickle.HIGHEST_PROTOCOL)
            
            logger.info(f"Saved metadata mapper to {path} ({self.get_size()} documents)")
            
        except Exception as e:
            logger.error(f"Failed to save mapper to {path}: {e}")
            raise RuntimeError(f"Could not save metadata mapper: {e}")
    
    @classmethod
    def load(cls, path: str) -> 'MetadataMapper':
        """
        Load mapper from disk.
        
        Args:
            path: File path to load mapper from
            
        Returns:
            Loaded MetadataMapper instance
            
        Raises:
            FileNotFoundError: If mapper file doesn't exist
            RuntimeError: If load fails
            
        Example:
            >>> mapper = MetadataMapper.load("data/documents_metadata.pkl")
        """
        path_obj = Path(path)
        
        if not path_obj.exists():
            raise FileNotFoundError(f"Mapper file not found: {path}")
        
        try:
            # Load with pickle
            with open(path, 'rb') as f:
                id_to_document = pickle.load(f)
            
            # Validate loaded data
            if not isinstance(id_to_document, dict):
                raise ValueError(f"Loaded data is not a dict: {type(id_to_document)}")
            
            # Create instance and assign loaded mapping
            mapper = cls()
            mapper.id_to_document = id_to_document
            
            logger.info(f"Loaded metadata mapper from {path} ({mapper.get_size()} documents)")
            
            return mapper
            
        except Exception as e:
            logger.error(f"Failed to load mapper from {path}: {e}")
            raise RuntimeError(f"Could not load metadata mapper: {e}")
    
    def get_statistics(self) -> Dict[str, int]:
        """
        Get statistics about mapped documents.
        
        Returns:
            Dictionary with stats (total_docs, with_topics, with_people, etc.)
        """
        stats = {
            'total_docs': self.get_size(),
            'with_topics': 0,
            'with_people': 0,
            'with_story_id': 0,
            'stub_status': {}
        }
        
        for doc in self.id_to_document.values():
            if doc.metadata and doc.metadata.topics:
                stats['with_topics'] += 1
            if doc.metadata and doc.metadata.people:
                stats['with_people'] += 1
            if doc.metadata and doc.metadata.story_id:
                stats['with_story_id'] += 1
            
            # Count by stub status
            status = doc.status or 'unknown'
            stats['stub_status'][status] = stats['stub_status'].get(status, 0) + 1
        
        return stats
    
    def __repr__(self) -> str:
        """String representation of the mapper."""
        size = self.get_size()
        return f"MetadataMapper(size={size})"
    
    def __len__(self) -> int:
        """Support len() function."""
        return self.get_size()