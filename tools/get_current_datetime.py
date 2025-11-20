"""
Google ADK Tool: Get Current Date and Time

This tool provides the current date and time information to the agent.
It helps the agent understand temporal context when searching for articles
or when users ask about "recent" or "today's" news.
"""

from datetime import datetime
from typing import Dict, Any
import pytz


def get_current_datetime(timezone: str = "UTC") -> Dict[str, Any]:
    """
    Get current date and time information.
    
    Use this tool when you need to know the current date and time,
    especially for understanding temporal queries like:
    - "What happened today?"
    - "Show me recent articles"
    - "What's in the news this week?"
    
    This helps you determine appropriate date ranges for searches.
    
    Args:
        timezone: Timezone name (default: "UTC"). Examples: "UTC", "US/Eastern", "Europe/London"
    
    Returns:
        Dictionary containing current datetime information:
        - current_datetime: ISO format datetime string
        - date: ISO format date string (YYYY-MM-DD)
        - time: Time string (HH:MM:SS)
        - timezone: Timezone name
        - day_of_week: Day name (e.g., "Monday")
        - formatted: Human-readable datetime string
        - unix_timestamp: Unix timestamp (seconds since epoch)
    
    Example:
        >>> get_current_datetime()
        {
            "current_datetime": "2025-11-20T14:30:00Z",
            "date": "2025-11-20",
            "time": "14:30:00",
            "timezone": "UTC",
            "day_of_week": "Wednesday",
            "formatted": "Wednesday, November 20, 2025 at 14:30 UTC",
            "unix_timestamp": 1732114200
        }
    """
    try:
        # Get timezone
        tz = pytz.timezone(timezone)
        
        # Get current time in specified timezone
        now = datetime.now(tz)
        
        # Format various representations
        result = {
            "current_datetime": now.isoformat(),
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "timezone": timezone,
            "day_of_week": now.strftime("%A"),
            "formatted": now.strftime("%A, %B %d, %Y at %H:%M %Z"),
            "unix_timestamp": int(now.timestamp()),
            "year": now.year,
            "month": now.month,
            "day": now.day,
            "hour": now.hour,
            "minute": now.minute
        }
        
        return result
        
    except Exception as e:
        # Return UTC as fallback
        now = datetime.utcnow()
        return {
            "current_datetime": now.isoformat() + "Z",
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "timezone": "UTC",
            "day_of_week": now.strftime("%A"),
            "formatted": now.strftime("%A, %B %d, %Y at %H:%M UTC"),
            "unix_timestamp": int(now.timestamp()),
            "year": now.year,
            "month": now.month,
            "day": now.day,
            "hour": now.hour,
            "minute": now.minute,
            "error": f"Invalid timezone '{timezone}', using UTC as fallback"
        }


# ============================================================================
# TOOL METADATA FOR GOOGLE ADK
# ============================================================================

# This metadata can be used by Google ADK for tool registration
TOOL_NAME = "get_current_datetime"
TOOL_DESCRIPTION = "Get current date and time to understand temporal context for searches"