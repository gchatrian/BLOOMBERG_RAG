#!/usr/bin/env python3
"""
Reconcile Orphaned Stubs Script - WITH FIXED FINGERPRINT MATCHING

Fixes stubs that remain in /stubs/ folder even though their complete email
is already processed and in /indexed/.

KEY FIX: Uses StubRegistry.create_fingerprint() for consistent fingerprint
generation that normalizes Bloomberg prefixes (BN), (BI), (BBF), etc.

Usage:
    python scripts/reconcile_stubs.py --debug  (show matching details)
    python scripts/reconcile_stubs.py --dry-run
"""

import sys
import logging
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.outlook.extractor import OutlookExtractor
from src.processing.cleaner import ContentCleaner
from src.processing.metadata_extractor import MetadataExtractor
from src.stub.registry import StubRegistry
from src.stub.matcher import StubMatcher
from src.models import StubEntry
from config.settings import (
    get_outlook_config,
    get_persistence_config
)


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )


def extract_indexed_emails_metadata(outlook_extractor: OutlookExtractor,
                                    content_cleaner: ContentCleaner,
                                    metadata_extractor: MetadataExtractor) -> List[Dict]:
    """
    Extract Story ID and fingerprint from all emails in /indexed/.
    
    CRITICAL: Uses StubRegistry.create_fingerprint() for consistent
    fingerprint generation that normalizes Bloomberg prefixes.
    """
    logger = logging.getLogger(__name__)
    logger.info("Scanning /indexed/ folder for complete emails...")
    
    try:
        indexed_folder = outlook_extractor.get_folder(outlook_extractor.indexed_folder_path)
        emails = indexed_folder.Items
        
        indexed_metadata = []
        
        for email in emails:
            if email.Class != 43:
                continue
            
            try:
                subject = email.Subject
                body = email.Body
                received_date = outlook_extractor._convert_outlook_date(email.ReceivedTime)
                outlook_entry_id = email.EntryID
                
                # Clean and extract metadata
                cleaned_body = content_cleaner.clean(body)
                metadata = metadata_extractor.extract(
                    subject=subject,
                    body=cleaned_body,
                    received_date=received_date
                )
                
                # =============================================================
                # FIX: Use StubRegistry.create_fingerprint()
                # This automatically normalizes Bloomberg prefixes!
                # =============================================================
                fingerprint = StubRegistry.create_fingerprint(subject, received_date)
                
                indexed_metadata.append({
                    'story_id': metadata.story_id,
                    'fingerprint': fingerprint,
                    'subject': subject,
                    'outlook_entry_id': outlook_entry_id,
                    'received_date': received_date
                })
                
            except Exception as e:
                logger.warning(f"Failed to extract metadata from indexed email: {e}")
                continue
        
        logger.info(f"Extracted metadata from {len(indexed_metadata)} indexed emails")
        return indexed_metadata
        
    except Exception as e:
        logger.error(f"Failed to scan /indexed/ folder: {e}")
        return []


def print_debug_samples(pending_stubs: List[StubEntry],
                       indexed_emails: List[Dict],
                       num_samples: int = 5):
    """
    Print samples of stubs and indexed emails for debugging.
    """
    print("\n" + "=" * 80)
    print("DEBUG: SAMPLE DATA")
    print("=" * 80)
    
    print(f"\n📧 First {num_samples} PENDING STUBS:")
    print("-" * 80)
    for i, stub in enumerate(pending_stubs[:num_samples]):
        print(f"\n[{i+1}] Subject: {stub.subject}")
        print(f"    Story ID: {stub.story_id or '(none)'}")
        print(f"    Fingerprint: {stub.fingerprint}")
        print(f"    Date: {stub.received_time}")
    
    print(f"\n\n📬 First {num_samples} INDEXED EMAILS:")
    print("-" * 80)
    for i, email in enumerate(indexed_emails[:num_samples]):
        print(f"\n[{i+1}] Subject: {email['subject']}")
        print(f"    Story ID: {email['story_id'] or '(none)'}")
        print(f"    Fingerprint: {email['fingerprint']}")
        print(f"    Date: {email['received_date']}")
    
    # Count how many have Story IDs
    stubs_with_story_id = sum(1 for s in pending_stubs if s.story_id)
    emails_with_story_id = sum(1 for e in indexed_emails if e['story_id'])
    
    print("\n" + "-" * 80)
    print(f"STATISTICS:")
    print(f"  Stubs with Story ID: {stubs_with_story_id}/{len(pending_stubs)}")
    print(f"  Indexed with Story ID: {emails_with_story_id}/{len(indexed_emails)}")
    print("=" * 80 + "\n")


