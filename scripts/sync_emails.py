"""
Email Sync Script for Bloomberg RAG System.

Main entry point for syncing Bloomberg emails from Outlook.
Runs the complete ingestion pipeline.

Usage:
    python sync_emails.py [--max-emails N] [--verbose]
"""

import sys
import logging
import argparse
from pathlib import Path
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))

# Import components
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
from src.orchestration.ingestion_pipeline import IngestionPipeline
from config.settings import (
    get_outlook_config,
    get_embedding_config,
    get_vectorstore_config,
    get_persistence_config
)


def setup_logging(verbose: bool = False):
    """
    Setup logging configuration.
    
    Args:
        verbose: If True, set log level to DEBUG
    """
    # Ensure logs directory exists
    log_dir = PROJECT_ROOT / 'logs'
    log_dir.mkdir(exist_ok=True)
    
    level = logging.DEBUG if verbose else logging.INFO
    
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
    
    # Initialize components
    outlook_extractor = OutlookExtractor(
        outlook_config.source_folder,
        outlook_config.indexed_folder,
        outlook_config.stubs_folder,
        outlook_config.processed_folder
    )
    content_cleaner = ContentCleaner()
    metadata_extractor = MetadataExtractor()
    document_builder = DocumentBuilder()
    
    # CRITICAL: Pass content_cleaner to StubDetector
    stub_detector = StubDetector(content_cleaner)
    
    stub_registry = StubRegistry(persistence_config.stub_registry_json)
    
    # CRITICAL: Pass stub_registry to StubManager (NOT outlook_extractor)
    stub_manager = StubManager(stub_registry)
    
    # StubMatcher takes registry in __init__
    stub_matcher = StubMatcher(stub_registry)
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
    reporter = StubReporter()
    report = reporter.generate_report(stub_registry)
    print(report)


def main():
    """Main entry point for email sync script."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Sync Bloomberg emails from Outlook')
    parser.add_argument('--max-emails', type=int, default=None,
                       help='Maximum number of emails to process (default: no limit)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose debug logging')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(verbose=args.verbose)
    logger = logging.getLogger(__name__)
    
    # Print header
    print("="*60)
    print("BLOOMBERG RAG - EMAIL SYNC")
    print("="*60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        # Initialize components
        print("Initializing components...")
        (
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
        ) = initialize_components(max_emails=args.max_emails)
        
        # Load stub registry
        stub_registry.load()
        
        # Create ingestion pipeline
        pipeline = IngestionPipeline(
            outlook_extractor=outlook_extractor,
            content_cleaner=content_cleaner,
            metadata_extractor=metadata_extractor,
            document_builder=document_builder,
            stub_detector=stub_detector,
            stub_registry=stub_registry,
            stub_manager=stub_manager,
            stub_matcher=stub_matcher,
            embedding_generator=embedding_generator,
            vector_store=vector_store
        )
        
        # Run ingestion pipeline
        print("Starting ingestion pipeline...")
        stats = pipeline.run()
        
        # Save vector store
        print("\nSaving vector store...")
        vectorstore_config = get_vectorstore_config()
        vector_store.save(str(vectorstore_config.index_path))
        
        # Save stub registry
        stub_registry.save()
        
        # Generate stub report
        print()
        generate_stub_report(stub_registry)
        
        # Final summary
        print()
        print("="*60)
        print("SYNC COMPLETED SUCCESSFULLY")
        print("="*60)
        print(f"Total emails processed: {stats.total_emails_processed}")
        print(f"Complete emails to /indexed/: {stats.complete_indexed}")
        print(f"New stubs to /stubs/: {stats.stubs_created}")
        print(f"Stubs completed to /processed/: {stats.stubs_completed}")
        print(f"Errors: {stats.errors}")
        print(f"Duration: {stats.duration_seconds():.2f} seconds")
        print("="*60)
        
    except KeyboardInterrupt:
        print("\n\nSync interrupted by user.")
        logger.warning("Sync interrupted by user")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n\nERROR: {e}")
        logger.error(f"Sync failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()