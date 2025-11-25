#!/usr/bin/env python3
"""
Test script for stub detection.
Tests the StubDetector with sample email bodies.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.stub.detector import StubDetector
from src.processing.cleaner import ContentCleaner


def test_email(detector, email_body, subject):
    """Test stub detection on an email."""
    
    raw_email = {
        'subject': subject,
        'body': email_body,
        'received_date': None
    }
    
    print("="*60)
    print("STUB DETECTION TEST")
    print("="*60)
    print(f"Subject: {subject}")
    print()
    
    # Run detection
    result = detector.detect_from_email(raw_email)
    print(f"Result: {'STUB' if result else 'COMPLETE'}")
    print()
    
    # Get details
    details = detector.get_detection_details(raw_email)
    print("Detection Details:")
    print(f"  Classification: {details['classification']}")
    print(f"  Has Bloomberg pattern: {details['has_bloomberg_pattern']}")
    print(f"  Has author at start: {details['has_author_at_start']}")
    print(f"  Source position: {details['source_position']}")
    print(f"  Source is early: {details['source_is_early']}")
    print(f"  Content after Source: {details['content_after_source_length']} chars")
    print(f"  Total content length: {details['content_length']}")
    print(f"  Story ID: {details['story_id']}")
    
    # Show body after disclaimer removal
    body_clean = detector._remove_email_disclaimer(email_body)
    print()
    print("="*60)
    print("BODY AFTER DISCLAIMER REMOVAL (first 500 chars):")
    print("="*60)
    print(body_clean[:500])
    
    # Show content after Source: if found
    if details['source_position'] is not None:
        print()
        print("="*60)
        print("CONTENT AFTER SOURCE:")
        print("="*60)
        content_after = detector._extract_content_after_source(body_clean, details['source_position'])
        if len(content_after) > 0:
            print(f"Length: {len(content_after)} chars")
            print(content_after[:300])
            if len(content_after) > 300:
                print("...")
        else:
            print("(empty)")
    
    print()


def main():
    """Main test function."""
    
    # Initialize detector
    content_cleaner = ContentCleaner()
    detector = StubDetector(content_cleaner)
    
    # Test email from the logs (should be COMPLETE)
    test_email_1 = """External Email - Be CAUTIOUS, particularly with links and attachments. If you suspect you have received a malicious email, click on the top right SPAM/Phishing button.

UK INSIGHT: Gilt Gyrations Show Budget Is High Stakes for Reeves

Alert: SPOTLIGHT NEWS
Source: BI (Bloomberg Intelligence)

The UK gilt market's recent volatility highlights the high stakes for Chancellor Rachel Reeves as she prepares to deliver her first budget. Market participants are closely watching for fiscal policy announcements that could impact sovereign debt dynamics.

The analysis suggests that any missteps in fiscal messaging could trigger further market instability, particularly given the current economic headwinds facing the UK economy.

People
Rt Hon Rachel Reeves (United Kingdom of Great Britain and Northern Ireland)

Topics
Bloomberg Economic Analysis
Gilts
UK Treasury
Budget News
Currencies

To suspend this alert, click here
To modify this alert, click here

This message was originally sent to GIULIO CHATRIAN via the Bloomberg Terminal."""

    test_email(detector, test_email_1, "UK INSIGHT: Gilt Gyrations Show Budget Is High Stakes for Reeves")
    
    print("\n" + "="*60)
    print()
    
    # Test a clear STUB email
    stub_email = """External Email - Be CAUTIOUS

BHP Says It's 'No Longer Considering' Anglo Takeover (Video)

Alert: SPOTLIGHT NEWS
Source: BLC (Bloomberg TV & Video)

Tickers
AAL LN (Anglo American PLC)
BHP AU (BHP Group Ltd)

Topics
Mergers & Acquisitions
Corporate Finance

To suspend this alert, click here"""

    test_email(detector, stub_email, "BHP Says It's 'No Longer Considering' Anglo Takeover (Video)")
    
    print("\n" + "="*60)
    print()
    
    # Test a clear COMPLETE email with (Bloomberg) pattern
    complete_email = """External Email - Be CAUTIOUS

Yen Tails Are in Demand While Pound Traders Favor ATM Volatility

Alert: FX OPTIONS COLUMN
Source: BFW (Bloomberg First Word)

By Vassilis Karamanis

11/24/2025 03:47:54 [BFW]

(Bloomberg) -- Demand for low-probability yen options remains intact as traders
position for volatility to continue, with intervention speculation doing the rounds.

USD/JPY one-week and one-month 10d flies rally to levels last seen in April,
retaining a persistently bid tone throughout November.

Fiscal concerns push the pair north in the spot market, raising the
risk of intervention by Japanese authorities.

Read more: Yen Intervention Could Come Well Before 160 Level:
Trader Talk

To contact the reporter on this story:
Vassilis Karamanis in Athens at vkaramanis1@bloomberg.net

People
Topics
Currencies
Currency Markets

To suspend this alert, click here"""

    test_email(detector, complete_email, "Yen Tails Are in Demand While Pound Traders Favor ATM Volatility")


if __name__ == '__main__':
    main()