def find_matches(pending_stubs: List[StubEntry],
                indexed_emails: List[Dict],
                debug: bool = False) -> List[Tuple[StubEntry, Dict]]:
    """
    Find matches between pending stubs and indexed emails.
    """
    logger = logging.getLogger(__name__)
    logger.info("Matching pending stubs with indexed emails...")
    
    matches = []
    
    # Create lookup maps
    story_id_map = {}
    fingerprint_map = {}
    
    for email_meta in indexed_emails:
        if email_meta['story_id']:
            story_id_map[email_meta['story_id']] = email_meta
        if email_meta['fingerprint']:
            fingerprint_map[email_meta['fingerprint']] = email_meta
    
    if debug:
        print(f"\n[DEBUG] Story ID map has {len(story_id_map)} entries")
        print(f"[DEBUG] Fingerprint map has {len(fingerprint_map)} entries")
        
        if story_id_map:
            sample_story_ids = list(story_id_map.keys())[:3]
            print(f"[DEBUG] Sample Story IDs: {sample_story_ids}")
        
        if fingerprint_map:
            sample_fingerprints = list(fingerprint_map.keys())[:3]
            print(f"[DEBUG] Sample fingerprints:")
            for fp in sample_fingerprints:
                print(f"  - {fp}")
    
    # Try to match each stub
    matched_count = 0
    no_match_count = 0
    
    for stub in pending_stubs:
        matched_email = None
        match_method = None
        
        # Try Story ID match first
        if stub.story_id:
            if stub.story_id in story_id_map:
                matched_email = story_id_map[stub.story_id]
                match_method = "Story ID"
                if debug and matched_count < 3:
                    print(f"\n[DEBUG] ✓ Story ID match: {stub.story_id}")
                    print(f"  Stub: {stub.subject[:60]}")
                    print(f"  Email: {matched_email['subject'][:60]}")
        
        # Fallback to fingerprint
        if not matched_email and stub.fingerprint:
            if stub.fingerprint in fingerprint_map:
                matched_email = fingerprint_map[stub.fingerprint]
                match_method = "Fingerprint"
                if debug and matched_count < 3:
                    print(f"\n[DEBUG] ✓ Fingerprint match:")
                    print(f"  Stub fingerprint: {stub.fingerprint}")
                    print(f"  Stub subject: {stub.subject[:60]}")
                    print(f"  Email subject: {matched_email['subject'][:60]}")
        
        if matched_email:
            matched_count += 1
            logger.info(f"  ✓ MATCH ({match_method}): {stub.subject[:50]}...")
            matches.append((stub, matched_email))
        else:
            no_match_count += 1
            if debug and no_match_count <= 3:
                print(f"\n[DEBUG] ✗ No match for stub:")
                print(f"  Subject: {stub.subject[:60]}")
                print(f"  Story ID: {stub.story_id or '(none)'}")
                print(f"  Fingerprint: {stub.fingerprint}")
    
    logger.info(f"Found {len(matches)} matches out of {len(pending_stubs)} pending stubs")
    return matches


