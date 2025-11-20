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
        article: Article dictionary
        rank: Rank number (1-based)
        
    Returns:
        Formatted article string
    """
    metadata = article.get('metadata', {})
    bloomberg = metadata.get('bloomberg_metadata', {})
    
    subject = article.get('subject', 'N/A')
    date = bloomberg.get('article_date', metadata.get('date', 'N/A'))
    author = bloomberg.get('author', 'N/A')
    topics = ', '.join(bloomberg.get('topics', []))
    people = ', '.join(bloomberg.get('people', []))
    tickers = ', '.join(bloomberg.get('tickers', []))
    
    # Scores
    semantic_score = article.get('semantic_score', 0.0)
    temporal_score = article.get('temporal_score', 0.0)
    combined_score = article.get('score', 0.0)
    
    # Content snippet
    content = article.get('body', '')
    snippet = content[:200] + '...' if len(content) > 200 else content
    
    output = []
    output.append(f"\n{'='*60}")
    output.append(f"RANK #{rank}")
    output.append(f"{'='*60}")
    output.append(f"Subject: {subject}")
    output.append(f"Date:    {date}")
    output.append(f"Author:  {author}")
    
    if topics:
        output.append(f"Topics:  {topics}")
    if people:
        output.append(f"People:  {people}")
    if tickers:
        output.append(f"Tickers: {tickers}")
    
    output.append(f"\nScores:")
    output.append(f"  Semantic:  {semantic_score:.4f}")
    output.append(f"  Temporal:  {temporal_score:.4f}")
    output.append(f"  Combined:  {combined_score:.4f}")
    
    output.append(f"\nSnippet:")
    output.append(f"{snippet}")
    
    return '\n'.join(output)


def search(
    retriever: HybridRetriever,
    query: str,
    top_k: int = 10,
    recency_weight: float = 0.3,
    start_date: str = None,
    end_date: str = None,
    topics: list = None,
    people: list = None,
    tickers: list = None
) -> None:
    """
    Perform search and display results.
    
    Args:
        retriever: HybridRetriever instance
        query: Search query
        top_k: Number of results to return
        recency_weight: Weight for temporal scoring (0.0-1.0)
        start_date: Filter start date (YYYY-MM-DD)
        end_date: Filter end date (YYYY-MM-DD)
        topics: List of topics to filter
        people: List of people to filter
        tickers: List of tickers to filter
    """
    print("\n" + "="*60)
    print("SEARCH QUERY")
    print("="*60)
    print(f"Query: {query}")
    print(f"Top-K: {top_k}")
    print(f"Recency Weight: {recency_weight}")
    
    # Build filters
    filters = {}
    if start_date:
        filters['start_date'] = start_date
        print(f"Start Date: {start_date}")
    if end_date:
        filters['end_date'] = end_date
        print(f"End Date: {end_date}")
    if topics:
        filters['topics'] = topics
        print(f"Topics: {', '.join(topics)}")
    if people:
        filters['people'] = people
        print(f"People: {', '.join(people)}")
    if tickers:
        filters['tickers'] = tickers
        print(f"Tickers: {', '.join(tickers)}")
    
    # Perform search
    print("\nSearching...")
    results = retriever.search(
        query=query,
        top_k=top_k,
        filters=filters if filters else None,
        recency_weight=recency_weight
    )
    
    # Display results
    print(f"\nFound {len(results)} results")
    
    for i, article in enumerate(results, 1):
        print(format_article(article, i))
    
    print("\n" + "="*60)


def interactive_mode(retriever: HybridRetriever) -> None:
    """
    Interactive search mode.
    
    Args:
        retriever: HybridRetriever instance
    """
    print("\n" + "="*60)
    print("BLOOMBERG RAG - INTERACTIVE SEARCH")
    print("="*60)
    print("\nCommands:")
    print("  /exit             - Exit")
    print("  /help             - Show help")
    print("  /set top_k N      - Set top-K results (default: 10)")
    print("  /set weight W     - Set recency weight 0.0-1.0 (default: 0.3)")
    print("\nJust type your query to search!")
    
    # Default settings
    settings = {
        'top_k': 10,
        'recency_weight': 0.3
    }
    
    while True:
        try:
            user_input = input("\n> ").strip()
            
            if not user_input:
                continue
            
            if user_input == "/exit":
                print("Goodbye!")
                break
            
            if user_input == "/help":
                print("\nCommands:")
                print("  /exit             - Exit")
                print("  /help             - Show help")
                print("  /set top_k N      - Set top-K results")
                print("  /set weight W     - Set recency weight")
                print("\nCurrent settings:")
                print(f"  top_k: {settings['top_k']}")
                print(f"  recency_weight: {settings['recency_weight']}")
                continue
            
            if user_input.startswith("/set "):
                parts = user_input.split()
                if len(parts) != 3:
                    print("Usage: /set <parameter> <value>")
                    continue
                
                param = parts[1]
                value = parts[2]
                
                if param == "top_k":
                    try:
                        settings['top_k'] = int(value)
                        print(f"Set top_k = {settings['top_k']}")
                    except ValueError:
                        print("Error: top_k must be an integer")
                
                elif param == "weight":
                    try:
                        settings['recency_weight'] = float(value)
                        if not 0.0 <= settings['recency_weight'] <= 1.0:
                            print("Warning: weight should be between 0.0 and 1.0")
                        print(f"Set recency_weight = {settings['recency_weight']}")
                    except ValueError:
                        print("Error: weight must be a float")
                
                else:
                    print(f"Unknown parameter: {param}")
                
                continue
            
            # Perform search
            search(
                retriever=retriever,
                query=user_input,
                top_k=settings['top_k'],
                recency_weight=settings['recency_weight']
            )
            
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}")


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
        embedding_generator = EmbeddingGenerator(embedding_config)
        
        if vectorstore_config.index_path.exists():
            vector_store = FAISSVectorStore.load(
                str(vectorstore_config.index_path),
                embedding_config.embedding_dim
            )
        else:
            print(f"\nError: Vector store not found at {vectorstore_config.index_path}")
            print("Run 'python scripts/sync_emails.py' first to index emails")
            return 1
        
        retriever = HybridRetriever(
            vector_store=vector_store,
            embedding_generator=embedding_generator
        )
        
        print(f"Loaded {vector_store.get_index_size()} documents")
        
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
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())