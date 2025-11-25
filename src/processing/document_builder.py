"""
Document builder module for Bloomberg RAG system.
Combines cleaned content and metadata into EmailDocument objects.
"""

from datetime import datetime
from typing import Dict, Any
import logging

# Import models
from src.models import EmailDocument, BloombergMetadata


class DocumentBuilder:
    """
    Builds EmailDocument objects from processed components.
    
    Responsibilities:
    - Combine raw email data + cleaned body + metadata
    - Create full text for embedding
    - Validate document completeness
    - Set document status (complete/stub/processed)
    """
    
    def __init__(self):
        """Initialize document builder."""
        self.logger = logging.getLogger(__name__)
    
    def build(self, 
              raw_email_data: Dict[str, Any],
              cleaned_body: str,
              metadata: BloombergMetadata,
              status: str = "complete",
              is_stub: bool = False) -> EmailDocument:
        """
        Build complete EmailDocument.
        
        Args:
            raw_email_data: Raw email dict from OutlookExtractor
                {subject, body, sender, received_date, outlook_entry_id}
            cleaned_body: Cleaned body text from ContentCleaner
            metadata: Extracted Bloomberg metadata
            status: Document status ("complete", "stub", "processed")
            is_stub: Whether this is a stub email
            
        Returns:
            Complete EmailDocument object
        """
        # Create document
        document = EmailDocument(
            outlook_entry_id=raw_email_data['outlook_entry_id'],
            subject=raw_email_data['subject'],
            body=cleaned_body,
            raw_body=raw_email_data['body'],
            sender=raw_email_data['sender'],
            received_date=raw_email_data['received_date'],
            bloomberg_metadata=metadata,
            status=status,
            is_stub=is_stub,
            embedding=None,  # Will be populated later by embedding pipeline
            processed_at=datetime.now()
        )
        
        # Validate
        if not self.validate(document):
            self.logger.warning(f"Document validation failed: {document.subject[:50]}...")
        
        return document
    
    def validate(self, document: EmailDocument) -> bool:
        """
        Validate document completeness.
        
        Checks:
        - All required fields present
        - Content has minimum length
        - EntryID exists
        
        Args:
            document: EmailDocument to validate
            
        Returns:
            True if valid, False otherwise
        """
        errors = []
        
        # Check required fields
        if not document.outlook_entry_id:
            errors.append("Missing outlook_entry_id")
        
        if not document.subject:
            errors.append("Missing subject")
        
        if not document.body:
            errors.append("Missing body")
        
        if not document.sender:
            errors.append("Missing sender")
        
        if not document.received_date:
            errors.append("Missing received_date")
        
        # Check minimum body length (at least 10 chars)
        if len(document.body.strip()) < 10:
            errors.append(f"Body too short: {len(document.body)} chars")
        
        # Log errors if any
        if errors:
            self.logger.error(f"Document validation errors: {', '.join(errors)}")
            return False
        
        return True
    
    def create_full_text_for_embedding(self, document: EmailDocument) -> str:
        """
        Create structured full text for embedding.
        
        Format:
            Subject: [subject]
            Date: [date]
            Category: [category]
            Author: [author]
            Tickers: [ticker1, ticker2]
            Topics: [topic1, topic2]
            People: [person1, person2]
            
            [body text]
        
        Note: This is essentially the same as document.get_full_text()
              but provided as explicit method for clarity.
        
        Args:
            document: EmailDocument
            
        Returns:
            Formatted text string
        """
        return document.get_full_text()