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
from typing import List, Dict, Any
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
            # Step 0: Connect to Outlook
            logger.info("Connecting to Outlook...")
            self.outlook_extractor.connect()
            
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
        finally:
            # Always close Outlook connection
            try:
                self.outlook_extractor.close()
                logger.info("Outlook connection closed")
            except:
                pass
    
    def _extract_emails(self) -> List[Dict[str, Any]]:
        """
        Extract emails from Outlook source folder.
        
        Returns:
            List of raw email dictionaries
        """
        try:
            # Extract only from source folder (skip indexed, stubs, processed)
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
        is_stub = self.stub_detector.is_stub(
            body=raw_email.get('body', ''),
            cleaned_body=self.content_cleaner.clean(raw_email.get('body', ''))
        )
        
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
        
        logger.info(f"Detected STUB: {subject}")
        
        try:
            # Extract story ID and create fingerprint
            story_id = self.stub_detector.extract_story_id(raw_email)
            fingerprint = self.stub_detector.create_fingerprint(raw_email)
            
            # Register stub
            self.stub_registry.register_stub(
                outlook_entry_id=outlook_entry_id,
                story_id=story_id,
                fingerprint=fingerprint,
                subject=subject,
                received_time=raw_email.get('received_time')
            )
            
            # Move to /stubs/ folder
            self.stub_manager.move_to_stubs(outlook_entry_id)
            
            self.stats.stubs_created += 1
            logger.info(f"Stub registered and moved to /stubs/: {subject}")
            
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
        
        logger.info(f"Detected COMPLETE: {subject}")
        
        try:
            # Step 1: Clean content
            cleaned_content = self.content_cleaner.clean(raw_email.get('body', ''))
            
            # Step 2: Extract metadata
            metadata = self.metadata_extractor.extract(
                subject=raw_email.get('subject', ''),
                body=cleaned_content,
                received_date=raw_email.get('received_date')
            )
            
            # Step 3: Check for stub match
            story_id = metadata.story_id
            matched_stub = None
            
            if story_id:
                # Try to match by story_id (primary method)
                matched_stub = self.stub_matcher.match_by_story_id(story_id)
            
            if not matched_stub:
                # Fallback: try to match by fingerprint
                fingerprint = self.stub_detector.create_fingerprint(raw_email)
                matched_stub = self.stub_matcher.match_by_fingerprint(fingerprint)
            
            # Step 4: If stub match found, move stub to /processed/
            if matched_stub:
                logger.info(f"Found matching stub for {subject}, moving stub to /processed/")
                self.stub_manager.move_to_processed(matched_stub['outlook_entry_id'])
                self.stub_registry.mark_completed(matched_stub['outlook_entry_id'])
                self.stats.stubs_completed += 1
            
            # Step 5: Build EmailDocument
            email_document = self.document_builder.build(
                raw_email_data=raw_email,
                cleaned_body=cleaned_content,
                metadata=metadata
            )
            
            # Step 6: Generate embedding
            embedding = self.embedding_generator.generate_single_embedding(email_document.get_full_text())
            
            # Step 7: Add to vector store
            self.vector_store.add_vectors(embedding.reshape(1, -1))
            
            # Step 8: Move email to /indexed/ folder
            self.outlook_extractor.move_to_indexed(outlook_entry_id)
            
            self.stats.complete_indexed += 1
            logger.info(f"Complete email indexed and moved to /indexed/: {subject}")
            
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