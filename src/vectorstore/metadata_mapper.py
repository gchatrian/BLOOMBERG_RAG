"""
Metadata Mapper for FAISS Vector Store.

Maps vector IDs to EmailDocument objects with metadata.
Uses JSON serialization instead of pickle to avoid pywintypes.datetime issues.
"""

import json
from pathlib import Path
from typing import Dict, Optional, Any
from datetime import datetime
import logging

from src.models import EmailDocument


class MetadataMapper:
    """
    Maps FAISS vector IDs to EmailDocument metadata.
    
    Responsibilities:
    - Store mapping: vector_id → EmailDocument
    - Serialize/deserialize mapping to disk (JSON format)
    - Handle datetime conversion for JSON compatibility
    - Provide lookup by vector_id
    
    Note: Uses JSON instead of pickle to avoid pywintypes.datetime
    serialization issues with Outlook COM objects.
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
    def _serialize_datetime(obj: Any) -> Any:
        """
        Convert datetime objects to ISO format strings recursively.
        
        Handles:
        - datetime.datetime objects
        - pywintypes.datetime objects
        - Dictionaries with datetime values
        - Lists with datetime values
        
        Args:
            obj: Object to serialize
            
        Returns:
            Serialized object with datetime as ISO strings
        """
        # Handle datetime objects (including pywintypes.datetime)
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif type(obj).__name__ == 'datetime':  # pywintypes.datetime
            try:
                # Try to convert to standard datetime first
                dt = datetime(
                    year=obj.year,
                    month=obj.month,
                    day=obj.day,
                    hour=obj.hour,
                    minute=obj.minute,
                    second=obj.second
                )
                return dt.isoformat()
            except:
                return datetime.now().isoformat()
        
        # Handle dictionaries
        elif isinstance(obj, dict):
            return {k: MetadataMapper._serialize_datetime(v) for k, v in obj.items()}
        
        # Handle lists
        elif isinstance(obj, list):
            return [MetadataMapper._serialize_datetime(item) for item in obj]
        
        # Handle tuples (convert to list for JSON)
        elif isinstance(obj, tuple):
            return [MetadataMapper._serialize_datetime(item) for item in obj]
        
        # Handle objects with __dict__ (like EmailDocument, BloombergMetadata)
        elif hasattr(obj, '__dict__'):
            return MetadataMapper._serialize_datetime(obj.__dict__)
        
        # Other types: pass through (will fail if not JSON serializable)
        else:
            return obj
    
    def save(self, path: str) -> None:
        """
        Save metadata mapper to disk in JSON format.
        
        Uses JSON instead of pickle to avoid pywintypes.datetime issues.
        All datetime objects are converted to ISO format strings.
        
        Args:
            path: Path to save JSON file
            
        Raises:
            RuntimeError: If save fails
        """
        try:
            self.logger.info(f"Saving metadata mapper to {path}...")
            
            # Convert all documents to JSON-serializable format
            json_mapping = {}
            
            for vector_id, email_doc in self.id_to_document.items():
                # Convert EmailDocument to dict and serialize datetimes
                doc_dict = self._serialize_datetime(email_doc)
                json_mapping[str(vector_id)] = doc_dict  # JSON keys must be strings
            
            # Ensure directory exists
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            
            # Save as JSON
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(json_mapping, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Saved metadata mapper: {len(json_mapping)} documents")
            
        except Exception as e:
            self.logger.error(f"Failed to save mapper to {path}: {e}", exc_info=True)
            raise RuntimeError(f"Could not save metadata mapper: {e}")
    
    @classmethod
    def load(cls, path: str) -> 'MetadataMapper':
        """
        Load metadata mapper from disk.
        
        Args:
            path: Path to JSON file
            
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
            
            with open(path, 'r', encoding='utf-8') as f:
                json_mapping = json.load(f)
            
            # Convert JSON back to internal format
            # Keys are strings in JSON, convert back to int
            for vector_id_str, doc_dict in json_mapping.items():
                vector_id = int(vector_id_str)
                # Store as dict (we don't need to reconstruct EmailDocument objects
                # since we just need the data for retrieval)
                mapper.id_to_document[vector_id] = doc_dict
            
            mapper.logger.info(f"Loaded metadata mapper: {len(json_mapping)} documents")
            return mapper
            
        except Exception as e:
            mapper.logger.error(f"Failed to load mapper from {path}: {e}")
            raise RuntimeError(f"Could not load metadata mapper: {e}")
    
    def clear(self) -> None:
        """Clear all document mappings."""
        self.id_to_document.clear()
        self.logger.debug("Cleared all document mappings")