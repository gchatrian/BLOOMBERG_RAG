"""
Ingestion Pipeline for Bloomberg RAG System.

Orchestrates the complete email ingestion workflow:
1. Extract emails from Outlook source folder
2. Detect stub vs complete emails
3. For stubs: register and move to /stubs/ folder
4. For complete: clean, extract metadata, check stub match, embed, move to /indexed/
5. Generate final report with statistics
"""

import logging
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class IngestionStats:
    """Statistics for an ingestion run."""
    total_emails_processed: int = 0
    complete_indexed: int = 0
    stubs_created: int = 0
    stubs_completed: int = 0
    errors: int = 0
    start_time: datetime = None
    end_time: datetime = None
    
    def duration_seconds(self) -> float:
        """Calculate duration in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0


class IngestionPipeline:
    """
    Coordinates the complete email ingestion workflow.
    
    This pipeline handles:
    - Email extraction from Outlook source folder
    - Stub detection and registration
    - Email cleaning and metadata extraction
    - Stub-complete matching and cleanup
    - Embedding generation
    - Email movement between folders
    - Error handling and reporting
    """
    
    def __init__(
        self,
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
    ):
        """
        Initialize ingestion pipeline with all required components.
        
        Args:
            outlook_extractor: OutlookExtractor instance
            content_cleaner: ContentCleaner instance
            metadata_extractor: MetadataExtractor instance
            document_builder: DocumentBuilder instance
            stub_detector: StubDetector instance
            stub_registry: StubRegistry instance
            stub_manager: StubManager instance
            stub_matcher: StubMatcher instance
            embedding_generator: EmbeddingGenerator instance
            vector_store: FAISSStore instance
        """
        self.outlook_extractor = outlook_extractor
        self.content_cleaner = content_cleaner
        self.metadata_extractor = metadata_extractor
        self.document_builder = document_builder
        self.stub_detector = stub_detector
        self.stub_registry = stub_registry
        self.stub_manager = stub_manager
        self.stub_matcher = stub_matcher
        self.embedding_generator = embedding_generator
        self.vector_store = vector_store
        
        self.stats = IngestionStats()
    
    def run(self) -> IngestionStats:
        """
        Run the complete ingestion pipeline.
        
        Returns:
            IngestionStats with processing statistics
        """
        logger.info("Starting ingestion pipeline...")
        self.stats = IngestionStats(start_time=datetime.now())
        
        try:
            # Step 1: Extract emails from source folder
            raw_emails = self._extract_emails()
            self.stats.total_emails_processed = len(raw_emails)
            logger.info(f"Extracted {len(raw_emails)} emails from source folder")
            
            # Step 2: Process each email
            for raw_email in raw_emails:
                try:
                    self._process_email(raw_email)
                except Exception as e:
                    logger.error(f"Error processing email {raw_email.get('subject', 'Unknown')}: {e}", exc_info=True)
                    self.stats.errors += 1
            
            # Step 3: Finalize
            self.stats.end_time = datetime.now()
            self._log_final_report()
            
            return self.stats
            
        except Exception as e:
            logger.error(f"Ingestion pipeline failed: {e}", exc_info=True)
            self.stats.end_time = datetime.now()
            raise
    
    def _extract_emails(self) -> List[Dict[str, Any]]:
        """
        Extract emails from Outlook source folder.
        
        Returns:
            List of raw email dictionaries
        """
        try:
            # Connect to Outlook first
            self.outlook_extractor.connect()
            
            # Extract emails using the correct method name
            emails = self.outlook_extractor.extract_emails()
            return emails
        except Exception as e:
            logger.error(f"Failed to extract emails: {e}", exc_info=True)
            return []
    
    def _process_email(self, raw_email: Dict[str, Any]) -> None:
        """
        Process a single email through the pipeline.
        
        Args:
            raw_email: Raw email dictionary from Outlook
        """
        outlook_entry_id = raw_email.get('outlook_entry_id')
        subject = raw_email.get('subject', 'Unknown')
        
        logger.info(f"Processing email: {subject}")
        
        # Step 1: Detect if stub or complete
        body = raw_email.get('body', '')
        cleaned_body = self.content_cleaner.clean(body)
        
        # Get detection details for debugging
        detection_details = self.stub_detector.get_detection_details(body, cleaned_body)
        
        logger.debug(f"Detection details for '{subject[:50]}':")
        logger.debug(f"  - Has Alert+Source markers: {detection_details['has_required_markers']}")
        logger.debug(f"  - Content length: {detection_details['content_length']} chars")
        logger.debug(f"  - Is short: {detection_details['is_short_content']}")
        logger.debug(f"  - Has substantial content: {detection_details['has_substantial_content']}")
        logger.debug(f"  - Classification: {detection_details['classification']}")
        
        is_stub = detection_details['is_stub']
        
        if is_stub:
            self._process_stub(raw_email)
        else:
            self._process_complete(raw_email)
    
    def _process_stub(self, raw_email: Dict[str, Any]) -> None:
        """
        Process a stub email: register and move to /stubs/.
        
        Args:
            raw_email: Raw stub email dictionary
        """
        outlook_entry_id = raw_email.get('outlook_entry_id')
        subject = raw_email.get('subject', 'Unknown')
        body = raw_email.get('body', '')
        received_date = raw_email.get('received_date')
        
        logger.info(f"Detected STUB: {subject}")
        
        try:
            # Build EmailDocument for stub
            metadata = self.metadata_extractor.extract(subject, body, received_date)
            email_document = self.document_builder.build(
                raw_email_data=raw_email,
                cleaned_body=body,
                metadata=metadata,
                status="stub",
                is_stub=True
            )
            
            # Process stub (register + move)
            success = self.stub_manager.process_stub(email_document, self.outlook_extractor)
            
            if success:
                self.stats.stubs_created += 1
                logger.info(f"Stub registered and moved to /stubs/: {subject}")
            else:
                self.stats.errors += 1
            
        except Exception as e:
            logger.error(f"Failed to process stub {subject}: {e}", exc_info=True)
            self.stats.errors += 1
    
    def _process_complete(self, raw_email: Dict[str, Any]) -> None:
        """
        Process a complete email: clean, extract metadata, check stub match, embed, move.
        
        Args:
            raw_email: Raw complete email dictionary
        """
        outlook_entry_id = raw_email.get('outlook_entry_id')
        subject = raw_email.get('subject', 'Unknown')
        body = raw_email.get('body', '')
        received_date = raw_email.get('received_date')
        
        logger.info(f"Detected COMPLETE: {subject}")
        
        try:
            # Step 1: Clean content
            cleaned_content = self.content_cleaner.clean(body)
            
            # Step 2: Extract metadata
            metadata = self.metadata_extractor.extract(subject, cleaned_content, received_date)
            
            # Step 3: Build EmailDocument
            email_document = self.document_builder.build(
                raw_email_data=raw_email,
                cleaned_body=cleaned_content,
                metadata=metadata,
                status="complete",
                is_stub=False
            )
            
            # Step 4: Check for stub match
            match_found, matched_stub = self.stub_matcher.process_complete_email(
                email_document,
                self.outlook_extractor
            )
            
            if match_found:
                self.stats.stubs_completed += 1
                logger.info(f"Found and completed matching stub for: {subject}")
            
            # Step 5: Move email to /indexed/ folder
            self.outlook_extractor.move_to_indexed(outlook_entry_id)
            
            self.stats.complete_indexed += 1
            logger.info(f"Complete email moved to /indexed/: {subject}")
            
            # Note: Email document is created but not added to vector store yet
            # Vector indexing will be done in a separate step
            
        except Exception as e:
            logger.error(f"Failed to process complete email {subject}: {e}", exc_info=True)
            self.stats.errors += 1
    
    def _log_final_report(self) -> None:
        """Log final ingestion statistics."""
        duration = self.stats.duration_seconds()
        
        logger.info("="*60)
        logger.info("INGESTION PIPELINE COMPLETED")
        logger.info("="*60)
        logger.info(f"Total emails processed: {self.stats.total_emails_processed}")
        logger.info(f"Complete emails indexed: {self.stats.complete_indexed}")
        logger.info(f"New stubs created: {self.stats.stubs_created}")
        logger.info(f"Stubs completed (matched): {self.stats.stubs_completed}")
        logger.info(f"Errors: {self.stats.errors}")
        logger.info(f"Duration: {duration:.2f} seconds")
        logger.info("="*60)
    
    def get_stats(self) -> IngestionStats:
        """
        Get current ingestion statistics.
        
        Returns:
            IngestionStats object
        """
        return self.stats