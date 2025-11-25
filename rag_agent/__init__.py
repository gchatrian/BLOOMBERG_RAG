"""
Bloomberg RAG Agent Package

This package provides a Google ADK agent for searching and analyzing
Bloomberg email newsletters.

The agent uses OpenAI GPT-4o via LiteLLM and provides tools for:
- Hybrid search (semantic + temporal ranking)
- Semantic search
- Date range filtering
- Topic filtering
- People filtering
- Ticker filtering

Usage:
    cd bloomberg-rag
    adk web
    # Select "rag_agent" in the dropdown
"""

from .agent import root_agent

__all__ = ["root_agent"]