"""
Google ADK Tool: Hybrid Search

This tool performs comprehensive search combining semantic similarity,
temporal relevance, and optional metadata filters. This is the most
powerful search tool and should be used for most user queries.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from tools import get_toolkit

logger = logging.getLogger(__name__)


def hybrid_search(
    query: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    topics: Optional[List[str]] = None,
    people: Optional[List[str]] = None,
    tickers: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Search Bloomberg emails with semantic + temporal ranking and filters.
    
    This is the MOST POWERFUL search tool. Use it when:
    - You need recent articles (temporal scoring boosts newer content)
    - You want to filter by date range, topics, people, or tickers
    - You need comprehensive search results
    
    The tool combines:
    1. Semantic similarity (content relevance)
    2. Temporal scoring (newer articles get higher scores)
    3. Optional metadata filters (topics, people, tickers, dates)
    
    Args:
        query: Search query describing what to look for.
               Examples:
               - "Federal Reserve interest rate decisions"
               - "artificial intelligence regulation"
               - "semiconductor supply chain"
               
        start_date: Filter articles from this date onwards (YYYY-MM-DD format).
                   Examples: "2024-01-01", "2024-10-15"
                   
        end_date: Filter articles up to this date (YYYY-MM-DD format).
                 Examples: "2024-12-31", "2024-10-20"
                 
        topics: Filter by Bloomberg topics (list of topic names).
               Examples: ["Technology", "Finance"], ["Energy", "Climate"]
               Common topics: "Technology", "Finance", "Energy", "Healthcare",
                            "Politics", "Markets", "Economy"
               
        people: Filter by people mentioned in articles (list of names).
               Examples: ["Elon Musk"], ["Jerome Powell", "Janet Yellen"]
               
        tickers: Filter by stock tickers mentioned (list of ticker symbols).
                Examples: ["TSLA"], ["AAPL", "GOOGL", "MSFT"]
    
    Returns:
        Dictionary containing:
        - success: Whether the search succeeded
        - articles: List of matching articles with metadata
          - subject: Article title
          - date: Publication date (YYYY-MM-DD)
          - author: Article author
          - topics: Bloomberg topics (list)
          - people: People mentioned (list)
          - tickers: Stock tickers mentioned (list)
          - content: Article snippet or full content
          - score: Combined score (semantic + temporal)
        - count: Number of articles returned
        - query_info: Query and filter metadata
        - message: Status or error message
    
    Example:
        >>> hybrid_search(
        ...     query="Tesla earnings",
        ...     start_date="2024-01-01",
        ...     topics=["Technology"],
        ...     tickers=["TSLA"]
        ... )
        {
            "success": True,
            "articles": [
                {
                    "subject": "Tesla Reports Record Q3 Earnings",
                    "date": "2024-10-15",
                    "author": "John Smith",
                    "topics": ["Technology", "Earnings"],
                    "people": ["Elon Musk"],
                    "tickers": ["TSLA"],
                    "content": "Tesla Inc. reported record earnings...",
                    "score": 0.92
                }
            ],
            "count": 1,
            "query_info": {
                "query": "Tesla earnings",
                "search_type": "hybrid",
                "filters_applied": {
                    "start_date": "2024-01-01",
                    "topics": ["Technology"],
                    "tickers": ["TSLA"]
                },
                "timestamp": "2025-11-20T14:30:00"
            },
            "message": "Found 1 articles"
        }
    """
    try:
        logger.info(f"Hybrid search for query: {query}")
        
        # Build filters dict
        filters = {}
        if start_date:
            filters["start_date"] = start_date
        if end_date:
            filters["end_date"] = end_date
        if topics:
            filters["topics"] = topics
        if people:
            filters["people"] = people
        if tickers:
            filters["tickers"] = tickers
        
        logger.info(f"Filters: {filters}")
        
        # Get toolkit
        toolkit = get_toolkit()
        
        # Perform hybrid search
        results = toolkit.search_hybrid(
            query=query,
            filters=filters if filters else None
        )
        
        # Format response
        response = toolkit.format_response(
            articles=results,
            query_info={
                "query": query,
                "search_type": "hybrid",
                "filters_applied": filters
            },
            success=True,
            message=f"Found {len(results)} articles" if results else "No articles found matching your query and filters"
        )
        
        logger.info(f"Hybrid search returned {response['count']} articles")
        return response
        
    except Exception as e:
        logger.error(f"Hybrid search failed: {str(e)}", exc_info=True)
        return {
            "success": False,
            "articles": [],
            "count": 0,
            "query_info": {
                "query": query,
                "search_type": "hybrid",
                "filters_applied": {
                    "start_date": start_date,
                    "end_date": end_date,
                    "topics": topics,
                    "people": people,
                    "tickers": tickers
                }
            },
            "message": f"Search failed: {str(e)}"
        }


# ============================================================================
# TOOL METADATA FOR GOOGLE ADK
# ============================================================================

TOOL_NAME = "hybrid_search"
TOOL_DESCRIPTION = "Comprehensive search with semantic similarity, temporal ranking, and metadata filters"