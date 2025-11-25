"""
Configuration settings for Bloomberg RAG System.

Centralized configuration for all components using dataclasses.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List


# ============================================================================
# BASE PATHS
# ============================================================================

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent

# Data directories
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)


# ============================================================================
# OUTLOOK CONFIGURATION
# ============================================================================

@dataclass
class OutlookConfig:
    """Outlook email extraction settings."""
    
    # Folder paths in Outlook (relative to Inbox or absolute)
    source_folder: str = "Inbox/Bloomberg"
    indexed_folder: str = "Inbox/Bloomberg/indexed"
    stubs_folder: str = "Inbox/Bloomberg/stubs"
    processed_folder: str = "Inbox/Bloomberg/processed"
    
    # Processing limits
    max_emails_per_sync: int = 100
    
    # Date filtering (optional)
    days_back: Optional[int] = None  # None = no limit


# ============================================================================
# EMBEDDING CONFIGURATION
# ============================================================================

@dataclass
class EmbeddingConfig:
    """Sentence transformer model settings."""
    
    # Model name (English-only for best performance)
    model_name: str = "all-mpnet-base-v2"
    
    # Device to use
    device: str = "cpu"  # or "cuda" if GPU available
    
    # Batch size for encoding
    batch_size: int = 32
    
    # Normalize embeddings (required for FAISS)
    normalize_embeddings: bool = True
    
    # Expected embedding dimension
    embedding_dim: int = 768  # for all-mpnet-base-v2


# ============================================================================
# VECTOR STORE CONFIGURATION
# ============================================================================

@dataclass
class VectorStoreConfig:
    """FAISS vector store settings."""
    
    # Index type
    index_type: str = "IndexFlatL2"  # or "IndexIVFFlat" for larger datasets
    
    # Persistence paths
    index_path: Path = DATA_DIR / "faiss_index.bin"
    metadata_path: Path = DATA_DIR / "documents_metadata.json"
    
    # Search settings
    default_top_k: int = 20


# ============================================================================
# RETRIEVAL CONFIGURATION
# ============================================================================

@dataclass
class RetrievalConfig:
    """Hybrid retrieval settings."""
    
    # Temporal scoring
    recency_weight: float = 0.3  # weight for recency (0.0-1.0)
    temporal_halflife_days: int = 30  # days for score to halve
    
    # Default search params
    default_top_k: int = 20
    
    # Metadata filtering
    enable_topic_filter: bool = True
    enable_people_filter: bool = True
    enable_date_filter: bool = True
    enable_ticker_filter: bool = True


# ============================================================================
# GOOGLE ADK TOOLS CONFIGURATION
# ============================================================================

@dataclass
class ToolConfig:
    """Google ADK Tools configuration."""
    
    # Result limits
    max_articles_per_call: int = 10  # max articles returned by any tool
    max_snippet_length: int = 200  # max characters for article snippet
    
    # Retrieval defaults (before limiting results)
    default_top_k: int = 20  # retrieve 20, then limit to max_articles_per_call
    
    # Response settings
    include_full_content: bool = False  # if True, include full article body instead of snippet
    
    # Caching (optional for MVP)
    enable_caching: bool = False
    cache_ttl_seconds: int = 300  # 5 minutes
    
    # Timezone for datetime tool
    timezone: str = "UTC"


# ============================================================================
# GOOGLE ADK AGENT CONFIGURATION
# ============================================================================

@dataclass
class AgentConfig:
    """Google ADK Agent configuration."""
    
    # Model settings (via LiteLLM)
    model_name: str = "openai/gpt-4o"  # LiteLLM format
    
    # API Keys (from environment)
    openai_api_key: Optional[str] = field(default_factory=lambda: os.getenv("OPENAI_API_KEY"))
    
    # Session settings
    session_type: str = "memory"  # "memory" or "persistent"
    
    # Response settings
    max_tokens: int = 2000
    temperature: float = 0.7
    
    # Tool settings
    enable_all_tools: bool = True
    enabled_tools: List[str] = field(default_factory=lambda: [
        "hybrid_search",
        "semantic_search",
        "filter_by_date",
        "filter_by_topic",
        "filter_by_people",
        "filter_by_ticker",
        "get_current_datetime"
    ])


# ============================================================================
# PERSISTENCE CONFIGURATION
# ============================================================================

@dataclass
class PersistenceConfig:
    """Data persistence settings."""
    
    # File paths
    emails_pickle: Path = DATA_DIR / "emails.pkl"
    stub_registry_json: Path = DATA_DIR / "stub_registry.json"
    last_sync_json: Path = DATA_DIR / "last_sync.json"
    
    # Backup settings
    enable_backup: bool = True
    backup_dir: Path = DATA_DIR / "backups"
    max_backups: int = 5


# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

@dataclass
class LoggingConfig:
    """Logging settings."""
    
    # Log file
    log_file: Path = LOGS_DIR / "bloomberg_rag.log"
    
    # Log level
    log_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    
    # Format
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Console logging
    console_logging: bool = True


# ============================================================================
# GLOBAL CONFIG INSTANCE
# ============================================================================

# Initialize all configs
outlook_config = OutlookConfig()
embedding_config = EmbeddingConfig()
vectorstore_config = VectorStoreConfig()
retrieval_config = RetrievalConfig()
tool_config = ToolConfig()
agent_config = AgentConfig()
persistence_config = PersistenceConfig()
logging_config = LoggingConfig()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_outlook_config() -> OutlookConfig:
    """Get Outlook configuration."""
    return outlook_config


def get_embedding_config() -> EmbeddingConfig:
    """Get Embedding configuration."""
    return embedding_config


def get_vectorstore_config() -> VectorStoreConfig:
    """Get Vector Store configuration."""
    return vectorstore_config


def get_retrieval_config() -> RetrievalConfig:
    """Get Retrieval configuration."""
    return retrieval_config


def get_tool_config() -> ToolConfig:
    """Get Tool configuration."""
    return tool_config


def get_agent_config() -> AgentConfig:
    """Get Agent configuration."""
    return agent_config


def get_persistence_config() -> PersistenceConfig:
    """Get Persistence configuration."""
    return persistence_config


def get_logging_config() -> LoggingConfig:
    """Get Logging configuration."""
    return logging_config