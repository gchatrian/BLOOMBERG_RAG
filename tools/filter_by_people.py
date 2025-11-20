"""
Google ADK Tool: Filter by People

This tool retrieves articles that mention specific people
without semantic search. Use when the user explicitly asks for
articles mentioning particular individuals.
"""

import logging
from typing import Dict, Any, List
from tools import get_toolkit

logger = logging.getLogger(__name__)


def filter_by_people(people: List[str]) -> Dict[str, Any]:
    """
    Retrieve articles that mention specific people.
    
    Use this tool when users ask for articles about specific individuals
    WITHOUT a specific search query. For example:
    - "Show me articles mentioning Elon Musk"
    - "What do we have about Jerome Powell?"
    - "Give me articles about Warren Buffett and Jamie Dimon"
    
    If the user ALSO specifies a search query, use hybrid_search instead.
    
    Args:
        people: List of people names to filter by.
               The tool returns articles that mention ANY of the people.
               Examples:
               - ["Elon Musk"]
               - ["Jerome Powell", "Janet Yellen"]
               - ["Warren Buffett", "Charlie Munger"]
               
    Note: Names should match how they appear in Bloomberg articles.
          Use full names when possible (e.g., "Jerome Powell" not "Powell").
    
    Returns:
        Dictionary containing:
        - success: Whether the filter succeeded
        - articles: List of articles mentioning the people
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
        >>> filter_by_people(["Elon Musk"])
        {
            "success": True,
            "articles": [
                {
                    "subject": "Tesla CEO Discusses Q3 Results",
                    "date": "2024-10-15",
                    "author": "John Smith",
                    "topics": ["Technology", "Earnings"],
                    "people": ["Elon Musk"],
                    "tickers": ["TSLA"],
                    "content": "Tesla CEO Elon Musk discussed...",
                    "score": 1.0
                }
            ],
            "count": 1,
            "query_info": {
                "search_type": "filter_people",
                "filters_applied": {
                    "people": ["Elon Musk"]
                },
                "timestamp": "2025-11-20T14:30:00"
            },
            "message": "Found 1 articles"
        }
    """
    try:
        logger.info(f"Filter by people: {people}")
        
        # Get toolkit
        toolkit = get_toolkit()
        
        # Use hybrid search with no query and people filters
        filters = {
            "people": people
        }
        
        results = toolkit.search_hybrid(
            query="",  # Empty query to retrieve all articles
            filters=filters
        )
        
        # Format response
        people_str = ", ".join(people)
        response = toolkit.format_response(
            articles=results,
            query_info={
                "search_type": "filter_people",
                "filters_applied": filters
            },
            success=True,
            message=f"Found {len(results)} articles mentioning {people_str}" if results else f"No articles found mentioning {people_str}"
        )
        
        logger.info(f"People filter returned {response['count']} articles")
        return response
        
    except Exception as e:
        logger.error(f"People filter failed: {str(e)}", exc_info=True)
        return {
            "success": False,
            "articles": [],
            "count": 0,
            "query_info": {
                "search_type": "filter_people",
                "filters_applied": {
                    "people": people
                }
            },
            "message": f"Filter failed: {str(e)}"
        }


# ============================================================================
# TOOL METADATA FOR GOOGLE ADK
# ============================================================================

TOOL_NAME = "filter_by_people"
TOOL_DESCRIPTION = "Retrieve articles that mention specific people"