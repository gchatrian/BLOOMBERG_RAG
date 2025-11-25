#!/usr/bin/env python3
"""
Interactive Search Script for Bloomberg RAG System.

This script provides interactive search interface to test retrieval:
- Load vector store and retriever
- Accept queries from command line or interactive mode
- Show results with Bloomberg metadata
- Display score breakdown (semantic, temporal, combined)
- Support parameter tuning (weights, top_k, halflife)
- Support filtering (topics, people, date, ticker)

Usage:
    python scripts/search.py "Federal Reserve interest rates"
    python scripts/search.py --interactive
    python scripts/search.py --query "Tesla" --topics Technology --top-k 5
"""

import sys
from pathlib import Path
from datetime import datetime
import argparse

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.embedding.generator import EmbeddingGenerator
from src.vectorstore.faiss_store import FAISSVectorStore
from src.retrieval.hybrid_retriever import HybridRetriever
from config.settings import (
    get_embedding_config,
    get_vectorstore_config,
    get_retrieval_config
)


def format_article(article: dict, rank: int) -> str:
    """
    Format article for display.
    
    Args:
        article: Article dictionary with metadata
        rank: Result rank number
        
    Returns:
        Formatted string
    """
    lines = []
    lines.append(f"\n{'='*80}")
    lines.append(f"RESULT #{rank}")
    lines.append(f"{'='*80}")
    
    # Title
    if 'subject' in article:
        lines.append(f"📰 {article['subject']}")
    
    # Date and Author
    metadata_line = []
    if 'date' in article:
        date_str = article['date'].strftime('%Y-%m-%d') if hasattr(article['date'], 'strftime') else str(article['date'])
        metadata_line.append(f"📅 {date_str}")
    if 'author' in article:
        metadata_line.append(f"✍️ {article['author']}")
    if metadata_line:
        lines.append(" | ".join(metadata_line))
    
    # Scores
    if 'combined_score' in article:
        lines.append(f"\n🎯 Combined Score: {article['combined_score']:.4f}")
        if 'semantic_score' in article:
            lines.append(f"   └─ Semantic: {article['semantic_score']:.4f}")
        if 'temporal_score' in article:
            lines.append(f"   └─ Temporal: {article['temporal_score']:.4f}")
    
    # Topics
    if 'topics' in article and article['topics']:
        topics = ', '.join(article['topics'][:5])  # Show first 5
        lines.append(f"\n🏷️  Topics: {topics}")
    
    # People
    if 'people' in article and article['people']:
        people = ', '.join(article['people'][:5])  # Show first 5
        lines.append(f"👤 People: {people}")
    
    # Tickers
    if 'tickers' in article and article['tickers']:
        tickers = ', '.join(article['tickers'][:10])  # Show first 10
        lines.append(f"💹 Tickers: {tickers}")
    
    # Preview (first 200 chars of body)
    if 'body' in article:
        preview = article['body'][:200].replace('\n', ' ').strip()
        if len(article['body']) > 200:
            preview += "..."
        lines.append(f"\n📝 Preview: {preview}")
    
    return '\n'.join(lines)


def search(retriever, query: str, top_k: int = 10, recency_weight: float = 0.3, 
          start_date: str = None, end_date: str = None, topics: list = None,
          people: list = None, tickers: list = None):
    """
    Execute search and display results.
    
    Args:
        retriever: HybridRetriever instance
        query: Search query string
        top_k: Number of results to return
        recency_weight: Weight for temporal scoring (0.0-1.0)
        start_date: Start date filter (YYYY-MM-DD)
        end_date: End date filter (YYYY-MM-DD)
        topics: List of topics to filter by
        people: List of people to filter by
        tickers: List of tickers to filter by
    """
    print(f"\n🔍 Searching for: \"{query}\"")
    print(f"   Settings: top_k={top_k}, recency_weight={recency_weight}")
    
    # Build filters
    filters = {}
    if start_date:
        filters['start_date'] = datetime.strptime(start_date, '%Y-%m-%d')
    if end_date:
        filters['end_date'] = datetime.strptime(end_date, '%Y-%m-%d')
    if topics:
        filters['topics'] = topics
    if people:
        filters['people'] = people
    if tickers:
        filters['tickers'] = tickers
    
    if filters:
        print(f"   Filters: {filters}")
    
    print("\nSearching...")
    
    # Execute search
    results = retriever.search(
        query=query,
        top_k=top_k,
        recency_weight=recency_weight,
        **filters
    )
    
    # Display results
    print(f"\n✅ Found {len(results)} results\n")
    
    for i, article in enumerate(results, 1):
        print(format_article(article, i))
    
    print(f"\n{'='*80}\n")


