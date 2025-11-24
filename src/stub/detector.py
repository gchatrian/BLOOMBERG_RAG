"""
Stub detection module for Bloomberg emails.
Identifies incomplete stub emails vs complete articles.

DETECTION LOGIC (based on real Bloomberg email structure):

STUB emails:
- "Alert:" appears at the BEGINNING (first ~500 chars)
- No substantial content before Alert/Source
- Structure: External Email → Alert → Source → Tickers → Topics → footer

COMPLETE emails:
- Substantial article content at the beginning
- "(Bloomberg) --" pattern indicates article start
- "Alert:" and "Source:" appear at the END (after article)
- Structure: Title → Author → Date → Article → Contacts → Alert → Source → Topics → footer
"""

import re
from typing import Dict, Any, Optional
import logging


class StubDetector:
    """
    Detects whether a Bloomberg email is a stub or complete article.
    
    Detection strategy:
    1. Check for "(Bloomberg) --" pattern → COMPLETE (definitive)
    2. Check position of "Alert:" marker:
       - If in first ~500 chars with no content before → STUB
       - If after substantial content → COMPLETE
    3. Fallback: Check content length and structure
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
        
        # Pattern that definitively indicates a COMPLETE article
        # "(Bloomberg) --" is the standard Bloomberg article opening
        self.bloomberg_article_pattern = re.compile(
            r'\(Bloomberg\)\s*--',
            re.IGNORECASE
        )
        
        # Author pattern "By [Name]" at start of line
        self.author_pattern = re.compile(
            r'^By\s+[A-Z][a-z]+\s+[A-Z]',
            re.MULTILINE
        )
        
        # Alert marker pattern
        self.alert_pattern = re.compile(
            r'^\s*Alert:\s*',
            re.MULTILINE | re.IGNORECASE
        )
        
        # Source marker pattern  
        self.source_pattern = re.compile(
            r'^\s*Source:\s*',
            re.MULTILINE | re.IGNORECASE
        )
        
        # Bloomberg URL pattern for Story ID extraction
        self.url_pattern = re.compile(
            r'bloomberg\.com/news/articles/([A-Z0-9-]+)',
            re.IGNORECASE
        )
        
        # Metadata markers
        self.metadata_markers = ["Tickers", "People", "Topics"]
        
        # Characters to check for "early Alert" detection
        self.early_alert_threshold = 500
    
    def detect_from_email(self, raw_email: Dict[str, Any]) -> bool:
        """
        Determine if email is a stub.
        
        Main entry point for stub detection from raw email dict.
        
        Args:
            raw_email: Raw email dictionary with 'body' key
            
        Returns:
            True if stub, False if complete
        """
        raw_body = raw_email.get('body', '')
        subject = raw_email.get('subject', '')
        
        # Remove External Email disclaimer for cleaner analysis
        body_for_analysis = self._remove_email_disclaimer(raw_body)
        
        # =================================================================
        # CHECK 1: "(Bloomberg) --" pattern = DEFINITIVE COMPLETE
        # =================================================================
        if self._has_bloomberg_article_pattern(body_for_analysis):
            self.logger.debug(f"Found '(Bloomberg) --' pattern → COMPLETE: {subject[:50]}")
            return False  # NOT a stub
        
        # =================================================================
        # CHECK 2: "By [Author]" at beginning = likely COMPLETE
        # =================================================================
        if self._has_author_at_start(body_for_analysis):
            self.logger.debug(f"Found 'By [Author]' at start → COMPLETE: {subject[:50]}")
            return False  # NOT a stub
        
        # =================================================================
        # CHECK 3: Position of "Alert:" marker
        # =================================================================
        alert_position = self._find_alert_position(body_for_analysis)
        
        if alert_position is not None:
            # Check if Alert: appears EARLY (within first ~500 chars)
            if alert_position < self.early_alert_threshold:
                # Check content BEFORE Alert:
                content_before_alert = body_for_analysis[:alert_position].strip()
                
                # Remove common headers
                content_before_alert = self._remove_headers(content_before_alert)
                
                # If little/no content before Alert: → STUB
                if len(content_before_alert) < 100:
                    self.logger.debug(f"Alert: in first {self.early_alert_threshold} chars with minimal content → STUB: {subject[:50]}")
                    return True  # IS a stub
                else:
                    self.logger.debug(f"Alert: early but has content before ({len(content_before_alert)} chars) → COMPLETE: {subject[:50]}")
                    return False  # NOT a stub
            else:
                # Alert: appears LATE (after substantial content) → COMPLETE
                self.logger.debug(f"Alert: at position {alert_position} (after content) → COMPLETE: {subject[:50]}")
                return False  # NOT a stub
        
        # =================================================================
        # CHECK 4: No Alert: found - check content length
        # =================================================================
        cleaned_body = self.content_cleaner.clean(raw_body)
        
        if len(cleaned_body.strip()) < self.min_complete_length:
            self.logger.debug(f"No Alert:, short content ({len(cleaned_body)} chars) → STUB: {subject[:50]}")
            return True  # IS a stub
        
        # =================================================================
        # DEFAULT: Assume complete if none of the above
        # =================================================================
        self.logger.debug(f"No definitive markers, assuming COMPLETE: {subject[:50]}")
        return False  # NOT a stub
    
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
            raw_email: Raw email dictionary with 'subject' and 'received_date'
            
        Returns:
            Fingerprint string
        """
        subject = raw_email.get('subject', 'unknown')
        received_time = raw_email.get('received_date')
        
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
        body_for_analysis = self._remove_email_disclaimer(raw_body)
        cleaned_body = self.content_cleaner.clean(raw_body)
        
        alert_position = self._find_alert_position(body_for_analysis)
        has_bloomberg_pattern = self._has_bloomberg_article_pattern(body_for_analysis)
        has_author = self._has_author_at_start(body_for_analysis)
        is_stub_result = self.detect_from_email(raw_email)
        
        return {
            "is_stub": is_stub_result,
            "classification": "stub" if is_stub_result else "complete",
            "has_bloomberg_pattern": has_bloomberg_pattern,
            "has_author_at_start": has_author,
            "alert_position": alert_position,
            "alert_is_early": alert_position is not None and alert_position < self.early_alert_threshold,
            "content_length": len(cleaned_body.strip()),
            "story_id": self.extract_story_id(raw_email),
            "fingerprint": self.create_fingerprint(raw_email)
        }
    
    # ========================================================================
    # INTERNAL METHODS
    # ========================================================================
    
    def _remove_email_disclaimer(self, body: str) -> str:
        """
        Remove common email disclaimers for cleaner analysis.
        
        Args:
            body: Raw email body
            
        Returns:
            Body without disclaimers
        """
        # Remove "External Email" disclaimer
        patterns = [
            r'External Email\s*-\s*Be CAUTIOUS.*?button\.',
            r'External Email.*?(?=\n\n|\n[A-Z])',
        ]
        
        result = body
        for pattern in patterns:
            result = re.sub(pattern, '', result, flags=re.IGNORECASE | re.DOTALL)
        
        return result.strip()
    
    def _remove_headers(self, text: str) -> str:
        """
        Remove common email headers from text.
        
        Args:
            text: Text to clean
            
        Returns:
            Text without headers
        """
        header_patterns = [
            r'^From:.*$',
            r'^To:.*$',
            r'^Subject:.*$',
            r'^Date:.*$',
            r'^Sent:.*$',
            r'^\s*$',  # Empty lines
        ]
        
        result = text
        for pattern in header_patterns:
            result = re.sub(pattern, '', result, flags=re.MULTILINE | re.IGNORECASE)
        
        return result.strip()
    
    def _has_bloomberg_article_pattern(self, body: str) -> bool:
        """
        Check for "(Bloomberg) --" pattern that indicates a complete article.
        
        Args:
            body: Email body text
            
        Returns:
            True if pattern found
        """
        return bool(self.bloomberg_article_pattern.search(body))
    
    def _has_author_at_start(self, body: str) -> bool:
        """
        Check for "By [Author Name]" at the start of the email.
        
        Args:
            body: Email body text
            
        Returns:
            True if author pattern found in first 500 chars
        """
        # Only check first part of email
        first_part = body[:500]
        return bool(self.author_pattern.search(first_part))
    
    def _find_alert_position(self, body: str) -> Optional[int]:
        """
        Find position of "Alert:" marker in body.
        
        Args:
            body: Email body text
            
        Returns:
            Character position of Alert: or None if not found
        """
        match = self.alert_pattern.search(body)
        
        if match:
            return match.start()
        
        return None
    
    def _has_bloomberg_url(self, body: str) -> bool:
        """
        Check if body contains Bloomberg article URL.
        
        Args:
            body: Email body text
            
        Returns:
            True if Bloomberg URL found
        """
        return bool(self.url_pattern.search(body))


