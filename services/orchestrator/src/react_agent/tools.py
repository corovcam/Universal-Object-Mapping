"""This module provides the tools for the orchestrator agent.

It defines static tools (validators) and re-exports the async loaders
for database and documentation tools which must be loaded at runtime
in graph nodes.
"""

from typing import Any, List, Optional, cast

from langchain_tavily import TavilySearch
from langgraph.runtime import get_runtime

from react_agent.context import Context
from react_agent.custom_tools.docs_search import fetch_web_docs, load_docs_mcp_tools
from react_agent.custom_tools.dotnet_validator import validate_dotnet_code
from react_agent.custom_tools.java_validator import validate_java_code
from react_agent.custom_tools.mcp_database import load_database_tools
from react_agent.custom_tools.ssh_tools import execute_in_sandbox


async def search(query: str) -> Optional[dict[str, Any]]:
    """Search for general web results.

    This function performs a search using the Tavily search engine, which is designed
    to provide comprehensive, accurate, and trusted results. It's particularly useful
    for answering questions about current events.
    """
    runtime = get_runtime(Context)
    wrapped = TavilySearch(max_results=runtime.context.max_search_results)
    return cast(dict[str, Any], await wrapped.ainvoke({"query": query}))


# Static tools available without async initialization.
# Database and documentation tools are loaded dynamically in graph nodes.
TOOLS: List[Any] = [
    validate_java_code,
    validate_dotnet_code,
    fetch_web_docs,
    execute_in_sandbox,
]

__all__ = [
    "TOOLS",
    "load_database_tools",
    "load_docs_mcp_tools",
    "search",
]
