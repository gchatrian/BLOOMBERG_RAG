#!/usr/bin/env python3
"""
Sync Emails Script for Bloomberg RAG System.

This script performs complete email synchronization:
1. Extracts emails from Outlook source folder
2. Identifies stubs and complete emails
3. Moves stubs to /stubs/ folder
4. Processes complete emails: cleans, extracts metadata, embeds, moves to /indexed/
5. Matches complete emails with existing stubs and moves matched stubs to /processed/
6. Generates stub report
7. Shows final statistics

Usage:
    python scripts/sync_emails.py
    python scripts/sync_emails.py --max-emails 100
    python scripts/sync_emails.py --verbose
"""

import sys
import logging
import argparse
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.orchestration.ingestion_pipeline import IngestionPipeline
from src.outlook.extractor import OutlookExtractor
from src.processing.cleaner import ContentCleaner
from src.processing.metadata_extractor import MetadataExtractor
from src.processing.document_builder import DocumentBuilder
from src.stub.detector import StubDetector
from src.stub.registry import StubRegistry
from src.stub.manager import StubManager
from src.stub.matcher import StubMatcher
from src.stub.reporter import StubReporter
from src.embedding.generator import EmbeddingGenerator
from src.vectorstore.faiss_store import FAISSVectorStore
from src.vectorstore.metadata_mapper import MetadataMapper
from config.settings import (
    get_outlook_config,
    get_embedding_config,
    get_vectorstore_config,
    get_persistence_config
)


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    
    # Ensure logs directory exists
    (PROJECT_ROOT / 'logs').mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(PROJECT_ROOT / 'logs' / 'sync_emails.log')
        ]
    )


def initialize_components(max_emails: int = None):
    """
    Initialize all components needed for ingestion pipeline.
    
    Args:
        max_emails: Maximum number of emails to process (None = no limit)
        
    Returns:
        Tuple of initialized components
    """
    logger = logging.getLogger(__name__)
    logger.info("Initializing components...")
    
    # Configurations
    outlook_config = get_outlook_config()
    embedding_config = get_embedding_config()
    vectorstore_config = get_vectorstore_config()
    persistence_config = get_persistence_config()
    
    # Override max_emails if specified
    if max_emails:
        outlook_config.max_emails_per_sync = max_emails
    
    # Initialize OutlookExtractor
    outlook_extractor = OutlookExtractor(
        outlook_config.source_folder,
        outlook_config.indexed_folder,
        outlook_config.stubs_folder,
        outlook_config.processed_folder
    )
    
    # Initialize processing components
    content_cleaner = ContentCleaner()
    metadata_extractor = MetadataExtractor()
    document_builder = DocumentBuilder()
    
    # StubDetector requires content_cleaner as first parameter
    stub_detector = StubDetector(content_cleaner)
    
    # Initialize stub management components
    stub_registry = StubRegistry(persistence_config.stub_registry_json)
    stub_manager = StubManager(stub_registry)
    
    # StubMatcher requires registry parameter
    stub_matcher = StubMatcher(stub_registry)
    
    # Initialize embedding components
    embedding_generator = EmbeddingGenerator(embedding_config.model_name)

    # =================================================================
    # FIX: Load existing metadata mapper OR create new one
    # This ensures FAISS vector IDs stay synchronized with metadata
    # =================================================================
    metadata_path = vectorstore_config.index_path.parent / "documents_metadata.json"
    if metadata_path.exists():
        logger.info(f"Loading existing metadata mapper from {metadata_path}")
        metadata_mapper = MetadataMapper.load(str(metadata_path))
        logger.info(f"Loaded metadata mapper with {metadata_mapper.size()} documents")
    else:
        logger.info("No existing metadata mapper found, creating new one")
        metadata_mapper = MetadataMapper()
    
    # Load or create vector store
    if vectorstore_config.index_path.exists():
        logger.info(f"Loading existing vector store from {vectorstore_config.index_path}")
        vector_store = FAISSVectorStore.load(
            str(vectorstore_config.index_path),
            embedding_config.embedding_dim
        )
        logger.info(f"Loaded vector store with {vector_store.get_index_size()} vectors")
    else:
        logger.info("No existing vector store found, creating new one")
        vector_store = FAISSVectorStore(embedding_config.embedding_dim)
    
    # =================================================================
    # VALIDATION: Check that FAISS and MetadataMapper are in sync
    # =================================================================
    faiss_size = vector_store.get_index_size()
    mapper_size = metadata_mapper.size()
    if faiss_size != mapper_size:
        logger.warning(
            f"SIZE MISMATCH: FAISS has {faiss_size} vectors, "
            f"MetadataMapper has {mapper_size} documents. "
            f"Consider running with --reset to rebuild index."
        )
    
    logger.info("Components initialized successfully")
    
    return (
        outlook_extractor,
        content_cleaner,
        metadata_extractor,
        document_builder,
        stub_detector,
        stub_registry,
        stub_manager,
        stub_matcher,
        embedding_generator,
        vector_store,
        metadata_mapper,
        vectorstore_config
    )


