#!/usr/bin/env python3
"""
Status Script for Bloomberg RAG System.

This script displays the current status of the system:
- Email counts in Outlook folders (source, indexed, stubs, processed)
- Vector store size
- Stub statistics (pending, completed)
- Last sync date and stats
- Top topics and authors indexed

Usage:
    python scripts/status.py
    python scripts/status.py --detailed
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from collections import Counter

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.outlook.extractor import OutlookExtractor
from src.stub.registry import StubRegistry
from src.vectorstore.faiss_store import FAISSVectorStore 
from config.settings import (
    get_outlook_config,
    get_vectorstore_config,
    get_persistence_config
)


def count_outlook_folders(outlook_extractor: OutlookExtractor) -> dict:
    """
    Count emails in each Outlook folder.
    
    Args:
        outlook_extractor: OutlookExtractor instance
        
    Returns:
        Dictionary with folder counts
    """
    try:
        # FIX: Usa get_folder_counts() invece dei metodi inesistenti
        outlook_extractor.connect()
        counts = outlook_extractor.get_folder_counts()
        return counts
    except Exception as e:
        print(f"Warning: Could not access Outlook folders - {e}")
        return {'source': 0, 'indexed': 0, 'stubs': 0, 'processed': 0}


def get_vector_store_stats(vector_store: FAISSVectorStore ) -> dict:
    """
    Get vector store statistics.
    
    Args:
        vector_store: FAISSStore instance
        
    Returns:
        Dictionary with vector store stats
    """
    return {
        'size': vector_store.size(),
        'dimension': vector_store.dimension()
    }


def get_stub_stats(stub_registry: StubRegistry) -> dict:
    """
    Get stub statistics.
    
    Args:
        stub_registry: StubRegistry instance
        
    Returns:
        Dictionary with stub stats
    """
    # FIX: Usa stub_registry.stubs invece di get_all_stubs()
    all_stubs = stub_registry.stubs
    
    # Gli stub sono oggetti StubEntry, non dizionari
    pending = [s for s in all_stubs if s.status == 'pending']
    completed = [s for s in all_stubs if s.status == 'completed']
    
    return {
        'total': len(all_stubs),
        'pending': len(pending),
        'completed': len(completed)
    }


def get_last_sync_stats(persistence_config) -> dict:
    """
    Get last sync statistics.
    
    Args:
        persistence_config: PersistenceConfig instance
        
    Returns:
        Dictionary with last sync stats (or None if no sync yet)
    """
    try:
        if not persistence_config.last_sync_json.exists():
            return None
        
        with open(persistence_config.last_sync_json, 'r') as f:
            return json.load(f)
    except Exception:
        return None


def get_top_topics(vector_store: FAISSVectorStore , top_n: int = 10) -> list:
    """
    Get most common topics in indexed documents.
    
    Args:
        vector_store: FAISSStore instance
        top_n: Number of top topics to return
        
    Returns:
        List of (topic, count) tuples
    """
    try:
        all_docs = vector_store.get_all_documents()
        all_topics = []
        
        for doc in all_docs:
            metadata = doc.get('metadata', {})
            bloomberg_meta = metadata.get('bloomberg_metadata', {})
            topics = bloomberg_meta.get('topics', [])
            all_topics.extend(topics)
        
        topic_counts = Counter(all_topics)
        return topic_counts.most_common(top_n)
        
    except Exception as e:
        print(f"Warning: Could not analyze topics - {e}")
        return []


def get_top_authors(vector_store: FAISSVectorStore , top_n: int = 10) -> list:
    """
    Get most common authors in indexed documents.
    
    Args:
        vector_store: FAISSStore instance
        top_n: Number of top authors to return
        
    Returns:
        List of (author, count) tuples
    """
    try:
        all_docs = vector_store.get_all_documents()
        all_authors = []
        
        for doc in all_docs:
            metadata = doc.get('metadata', {})
            bloomberg_meta = metadata.get('bloomberg_metadata', {})
            author = bloomberg_meta.get('author')
            if author:
                all_authors.append(author)
        
        author_counts = Counter(all_authors)
        return author_counts.most_common(top_n)
        
    except Exception as e:
        print(f"Warning: Could not analyze authors - {e}")
        return []


def print_status(detailed: bool = False) -> None:
    """
    Print system status.
    
    Args:
        detailed: If True, show detailed statistics
    """
    print("="*60)
    print("BLOOMBERG RAG - SYSTEM STATUS")
    print("="*60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Initialize components
    outlook_config = get_outlook_config()
    vectorstore_config = get_vectorstore_config()
    persistence_config = get_persistence_config()
    
    outlook_extractor = OutlookExtractor(outlook_config)
    stub_registry = StubRegistry(persistence_config.stub_registry_json)
    vector_store = FAISSVectorStore (vectorstore_config)
    
    # Load vector store if exists
    if vectorstore_config.index_path.exists():
        vector_store.load(vectorstore_config.index_path)
    
    # 1. Outlook Folder Counts
    print("📁 OUTLOOK FOLDERS")
    print("-"*60)
    folder_counts = count_outlook_folders(outlook_extractor)
    print(f"  Source folder:     {folder_counts['source']:>5} emails")
    print(f"  Indexed:           {folder_counts['indexed']:>5} emails")
    print(f"  Stubs (pending):   {folder_counts['stubs']:>5} emails")
    print(f"  Processed (done):  {folder_counts['processed']:>5} emails")
    print()
    
    # 2. Vector Store
    print("🗄️  VECTOR STORE")
    print("-"*60)
    vs_stats = get_vector_store_stats(vector_store)
    print(f"  Documents indexed: {vs_stats['size']:>5}")
    print(f"  Embedding dimension: {vs_stats['dimension']}")
    print(f"  Index file: {vectorstore_config.index_path}")
    print()
    
    # 3. Stub Statistics
    print("📋 STUB STATISTICS")
    print("-"*60)
    stub_stats = get_stub_stats(stub_registry)
    print(f"  Total stubs:       {stub_stats['total']:>5}")
    print(f"  Pending:           {stub_stats['pending']:>5}")
    print(f"  Completed:         {stub_stats['completed']:>5}")
    print()
    
    # 4. Last Sync
    print("🔄 LAST SYNC")
    print("-"*60)
    last_sync = get_last_sync_stats(persistence_config)
    if last_sync:
        sync_time = datetime.fromisoformat(last_sync['timestamp'])
        print(f"  Date: {sync_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Emails processed:  {last_sync['total_emails_processed']}")
        print(f"  → Indexed:         {last_sync['complete_indexed']}")
        print(f"  → Stubs created:   {last_sync['stubs_created']}")
        print(f"  → Stubs completed: {last_sync['stubs_completed']}")
        print(f"  Errors:            {last_sync['errors']}")
        print(f"  Duration:          {last_sync['duration_seconds']:.2f}s")
    else:
        print("  No sync performed yet")
    print()
    
    # 5. Detailed stats (if requested)
    if detailed:
        print("📊 TOP TOPICS")
        print("-"*60)
        top_topics = get_top_topics(vector_store, top_n=10)
        if top_topics:
            for i, (topic, count) in enumerate(top_topics, 1):
                print(f"  {i:>2}. {topic:<30} {count:>4} articles")
        else:
            print("  No topics data available")
        print()
        
        print("✍️  TOP AUTHORS")
        print("-"*60)
        top_authors = get_top_authors(vector_store, top_n=10)
        if top_authors:
            for i, (author, count) in enumerate(top_authors, 1):
                print(f"  {i:>2}. {author:<30} {count:>4} articles")
        else:
            print("  No author data available")
        print()
    
    print("="*60)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Show Bloomberg RAG system status'
    )
    parser.add_argument(
        '--detailed',
        '-d',
        action='store_true',
        help='Show detailed statistics (top topics, authors)'
    )
    
    args = parser.parse_args()
    
    try:
        print_status(detailed=args.detailed)
        return 0
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())