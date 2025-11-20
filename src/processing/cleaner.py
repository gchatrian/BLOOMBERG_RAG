"""
Content cleaning module for Bloomberg emails.
Removes HTML, disclaimers, fixes encoding, and normalizes text.
"""

from bs4 import BeautifulSoup
import re
from typing import Optional, List
import logging


class ContentCleaner:
    """
    Cleans raw email content for processing.
    
    Responsibilities:
    - Remove HTML tags and convert to clean text
    - Remove email disclaimers (External Email, etc.)
    - Fix encoding issues (smart quotes, em dashes, etc.)
    - Remove Bloomberg footer links
    - Normalize whitespace
    - Separate header from main content
    """
    
    def __init__(self, remove_patterns: Optional[List[str]] = None):
        """
        Initialize content cleaner.
        
        Args:
            remove_patterns: List of patterns to remove from content
        """
        self.logger = logging.getLogger(__name__)
        
        # Default patterns to remove
        if remove_patterns is None:
            self.remove_patterns = [
                "External Email",
                "EXTERNAL:",
                "This message originated outside",
                "To unsubscribe",
                "Privacy Policy",
                "Terms of Service",
                "Click here to unsubscribe",
                "Manage your email preferences"
            ]
        else:
            self.remove_patterns = remove_patterns
        
        # Encoding fixes mapping
        self.encoding_fixes = {
            'â€™': "'",      # Smart single quote
            'â€œ': '"',      # Smart double quote open
            'â€': '"',       # Smart double quote close
            'â€"': '—',      # Em dash
            'â€"': '–',      # En dash
            'â€¢': '•',      # Bullet
            'â€¦': '...',    # Ellipsis
            'Â': '',         # Non-breaking space artifact
            'Ã©': 'é',       # e with acute
            'Ã¨': 'è',       # e with grave
            'Ã ': 'à',       # a with grave
        }
    
    def clean(self, raw_body: str, html_body: Optional[str] = None) -> str:
        """
        Main cleaning pipeline.
        
        Args:
            raw_body: Plain text body from email
            html_body: HTML body from email (optional, used if raw_body is poor quality)
            
        Returns:
            Cleaned text content
        """
        # Prefer HTML body if available (often has better formatting)
        if html_body and len(html_body.strip()) > len(raw_body.strip()):
            text = self.remove_html(html_body)
        else:
            text = raw_body
        
        # Apply cleaning steps
        text = self.remove_disclaimers(text)
        text = self.fix_encoding(text)
        text = self.remove_bloomberg_footer(text)
        text = self.normalize_whitespace(text)
        
        return text.strip()
    
    def remove_html(self, html_content: str) -> str:
        """
        Remove HTML tags and convert to plain text.
        
        Args:
            html_content: HTML string
            
        Returns:
            Plain text without HTML tags
        """
        if not html_content:
            return ""
        
        try:
            soup = BeautifulSoup(html_content, 'lxml')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text
            text = soup.get_text()
            
            return text
            
        except Exception as e:
            self.logger.warning(f"Failed to parse HTML, returning as-is: {e}")
            return html_content
    
    def remove_disclaimers(self, text: str) -> str:
        """
        Remove email disclaimers and warnings.
        
        Args:
            text: Input text
            
        Returns:
            Text without disclaimer patterns
        """
        for pattern in self.remove_patterns:
            # Case-insensitive removal
            text = re.sub(re.escape(pattern), '', text, flags=re.IGNORECASE)
        
        return text
    
    def fix_encoding(self, text: str) -> str:
        """
        Fix common encoding issues from email.
        
        Args:
            text: Input text with potential encoding issues
            
        Returns:
            Text with fixed encoding
        """
        for wrong, correct in self.encoding_fixes.items():
            text = text.replace(wrong, correct)
        
        return text
    
    def remove_bloomberg_footer(self, text: str) -> str:
        """
        Remove Bloomberg footer links and promotional content.
        
        Args:
            text: Input text
            
        Returns:
            Text without Bloomberg footer
        """
        # Remove common Bloomberg footer patterns
        footer_patterns = [
            r'To unsubscribe.*?bloomberg\.com.*?$',
            r'View this email in your browser.*?$',
            r'Bloomberg L\.P\..*?rights reserved.*?$',
            r'Copyright.*?Bloomberg.*?$',
            r'This email was sent to.*?$',
            r'Update your email preferences.*?$',
        ]
        
        for pattern in footer_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL | re.MULTILINE)
        
        return text
    
    def normalize_whitespace(self, text: str) -> str:
        """
        Normalize whitespace in text.
        
        - Replace multiple spaces with single space
        - Replace multiple newlines with max 2 newlines
        - Remove leading/trailing whitespace from lines
        
        Args:
            text: Input text
            
        Returns:
            Text with normalized whitespace
        """
        # Replace multiple spaces with single space
        text = re.sub(r' +', ' ', text)
        
        # Replace tabs with spaces
        text = text.replace('\t', ' ')
        
        # Remove trailing whitespace from each line
        lines = [line.rstrip() for line in text.split('\n')]
        text = '\n'.join(lines)
        
        # Replace more than 2 consecutive newlines with 2
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text
    
    def separate_header(self, text: str) -> tuple[str, str]:
        """
        Separate email header from main content.
        
        Heuristic: First few lines often contain metadata like "From:", "To:", etc.
        We identify and separate them from the main article content.
        
        Args:
            text: Input text
            
        Returns:
            Tuple of (header, main_content)
        """
        lines = text.split('\n')
        
        # Common header patterns
        header_patterns = [
            r'^From:',
            r'^To:',
            r'^Subject:',
            r'^Date:',
            r'^Sent:',
            r'^Cc:',
        ]
        
        header_lines = []
        content_start_idx = 0
        
        # Check first 10 lines for header patterns
        for i, line in enumerate(lines[:10]):
            is_header = any(re.match(pattern, line.strip(), re.IGNORECASE) for pattern in header_patterns)
            
            if is_header:
                header_lines.append(line)
                content_start_idx = i + 1
            elif header_lines:
                # First non-header line after headers found
                break
        
        header = '\n'.join(header_lines)
        content = '\n'.join(lines[content_start_idx:])
        
        return header, content
    
    def get_content_before_metadata(self, text: str, metadata_markers: Optional[List[str]] = None) -> str:
        """
        Extract content BEFORE metadata sections (Tickers, People, Topics).
        
        This is critical for distinguishing complete emails from stubs:
        - Complete emails: substantial content BEFORE metadata
        - Stub emails: little/no content before metadata
        
        Args:
            text: Full email text
            metadata_markers: List of metadata section markers (default: ["Tickers", "People", "Topics"])
            
        Returns:
            Content before first metadata marker
        """
        if metadata_markers is None:
            metadata_markers = ["Tickers", "People", "Topics"]
        
        # Find earliest occurrence of any metadata marker
        earliest_idx = len(text)
        
        for marker in metadata_markers:
            # Look for marker at start of line (case-insensitive)
            pattern = re.compile(r'^\s*' + re.escape(marker) + r'\s*:?\s*$', re.MULTILINE | re.IGNORECASE)
            match = pattern.search(text)
            
            if match and match.start() < earliest_idx:
                earliest_idx = match.start()
        
        # Extract content before metadata
        if earliest_idx < len(text):
            content = text[:earliest_idx].strip()
        else:
            # No metadata markers found, return all content
            content = text.strip()
        
        return content


