"""
Metadata extraction module for Bloomberg emails.
Extracts author, date, story ID, topics, people, and category.
"""

import re
from datetime import datetime
from typing import Optional, List
import logging

# Import BloombergMetadata from models
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from models import BloombergMetadata


class MetadataExtractor:
    """
    Extracts Bloomberg-specific metadata from email content.
    
    Responsibilities:
    - Extract category (BFW, BI, BBF, BNEF) from subject
    - Extract author from "By [Name]" pattern
    - Extract Bloomberg Story ID from article URL
    - Extract article date (priority over received date)
    - Extract People section (optional, at end of email)
    - Extract Topics section (optional, at end of email)
    - Extract Tickers section (optional, at end of email)
    """
    
    def __init__(self):
        """Initialize metadata extractor with regex patterns."""
        self.logger = logging.getLogger(__name__)
        
        # Bloomberg categories
        self.categories = ["BFW", "BI", "BBF", "BNEF"]
        
        # Regex patterns
        self.author_pattern = re.compile(
            r'By\s+([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+and\s+[A-Z][a-z]+\s+[A-Z][a-z]+)?)',
            re.IGNORECASE
        )
        
        self.story_id_pattern = re.compile(
            r'bloomberg\.com/news/articles/([A-Z0-9-]+)',
            re.IGNORECASE
        )
        
        # Date patterns (various formats)
        self.date_patterns = [
            # January 15, 2024
            re.compile(r'([A-Z][a-z]+)\s+(\d{1,2}),?\s+(\d{4})', re.IGNORECASE),
            # 15 January 2024
            re.compile(r'(\d{1,2})\s+([A-Z][a-z]+)\s+(\d{4})', re.IGNORECASE),
            # 2024-01-15
            re.compile(r'(\d{4})-(\d{2})-(\d{2})'),
        ]
        
        # Month name to number mapping
        self.months = {
            'january': 1, 'february': 2, 'march': 3, 'april': 4,
            'may': 5, 'june': 6, 'july': 7, 'august': 8,
            'september': 9, 'october': 10, 'november': 11, 'december': 12,
            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4,
            'jun': 6, 'jul': 7, 'aug': 8, 'sep': 9,
            'oct': 10, 'nov': 11, 'dec': 12
        }
    
    def extract(self, subject: str, body: str, received_date: datetime) -> BloombergMetadata:
        """
        Extract all metadata from email.
        
        Args:
            subject: Email subject line
            body: Cleaned email body text
            received_date: Date email was received
            
        Returns:
            BloombergMetadata object with all extracted fields
        """
        metadata = BloombergMetadata()
        
        # Extract from subject
        metadata.category = self.extract_category(subject)
        
        # Extract from body
        metadata.author = self.extract_author(body)
        metadata.story_id = self.extract_story_id(body)
        metadata.article_date = self.extract_article_date(body, received_date)
        metadata.people = self.extract_people(body)
        metadata.topics = self.extract_topics(body)
        metadata.tickers = self.extract_tickers(body)
        
        return metadata
    
    def extract_category(self, subject: str) -> Optional[str]:
        """
        Extract Bloomberg category from subject line.
        
        Categories: BFW, BI, BBF, BNEF
        
        Args:
            subject: Email subject line
            
        Returns:
            Category code or None
        """
        subject_upper = subject.upper()
        
        for category in self.categories:
            if category in subject_upper:
                self.logger.debug(f"Found category: {category}")
                return category
        
        return None
    
    def extract_author(self, body: str) -> Optional[str]:
        """
        Extract author name from body.
        
        Patterns:
        - "By John Doe"
        - "By John Doe and Jane Smith"
        
        Args:
            body: Email body text
            
        Returns:
            Author name(s) or None
        """
        # Search in first 1000 chars (author usually at top)
        search_text = body[:1000]
        
        match = self.author_pattern.search(search_text)
        if match:
            author = match.group(1).strip()
            self.logger.debug(f"Found author: {author}")
            return author
        
        return None
    
    def extract_story_id(self, body: str) -> Optional[str]:
        """
        Extract Bloomberg Story ID from article URL.
        
        Pattern: bloomberg.com/news/articles/[STORY_ID]
        
        Args:
            body: Email body text
            
        Returns:
            Story ID or None
        """
        match = self.story_id_pattern.search(body)
        if match:
            story_id = match.group(1)
            self.logger.debug(f"Found Story ID: {story_id}")
            return story_id
        
        return None
    
    def extract_article_date(self, body: str, fallback_date: datetime) -> datetime:
        """
        Extract article publication date from body.
        
        Priority: Date found in text > received_date
        
        Args:
            body: Email body text
            fallback_date: Fallback date (email received date)
            
        Returns:
            Article date (or fallback)
        """
        # Search in first 2000 chars (date usually near top)
        search_text = body[:2000]
        
        # Try each date pattern
        for pattern in self.date_patterns:
            match = pattern.search(search_text)
            if match:
                try:
                    date = self._parse_date_match(match)
                    if date:
                        self.logger.debug(f"Found article date: {date}")
                        return date
                except:
                    continue
        
        # No date found, use fallback
        return fallback_date
    
    def _parse_date_match(self, match) -> Optional[datetime]:
        """
        Parse date from regex match.
        
        Handles different date formats.
        """
        groups = match.groups()
        
        if len(groups) == 3:
            # Check if first group is month name (January 15, 2024)
            if groups[0].lower() in self.months:
                month = self.months[groups[0].lower()]
                day = int(groups[1])
                year = int(groups[2])
                return datetime(year, month, day)
            
            # Check if second group is month name (15 January 2024)
            elif groups[1].lower() in self.months:
                day = int(groups[0])
                month = self.months[groups[1].lower()]
                year = int(groups[2])
                return datetime(year, month, day)
            
            # ISO format (2024-01-15)
            else:
                year = int(groups[0])
                month = int(groups[1])
                day = int(groups[2])
                return datetime(year, month, day)
        
        return None
    
    def extract_people(self, body: str) -> List[str]:
        """
        Extract people names from "People:" section.
        
        Section appears at END of complete emails (optional).
        Format:
            People:
            Name1, Name2
            Name3
        
        Args:
            body: Email body text
            
        Returns:
            List of people names
        """
        return self._extract_section(body, "People")
    
    def extract_topics(self, body: str) -> List[str]:
        """
        Extract topics from "Topics:" section.
        
        Section appears at END of complete emails (optional).
        Format:
            Topics:
            AI, Technology
            Regulation
        
        Args:
            body: Email body text
            
        Returns:
            List of topics
        """
        return self._extract_section(body, "Topics")
    
    def extract_tickers(self, body: str) -> List[str]:
        """
        Extract stock tickers from "Tickers:" section.
        
        Section appears at END of complete emails (optional).
        Format:
            Tickers:
            AAPL US, MSFT US
        
        Args:
            body: Email body text
            
        Returns:
            List of tickers
        """
        return self._extract_section(body, "Tickers")
    
    def _extract_section(self, body: str, section_name: str) -> List[str]:
        """
        Generic method to extract a metadata section.
        
        Sections are at the END of emails and have format:
            SectionName:
            Item1, Item2
            Item3
        
        Args:
            body: Email body text
            section_name: Name of section to extract
            
        Returns:
            List of items in section
        """
        # Look for section marker (case-insensitive, at start of line)
        pattern = re.compile(
            r'^\s*' + re.escape(section_name) + r'\s*:?\s*$',
            re.MULTILINE | re.IGNORECASE
        )
        
        match = pattern.search(body)
        if not match:
            return []
        
        # Get text after the marker
        start_idx = match.end()
        remaining_text = body[start_idx:]
        
        # Find next section marker or end of text
        next_section_pattern = re.compile(
            r'^\s*(People|Topics|Tickers|Alert|Source)\s*:?\s*$',
            re.MULTILINE | re.IGNORECASE
        )
        
        next_match = next_section_pattern.search(remaining_text)
        if next_match:
            section_text = remaining_text[:next_match.start()]
        else:
            section_text = remaining_text
        
        # Parse items (split by comma and/or newline)
        items = []
        
        # First split by newlines
        lines = section_text.strip().split('\n')
        
        for line in lines:
            # Then split each line by commas
            parts = [p.strip() for p in line.split(',')]
            items.extend([p for p in parts if p])
        
        # Remove duplicates while preserving order
        seen = set()
        unique_items = []
        for item in items:
            if item and item not in seen:
                seen.add(item)
                unique_items.append(item)
        
        if unique_items:
            self.logger.debug(f"Found {section_name}: {unique_items}")
        
        return unique_items


# Example usage
if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    extractor = MetadataExtractor()
    
    # Test email
    subject = "BFW: AI Regulation Update"
    body = """
    By John Doe and Jane Smith
    January 15, 2024
    
    This is the main article content about AI regulation.
    Multiple paragraphs with substantial information.
    
    Read more at: https://bloomberg.com/news/articles/L123ABC456DEF
    
    More content here.
    
    Tickers:
    AAPL US, MSFT US, GOOGL US
    
    People:
    Elon Musk, Sam Altman
    Jensen Huang
    
    Topics:
    AI, Technology
    Regulation, Policy
    """
    
    received_date = datetime.now()
    
    # Extract metadata
    metadata = extractor.extract(subject, body, received_date)
    
    # Display results
    print("\n" + "="*60)
    print("EXTRACTED METADATA")
    print("="*60)
    print(f"Category:      {metadata.category}")
    print(f"Author:        {metadata.author}")
    print(f"Story ID:      {metadata.story_id}")
    print(f"Article Date:  {metadata.article_date}")
    print(f"Tickers:       {metadata.tickers}")
    print(f"Topics:        {metadata.topics}")
    print(f"People:        {metadata.people}")
    print("\n" + "="*60)