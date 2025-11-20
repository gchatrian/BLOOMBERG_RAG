"""
Google ADK Tool: Filter by Date

This tool retrieves articles within a specific date range without
semantic search. Use when the user explicitly asks for articles
from a specific time period.
"""

import logging
from typing import Dict, Any
from tools import get_toolkit

logger = logging.getLogger(__name__)


def filter_by_date(start_date: str, end_date: str) -> Dict[str, Any]:
    """
    Retrieve articles published within a specific date range.
    
    Use this tool when users ask for articles from a specific time period
    WITHOUT a specific topic or search query. For example:
    - "Show me articles from last week"
    - "What did we receive in October 2024?"
    - "Give me all articles between Jan 1 and Jan 31"
    
    If the user ALSO specifies a topic or search term, use hybrid_search instead.
    
    Args:
        start_date: Start date in YYYY-MM-DD format (inclusive).
                   Example: "2024-10-01"
                   
        end_date: End date in YYYY-MM-DD format (inclusive).
                 Example: "2024-10-31"
    
    Returns:
        Dictionary containing:
        - success: Whether the filter succeeded
        - articles: List of articles within date range
          - subject: Article title
          - date: Publication date (YYYY-MM-DD)
          - author: Article author
          - topics: Bloomberg topics (list)
          - people: People mentioned (list)
          - tickers: Stock tickers mentioned (list)
          - content: Article snippet or full content
          - score: 1.0 (no ranking, chronological order)
        - count: Number of articles returned
        - query_info: Filter metadata
        - message: Status or error message
    
    Example:
        >>> filter_by_date("2024-10-01", "2024-10-31")
        {
            "success": True,
            "articles": [
                {
                    "subject": "Fed Holds Rates Steady",
                    "date": "2024-10-15",
                    "author": "Jane Doe",
                    "topics": ["Finance", "Central Banks"],
                    "people": ["Jerome Powell"],
                    "tickers": [],
                    "content": "The Federal Reserve maintained...",
                    "score": 1.0
                }
            ],
            "count": 1,
            "query_info": {
                "search_type": "filter_date",
                "filters_applied": {
                    "start_date": "2024-10-01",
                    "end_date": "2024-10-31"
                },
                "timestamp": "2025-11-20T14:30:00"
            },
            "message": "Found 1 articles"
        }
    """
    try:
        logger.info(f"Filter by date: {start_date} to {end_date}")
        
        # Get toolkit
        toolkit = get_toolkit()
        
        # Use hybrid search with no query (empty query retrieves all)
        # and date filters
        filters = {
            "start_date": start_date,
            "end_date": end_date
        }
        
        results = toolkit.search_hybrid(
            query="",  # Empty query to retrieve all articles
            filters=filters
        )
        
        # Format response
        response = toolkit.format_response(
            articles=results,
            query_info={
                "search_type": "filter_date",
                "filters_applied": filters
            },
            success=True,
            message=f"Found {len(results)} articles between {start_date} and {end_date}" if results else f"No articles found between {start_date} and {end_date}"
        )
        
        logger.info(f"Date filter returned {response['count']} articles")
        return response
        
    except Exception as e:
        logger.error(f"Date filter failed: {str(e)}", exc_info=True)
        return {
            "success": False,
            "articles": [],
            "count": 0,
            "query_info": {
                "search_type": "filter_date",
                "filters_applied": {
                    "start_date": start_date,
                    "end_date": end_date
                }
            },
            "message": f"Filter failed: {str(e)}"
        }


# ============================================================================
# TOOL METADATA FOR GOOGLE ADK
# ============================================================================

TOOL_NAME = "filter_by_date"
TOOL_DESCRIPTION = "Retrieve articles within a specific date range"