# Example usage
if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    cleaner = ContentCleaner()
    
    # Test HTML removal
    html = """
    <html>
    <head><style>body { font-family: Arial; }</style></head>
    <body>
        <p>This is a <strong>Bloomberg</strong> article.</p>
        <p>It contains important information.</p>
    </body>
    </html>
    """
    
    print("HTML Cleaning Test:")
    print(cleaner.remove_html(html))
    print("\n" + "="*50 + "\n")
    
    # Test encoding fix
    bad_encoding = "It's a test — with smart quotes"
    print("Encoding Fix Test:")
    print(f"Before: {bad_encoding}")
    print(f"After: {cleaner.fix_encoding(bad_encoding)}")
    print("\n" + "="*50 + "\n")
    
    # Test disclaimer removal
    with_disclaimer = """
    External Email - Use caution
    
    This is the actual email content.
    It has important information.
    
    To unsubscribe from this list, click here.
    """
    
    print("Disclaimer Removal Test:")
    print(cleaner.remove_disclaimers(with_disclaimer))
    print("\n" + "="*50 + "\n")
    
    # Test content before metadata
    email_with_metadata = """
    This is the main article content.
    It has multiple paragraphs with substantial information.
    
    More content here.
    
    Tickers:
    AAPL US, MSFT US
    
    People:
    Elon Musk, Sam Altman
    
    Topics:
    AI, Technology, Regulation
    """
    
    print("Content Before Metadata Test:")
    content = cleaner.get_content_before_metadata(email_with_metadata)
    print(f"Content length: {len(content)} chars")
    print(content)
    print("\n" + "="*50 + "\n")
    
    # Test full cleaning pipeline
    raw_text = """
    External Email
    
    From: bloomberg@bloomberg.com
    
    This is a test article with â€™smart quotesâ€ and â€" dashes.
    
    <p>Some HTML might be here</p>
    
    
    Multiple       spaces    and newlines.
    
    
    
    To unsubscribe, click here: bloomberg.com/unsubscribe
    """
    
    print("Full Cleaning Pipeline Test:")
    cleaned = cleaner.clean(raw_text)
    print(cleaned)