def reconcile_stubs(matches: List[Tuple[StubEntry, Dict]],
                   stub_matcher: StubMatcher,
                   outlook_extractor: OutlookExtractor,
                   dry_run: bool = False) -> Dict[str, int]:
    """
    Reconcile matched stubs.
    """
    logger = logging.getLogger(__name__)
    
    stats = {
        'completed': 0,
        'failed': 0
    }
    
    if dry_run:
        logger.info("=" * 60)
        logger.info("DRY RUN MODE - No changes will be made")
        logger.info("=" * 60)
    
    logger.info(f"Reconciling {len(matches)} orphaned stubs...")
    
    for stub, matched_email in matches:
        logger.info(f"\nProcessing stub: {stub.subject}")
        logger.info(f"  Matched with: {matched_email['subject']}")
        
        if dry_run:
            logger.info("  [DRY RUN] Would move stub to /processed/ and update registry")
            stats['completed'] += 1
            continue
        
        try:
            success = stub_matcher.complete_stub(stub, outlook_extractor)
            
            if success:
                stats['completed'] += 1
                logger.info(f"  ✓ Successfully reconciled stub")
            else:
                stats['failed'] += 1
                logger.error(f"  ✗ Failed to reconcile stub")
                
        except Exception as e:
            stats['failed'] += 1
            logger.error(f"  ✗ Error reconciling stub: {e}")
    
    return stats


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Reconcile orphaned stubs with indexed emails'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without applying them'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Show detailed matching information'
    )
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose or args.debug)
    logger = logging.getLogger(__name__)
    
    print("=" * 60)
    print("STUB RECONCILIATION")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if args.dry_run:
        print("MODE: DRY RUN (preview only)")
    if args.debug:
        print("MODE: DEBUG (detailed output)")
    print()
    
    outlook_extractor = None
    
    try:
        # Load configurations
        outlook_config = get_outlook_config()
        persistence_config = get_persistence_config()
        
        # Initialize components
        logger.info("Initializing components...")
        
        outlook_extractor = OutlookExtractor(
            outlook_config.source_folder,
            outlook_config.indexed_folder,
            outlook_config.stubs_folder,
            outlook_config.processed_folder
        )
        
        content_cleaner = ContentCleaner()
        metadata_extractor = MetadataExtractor()
        stub_registry = StubRegistry(persistence_config.stub_registry_json)
        stub_matcher = StubMatcher(stub_registry)
        
        # Connect to Outlook
        logger.info("Connecting to Outlook...")
        outlook_extractor.connect()
        logger.info("Connected successfully")
        
        # Step 1: Extract metadata from /indexed/ emails
        indexed_emails = extract_indexed_emails_metadata(
            outlook_extractor,
            content_cleaner,
            metadata_extractor
        )
        
        if not indexed_emails:
            print("\nNo emails found in /indexed/ folder")
            return 0
        
        # Step 2: Get pending stubs
        pending_stubs = stub_registry.get_all_pending()
        
        if not pending_stubs:
            print("\nNo pending stubs in registry")
            return 0
        
        logger.info(f"Found {len(pending_stubs)} pending stubs in registry")
        
        # Show debug samples if requested
        if args.debug:
            print_debug_samples(pending_stubs, indexed_emails)
        
        # Step 3: Find matches
        matches = find_matches(pending_stubs, indexed_emails, debug=args.debug)
        
        if not matches:
            print("\n" + "=" * 60)
            print("No orphaned stubs found")
            if args.debug:
                print("\n⚠  This might indicate a matching logic problem!")
                print("   Check the DEBUG output above to see why stubs don't match.")
            print("=" * 60)
            return 0
        
        # Step 4: Reconcile stubs
        stats = reconcile_stubs(
            matches,
            stub_matcher,
            outlook_extractor,
            dry_run=args.dry_run
        )
        
        # Print final summary
        print("\n" + "=" * 60)
        print("RECONCILIATION COMPLETED")
        print("=" * 60)
        print(f"Total orphaned stubs found: {len(matches)}")
        print(f"Successfully reconciled: {stats['completed']}")
        print(f"Failed: {stats['failed']}")
        
        if args.dry_run:
            print("\n⚠  DRY RUN - No actual changes were made")
            print("   Run without --dry-run to apply changes")
        
        print("=" * 60)
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\nReconciliation interrupted by user")
        return 1
        
    except Exception as e:
        logger.error(f"Reconciliation failed: {e}", exc_info=True)
        print(f"\n\nERROR: Reconciliation failed - {e}")
        return 1
    
    finally:
        if outlook_extractor:
            try:
                outlook_extractor.close()
                logger.info("Outlook connection closed")
            except:
                pass


if __name__ == '__main__':
    sys.exit(main())