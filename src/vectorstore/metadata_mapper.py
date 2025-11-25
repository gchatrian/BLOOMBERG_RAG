"""
Metadata Mapper for FAISS Vector Store.

Maps vector IDs to EmailDocument objects with metadata.
Handles serialization with proper pywintypes.datetime conversion.
"""

import pickle
import json
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
import logging

from src.models import EmailDocument


class MetadataMapper:
    """
    Maps FAISS vector IDs to EmailDocument metadata.
    
    Responsibilities:
    - Store mapping: vector_id → EmailDocument
    - Serialize/deserialize mapping to disk
    - Handle pywintypes.datetime conversion for Outlook dates
    - Provide lookup by vector_id
    """
    
    def __init__(self):
        """Initialize metadata mapper."""
        self.id_to_document: Dict[int, EmailDocument] = {}
        self.logger = logging.getLogger(__name__)
        self.logger.info("MetadataMapper initialized")
    
    def add_document(self, vector_id: int, document: EmailDocument) -> None:
        """
        Add document metadata for a vector ID.
        
        Args:
            vector_id: FAISS vector index
            document: EmailDocument with metadata
        """
        self.id_to_document[vector_id] = document
        self.logger.debug(f"Added document metadata for vector_id {vector_id}")
    
    def get_document(self, vector_id: int) -> Optional[EmailDocument]:
        """
        Get document metadata by vector ID.
        
        Args:
            vector_id: FAISS vector index
            
        Returns:
            EmailDocument or None if not found
        """
        return self.id_to_document.get(vector_id)
    
    def get_all_documents(self) -> Dict[int, EmailDocument]:
        """
        Get all document mappings.
        
        Returns:
            Dictionary of vector_id → EmailDocument
        """
        return self.id_to_document.copy()
    
    def size(self) -> int:
        """
        Get number of documents in mapper.
        
        Returns:
            Count of documents
        """
        return len(self.id_to_document)
    
    @staticmethod
    def _convert_to_standard_datetime(obj):
        """
        Convert pywintypes.datetime to standard datetime recursively.
        
        Handles:
        - pywintypes.datetime objects
        - Dictionaries with datetime values
        - Lists with datetime values
        - EmailDocument objects
        - BloombergMetadata objects
        
        Args:
            obj: Object to convert
            
        Returns:
            Converted object with standard datetime objects
        """
        # Handle pywintypes.datetime
        if type(obj).__name__ == 'datetime' and hasattr(obj, 'timestamp'):
            try:
                # Convert to standard datetime
                return datetime.fromtimestamp(obj.timestamp())
            except:
                # Fallback: try to extract components
                try:
                    return datetime(
                        year=obj.year,
                        month=obj.month,
                        day=obj.day,
                        hour=obj.hour,
                        minute=obj.minute,
                        second=obj.second
                    )
                except:
                    # Last resort: return current time
                    return datetime.now()
        
        # Handle standard datetime (pass through)
        elif isinstance(obj, datetime):
            return obj
        
        # Handle EmailDocument objects - convert to dict
        elif hasattr(obj, '__dict__') and hasattr(obj, 'outlook_entry_id'):
            # This is an EmailDocument
            obj_dict = {}
            for key, value in obj.__dict__.items():
                obj_dict[key] = MetadataMapper._convert_to_standard_datetime(value)
            return obj_dict
        
        # Handle dictionaries
        elif isinstance(obj, dict):
            return {
                k: MetadataMapper._convert_to_standard_datetime(v) 
                for k, v in obj.items()
            }
        
        # Handle lists
        elif isinstance(obj, list):
            return [MetadataMapper._convert_to_standard_datetime(item) for item in obj]
        
        # Handle tuples
        elif isinstance(obj, tuple):
            return tuple(MetadataMapper._convert_to_standard_datetime(item) for item in obj)
        
        # Other types: pass through
        else:
            return obj
    
    def save(self, path: str) -> None:
        """
        Save metadata mapper to disk with pywintypes.datetime conversion.
        
        CRITICAL: Converts all pywintypes.datetime objects to standard
        datetime.datetime before pickling to avoid serialization errors.
        
        Args:
            path: Path to save pickle file
            
        Raises:
            RuntimeError: If save fails
        """
        try:
            self.logger.info(f"Saving metadata mapper to {path}...")
            
            # Convert all documents to serializable format
            # This converts pywintypes.datetime → datetime.datetime
            converted_mapping = {}
            
            for vector_id, email_doc in self.id_to_document.items():
                # Convert EmailDocument and all nested objects
                converted_doc = self._convert_to_standard_datetime(email_doc)
                converted_mapping[vector_id] = converted_doc
            
            # Ensure directory exists
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            
            # Save with pickle
            with open(path, 'wb') as f:
                pickle.dump(converted_mapping, f, protocol=pickle.HIGHEST_PROTOCOL)
            
            self.logger.info(f"Saved metadata mapper: {len(converted_mapping)} documents")
            
        except Exception as e:
            self.logger.error(f"Failed to save mapper to {path}: {e}", exc_info=True)
            raise RuntimeError(f"Could not save metadata mapper: {e}")
    
    @classmethod
    def load(cls, path: str) -> 'MetadataMapper':
        """
        Load metadata mapper from disk.
        
        Args:
            path: Path to pickle file
            
        Returns:
            MetadataMapper instance
            
        Raises:
            FileNotFoundError: If file doesn't exist
            RuntimeError: If load fails
        """
        mapper = cls()
        
        if not Path(path).exists():
            raise FileNotFoundError(f"Metadata mapper file not found: {path}")
        
        try:
            mapper.logger.info(f"Loading metadata mapper from {path}...")
            
            with open(path, 'rb') as f:
                loaded_mapping = pickle.load(f)
            
            # Loaded data is already in dict format (converted during save)
            # We can use it directly or reconstruct EmailDocument objects
            mapper.id_to_document = loaded_mapping
            
            mapper.logger.info(f"Loaded metadata mapper: {len(loaded_mapping)} documents")
            return mapper
            
        except Exception as e:
            mapper.logger.error(f"Failed to load mapper from {path}: {e}")
            raise RuntimeError(f"Could not load metadata mapper: {e}")
    
    def clear(self) -> None:
        """Clear all document mappings."""
        self.id_to_document.clear()
        self.logger.debug("Cleared all document mappings")