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
    - Metadata mapper (pickle)
    
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
    DEFAULT_METADATA_FILE = "documents_metadata.pkl"
    
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
            path: Optional custom path (default: base_dir/documents_metadata.pkl)
            
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
            path: Optional custom path (default: base_dir/documents_metadata.pkl)
            
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
            backup_suffix: Optional custom suffix (default: timestamp)
            
        Raises:
            RuntimeError: If backup fails
        """
        if backup_suffix is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_suffix = f"backup_{timestamp}"
        
        backup_dir = self.base_dir / backup_suffix
        
        try:
            # Create backup directory
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy existing files
            files_to_backup = [
                (self.documents_path, backup_dir / self.DEFAULT_DOCUMENTS_FILE),
                (self.faiss_index_path, backup_dir / self.DEFAULT_FAISS_INDEX_FILE),
                (self.metadata_path, backup_dir / self.DEFAULT_METADATA_FILE)
            ]
            
            backed_up = 0
            for src, dst in files_to_backup:
                if src.exists():
                    shutil.copy2(src, dst)
                    backed_up += 1
            
            logger.info(f"Created backup in {backup_dir} ({backed_up} files)")
            
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            raise RuntimeError(f"Could not create backup: {e}")
    
    def clear_data(self):
        """
        Delete all data files.
        
        Warning: This will permanently delete all saved state!
        """
        files = [
            self.documents_path,
            self.faiss_index_path,
            self.metadata_path
        ]
        
        deleted = 0
        for file in files:
            if file.exists():
                file.unlink()
                deleted += 1
        
        logger.warning(f"Cleared {deleted} data files from {self.base_dir}")
    
    def __repr__(self) -> str:
        """String representation of the persistence manager."""
        status = self.check_data_exists()
        return (
            f"PersistenceManager("
            f"base_dir={self.base_dir}, "
            f"all_present={status['all_present']})"
        )


class DataDirectoryManager:
    """
    Manages data directory structure and maintenance tasks.
    
    Handles:
    - Sync statistics tracking
    - Temporary file management
    - Backup versioning and cleanup
    - Directory validation
    
    Attributes:
        base_dir: Base directory for all data files
        sync_stats_path: Path to sync statistics JSON file
        temp_dir: Directory for temporary files
    """
    
    DEFAULT_SYNC_STATS_FILE = "last_sync.json"
    DEFAULT_TEMP_DIR = "temp"
    
    def __init__(self, base_dir: str = "data"):
        """
        Initialize data directory manager.
        
        Args:
            base_dir: Base directory for all data files (default: "data")
        """
        self.base_dir = Path(base_dir)
        self.sync_stats_path = self.base_dir / self.DEFAULT_SYNC_STATS_FILE
        self.temp_dir = self.base_dir / self.DEFAULT_TEMP_DIR
        
        logger.info(f"DataDirectoryManager initialized with base_dir: {self.base_dir}")
    
    def _ensure_base_dir(self):
        """Ensure base directory exists."""
        if not self.base_dir.exists():
            self.base_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created base directory: {self.base_dir}")
    
    def _ensure_temp_dir(self):
        """Ensure temp directory exists."""
        if not self.temp_dir.exists():
            self.temp_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Created temp directory: {self.temp_dir}")
    
    # ==================== SYNC STATISTICS ====================
    
    def save_sync_stats(self, stats: Dict[str, Any]):
        """
        Save sync statistics to JSON file.
        
        Args:
            stats: Dictionary with sync statistics
                Expected keys: timestamp, total_processed, indexed_count,
                              stubs_count, completed_stubs_count, etc.
                              
        Raises:
            RuntimeError: If save fails
            
        Example:
            >>> stats = {
            ...     'timestamp': '2025-01-15T10:30:00',
            ...     'total_processed': 150,
            ...     'indexed_count': 120,
            ...     'stubs_count': 25,
            ...     'completed_stubs_count': 5
            ... }
            >>> manager.save_sync_stats(stats)
        """
        try:
            self._ensure_base_dir()
            
            # Add timestamp if not present
            if 'timestamp' not in stats:
                stats['timestamp'] = datetime.now().isoformat()
            
            # Save as JSON
            import json
            with open(self.sync_stats_path, 'w') as f:
                json.dump(stats, f, indent=2)
            
            logger.info(f"Saved sync statistics to {self.sync_stats_path}")
            
        except Exception as e:
            logger.error(f"Failed to save sync stats: {e}")
            raise RuntimeError(f"Could not save sync statistics: {e}")
    
    def load_sync_stats(self) -> Optional[Dict[str, Any]]:
        """
        Load sync statistics from JSON file.
        
        Returns:
            Dictionary with sync statistics, or None if file doesn't exist
            
        Raises:
            RuntimeError: If load fails
        """
        if not self.sync_stats_path.exists():
            logger.debug("No sync statistics file found")
            return None
        
        try:
            import json
            with open(self.sync_stats_path, 'r') as f:
                stats = json.load(f)
            
            logger.debug(f"Loaded sync statistics from {self.sync_stats_path}")
            return stats
            
        except Exception as e:
            logger.error(f"Failed to load sync stats: {e}")
            raise RuntimeError(f"Could not load sync statistics: {e}")
    
    def get_last_sync_time(self) -> Optional[datetime]:
        """
        Get timestamp of last sync.
        
        Returns:
            datetime of last sync, or None if no sync stats exist
        """
        stats = self.load_sync_stats()
        if stats and 'timestamp' in stats:
            try:
                return datetime.fromisoformat(stats['timestamp'])
            except:
                return None
        return None
    
    # ==================== TEMPORARY FILES ====================
    
    def create_temp_file(
        self, 
        prefix: str = "temp", 
        suffix: str = ""
    ) -> Path:
        """
        Create temporary file in temp directory.
        
        Args:
            prefix: Filename prefix (default: "temp")
            suffix: Filename suffix/extension (default: "")
            
        Returns:
            Path to created temporary file
            
        Example:
            >>> temp_path = manager.create_temp_file("processing", ".pkl")
        """
        self._ensure_temp_dir()
        
        # Create unique filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"{prefix}_{timestamp}{suffix}"
        temp_path = self.temp_dir / filename
        
        # Create empty file
        temp_path.touch()
        
        logger.debug(f"Created temp file: {temp_path}")
        return temp_path
    
    def cleanup_temp_files(self, max_age_hours: int = 24):
        """
        Remove temporary files older than specified age.
        
        Args:
            max_age_hours: Maximum age in hours (default: 24)
        """
        if not self.temp_dir.exists():
            return
        
        cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
        removed = 0
        
        for file in self.temp_dir.iterdir():
            if file.is_file():
                if file.stat().st_mtime < cutoff_time:
                    file.unlink()
                    removed += 1
        
        logger.info(f"Cleaned up {removed} temp files older than {max_age_hours}h")
    
    def clear_temp_files(self):
        """Remove all temporary files."""
        if not self.temp_dir.exists():
            return
        
        removed = 0
        for file in self.temp_dir.iterdir():
            if file.is_file():
                file.unlink()
                removed += 1
        
        logger.info(f"Cleared {removed} temp files")
    
    # ==================== BACKUP MANAGEMENT ====================
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """
        List all backup directories.
        
        Returns:
            List of dictionaries with backup info:
                - path: Path to backup directory
                - name: Backup directory name
                - created: datetime of creation
                - size: Total size in bytes
                
        Example:
            >>> backups = manager.list_backups()
            >>> for backup in backups:
            ...     print(f"{backup['name']}: {backup['size']} bytes")
        """
        if not self.base_dir.exists():
            return []
        
        backups = []
        
        for item in self.base_dir.iterdir():
            if item.is_dir() and item.name.startswith("backup_"):
                # Calculate total size
                total_size = sum(
                    f.stat().st_size 
                    for f in item.rglob('*') 
                    if f.is_file()
                )
                
                backups.append({
                    'path': item,
                    'name': item.name,
                    'created': datetime.fromtimestamp(item.stat().st_ctime),
                    'size': total_size
                })
        
        # Sort by creation time (newest first)
        backups.sort(key=lambda x: x['created'], reverse=True)
        
        logger.debug(f"Found {len(backups)} backups")
        return backups
    
    def cleanup_old_backups(self, keep_last_n: int = 5):
        """
        Keep only the N most recent backups, delete older ones.
        
        Args:
            keep_last_n: Number of recent backups to keep (default: 5)
        """
        backups = self.list_backups()
        
        if len(backups) <= keep_last_n:
            logger.info(f"No cleanup needed: {len(backups)} backups <= {keep_last_n}")
            return
        
        # Delete backups beyond keep_last_n
        to_delete = backups[keep_last_n:]
        deleted = 0
        
        for backup in to_delete:
            try:
                shutil.rmtree(backup['path'])
                deleted += 1
            except Exception as e:
                logger.error(f"Failed to delete backup {backup['name']}: {e}")
        
        logger.info(f"Cleaned up {deleted} old backups (kept last {keep_last_n})")
    
    def cleanup_old_versions(self, days: int = 30):
        """
        Remove backups older than specified number of days.
        
        Args:
            days: Maximum age in days (default: 30)
        """
        backups = self.list_backups()
        cutoff_date = datetime.now() - timedelta(days=days)
        
        deleted = 0
        for backup in backups:
            if backup['created'] < cutoff_date:
                try:
                    shutil.rmtree(backup['path'])
                    deleted += 1
                except Exception as e:
                    logger.error(f"Failed to delete backup {backup['name']}: {e}")
        
        logger.info(f"Cleaned up {deleted} backups older than {days} days")
    
    def get_oldest_backup(self) -> Optional[Dict[str, Any]]:
        """Get oldest backup info."""
        backups = self.list_backups()
        return backups[-1] if backups else None
    
    def get_newest_backup(self) -> Optional[Dict[str, Any]]:
        """Get newest backup info."""
        backups = self.list_backups()
        return backups[0] if backups else None
    
    # ==================== VALIDATION ====================
    
    def validate_directory_structure(self) -> Dict[str, bool]:
        """
        Validate integrity of data directory structure.
        
        Returns:
            Dictionary with validation results:
                - base_dir_exists: bool
                - temp_dir_exists: bool
                - has_data_files: bool
                - structure_valid: bool (all checks passed)
        """
        validation = {
            'base_dir_exists': self.base_dir.exists(),
            'temp_dir_exists': self.temp_dir.exists(),
            'has_data_files': False,
            'structure_valid': False
        }
        
        if validation['base_dir_exists']:
            # Check for at least one data file
            data_files = [
                self.base_dir / "emails.pkl",
                self.base_dir / "faiss_index.bin",
                self.base_dir / "documents_metadata.pkl"
            ]
            validation['has_data_files'] = any(f.exists() for f in data_files)
        
        # Overall validation
        validation['structure_valid'] = (
            validation['base_dir_exists'] and
            validation['temp_dir_exists']
        )
        
        logger.debug(f"Directory validation: {validation}")
        return validation
    
    def get_directory_info(self) -> Dict[str, Any]:
        """
        Get comprehensive information about data directory.
        
        Returns:
            Dictionary with directory info:
                - base_dir: str
                - total_size: int (bytes)
                - file_count: int
                - backup_count: int
                - temp_file_count: int
                - last_sync: datetime or None
                - backups: list of backup info
        """
        info = {
            'base_dir': str(self.base_dir),
            'total_size': 0,
            'file_count': 0,
            'backup_count': 0,
            'temp_file_count': 0,
            'last_sync': self.get_last_sync_time(),
            'backups': []
        }
        
        if not self.base_dir.exists():
            return info
        
        # Count files and calculate total size
        for file in self.base_dir.rglob('*'):
            if file.is_file():
                info['file_count'] += 1
                info['total_size'] += file.stat().st_size
        
        # Count temp files
        if self.temp_dir.exists():
            info['temp_file_count'] = sum(
                1 for f in self.temp_dir.iterdir() if f.is_file()
            )
        
        # Get backup info
        backups = self.list_backups()
        info['backup_count'] = len(backups)
        info['backups'] = backups
        
        return info
    
    def print_directory_info(self):
        """Print formatted directory information."""
        info = self.get_directory_info()
        
        print(f"\n{'='*60}")
        print(f"Data Directory: {info['base_dir']}")
        print(f"{'='*60}")
        print(f"Total Size: {info['total_size'] / 1024 / 1024:.2f} MB")
        print(f"File Count: {info['file_count']}")
        print(f"Temp Files: {info['temp_file_count']}")
        print(f"Backups: {info['backup_count']}")
        
        if info['last_sync']:
            print(f"Last Sync: {info['last_sync'].strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print("Last Sync: Never")
        
        if info['backups']:
            print(f"\nRecent Backups:")
            for backup in info['backups'][:3]:  # Show 3 most recent
                size_mb = backup['size'] / 1024 / 1024
                created = backup['created'].strftime('%Y-%m-%d %H:%M')
                print(f"  - {backup['name']}: {size_mb:.2f} MB ({created})")
        
        print(f"{'='*60}\n")
    
    def __repr__(self) -> str:
        """String representation of the directory manager."""
        return f"DataDirectoryManager(base_dir={self.base_dir})"