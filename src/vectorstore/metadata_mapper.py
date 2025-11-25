"""
Metadata Mapper for Bloomberg RAG System.

Maintains bidirectional mapping between FAISS vector IDs and EmailDocument metadata.
Handles serialization and retrieval of document metadata.
"""

import logging
import pickle
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime

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
    
    @staticmethod
    def _convert_pywintypes_datetime(obj):
        """
        Convert pywintypes.datetime to standard datetime.datetime recursively.
        
        This is needed because pywintypes.datetime from Outlook COM interface
        cannot be pickled. We need to convert them to standard Python datetime.
        
        Args:
            obj: Object to convert (can be any type)
            
        Returns:
            Converted object with all pywintypes.datetime replaced by datetime.datetime
        """
        # Check if it's a pywintypes.datetime
        if type(obj).__name__ == 'datetime' and hasattr(obj, 'utctimetuple'):
            # Convert pywintypes.datetime to standard datetime
            try:
                # Use the utctimetuple method available in pywintypes.datetime
                import time
                timestamp = time.mktime(obj.timetuple())
                return datetime.fromtimestamp(timestamp)
            except Exception as e:
                logger.warning(f"Failed to convert pywintypes.datetime: {e}, using current time")
                return datetime.now()
        
        # Recursively handle common container types
        elif isinstance(obj, dict):
            return {k: MetadataMapper._convert_pywintypes_datetime(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [MetadataMapper._convert_pywintypes_datetime(item) for item in obj]
        elif isinstance(obj, tuple):
            return tuple(MetadataMapper._convert_pywintypes_datetime(item) for item in obj)
        elif hasattr(obj, '__dict__'):
            # Handle objects with __dict__ (like dataclasses)
            for attr_name in dir(obj):
                if not attr_name.startswith('_'):
                    try:
                        attr_value = getattr(obj, attr_name)
                        if type(attr_value).__name__ == 'datetime':
                            # Convert and set the attribute
                            converted = MetadataMapper._convert_pywintypes_datetime(attr_value)
                            setattr(obj, attr_name, converted)
                    except (AttributeError, TypeError):
                        pass
            return obj
        else:
            # Return as-is for primitive types
            return obj
    
    def save(self, path: str):
        """
        Save mapper to disk using pickle.
        
        Converts all pywintypes.datetime objects to standard datetime.datetime
        before pickling to avoid serialization errors.
        
        Args:
            path: File path to save mapper (will create parent dirs if needed)
            
        Raises:
            RuntimeError: If save fails
        """
        try:
            # Ensure parent directory exists
            path_obj = Path(path)
            path_obj.parent.mkdir(parents=True, exist_ok=True)
            
            # =================================================================
            # FIX: Convert all pywintypes.datetime to standard datetime
            # =================================================================
            logger.debug("Converting pywintypes.datetime to standard datetime...")
            converted_mapping = {}
            
            for vector_id, email_doc in self.id_to_document.items():
                # Deep copy and convert the document
                converted_doc = MetadataMapper._convert_pywintypes_datetime(email_doc)
                converted_mapping[vector_id] = converted_doc
            
            # Save the converted mapping
            with open(path, 'wb') as f:
                pickle.dump(converted_mapping, f, protocol=pickle.HIGHEST_PROTOCOL)
            
            logger.info(f"Saved metadata mapper to {path} ({self.get_size()} documents)")
            
        except Exception as e:
            logger.error(f"Failed to save mapper to {path}: {e}", exc_info=True)
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
            if doc.bloomberg_metadata and doc.bloomberg_metadata.topics:
                stats['with_topics'] += 1
            if doc.bloomberg_metadata and doc.bloomberg_metadata.people:
                stats['with_people'] += 1
            if doc.bloomberg_metadata and doc.bloomberg_metadata.story_id:
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


# Example usage
if __name__ == "__main__":
    from src.models import EmailDocument, BloombergMetadata
    
    logging.basicConfig(level=logging.DEBUG)
    
    print("="*60)
    print("METADATA MAPPER TEST")
    print("="*60)
    
    # Create mapper
    mapper = MetadataMapper()
    
    # Create sample documents
    metadata1 = BloombergMetadata(
        category="BFW",
        story_id="L123ABC",
        topics=["AI", "Tech"],
        people=["Elon Musk"]
    )
    
    doc1 = EmailDocument(
        outlook_entry_id="ABC123",
        subject="Test Email 1",
        body="Content 1",
        raw_body="Raw 1",
        sender="test@test.com",
        received_date=datetime.now(),
        bloomberg_metadata=metadata1,
        status="complete",
        is_stub=False
    )
    
    # Add documents
    mapper.add_document(0, doc1)
    
    print(f"Added {mapper.get_size()} documents")
    
    # Save
    test_path = "test_metadata_mapper.pkl"
    mapper.save(test_path)
    print(f"Saved to {test_path}")
    
    # Load
    loaded_mapper = MetadataMapper.load(test_path)
    print(f"Loaded {loaded_mapper.get_size()} documents")
    
    # Cleanup
    import os
    if os.path.exists(test_path):
        os.remove(test_path)
        print("Cleaned up test file")