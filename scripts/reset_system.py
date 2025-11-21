#!/usr/bin/env python3
"""
Reset System Script for Bloomberg RAG System.

This script resets the system to initial state by deleting:
- FAISS vector store index
- Stub registry
- Saved documents
- Last sync statistics
- Temporary files

IMPORTANT: This does NOT affect emails in Outlook folders.
Emails remain in their current folders (source, indexed, stubs, processed).

Usage:
    python scripts/reset_system.py
    python scripts/reset_system.py --force  # Skip confirmation
"""

import sys
import json
from pathlib import Path
import shutil
import argparse

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import get_persistence_config, get_vectorstore_config


def get_files_to_delete() -> list:
    """
    Get list of files and directories to delete.
    
    Returns:
        List of (Path, description) tuples
    """
    persistence_config = get_persistence_config()
    vectorstore_config = get_vectorstore_config()
    
    files = []
    
    # FAISS index
    if vectorstore_config.index_path.exists():
        files.append((vectorstore_config.index_path, "FAISS vector store"))
    
    # Stub registry
    if persistence_config.stub_registry_json.exists():
        files.append((persistence_config.stub_registry_json, "Stub registry"))
    
    # Documents pickle
    if persistence_config.emails_pickle.exists():
        files.append((persistence_config.emails_pickle, "Saved documents"))
    
    # Last sync stats
    if persistence_config.last_sync_json.exists():
        files.append((persistence_config.last_sync_json, "Last sync statistics"))
    
    # Backup directory
    if persistence_config.backup_dir.exists():
        files.append((persistence_config.backup_dir, "Backup directory"))
    
    # Temp directory (if exists)
    data_dir = PROJECT_ROOT / "data"
    temp_dir = data_dir / "temp"
    if temp_dir.exists():
        files.append((temp_dir, "Temporary files"))
    
    return files


def display_files_to_delete(files: list):
    """
    Display files that will be deleted.
    
    Args:
        files: List of (Path, description) tuples
    """
    print("\n" + "="*60)
    print("FILES TO DELETE")
    print("="*60)
    
    if not files:
        print("No files found to delete (system already clean)")
        return
    
    for path, description in files:
        if path.is_dir():
            size = sum(f.stat().st_size for f in path.rglob('*') if f.is_file())
            size_str = f"{size / 1024:.1f} KB"
            item_type = "DIR"
        else:
            size_str = f"{path.stat().st_size / 1024:.1f} KB"
            item_type = "FILE"
        
        print(f"  [{item_type}] {description}")
        print(f"         {path}")
        print(f"         Size: {size_str}")
        print()


def confirm_reset() -> bool:
    """
    Ask user for confirmation.
    
    Returns:
        True if user confirms, False otherwise
    """
    print("="*60)
    print("⚠️  WARNING")
    print("="*60)
    print("This will DELETE all indexed data and reset the system")
    print("to its initial empty state.")
    print()
    print("Emails in Outlook folders will NOT be affected.")
    print("You will need to run 'sync' again to re-index emails.")
    print("="*60)
    print()
    
    while True:
        response = input("Are you sure you want to continue? (Y/N): ").strip().upper()
        
        if response in ['Y', 'YES']:
            return True
        elif response in ['N', 'NO']:
            return False
        else:
            print("Please enter Y or N")


def delete_files(files: list):
    """
    Delete files and directories.
    
    Args:
        files: List of (Path, description) tuples
    """
    print("\n" + "="*60)
    print("DELETING FILES")
    print("="*60)
    
    deleted_count = 0
    error_count = 0
    
    for path, description in files:
        try:
            if path.is_dir():
                shutil.rmtree(path)
                print(f"✓ Deleted {description} (directory)")
            else:
                path.unlink()
                print(f"✓ Deleted {description}")
            
            deleted_count += 1
            
        except Exception as e:
            print(f"✗ Failed to delete {description}: {e}")
            error_count += 1
    
    print()
    print(f"Deleted: {deleted_count} items")
    if error_count > 0:
        print(f"Errors: {error_count} items")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Reset Bloomberg RAG system to initial state'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Skip confirmation prompt'
    )
    
    args = parser.parse_args()
    
    print("="*60)
    print("BLOOMBERG RAG - SYSTEM RESET")
    print("="*60)
    
    try:
        # Get files to delete
        files = get_files_to_delete()
        
        # Display files
        display_files_to_delete(files)
        
        if not files:
            print("\n✓ System is already clean")
            return 0
        
        # Confirm (unless --force)
        if not args.force:
            if not confirm_reset():
                print("\nReset cancelled by user")
                return 0
        
        # Delete files
        delete_files(files)
        
        # Final message
        print()
        print("="*60)
        print("RESET COMPLETED")
        print("="*60)
        print("System has been reset to initial state.")
        print()
        print("Next steps:")
        print("  1. Run 'python main.py sync' to re-index emails")
        print("  2. Run 'python main.py status' to check system status")
        print("="*60)
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\nReset interrupted by user")
        return 1
        
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())