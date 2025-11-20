"""
Google ADK Tool: Filter by Ticker

This tool retrieves articles that mention specific stock tickers
without semantic search. Use when the user explicitly asks for
articles about particular companies by ticker symbol.
"""

import logging
from typing import Dict, Any, List
from tools import get_toolkit

logger = logging.getLogger(__name__)


def filter_by_ticker(tickers: List[str]) -> Dict[str, Any]:
    """
    Retrieve articles that mention specific stock tickers.
    
    Use this tool when users ask for articles about specific companies
    by ticker symbol WITHOUT a specific search query. For example:
    - "Show me articles about TSLA"
    - "What do we have about AAPL?"
    - "Give me articles mentioning GOOGL and MSFT"
    
    If the user ALSO specifies a search query, use hybrid_search instead.
    
    Args:
        tickers: List of stock ticker symbols to filter by.
                The tool returns articles that mention ANY of the tickers.
                Examples:
                - ["TSLA"]
                - ["AAPL", "GOOGL"]
                - ["JPM", "BAC", "WFC"]
                
    Note: Tickers should be in uppercase (e.g., "TSLA" not "tsla").
    
    Returns:
        Dictionary containing:
        - success: Whether the filter succeeded
        - articles: List of articles mentioning the tickers
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
        >>> filter_by_ticker(["TSLA"])
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
                    "score": 1.0
                }
            ],
            "count": 1,
            "query_info": {
                "search_type": "filter_ticker",
                "filters_applied": {
                    "tickers": ["TSLA"]
                },
                "timestamp": "2025-11-20T14:30:00"
            },
            "message": "Found 1 articles"
        }
    """
    try:
        logger.info(f"Filter by tickers: {tickers}")
        
        # Normalize tickers to uppercase
        tickers_upper = [ticker.upper() for ticker in tickers]
        
        # Get toolkit
        toolkit = get_toolkit()
        
        # Use hybrid search with no query and ticker filters
        filters = {
            "tickers": tickers_upper
        }
        
        results = toolkit.search_hybrid(
            query="",  # Empty query to retrieve all articles
            filters=filters
        )
        
        # Format response
        tickers_str = ", ".join(tickers_upper)
        response = toolkit.format_response(
            articles=results,
            query_info={
                "search_type": "filter_ticker",
                "filters_applied": filters
            },
            success=True,
            message=f"Found {len(results)} articles mentioning {tickers_str}" if results else f"No articles found mentioning {tickers_str}"
        )
        
        logger.info(f"Ticker filter returned {response['count']} articles")
        return response
        
    except Exception as e:
        logger.error(f"Ticker filter failed: {str(e)}", exc_info=True)
        return {
            "success": False,
            "articles": [],
            "count": 0,
            "query_info": {
                "search_type": "filter_ticker",
                "filters_applied": {
                    "tickers": tickers
                }
            },
            "message": f"Filter failed: {str(e)}"
        }


# ============================================================================
# TOOL METADATA FOR GOOGLE ADK
# ============================================================================

TOOL_NAME = "filter_by_ticker"
TOOL_DESCRIPTION = "Retrieve articles that mention specific stock tickers"