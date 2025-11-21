"""
Stub detection module for Bloomberg emails - IMPROVED VERSION.
Identifies incomplete stub emails vs complete articles with better logic.
"""

import re
from typing import Tuple
import logging


class StubDetector:
    """
    Detects whether a Bloomberg email is a stub or complete article.
    
    IMPROVED Detection criteria:
    1. Check for "Alert:" AND "Source:" markers
    2. If markers found, ALSO check content length and position
    3. Only classify as STUB if markers present AND (content is short OR no substantial content)
    4. Complete emails may have Alert/Source in signature/footer but have substantial content
    
    Real stub structure:
        Alert:
        SPOTLIGHT NEWS
        Source: BN (Bloomberg News)
        Tickers...
    
    Real complete structure:
        [Substantial article content - many paragraphs]
        ...
        Tickers...
        [May have Alert/Source in footer but irrelevant]
    """
    
    def __init__(self, min_complete_length: int = 500):
        """
        Initialize stub detector.
        
        Args:
            min_complete_length: Minimum content length for complete email (default: 500 chars)
        """
        self.min_complete_length = min_complete_length
        self.logger = logging.getLogger(__name__)
        
        # Stub indicators (not definitive alone)
        self.stub_markers = ["Alert:", "Source:"]
        
        # Metadata markers (optional sections)
        self.metadata_markers = ["Tickers", "People", "Topics"]
        
        # Bloomberg URL pattern
        self.url_pattern = re.compile(
            r'bloomberg\.com/news/articles/([A-Z0-9-]+)',
            re.IGNORECASE
        )
    
    def is_stub(self, body: str, cleaned_body: str) -> bool:
        """
        Determine if email is a stub using IMPROVED logic.
        
        Args:
            body: Raw email body (may contain HTML)
            cleaned_body: Cleaned email body text
            
        Returns:
            True if stub, False if complete
        """
        # Check all indicators
        has_markers = self.check_required_markers(body)
        is_short = self.check_content_length(cleaned_body)
        has_content = self.check_content_before_metadata(cleaned_body)
        
        # IMPROVED LOGIC: Markers alone are NOT definitive
        if has_markers:
            # Found Alert+Source markers
            if is_short or not has_content:
                # Markers + (short content OR no substantial content) = STUB
                self.logger.debug("Alert+Source markers + (short OR no content) → STUB")
                return True
            else:
                # Markers present BUT substantial content exists = COMPLETE
                # (markers might be in footer/signature)
                self.logger.debug("Alert+Source markers BUT substantial content present → COMPLETE")
                return False
        
        # No markers - use secondary checks
        if is_short and not has_content:
            self.logger.debug("No markers but short content + no substantial content → STUB")
            return True
        
        # Default: assume complete
        self.logger.debug("No definitive stub indicators → COMPLETE")
        return False
    
    def check_required_markers(self, body: str) -> bool:
        """
        Check for stub markers: "Alert:" AND "Source:".
        
        Note: These are now INDICATORS, not DEFINITIVE markers.
        
        Args:
            body: Email body text
            
        Returns:
            True if BOTH markers present, False otherwise
        """
        body_lower = body.lower()
        
        has_alert = "alert:" in body_lower
        has_source = "source:" in body_lower
        
        if has_alert and has_source:
            self.logger.debug("Found Alert: AND Source: markers (indicator)")
            return True
        
        return False
    
    def check_content_length(self, cleaned_body: str) -> bool:
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
    
    def check_content_before_metadata(self, cleaned_body: str) -> bool:
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
        
        self.logger.debug(f"Content before metadata: {content_length} chars (threshold: 200)")
        
        return has_content
    
    def has_bloomberg_url(self, body: str) -> bool:
        """
        Check if body contains Bloomberg article URL.
        
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
    
    def classify(self, body: str, cleaned_body: str) -> str:
        """
        Classify email as "complete" or "stub".
        
        Args:
            body: Raw email body
            cleaned_body: Cleaned email body
            
        Returns:
            "stub" or "complete"
        """
        if self.is_stub(body, cleaned_body):
            return "stub"
        else:
            return "complete"
    
    def get_detection_details(self, body: str, cleaned_body: str) -> dict:
        """
        Get detailed detection information for debugging.
        
        Args:
            body: Raw email body
            cleaned_body: Cleaned email body
            
        Returns:
            Dict with detection details
        """
        has_markers = self.check_required_markers(body)
        is_short = self.check_content_length(cleaned_body)
        has_content = self.check_content_before_metadata(cleaned_body)
        has_url = self.has_bloomberg_url(body)
        is_stub_result = self.is_stub(body, cleaned_body)
        
        return {
            "is_stub": is_stub_result,
            "classification": "stub" if is_stub_result else "complete",
            "has_required_markers": has_markers,
            "is_short_content": is_short,
            "has_substantial_content": has_content,
            "has_bloomberg_url": has_url,
            "content_length": len(cleaned_body.strip())
        }