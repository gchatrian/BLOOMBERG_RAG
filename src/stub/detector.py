"""
Stub detection module for Bloomberg emails.
Identifies incomplete stub emails vs complete articles.
"""

import re
from typing import Dict, Any, Optional
import logging


class StubDetector:
    """
    Detects whether a Bloomberg email is a stub or complete article.
    
    Detection criteria (based on real Bloomberg stub structure):
    1. DEFINITIVE: Presence of "Alert:" AND "Source:" markers → STUB
    2. Supporting: Content length < 500 chars (excluding metadata)
    3. Supporting: Little/no content before metadata sections
    
    Real stub structure:
        Alert:
        SPOTLIGHT NEWS
        Source: BN (Bloomberg News)
        Tickers
        ...
        People
        ...
        Topics
        ...
    
    Architecture:
    - Accepts raw_email dict from Outlook extractor
    - Uses ContentCleaner dependency for text cleaning
    - Provides high-level API for email classification
    """
    
    def __init__(self, content_cleaner, min_complete_length: int = 500):
        """
        Initialize stub detector.
        
        Args:
            content_cleaner: ContentCleaner instance for text cleaning
            min_complete_length: Minimum content length for complete email (default: 500 chars)
        """
        self.content_cleaner = content_cleaner
        self.min_complete_length = min_complete_length
        self.logger = logging.getLogger(__name__)
        
        # Required stub markers (BOTH must be present)
        self.required_stub_markers = ["Alert:", "Source:"]
        
        # Metadata markers (optional sections)
        self.metadata_markers = ["Tickers", "People", "Topics"]
        
        # Bloomberg URL pattern
        self.url_pattern = re.compile(
            r'bloomberg\.com/news/articles/([A-Z0-9-]+)',
            re.IGNORECASE
        )
    
    def detect_from_email(self, raw_email: Dict[str, Any]) -> bool:
        """
        Determine if email is a stub.
        
        Main entry point for stub detection from raw email dict.
        
        Args:
            raw_email: Raw email dictionary with 'body' key
            
        Returns:
            True if stub, False if complete
        """
        # Extract raw body
        raw_body = raw_email.get('body', '')
        
        # Clean body
        cleaned_body = self.content_cleaner.clean(raw_body)
        
        # PRIMARY CHECK: Alert: AND Source: markers
        has_markers = self._check_required_markers(raw_body)
        
        if has_markers:
            self.logger.debug("Stub markers found (Alert: + Source:) → STUB")
            return True
        
        # SECONDARY CHECKS (for edge cases)
        
        # Check content length
        is_short = self._check_content_length(cleaned_body)
        
        # Check content before metadata
        has_content = self._check_content_before_metadata(cleaned_body)
        
        # Combined decision for edge cases without clear markers
        if is_short and not has_content:
            self.logger.debug("Short content + no substantial content before metadata → STUB")
            return True
        
        # Default: assume complete
        return False
    
    def classify(self, raw_email: Dict[str, Any]) -> str:
        """
        Classify email as "complete" or "stub".
        
        Args:
            raw_email: Raw email dictionary
            
        Returns:
            "stub" or "complete"
        """
        if self.detect_from_email(raw_email):
            return "stub"
        else:
            return "complete"
    
    def extract_story_id(self, raw_email: Dict[str, Any]) -> Optional[str]:
        """
        Extract Bloomberg Story ID from email body.
        
        Searches for URL pattern: bloomberg.com/news/articles/[STORY_ID]
        
        Args:
            raw_email: Raw email dictionary with 'body' key
            
        Returns:
            Story ID string or None if not found
        """
        body = raw_email.get('body', '')
        
        match = self.url_pattern.search(body)
        
        if match:
            story_id = match.group(1)
            self.logger.debug(f"Extracted Story ID: {story_id}")
            return story_id
        
        return None
    
    def create_fingerprint(self, raw_email: Dict[str, Any]) -> str:
        """
        Create fingerprint for stub matching.
        
        Formula: subject.lower().strip() + "_" + date (YYYYMMDD)
        Used as fallback when Story ID is not available.
        
        Args:
            raw_email: Raw email dictionary with 'subject' and 'received_time'
            
        Returns:
            Fingerprint string
        """
        subject = raw_email.get('subject', 'unknown')
        received_time = raw_email.get('received_time')
        
        subject_clean = subject.lower().strip()
        
        if received_time:
            date_str = received_time.strftime("%Y%m%d")
        else:
            date_str = "00000000"
        
        fingerprint = f"{subject_clean}_{date_str}"
        
        self.logger.debug(f"Created fingerprint: {fingerprint[:50]}...")
        
        return fingerprint
    
    def get_detection_details(self, raw_email: Dict[str, Any]) -> dict:
        """
        Get detailed detection information for debugging.
        
        Args:
            raw_email: Raw email dictionary
            
        Returns:
            Dict with detection details
        """
        raw_body = raw_email.get('body', '')
        cleaned_body = self.content_cleaner.clean(raw_body)
        
        has_markers = self._check_required_markers(raw_body)
        is_short = self._check_content_length(cleaned_body)
        has_content = self._check_content_before_metadata(cleaned_body)
        has_url = self._has_bloomberg_url(raw_body)
        is_stub_result = self.detect_from_email(raw_email)
        
        return {
            "is_stub": is_stub_result,
            "classification": "stub" if is_stub_result else "complete",
            "has_required_markers": has_markers,
            "is_short_content": is_short,
            "has_substantial_content": has_content,
            "has_bloomberg_url": has_url,
            "content_length": len(cleaned_body.strip()),
            "story_id": self.extract_story_id(raw_email),
            "fingerprint": self.create_fingerprint(raw_email)
        }
    
    # ========================================================================
    # INTERNAL METHODS (not called externally)
    # ========================================================================
    
    def _check_required_markers(self, body: str) -> bool:
        """
        Check for REQUIRED stub markers: "Alert:" AND "Source:".
        
        CRITICAL: Both markers MUST be present for definitive stub identification.
        
        Args:
            body: Email body text
            
        Returns:
            True if BOTH markers present, False otherwise
        """
        body_lower = body.lower()
        
        has_alert = "alert:" in body_lower
        has_source = "source:" in body_lower
        
        if has_alert and has_source:
            self.logger.debug("✓ Found Alert: AND Source: markers")
            return True
        
        return False
    
    def _check_content_length(self, cleaned_body: str) -> bool:
        """
        Check if content is too short to be a complete article.
        
        Args:
            cleaned_body: Cleaned email body
            
        Returns:
            True if content is short (< min_complete_length), False otherwise
        """
        content_length = len(cleaned_body.strip())
        is_short = content_length < self.min_complete_length
        
        self.logger.debug(f"Content length: {content_length} chars (threshold: {self.min_complete_length})")
        
        return is_short
    
    def _check_content_before_metadata(self, cleaned_body: str) -> bool:
        """
        Check if there is substantial content BEFORE metadata sections.
        
        Complete emails: substantial article content BEFORE Tickers/People/Topics
        Stub emails: little/no content before metadata (just Alert/Source)
        
        Args:
            cleaned_body: Cleaned email body
            
        Returns:
            True if substantial content exists before metadata, False otherwise
        """
        # Find earliest metadata marker
        earliest_idx = len(cleaned_body)
        
        for marker in self.metadata_markers + ["Alert", "Source"]:
            # Look for marker at start of line
            pattern = re.compile(
                r'^\s*' + re.escape(marker) + r'\s*:?\s*$',
                re.MULTILINE | re.IGNORECASE
            )
            match = pattern.search(cleaned_body)
            
            if match and match.start() < earliest_idx:
                earliest_idx = match.start()
        
        # Extract content before first metadata marker
        content_before = cleaned_body[:earliest_idx].strip()
        
        # Remove common email headers
        header_patterns = [
            r'^From:.*$',
            r'^To:.*$',
            r'^Subject:.*$',
            r'^Date:.*$',
            r'^Sent:.*$',
            r'External Email.*$',
        ]
        
        for pattern in header_patterns:
            content_before = re.sub(pattern, '', content_before, flags=re.MULTILINE | re.IGNORECASE)
        
        content_before = content_before.strip()
        content_length = len(content_before)
        
        # Substantial content = at least 200 characters
        has_content = content_length >= 200
        
        self.logger.debug(f"Content before metadata: {content_length} chars")
        
        return has_content
    
    def _has_bloomberg_url(self, body: str) -> bool:
        """
        Check if body contains Bloomberg article URL.
        
        Pattern: bloomberg.com/news/articles/[STORY_ID]
        
        Note: Presence of URL does NOT determine stub status definitively.
              Both stubs and complete emails may contain URLs.
        
        Args:
            body: Email body text
            
        Returns:
            True if Bloomberg URL found, False otherwise
        """
        match = self.url_pattern.search(body)
        
        if match:
            self.logger.debug(f"Found Bloomberg URL with Story ID: {match.group(1)}")
            return True
        
        return False