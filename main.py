#!/usr/bin/env python3
"""
Bloomberg RAG - Main CLI Application

Unified command-line interface for all Bloomberg RAG operations:
- sync: Synchronize emails from Outlook
- status: Show system status
- search: Interactive search
- cleanup: Maintenance operations
- reset: Reset system to initial state

Usage:
    python main.py sync
    python main.py status --detailed
    python main.py search "Federal Reserve"
    python main.py cleanup --delete-old-stubs 30
    python main.py reset
"""

import sys
import argparse
from pathlib import Path
import subprocess

PROJECT_ROOT = Path(__file__).parent


def run_script(script_name: str, args: list) -> int:
    """
    Run a script with arguments.
    
    Args:
        script_name: Name of the script to run
        args: List of arguments to pass
        
    Returns:
        Exit code
    """
    script_path = PROJECT_ROOT / 'scripts' / script_name
    cmd = [sys.executable, str(script_path)] + args
    
    result = subprocess.run(cmd)
    return result.returncode


def cmd_sync(args) -> int:
    """Execute sync command."""
    script_args = []
    
    if args.max_emails:
        script_args.extend(['--max-emails', str(args.max_emails)])
    
    if args.verbose:
        script_args.append('--verbose')
    
    return run_script('sync_emails.py', script_args)


def cmd_status(args) -> int:
    """Execute status command."""
    script_args = []
    
    if args.detailed:
        script_args.append('--detailed')
    
    return run_script('status.py', script_args)


def cmd_search(args) -> int:
    """Execute search command."""
    script_args = []
    
    if args.interactive:
        script_args.append('--interactive')
    elif args.query:
        script_args.append(args.query)
    else:
        print("Error: Provide --query or use --interactive mode")
        return 1
    
    if args.top_k:
        script_args.extend(['--top-k', str(args.top_k)])
    
    if args.weight:
        script_args.extend(['--weight', str(args.weight)])
    
    if args.start_date:
        script_args.extend(['--start-date', args.start_date])
    
    if args.end_date:
        script_args.extend(['--end-date', args.end_date])
    
    if args.topics:
        script_args.extend(['--topics'] + args.topics)
    
    if args.people:
        script_args.extend(['--people'] + args.people)
    
    if args.tickers:
        script_args.extend(['--tickers'] + args.tickers)
    
    return run_script('search.py', script_args)


def cmd_cleanup(args) -> int:
    """Execute cleanup command."""
    script_args = []
    
    if args.delete_old_stubs:
        script_args.extend(['--delete-old-stubs', str(args.delete_old_stubs)])
    
    if args.archive_processed:
        script_args.extend(['--archive-processed', str(args.archive_processed)])
    
    if args.rebuild_registry:
        script_args.append('--rebuild-registry')
    
    if args.all:
        script_args.append('--all')
    
    if args.dry_run:
        script_args.append('--dry-run')
    
    return run_script('cleanup.py', script_args)


def cmd_reset(args) -> int:
    """Execute reset command."""
    script_args = []
    
    if args.force:
        script_args.append('--force')
    
    return run_script('reset_system.py', script_args)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        prog='main.py',
        description='Bloomberg RAG - Unified CLI',
        epilog='Run "main.py <command> --help" for command-specific help'
    )
    
    subparsers = parser.add_subparsers(
        title='commands',
        description='Available commands',
        dest='command',
        required=True
    )
    
    # ========================================================================
    # SYNC COMMAND
    # ========================================================================
    sync_parser = subparsers.add_parser(
        'sync',
        help='Synchronize emails from Outlook',
        description='Extract emails from Outlook, process stubs, index complete emails'
    )
    sync_parser.add_argument(
        '--max-emails',
        type=int,
        help='Maximum number of emails to process'
    )
    sync_parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose logging'
    )
    sync_parser.set_defaults(func=cmd_sync)
    
    # ========================================================================
    # STATUS COMMAND
    # ========================================================================
    status_parser = subparsers.add_parser(
        'status',
        help='Show system status',
        description='Display folder counts, vector store size, stub stats, and last sync info'
    )
    status_parser.add_argument(
        '--detailed', '-d',
        action='store_true',
        help='Show detailed statistics (top topics, authors)'
    )
    status_parser.set_defaults(func=cmd_status)
    
    # ========================================================================
    # SEARCH COMMAND
    # ========================================================================
    search_parser = subparsers.add_parser(
        'search',
        help='Search indexed emails',
        description='Interactive search with semantic and temporal ranking'
    )
    search_parser.add_argument(
        'query',
        nargs='?',
        help='Search query'
    )
    search_parser.add_argument(
        '--interactive', '-i',
        action='store_true',
        help='Interactive search mode'
    )
    search_parser.add_argument(
        '--top-k',
        type=int,
        help='Number of results (default: 10)'
    )
    search_parser.add_argument(
        '--weight',
        type=float,
        help='Recency weight 0.0-1.0 (default: 0.3)'
    )
    search_parser.add_argument(
        '--start-date',
        help='Start date filter (YYYY-MM-DD)'
    )
    search_parser.add_argument(
        '--end-date',
        help='End date filter (YYYY-MM-DD)'
    )
    search_parser.add_argument(
        '--topics',
        nargs='+',
        help='Topic filters'
    )
    search_parser.add_argument(
        '--people',
        nargs='+',
        help='People filters'
    )
    search_parser.add_argument(
        '--tickers',
        nargs='+',
        help='Ticker filters'
    )
    search_parser.set_defaults(func=cmd_search)
    
    # ========================================================================
    # CLEANUP COMMAND
    # ========================================================================
    cleanup_parser = subparsers.add_parser(
        'cleanup',
        help='Maintenance operations',
        description='Delete old stubs, archive processed emails, rebuild registry'
    )
    cleanup_parser.add_argument(
        '--delete-old-stubs',
        type=int,
        metavar='DAYS',
        help='Delete stubs older than N days'
    )
    cleanup_parser.add_argument(
        '--archive-processed',
        type=int,
        metavar='MONTHS',
        help='Archive processed stubs older than N months'
    )
    cleanup_parser.add_argument(
        '--rebuild-registry',
        action='store_true',
        help='Rebuild stub registry from Outlook folders'
    )
    cleanup_parser.add_argument(
        '--all',
        action='store_true',
        help='Run all cleanup operations'
    )
    cleanup_parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without doing it'
    )
    cleanup_parser.set_defaults(func=cmd_cleanup)
    
    # ========================================================================
    # RESET COMMAND
    # ========================================================================
    reset_parser = subparsers.add_parser(
        'reset',
        help='Reset system to initial state',
        description='Delete all indexed data and reset to empty state (emails in Outlook NOT affected)'
    )
    reset_parser.add_argument(
        '--force',
        action='store_true',
        help='Skip confirmation prompt'
    )
    reset_parser.set_defaults(func=cmd_reset)
    
    # Parse and execute
    args = parser.parse_args()
    
    try:
        exit_code = args.func(args)
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()