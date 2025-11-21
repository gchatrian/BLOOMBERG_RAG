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
    
    # CRITICAL: Connect to Outlook
    try:
        outlook_extractor.connect()
    except Exception as e:
        logger.error(f"Failed to connect to Outlook: {e}")
        raise
    
    # Initialize other components
    content_cleaner = ContentCleaner()
    metadata_extractor = MetadataExtractor()
    document_builder = DocumentBuilder()
    
    # StubDetector - NO parameters required (only optional min_complete_length)
    stub_detector = StubDetector()
    
    stub_registry = StubRegistry(persistence_config.stub_registry_json)
    stub_manager = StubManager(stub_registry)
    stub_matcher = StubMatcher()
    embedding_generator = EmbeddingGenerator(embedding_config)
    
    # Load or create vector store
    if vectorstore_config.index_path.exists():
        logger.info(f"Loading existing vector store from {vectorstore_config.index_path}")
        vector_store = FAISSVectorStore.load(
            str(vectorstore_config.index_path),
            embedding_config.embedding_dim
        )
    else:
        logger.info("No existing vector store found, creating new one")
        vector_store = FAISSVectorStore(embedding_config.embedding_dim)
    
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
        vector_store
    )


def generate_stub_report(stub_registry: StubRegistry) -> None:
    """
    Generate and display stub report.
    
    Args:
        stub_registry: StubRegistry instance
    """
    logger = logging.getLogger(__name__)
    
    try:
        reporter = StubReporter()
        report = reporter.generate_report(stub_registry)
        
        print("\n")
        print(report)
        
    except Exception as e:
        logger.error(f"Failed to generate stub report: {e}", exc_info=True)


def save_sync_stats(stats) -> None:
    """
    Save sync statistics to last_sync.json.
    
    Args:
        stats: IngestionStats object
    """
    persistence_config = get_persistence_config()
    
    stats_dict = {
        "timestamp": datetime.now().isoformat(),
        "total_emails_processed": stats.total_emails_processed,
        "complete_indexed": stats.complete_indexed,
        "stubs_created": stats.stubs_created,
        "stubs_completed": stats.stubs_completed,
        "errors": stats.errors,
        "duration_seconds": stats.duration_seconds()
    }
    
    with open(persistence_config.last_sync_json, 'w') as f:
        json.dump(stats_dict, f, indent=2)


def main():
    """Main entry point."""
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
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    print("="*60)
    print("BLOOMBERG RAG - EMAIL SYNC")
    print("="*60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    outlook_extractor = None
    
    try:
        # Initialize components (includes Outlook connection)
        components = initialize_components(args.max_emails)
        outlook_extractor = components[0]  # Keep reference for cleanup
        
        # Create ingestion pipeline
        pipeline = IngestionPipeline(*components)
        
        # Run pipeline
        logger.info("Starting ingestion pipeline...")
        stats = pipeline.run()
        
        # Generate stub report
        stub_registry = components[5]  # StubRegistry is at index 5
        generate_stub_report(stub_registry)
        
        # Save vector store
        vector_store = components[9]  # VectorStore is at index 9
        print("\nSaving vector store...")
        vector_store.save()
        
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