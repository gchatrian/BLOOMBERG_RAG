"""
Stub detection module for Bloomberg emails.
Identifies incomplete stub emails vs complete articles.
"""

import re
from typing import Tuple
import logging


class StubDetector:
    """
    Detects whether a Bloomberg email is a stub or complete article.
    
    Detection criteria (based on real Bloomberg stub structure):
    1. DEFINITIVE: Presence of "Alert:" AND "Source:" markers → STUB
    2. Supporting: Content length < 500 chars (excluding metadata)
    3. Supporting: Little/no content before metadata sections
    4. Supporting: Bloomberg URL present (but not definitive)
    
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
    """
    
    def __init__(self, min_complete_length: int = 500):
        """
        Initialize stub detector.
        
        Args:
            min_complete_length: Minimum content length for complete email (default: 500 chars)
        """
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
    
    def is_stub(self, body: str, cleaned_body: str) -> bool:
        """
        Determine if email is a stub.
        
        Args:
            body: Raw email body (may contain HTML)
            cleaned_body: Cleaned email body text
            
        Returns:
            True if stub, False if complete
        """
        # PRIMARY CHECK: Alert: AND Source: markers
        has_markers = self.check_required_markers(body)
        
        if has_markers:
            self.logger.debug("Stub markers found (Alert: + Source:) → STUB")
            return True
        
        # SECONDARY CHECKS (for edge cases)
        
        # Check content length
        is_short = self.check_content_length(cleaned_body)
        
        # Check content before metadata
        has_content = self.check_content_before_metadata(cleaned_body)
        
        # Combined decision for edge cases without clear markers
        if is_short and not has_content:
            self.logger.debug("Short content + no substantial content before metadata → STUB")
            return True
        
        # Default: assume complete
        return False
    
    def check_required_markers(self, body: str) -> bool:
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
        
        self.logger.debug(f"Content before metadata: {content_length} chars")
        
        return has_content
    
    def has_bloomberg_url(self, body: str) -> bool:
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


# Example usage
if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    detector = StubDetector()
    
    # Test STUB email (based on real example)
    stub_email = """
    External Email
    
    Swiss Watch Exports Fell Again in October on US Tariff Hit (1)
    Alert:
    SPOTLIGHT NEWS
    Source: BN (Bloomberg News)
    Tickers
    941772Z SW (Audemars Piguet Holding SA)
    SNBN SW (Schweizerische Nationalbank)
    People
    Donald John Trump (United States of America)
    Georges Kern (Breitling AG)
    Topics
    CEO Interviews
    Luxury Spending
    Switzerland Economy
    """
    
    print("="*60)
    print("TEST 1: STUB EMAIL")
    print("="*60)
    details = detector.get_detection_details(stub_email, stub_email)
    print(f"Is Stub: {details['is_stub']}")
    print(f"Classification: {details['classification']}")
    print(f"Has Alert+Source: {details['has_required_markers']}")
    print(f"Is Short: {details['is_short_content']}")
    print(f"Has Substantial Content: {details['has_substantial_content']}")
    print(f"Content Length: {details['content_length']} chars")
    
    # Test COMPLETE email
    complete_email = """
    By John Doe
    January 15, 2024
    
    Swiss watch exports declined for the second consecutive month in October,
    as US tariffs continued to weigh on the luxury goods sector. Industry
    leaders expressed concern about the prolonged impact of trade tensions
    on their businesses.
    
    The Federation of the Swiss Watch Industry reported a 5.2% year-over-year
    decline in exports, with the United States market showing particularly
    weak performance. This follows a 3.8% drop in September.
    
    "The current trade environment presents significant challenges," said
    Georges Kern, CEO of Breitling AG, in an interview. "We're seeing
    consumers hesitate on major purchases due to economic uncertainty."
    
    Analysts at major banks have revised their forecasts for the sector.
    Jean-Philippe Bertschy at Vontobel noted that the tariff situation
    could persist into 2025, potentially affecting annual results.
    
    Read more at: https://bloomberg.com/news/articles/ABC123DEF456
    
    Tickers:
    UHR SW (Swatch Group AG/The)
    CFR SW (Cie Financiere Richemont SA)
    
    People:
    Donald John Trump
    Georges Kern
    
    Topics:
    Luxury Spending
    Switzerland Economy
    Trade
    """
    
    print("\n" + "="*60)
    print("TEST 2: COMPLETE EMAIL")
    print("="*60)
    details = detector.get_detection_details(complete_email, complete_email)
    print(f"Is Stub: {details['is_stub']}")
    print(f"Classification: {details['classification']}")
    print(f"Has Alert+Source: {details['has_required_markers']}")
    print(f"Is Short: {details['is_short_content']}")
    print(f"Has Substantial Content: {details['has_substantial_content']}")
    print(f"Has Bloomberg URL: {details['has_bloomberg_url']}")
    print(f"Content Length: {details['content_length']} chars")