"""
Bloomberg RAG Agent - Google ADK Agent Definition

This module defines the root_agent for the Bloomberg RAG system using
Google ADK framework with OpenAI GPT-4o via LiteLLM.

Usage:
    cd bloomberg-rag
    adk web
    # Select "rag_agent" in the dropdown at http://localhost:8000

Configuration (via .env):
    OPENAI_API_KEY=sk-...
    MODEL_NAME=openai/gpt-4o
    TEMPERATURE=0.7
"""

import os
import sys
from pathlib import Path

# Add project root to path so we can import from tools/
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.genai import types

# Import system prompt
from .prompt import SYSTEM_PROMPT, AGENT_DESCRIPTION, AGENT_NAME

# Import tools from project root tools/ directory
from tools.hybrid_search import hybrid_search
from tools.semantic_search import semantic_search
from tools.filter_by_date import filter_by_date
from tools.filter_by_topic import filter_by_topic
from tools.filter_by_people import filter_by_people
from tools.filter_by_ticker import filter_by_ticker
from tools.get_current_datetime import get_current_datetime


# ============================================================================
# CONFIGURATION
# ============================================================================

# Model settings (can be overridden via .env)
MODEL_NAME = os.getenv("MODEL_NAME", "openai/gpt-4o")
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.7"))
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "2000"))


# ============================================================================
# AGENT DEFINITION
# ============================================================================

root_agent = Agent(
    # Model configuration: OpenAI GPT-4o via LiteLLM
    model=LiteLlm(model=MODEL_NAME),
    
    # Agent identity
    name=AGENT_NAME,
    description=AGENT_DESCRIPTION,
    
    # System instructions
    instruction=SYSTEM_PROMPT,
    
    # Generation settings
    generate_content_config=types.GenerateContentConfig(
        temperature=TEMPERATURE,
        max_output_tokens=MAX_TOKENS,
    ),
    
    # Tools available to the agent
    tools=[
        # Primary search tool (most powerful)
        hybrid_search,
        
        # Basic semantic search
        semantic_search,
        
        # Filter tools
        filter_by_date,
        filter_by_topic,
        filter_by_people,
        filter_by_ticker,
        
        # Utility tools
        get_current_datetime,
    ],
)


# ============================================================================
# MODULE INFO
# ============================================================================

__all__ = ["root_agent"]

if __name__ == "__main__":
    print(f"Agent: {root_agent.name}")
    print(f"Description: {root_agent.description}")
    print(f"Model: openai/gpt-4o via LiteLLM")
    print(f"Tools: {len(root_agent.tools)}")
    for tool in root_agent.tools:
        print(f"  - {tool.__name__}")