"""
Google ADK Tool: Hybrid Search

This tool performs comprehensive search combining semantic similarity
and temporal relevance. Filters have been removed as they were too restrictive.

The tool returns full article content for RAG synthesis.
"""

import logging
from typing import Dict, Any
from tools import get_toolkit

logger = logging.getLogger(__name__)


def hybrid_search(query: str) -> Dict[str, Any]:
    """
    Search Bloomberg emails with semantic + temporal ranking.
    
    This is the PRIMARY search tool for the RAG system. It retrieves
    relevant Bloomberg articles that the agent will use to synthesize
    answers to user questions.
    
    The tool combines:
    1. Semantic similarity (content relevance to the query)
    2. Temporal scoring (newer articles get higher scores)
    
    Args:
        query: Search query describing what to look for.
               Be descriptive and include relevant keywords.
               Examples:
               - "Federal Reserve interest rate decisions monetary policy"
               - "Tesla earnings revenue electric vehicles"
               - "oil prices crude energy market OPEC"
               - "artificial intelligence regulation technology policy"
               - "EUR USD euro dollar exchange rate forex"
    
    Returns:
        Dictionary containing:
        - success: Whether the search succeeded
        - articles: List of matching articles with FULL content
          - subject: Article title
          - date: Publication date (YYYY-MM-DD)
          - author: Article author
          - topics: Bloomberg topics (list)
          - people: People mentioned (list)
          - tickers: Stock tickers mentioned (list)
          - content: FULL article content for RAG synthesis
          - score: Combined relevance score
        - count: Number of articles returned
        - total_found: Total articles matching query
        - query_info: Query metadata
        - message: Status or error message
    
    Example:
        >>> hybrid_search("Federal Reserve interest rates inflation")
        {
            "success": True,
            "articles": [
                {
                    "subject": "Fed Signals Rate Cuts Ahead",
                    "date": "2024-11-15",
                    "author": "John Smith",
                    "content": "The Federal Reserve indicated that...",
                    "score": 0.92
                },
                ...
            ],
            "count": 20,
            "message": "Found 20 articles"
        }
    """
    try:
        logger.info(f"Hybrid search for query: {query}")
        
        # Get toolkit
        toolkit = get_toolkit()
        
        # Perform hybrid search WITHOUT filters
        results = toolkit.search_hybrid(
            query=query,
            filters=None  # No filters - let semantic search do the work
        )
        
        # Format response
        response = toolkit.format_response(
            articles=results,
            query_info={
                "query": query,
                "search_type": "hybrid"
            },
            success=True,
            message=f"Found {len(results)} articles" if results else "No articles found matching your query"
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
                "search_type": "hybrid"
            },
            "message": f"Search failed: {str(e)}"
        }


# ============================================================================
# TOOL METADATA FOR GOOGLE ADK
# ============================================================================

TOOL_NAME = "hybrid_search"
TOOL_DESCRIPTION = "Search Bloomberg articles with semantic similarity and temporal ranking"