def generate_stub_report(stub_registry, stats=None) -> None:
    """
    Generate and display stub report.
    
    Args:
        stub_registry: StubRegistry instance
        stats: Optional IngestionStats instance
    """
    # StubReporter() takes NO arguments in __init__
    reporter = StubReporter()
    
    # Convert stats to dict if provided
    session_stats = None
    if stats:
        session_stats = {
            'stubs_created': stats.stubs_created,
            'stubs_completed': stats.stubs_completed
        }
    
    # Pass registry (and optional session_stats) to generate_report()
    report = reporter.generate_report(stub_registry, session_stats)
    print(report)


def save_sync_stats(stats) -> None:
    """
    Save sync statistics to JSON file.
    
    Args:
        stats: IngestionStats instance
    """
    stats_path = PROJECT_ROOT / 'data' / 'last_sync.json'
    stats_path.parent.mkdir(exist_ok=True)
    
    stats_dict = {
        'timestamp': datetime.now().isoformat(),
        'total_emails_processed': stats.total_emails_processed,
        'complete_indexed': stats.complete_indexed,
        'stubs_created': stats.stubs_created,
        'stubs_completed': stats.stubs_completed,
        'errors': stats.errors,
        'duration_seconds': stats.duration_seconds()
    }
    
    with open(stats_path, 'w') as f:
        json.dump(stats_dict, f, indent=2)


def main():
    """Main entry point for email sync."""
    parser = argparse.ArgumentParser(
        description='Sync Bloomberg emails from Outlook to vector store'
    )
    parser.add_argument(
        '--max-emails',
        type=int,
        default=None,
        help='Maximum number of emails to process (default: no limit)'
    )
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    parser.add_argument(
        '--reset',
        action='store_true',
        help='Reset FAISS index and metadata mapper before sync (full rebuild)'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    print("="*60)
    print("BLOOMBERG RAG - EMAIL SYNC")
    print("="*60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Handle reset flag
    if args.reset:
        print("⚠️  RESET MODE: Deleting existing index and metadata...")
        vectorstore_config = get_vectorstore_config()
        
        # Delete FAISS index
        if vectorstore_config.index_path.exists():
            vectorstore_config.index_path.unlink()
            print(f"   Deleted: {vectorstore_config.index_path}")
        
        # Delete metadata mapper
        metadata_path = vectorstore_config.index_path.parent / "documents_metadata.json"
        if metadata_path.exists():
            metadata_path.unlink()
            print(f"   Deleted: {metadata_path}")
        
        print()
    
    outlook_extractor = None
    
    try:
        # Initialize components
        components = initialize_components(args.max_emails)
        outlook_extractor = components[0]  # Keep reference for cleanup
        stub_registry = components[5]  # StubRegistry
        vector_store = components[9]  # VectorStore
        metadata_mapper = components[10]  # Metadata Mapper
        vectorstore_config = components[11]  # Config
        
        # Connect to Outlook BEFORE running the pipeline
        logger.info("Connecting to Outlook...")
        outlook_extractor.connect()
        logger.info("Outlook connection established")
        
        # Create ingestion pipeline (pass first 11 components)
        pipeline = IngestionPipeline(*components[:11])
        
        # Run pipeline
        logger.info("Starting ingestion pipeline...")
        stats = pipeline.run()
        
        # Generate stub report (with stats)
        generate_stub_report(stub_registry, stats)
        
        # Save vector store
        print("\nSaving vector store...")
        vector_store.save(str(vectorstore_config.index_path))

        # Save metadata mapper
        print("Saving metadata mapper...")
        metadata_path = vectorstore_config.index_path.parent / "documents_metadata.json"
        metadata_mapper.save(str(metadata_path))
        
        # Save stats
        save_sync_stats(stats)
        
        # Print final summary
        print("\n" + "="*60)
        print("SYNC COMPLETED SUCCESSFULLY")
        print("="*60)
        print(f"Total emails processed: {stats.total_emails_processed}")
        print(f"Complete emails → /indexed/: {stats.complete_indexed}")
        print(f"New stubs → /stubs/: {stats.stubs_created}")
        print(f"Stubs completed → /processed/: {stats.stubs_completed}")
        print(f"Errors: {stats.errors}")
        print(f"Duration: {stats.duration_seconds():.2f} seconds")
        print()
        print(f"FAISS index: {vector_store.get_index_size()} vectors")
        print(f"Metadata mapper: {metadata_mapper.size()} documents")
        print("="*60)
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\nSync interrupted by user")
        return 1
        
    except Exception as e:
        logger.error(f"Sync failed: {e}", exc_info=True)
        print(f"\n\nERROR: Sync failed - {e}")
        return 1
    
    finally:
        # CRITICAL: Always close Outlook connection
        if outlook_extractor:
            try:
                outlook_extractor.close()
                logger.info("Outlook connection closed")
            except:
                pass


if __name__ == '__main__':
    sys.exit(main())