# Example usage and testing
if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Mock ContentCleaner for testing
    class MockCleaner:
        def clean(self, text):
            return text
    
    detector = StubDetector(MockCleaner())
    
    # Test STUB email
    stub_email = {
        'subject': 'BHP Says It\'s \'No Longer Considering\' Anglo Takeover (Video)',
        'body': '''External Email - Be CAUTIOUS...

BHP Says It's 'No Longer Considering' Anglo Takeover (Video)

Alert: SPOTLIGHT NEWS
Source: BLC (Bloomberg TV & Video)

Tickers
AAL LN (Anglo American PLC)
BHP AU (BHP Group Ltd)

Topics
Mergers & Acquisitions
Corporate Finance

To suspend this alert, click here
''',
        'received_date': None
    }
    
    # Test COMPLETE email
    complete_email = {
        'subject': 'Yen Tails Are in Demand While Pound Traders Favor ATM Volatility',
        'body': '''External Email - Be CAUTIOUS...

Yen Tails Are in Demand While Pound Traders Favor ATM Volatility

By Vassilis Karamanis

11/24/2025 03:47:54 [BFW]

(Bloomberg) -- Demand for low-probability yen options remains intact as traders
position for volatility to continue, with intervention speculation doing the rounds.

* USD/JPY one-week and one-month 10d flies rally to levels last seen in April,
  retaining a persistently bid tone throughout November

To contact the reporter on this story:
Vassilis Karamanis in Athens at vkaramanis1@bloomberg.net

Alert: FX OPTIONS COLUMN
Source: BFW (Bloomberg First Word)

Topics
Currencies
Currency Markets

To suspend this alert, click here
''',
        'received_date': None
    }
    
    print("=" * 60)
    print("STUB EMAIL TEST")
    print("=" * 60)
    result = detector.detect_from_email(stub_email)
    print(f"Is stub: {result}")
    print(f"Details: {detector.get_detection_details(stub_email)}")
    
    print("\n" + "=" * 60)
    print("COMPLETE EMAIL TEST")
    print("=" * 60)
    result = detector.detect_from_email(complete_email)
    print(f"Is stub: {result}")
    print(f"Details: {detector.get_detection_details(complete_email)}")