def interactive_mode(retriever):
    """
    Interactive search mode with command prompt.
    
    Args:
        retriever: HybridRetriever instance
    """
    print("\n" + "="*80)
    print("BLOOMBERG RAG - INTERACTIVE SEARCH")
    print("="*80)
    print("\nCommands:")
    print("  <query>                    - Search for query")
    print("  set top_k <n>             - Set number of results")
    print("  set weight <w>            - Set recency weight (0.0-1.0)")
    print("  filter topics <t1> <t2>   - Filter by topics")
    print("  filter people <p1> <p2>   - Filter by people")
    print("  filter tickers <t1> <t2>  - Filter by tickers")
    print("  filter date <start> <end> - Filter by date range (YYYY-MM-DD)")
    print("  clear filters             - Clear all filters")
    print("  quit / exit               - Exit interactive mode")
    print("="*80 + "\n")
    
    # Default settings
    top_k = 10
    recency_weight = 0.3
    filters = {}
    
    while True:
        try:
            user_input = input("search> ").strip()
            
            if not user_input:
                continue
            
            # Exit commands
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\nGoodbye!")
                break
            
            # Settings commands
            if user_input.startswith('set '):
                parts = user_input.split()
                if len(parts) >= 3:
                    setting = parts[1]
                    value = parts[2]
                    
                    if setting == 'top_k':
                        top_k = int(value)
                        print(f"✓ Set top_k = {top_k}")
                    elif setting == 'weight':
                        recency_weight = float(value)
                        print(f"✓ Set recency_weight = {recency_weight}")
                    else:
                        print(f"❌ Unknown setting: {setting}")
                else:
                    print("❌ Usage: set <setting> <value>")
                continue
            
            # Filter commands
            if user_input.startswith('filter '):
                parts = user_input.split()
                if len(parts) >= 3:
                    filter_type = parts[1]
                    filter_values = parts[2:]
                    
                    if filter_type == 'topics':
                        filters['topics'] = filter_values
                        print(f"✓ Filtering by topics: {filter_values}")
                    elif filter_type == 'people':
                        filters['people'] = filter_values
                        print(f"✓ Filtering by people: {filter_values}")
                    elif filter_type == 'tickers':
                        filters['tickers'] = filter_values
                        print(f"✓ Filtering by tickers: {filter_values}")
                    elif filter_type == 'date':
                        if len(filter_values) == 2:
                            filters['start_date'] = datetime.strptime(filter_values[0], '%Y-%m-%d')
                            filters['end_date'] = datetime.strptime(filter_values[1], '%Y-%m-%d')
                            print(f"✓ Filtering by date: {filter_values[0]} to {filter_values[1]}")
                        else:
                            print("❌ Usage: filter date <start> <end> (YYYY-MM-DD)")
                    else:
                        print(f"❌ Unknown filter type: {filter_type}")
                else:
                    print("❌ Usage: filter <type> <value1> [value2] ...")
                continue
            
            # Clear filters
            if user_input == 'clear filters':
                filters = {}
                print("✓ Cleared all filters")
                continue
            
            # Otherwise treat as search query
            query = user_input
            search(
                retriever=retriever,
                query=query,
                top_k=top_k,
                recency_weight=recency_weight,
                start_date=filters.get('start_date').strftime('%Y-%m-%d') if filters.get('start_date') else None,
                end_date=filters.get('end_date').strftime('%Y-%m-%d') if filters.get('end_date') else None,
                topics=filters.get('topics'),
                people=filters.get('people'),
                tickers=filters.get('tickers')
            )
            
        except KeyboardInterrupt:
            print("\n\nInterrupted. Type 'quit' to exit.")
        except Exception as e:
            print(f"\n❌ Error: {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Search Bloomberg emails'
    )
    parser.add_argument(
        'query',
        nargs='?',
        help='Search query'
    )
    parser.add_argument(
        '--interactive',
        '-i',
        action='store_true',
        help='Interactive mode'
    )
    parser.add_argument(
        '--top-k',
        type=int,
        default=10,
        help='Number of results (default: 10)'
    )
    parser.add_argument(
        '--weight',
        type=float,
        default=0.3,
        help='Recency weight 0.0-1.0 (default: 0.3)'
    )
    parser.add_argument(
        '--start-date',
        help='Start date filter (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--end-date',
        help='End date filter (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--topics',
        nargs='+',
        help='Topic filters'
    )
    parser.add_argument(
        '--people',
        nargs='+',
        help='People filters'
    )
    parser.add_argument(
        '--tickers',
        nargs='+',
        help='Ticker filters'
    )
    
    args = parser.parse_args()
    
    # Validate
    if not args.interactive and not args.query:
        parser.error("Either provide a query or use --interactive mode")
    
    try:
        # Initialize components
        print("Loading vector store and retriever...")
        
        embedding_config = get_embedding_config()
        vectorstore_config = get_vectorstore_config()
        retrieval_config = get_retrieval_config()
        
        # Check if index exists
        if not vectorstore_config.index_path.exists():
            print(f"\nError: Vector store not found at {vectorstore_config.index_path}")
            print("Run 'python scripts/sync_emails.py' first to index emails")
            return 1
        
        # Load components
        # FIX: Pass model_name string instead of config object
        embedding_generator = EmbeddingGenerator(embedding_config.model_name)
        
        vector_store = FAISSVectorStore.load(
            str(vectorstore_config.index_path),
            embedding_config.embedding_dim
        )
        
        retriever = HybridRetriever(
            vector_store=vector_store,
            embedding_generator=embedding_generator
        )
        
        print(f"✓ Loaded {vector_store.get_index_size()} documents\n")
        
        # Execute
        if args.interactive:
            interactive_mode(retriever)
        else:
            search(
                retriever=retriever,
                query=args.query,
                top_k=args.top_k,
                recency_weight=args.weight,
                start_date=args.start_date,
                end_date=args.end_date,
                topics=args.topics,
                people=args.people,
                tickers=args.tickers
            )
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())