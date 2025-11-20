"""
Google ADK Tool: Semantic Search

This tool performs basic semantic search on Bloomberg emails without
temporal scoring or advanced filters. Use this for simple keyword-based
searches when you don't need recency weighting.
"""

import logging
from typing import Dict, Any
from tools import get_toolkit

logger = logging.getLogger(__name__)


def semantic_search(query: str) -> Dict[str, Any]:
    """
    Search Bloomberg emails using semantic similarity only.
    
    Use this tool for basic semantic search without temporal weighting.
    Best for:
    - General topic searches where recency doesn't matter
    - Finding articles about specific companies, people, or events
    - Exploring historical coverage of a topic
    
    For time-sensitive queries or when recent articles are more important,
    use hybrid_search instead.
    
    Args:
        query: Search query describing what to look for.
               Examples:
               - "artificial intelligence regulation"
               - "Federal Reserve interest rates"
               - "Tesla earnings report"
               - "climate change policy"
    
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
          - score: Semantic similarity score (0-1)
        - count: Number of articles returned
        - query_info: Query metadata
        - message: Status or error message
    
    Example:
        >>> semantic_search("Tesla earnings Q3 2024")
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
                    "score": 0.89
                }
            ],
            "count": 1,
            "query_info": {
                "query": "Tesla earnings Q3 2024",
                "search_type": "semantic",
                "timestamp": "2025-11-20T14:30:00"
            },
            "message": "Found 1 articles"
        }
    """
    try:
        logger.info(f"Semantic search for query: {query}")
        
        # Get toolkit
        toolkit = get_toolkit()
        
        # Perform semantic search
        results = toolkit.search_semantic(query=query)
        
        # Format response
        response = toolkit.format_response(
            articles=results,
            query_info={
                "query": query,
                "search_type": "semantic",
                "filters_applied": {}
            },
            success=True,
            message=f"Found {len(results)} articles" if results else "No articles found matching your query"
        )
        
        logger.info(f"Semantic search returned {response['count']} articles")
        return response
        
    except Exception as e:
        logger.error(f"Semantic search failed: {str(e)}", exc_info=True)
        return {
            "success": False,
            "articles": [],
            "count": 0,
            "query_info": {
                "query": query,
                "search_type": "semantic",
                "filters_applied": {}
            },
            "message": f"Search failed: {str(e)}"
        }


# ============================================================================
# TOOL METADATA FOR GOOGLE ADK
# ============================================================================

TOOL_NAME = "semantic_search"
TOOL_DESCRIPTION = "Basic semantic search on Bloomberg emails without temporal weighting"