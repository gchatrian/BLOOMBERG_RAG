"""
Persistence Manager for Bloomberg RAG System.

Handles saving and loading of all system state including documents,
vector store, and metadata mappings.
"""

import logging
import pickle
import shutil
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime, timedelta

from src.models import EmailDocument
from src.vectorstore import FAISSVectorStore, MetadataMapper

logger = logging.getLogger(__name__)


class PersistenceManager:
    """
    Manages persistence of system state.
    
    Coordinates saving and loading of:
    - EmailDocument list (pickle)
    - FAISS vector store (binary)
    - Metadata mapper (JSON)
    
    Provides backup and validation functionality.
    
    Attributes:
        base_dir: Base directory for all data files
        documents_path: Path to documents pickle file
        faiss_index_path: Path to FAISS index file
        metadata_path: Path to metadata mapper file
    """
    
    # Default filenames
    DEFAULT_DOCUMENTS_FILE = "emails.pkl"
    DEFAULT_FAISS_INDEX_FILE = "faiss_index.bin"
    DEFAULT_METADATA_FILE = "documents_metadata.json"
    
    def __init__(self, base_dir: str = "data"):
        """
        Initialize persistence manager.
        
        Args:
            base_dir: Base directory for all data files (default: "data")
        """
        self.base_dir = Path(base_dir)
        
        # Define file paths
        self.documents_path = self.base_dir / self.DEFAULT_DOCUMENTS_FILE
        self.faiss_index_path = self.base_dir / self.DEFAULT_FAISS_INDEX_FILE
        self.metadata_path = self.base_dir / self.DEFAULT_METADATA_FILE
        
        logger.info(f"PersistenceManager initialized with base_dir: {self.base_dir}")
    
    def _ensure_base_dir(self):
        """Ensure base directory exists."""
        if not self.base_dir.exists():
            self.base_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created base directory: {self.base_dir}")
    
    # ==================== SAVE METHODS ====================
    
    def save_documents(
        self, 
        documents: List[EmailDocument], 
        path: Optional[str] = None
    ):
        """
        Save list of EmailDocument to disk using pickle.
        
        Args:
            documents: List of EmailDocument instances
            path: Optional custom path (default: base_dir/emails.pkl)
            
        Raises:
            RuntimeError: If save fails
        """
        if path is None:
            path = self.documents_path
        else:
            path = Path(path)
        
        try:
            self._ensure_base_dir()
            
            # Save with pickle
            with open(path, 'wb') as f:
                pickle.dump(documents, f, protocol=pickle.HIGHEST_PROTOCOL)
            
            logger.info(f"Saved {len(documents)} documents to {path}")
            
        except Exception as e:
            logger.error(f"Failed to save documents to {path}: {e}")
            raise RuntimeError(f"Could not save documents: {e}")
    
    def save_vector_store(
        self, 
        faiss_store: FAISSVectorStore, 
        path: Optional[str] = None
    ):
        """
        Save FAISS vector store to disk.
        
        Args:
            faiss_store: FAISSVectorStore instance
            path: Optional custom path (default: base_dir/faiss_index.bin)
            
        Raises:
            RuntimeError: If save fails
        """
        if path is None:
            path = self.faiss_index_path
        else:
            path = Path(path)
        
        try:
            self._ensure_base_dir()
            
            # Use FAISSVectorStore's save method
            faiss_store.save(str(path))
            
            logger.info(f"Saved vector store to {path}")
            
        except Exception as e:
            logger.error(f"Failed to save vector store to {path}: {e}")
            raise RuntimeError(f"Could not save vector store: {e}")
    
    def save_metadata_mapper(
        self, 
        mapper: MetadataMapper, 
        path: Optional[str] = None
    ):
        """
        Save metadata mapper to disk.
        
        Args:
            mapper: MetadataMapper instance
            path: Optional custom path (default: base_dir/documents_metadata.json)
            
        Raises:
            RuntimeError: If save fails
        """
        if path is None:
            path = self.metadata_path
        else:
            path = Path(path)
        
        try:
            self._ensure_base_dir()
            
            # Use MetadataMapper's save method
            mapper.save(str(path))
            
            logger.info(f"Saved metadata mapper to {path}")
            
        except Exception as e:
            logger.error(f"Failed to save metadata mapper to {path}: {e}")
            raise RuntimeError(f"Could not save metadata mapper: {e}")
    
    def save_all(
        self,
        faiss_store: FAISSVectorStore,
        metadata_mapper: MetadataMapper,
        documents: List[EmailDocument]
    ):
        """
        Save all system state (vector store, metadata, documents).
        
        Args:
            faiss_store: FAISSVectorStore instance
            metadata_mapper: MetadataMapper instance
            documents: List of EmailDocument instances
            
        Raises:
            RuntimeError: If any save operation fails
        """
        logger.info("Saving all system state...")
        
        try:
            # Save in order: documents, vector store, metadata
            self.save_documents(documents)
            self.save_vector_store(faiss_store)
            self.save_metadata_mapper(metadata_mapper)
            
            logger.info("Successfully saved all system state")
            
        except Exception as e:
            logger.error(f"Failed to save all system state: {e}")
            raise RuntimeError(f"Could not save system state: {e}")
    
    # ==================== LOAD METHODS ====================
    
    def load_documents(
        self, 
        path: Optional[str] = None
    ) -> List[EmailDocument]:
        """
        Load list of EmailDocument from disk.
        
        Args:
            path: Optional custom path (default: base_dir/emails.pkl)
            
        Returns:
            List of EmailDocument instances
            
        Raises:
            FileNotFoundError: If file doesn't exist
            RuntimeError: If load fails
        """
        if path is None:
            path = self.documents_path
        else:
            path = Path(path)
        
        if not path.exists():
            raise FileNotFoundError(f"Documents file not found: {path}")
        
        try:
            with open(path, 'rb') as f:
                documents = pickle.load(f)
            
            if not isinstance(documents, list):
                raise ValueError(f"Loaded data is not a list: {type(documents)}")
            
            logger.info(f"Loaded {len(documents)} documents from {path}")
            return documents
            
        except Exception as e:
            logger.error(f"Failed to load documents from {path}: {e}")
            raise RuntimeError(f"Could not load documents: {e}")
    
    def load_vector_store(
        self, 
        path: Optional[str] = None,
        dimension: int = 384
    ) -> FAISSVectorStore:
        """
        Load FAISS vector store from disk.
        
        Args:
            path: Optional custom path (default: base_dir/faiss_index.bin)
            dimension: Expected embedding dimension (default: 384)
            
        Returns:
            Loaded FAISSVectorStore instance
            
        Raises:
            FileNotFoundError: If file doesn't exist
            RuntimeError: If load fails
        """
        if path is None:
            path = self.faiss_index_path
        else:
            path = Path(path)
        
        if not path.exists():
            raise FileNotFoundError(f"Vector store file not found: {path}")
        
        try:
            # Use FAISSVectorStore's load method
            faiss_store = FAISSVectorStore.load(str(path), dimension)
            
            logger.info(f"Loaded vector store from {path}")
            return faiss_store
            
        except Exception as e:
            logger.error(f"Failed to load vector store from {path}: {e}")
            raise RuntimeError(f"Could not load vector store: {e}")
    
    def load_metadata_mapper(
        self, 
        path: Optional[str] = None
    ) -> MetadataMapper:
        """
        Load metadata mapper from disk.
        
        Args:
            path: Optional custom path (default: base_dir/documents_metadata.json)
            
        Returns:
            Loaded MetadataMapper instance
            
        Raises:
            FileNotFoundError: If file doesn't exist
            RuntimeError: If load fails
        """
        if path is None:
            path = self.metadata_path
        else:
            path = Path(path)
        
        if not path.exists():
            raise FileNotFoundError(f"Metadata mapper file not found: {path}")
        
        try:
            # Use MetadataMapper's load method
            mapper = MetadataMapper.load(str(path))
            
            logger.info(f"Loaded metadata mapper from {path}")
            return mapper
            
        except Exception as e:
            logger.error(f"Failed to load metadata mapper from {path}: {e}")
            raise RuntimeError(f"Could not load metadata mapper: {e}")
    
    def load_all(
        self, 
        dimension: int = 384
    ) -> Tuple[FAISSVectorStore, MetadataMapper, List[EmailDocument]]:
        """
        Load all system state (vector store, metadata, documents).
        
        Args:
            dimension: Expected embedding dimension (default: 384)
            
        Returns:
            Tuple of (FAISSVectorStore, MetadataMapper, List[EmailDocument])
            
        Raises:
            FileNotFoundError: If any required file doesn't exist
            RuntimeError: If any load operation fails
        """
        logger.info("Loading all system state...")
        
        try:
            # Load in order: documents, vector store, metadata
            documents = self.load_documents()
            faiss_store = self.load_vector_store(dimension=dimension)
            metadata_mapper = self.load_metadata_mapper()
            
            logger.info("Successfully loaded all system state")
            
            return faiss_store, metadata_mapper, documents
            
        except Exception as e:
            logger.error(f"Failed to load all system state: {e}")
            raise
    
    # ==================== UTILITY METHODS ====================
    
    def check_data_exists(self) -> Dict[str, bool]:
        """
        Check which data files exist.
        
        Returns:
            Dictionary with existence status for each file:
                - documents: bool
                - faiss_index: bool
                - metadata: bool
                - all_present: bool
        """
        status = {
            'documents': self.documents_path.exists(),
            'faiss_index': self.faiss_index_path.exists(),
            'metadata': self.metadata_path.exists()
        }
        
        status['all_present'] = all(status.values())
        
        logger.debug(f"Data existence check: {status}")
        return status
    
    def get_last_modified(self) -> Optional[datetime]:
        """
        Get last modification time of any data file.
        
        Returns:
            datetime of most recent modification, or None if no files exist
        """
        files = [
            self.documents_path,
            self.faiss_index_path,
            self.metadata_path
        ]
        
        existing_files = [f for f in files if f.exists()]
        
        if not existing_files:
            return None
        
        # Get most recent modification time
        mod_times = [f.stat().st_mtime for f in existing_files]
        latest = max(mod_times)
        
        return datetime.fromtimestamp(latest)
    
    def get_data_size(self) -> Dict[str, int]:
        """
        Get size of data files in bytes.
        
        Returns:
            Dictionary with file sizes:
                - documents: int (bytes)
                - faiss_index: int (bytes)
                - metadata: int (bytes)
                - total: int (bytes)
        """
        sizes = {}
        
        if self.documents_path.exists():
            sizes['documents'] = self.documents_path.stat().st_size
        else:
            sizes['documents'] = 0
        
        if self.faiss_index_path.exists():
            sizes['faiss_index'] = self.faiss_index_path.stat().st_size
        else:
            sizes['faiss_index'] = 0
        
        if self.metadata_path.exists():
            sizes['metadata'] = self.metadata_path.stat().st_size
        else:
            sizes['metadata'] = 0
        
        sizes['total'] = sum(sizes.values())
        
        return sizes
    
    def create_backup(self, backup_suffix: Optional[str] = None):
        """
        Create timestamped backup of all data files.
        
        Args:
            backup_suffix: Optional suffix for backup folder name
            
        Returns:
            Path to backup directory
            
        Raises:
            RuntimeError: If backup fails
        """
        # Create backup directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        suffix = f"_{backup_suffix}" if backup_suffix else ""
        backup_dir = self.base_dir / "backups" / f"backup_{timestamp}{suffix}"
        
        try:
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy each file if it exists
            for src_path in [self.documents_path, self.faiss_index_path, self.metadata_path]:
                if src_path.exists():
                    dst_path = backup_dir / src_path.name
                    shutil.copy2(src_path, dst_path)
                    logger.debug(f"Backed up {src_path.name}")
            
            logger.info(f"Created backup at {backup_dir}")
            return backup_dir
            
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            raise RuntimeError(f"Could not create backup: {e}")
    
    def cleanup_old_backups(self, max_backups: int = 5):
        """
        Remove old backups, keeping only the most recent ones.
        
        Args:
            max_backups: Maximum number of backups to keep (default: 5)
        """
        backup_base = self.base_dir / "backups"
        
        if not backup_base.exists():
            return
        
        # Get all backup directories sorted by modification time
        backups = sorted(
            [d for d in backup_base.iterdir() if d.is_dir()],
            key=lambda d: d.stat().st_mtime,
            reverse=True
        )
        
        # Remove old backups
        for old_backup in backups[max_backups:]:
            try:
                shutil.rmtree(old_backup)
                logger.info(f"Removed old backup: {old_backup.name}")
            except Exception as e:
                logger.warning(f"Failed to remove backup {old_backup}: {e}")