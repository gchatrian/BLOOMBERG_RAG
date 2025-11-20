#!/usr/bin/env python3
"""
Cleanup Script for Bloomberg RAG System.

This script performs maintenance operations:
1. Delete old stubs from /stubs/ folder (older than N days)
2. Archive old processed stubs from /processed/ folder (older than N months)
3. Rebuild stub_registry.json from Outlook folder scan

Usage:
    python scripts/cleanup.py --delete-old-stubs 30
    python scripts/cleanup.py --archive-processed 6
    python scripts/cleanup.py --rebuild-registry
    python scripts/cleanup.py --all
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
import argparse

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.outlook.extractor import OutlookExtractor
from src.stub.registry import StubRegistry
from config.settings import (
    get_outlook_config,
    get_persistence_config
)


def delete_old_stubs(
    outlook_extractor: OutlookExtractor,
    stub_registry: StubRegistry,
    days_old: int,
    dry_run: bool = False
) -> int:
    """
    Delete stubs older than N days from /stubs/ folder.
    
    Args:
        outlook_extractor: OutlookExtractor instance
        stub_registry: StubRegistry instance
        days_old: Age threshold in days
        dry_run: If True, only show what would be deleted
        
    Returns:
        Number of stubs deleted
    """
    print("\n" + "="*60)
    print(f"DELETE OLD STUBS (older than {days_old} days)")
    print("="*60)
    
    cutoff_date = datetime.now() - timedelta(days=days_old)
    print(f"Cutoff date: {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # FIX: Usa stub_registry.stubs invece di get_all_stubs()
    all_stubs = stub_registry.stubs
    # FIX: Gli stub sono oggetti StubEntry, quindi usa s.status invece di s['status']
    pending_stubs = [s for s in all_stubs if s.status == 'pending']
    
    # Find old stubs
    old_stubs = []
    for stub in pending_stubs:
        # FIX: received_time è già un datetime object in StubEntry
        received_time = stub.received_time
        if isinstance(received_time, str):
            received_time = datetime.fromisoformat(received_time)
        if received_time < cutoff_date:
            old_stubs.append(stub)
    
    print(f"\nFound {len(old_stubs)} stubs older than {days_old} days")
    
    if not old_stubs:
        print("Nothing to delete")
        return 0
    
    if dry_run:
        print("\nDRY RUN - Would delete:")
        for stub in old_stubs:
            # FIX: Usa stub.subject invece di stub['subject']
            print(f"  - {stub.subject} ({stub.received_time})")
        return 0
    
    # Confirm deletion
    response = input(f"\nDelete {len(old_stubs)} old stubs? (yes/no): ")
    if response.lower() != 'yes':
        print("Cancelled")
        return 0
    
    # Delete stubs
    deleted_count = 0
    for stub in old_stubs:
        try:
            # FIX: Usa stub.outlook_entry_id invece di stub['outlook_entry_id']
            outlook_entry_id = stub.outlook_entry_id
            
            # Delete from Outlook
            outlook_extractor.delete_email(outlook_entry_id)
            
            # Remove from registry
            stub_registry.remove_stub(outlook_entry_id)
            
            deleted_count += 1
            # FIX: Usa stub.subject invece di stub['subject']
            print(f"  ✓ Deleted: {stub.subject}")
            
        except Exception as e:
            # FIX: Usa stub.subject invece di stub['subject']
            print(f"  ✗ Failed to delete {stub.subject}: {e}")
    
    print(f"\nDeleted {deleted_count} stubs")
    return deleted_count


def archive_old_processed(
    outlook_extractor: OutlookExtractor,
    months_old: int,
    dry_run: bool = False
) -> int:
    """
    Archive processed stubs older than N months from /processed/ folder.
    
    Args:
        outlook_extractor: OutlookExtractor instance
        months_old: Age threshold in months
        dry_run: If True, only show what would be archived
        
    Returns:
        Number of emails archived
    """
    print("\n" + "="*60)
    print(f"ARCHIVE OLD PROCESSED (older than {months_old} months)")
    print("="*60)
    
    cutoff_date = datetime.now() - timedelta(days=months_old * 30)
    print(f"Cutoff date: {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Get all processed emails
    processed_emails = outlook_extractor.get_emails_from_processed()
    
    # Find old emails
    old_emails = []
    for email in processed_emails:
        received_time = email.get('received_time')
        if isinstance(received_time, str):
            received_time = datetime.fromisoformat(received_time)
        
        if received_time < cutoff_date:
            old_emails.append(email)
    
    print(f"\nFound {len(old_emails)} processed emails older than {months_old} months")
    
    if not old_emails:
        print("Nothing to archive")
        return 0
    
    if dry_run:
        print("\nDRY RUN - Would archive:")
        for email in old_emails:
            print(f"  - {email['subject']} ({email['received_time']})")
        return 0
    
    # Confirm archival
    response = input(f"\nArchive {len(old_emails)} old processed emails? (yes/no): ")
    if response.lower() != 'yes':
        print("Cancelled")
        return 0
    
    # Move to archive folder (or delete)
    archived_count = 0
    for email in old_emails:
        try:
            outlook_entry_id = email['outlook_entry_id']
            
            # Delete from /processed/ (or move to archive folder if exists)
            outlook_extractor.delete_email(outlook_entry_id)
            
            archived_count += 1
            print(f"  ✓ Archived: {email['subject']}")
            
        except Exception as e:
            print(f"  ✗ Failed to archive {email['subject']}: {e}")
    
    print(f"\nArchived {archived_count} emails")
    return archived_count


def rebuild_stub_registry(
    outlook_extractor: OutlookExtractor,
    stub_registry: StubRegistry
) -> None:
    """
    Rebuild stub_registry.json by scanning Outlook folders.
    
    Args:
        outlook_extractor: OutlookExtractor instance
        stub_registry: StubRegistry instance
    """
    print("\n" + "="*60)
    print("REBUILD STUB REGISTRY")
    print("="*60)
    
    # Confirm rebuild
    response = input("\nThis will replace the current registry. Continue? (yes/no): ")
    if response.lower() != 'yes':
        print("Cancelled")
        return
    
    # Clear current registry
    stub_registry.clear()
    
    # Scan /stubs/ folder
    print("\nScanning /stubs/ folder...")
    stubs_in_folder = outlook_extractor.get_emails_from_stubs()
    
    for stub_email in stubs_in_folder:
        try:
            # Register stub
            stub_registry.register_stub(
                outlook_entry_id=stub_email['outlook_entry_id'],
                story_id=stub_email.get('story_id'),
                fingerprint=stub_email.get('fingerprint'),
                subject=stub_email['subject'],
                received_time=stub_email['received_time'],
                status='pending'
            )
            print(f"  ✓ Registered: {stub_email['subject']}")
            
        except Exception as e:
            print(f"  ✗ Failed to register {stub_email['subject']}: {e}")
    
    # Scan /processed/ folder
    print("\nScanning /processed/ folder...")
    processed_in_folder = outlook_extractor.get_emails_from_processed()
    
    for processed_email in processed_in_folder:
        try:
            # Register as completed stub
            stub_registry.register_stub(
                outlook_entry_id=processed_email['outlook_entry_id'],
                story_id=processed_email.get('story_id'),
                fingerprint=processed_email.get('fingerprint'),
                subject=processed_email['subject'],
                received_time=processed_email['received_time'],
                status='completed'
            )
            print(f"  ✓ Registered: {processed_email['subject']}")
            
        except Exception as e:
            print(f"  ✗ Failed to register {processed_email['subject']}: {e}")
    
    # Save registry
    stub_registry.save()
    
    print(f"\nRegistry rebuilt:")
    print(f"  Pending stubs: {len(stubs_in_folder)}")
    print(f"  Completed stubs: {len(processed_in_folder)}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Cleanup and maintenance for Bloomberg RAG system'
    )
    parser.add_argument(
        '--delete-old-stubs',
        type=int,
        metavar='DAYS',
        help='Delete stubs older than N days from /stubs/'
    )
    parser.add_argument(
        '--archive-processed',
        type=int,
        metavar='MONTHS',
        help='Archive processed stubs older than N months from /processed/'
    )
    parser.add_argument(
        '--rebuild-registry',
        action='store_true',
        help='Rebuild stub_registry.json from Outlook folders'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Run all cleanup operations (delete stubs >30 days, archive >6 months, rebuild)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without actually doing it'
    )
    
    args = parser.parse_args()
    
    # Validate
    if not any([args.delete_old_stubs, args.archive_processed, args.rebuild_registry, args.all]):
        parser.error("Specify at least one operation")
    
    try:
        # Initialize components
        outlook_config = get_outlook_config()
        persistence_config = get_persistence_config()
        
        outlook_extractor = OutlookExtractor(outlook_config)
        stub_registry = StubRegistry(persistence_config.stub_registry_json)
        
        print("="*60)
        print("BLOOMBERG RAG - CLEANUP & MAINTENANCE")
        print("="*60)
        
        if args.dry_run:
            print("\n*** DRY RUN MODE - No changes will be made ***")
        
        # Execute operations
        if args.all:
            # Run all cleanup operations
            delete_old_stubs(outlook_extractor, stub_registry, 30, args.dry_run)
            archive_old_processed(outlook_extractor, 6, args.dry_run)
            if not args.dry_run:
                rebuild_stub_registry(outlook_extractor, stub_registry)
        else:
            if args.delete_old_stubs:
                delete_old_stubs(outlook_extractor, stub_registry, args.delete_old_stubs, args.dry_run)
            
            if args.archive_processed:
                archive_old_processed(outlook_extractor, args.archive_processed, args.dry_run)
            
            if args.rebuild_registry:
                if args.dry_run:
                    print("\nDRY RUN: Skipping registry rebuild")
                else:
                    rebuild_stub_registry(outlook_extractor, stub_registry)
        
        print("\n" + "="*60)
        print("CLEANUP COMPLETED")
        print("="*60)
        
        return 0
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())