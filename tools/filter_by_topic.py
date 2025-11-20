"""
Google ADK Tool: Filter by Topic

This tool retrieves articles tagged with specific Bloomberg topics
without semantic search. Use when the user explicitly asks for
articles about a specific Bloomberg topic category.
"""

import logging
from typing import Dict, Any, List
from tools import get_toolkit

logger = logging.getLogger(__name__)


def filter_by_topic(topics: List[str]) -> Dict[str, Any]:
    """
    Retrieve articles tagged with specific Bloomberg topics.
    
    Use this tool when users ask for articles by Bloomberg topic category
    WITHOUT a specific search query. For example:
    - "Show me all Technology articles"
    - "What do we have about Energy?"
    - "Give me Finance and Markets articles"
    
    If the user ALSO specifies a search query, use hybrid_search instead.
    
    Common Bloomberg topics include:
    - Technology
    - Finance
    - Energy
    - Healthcare
    - Politics
    - Markets
    - Economy
    - Climate
    - Regulation
    - Earnings
    - M&A (Mergers & Acquisitions)
    - Central Banks
    
    Args:
        topics: List of Bloomberg topic names to filter by.
               The tool returns articles that match ANY of the topics.
               Examples:
               - ["Technology"]
               - ["Finance", "Markets"]
               - ["Energy", "Climate"]
    
    Returns:
        Dictionary containing:
        - success: Whether the filter succeeded
        - articles: List of articles with matching topics
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
        >>> filter_by_topic(["Technology", "AI"])
        {
            "success": True,
            "articles": [
                {
                    "subject": "OpenAI Announces GPT-5",
                    "date": "2024-10-20",
                    "author": "Alice Johnson",
                    "topics": ["Technology", "AI"],
                    "people": ["Sam Altman"],
                    "tickers": [],
                    "content": "OpenAI has announced the release...",
                    "score": 1.0
                }
            ],
            "count": 1,
            "query_info": {
                "search_type": "filter_topic",
                "filters_applied": {
                    "topics": ["Technology", "AI"]
                },
                "timestamp": "2025-11-20T14:30:00"
            },
            "message": "Found 1 articles"
        }
    """
    try:
        logger.info(f"Filter by topics: {topics}")
        
        # Get toolkit
        toolkit = get_toolkit()
        
        # Use hybrid search with no query and topic filters
        filters = {
            "topics": topics
        }
        
        results = toolkit.search_hybrid(
            query="",  # Empty query to retrieve all articles
            filters=filters
        )
        
        # Format response
        topics_str = ", ".join(topics)
        response = toolkit.format_response(
            articles=results,
            query_info={
                "search_type": "filter_topic",
                "filters_applied": filters
            },
            success=True,
            message=f"Found {len(results)} articles about {topics_str}" if results else f"No articles found about {topics_str}"
        )
        
        logger.info(f"Topic filter returned {response['count']} articles")
        return response
        
    except Exception as e:
        logger.error(f"Topic filter failed: {str(e)}", exc_info=True)
        return {
            "success": False,
            "articles": [],
            "count": 0,
            "query_info": {
                "search_type": "filter_topic",
                "filters_applied": {
                    "topics": topics
                }
            },
            "message": f"Filter failed: {str(e)}"
        }


# ============================================================================
# TOOL METADATA FOR GOOGLE ADK
# ============================================================================

TOOL_NAME = "filter_by_topic"
TOOL_DESCRIPTION = "Retrieve articles tagged with specific Bloomberg topics"