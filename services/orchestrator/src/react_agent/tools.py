"""This module provides the tools for the orchestrator agent.

It defines static tools (validators) and re-exports the async loaders
for database and documentation tools which must be loaded at runtime
in graph nodes.
"""

from typing import Any, List, cast

from langchain_tavily import TavilySearch
from langgraph.runtime import get_runtime

from react_agent.context import Context
from react_agent.custom_tools.docs_search import load_docs_mcp_tools
from react_agent.custom_tools.dotnet_validator import validate_dotnet_code
from react_agent.custom_tools.java_validator import validate_java_code
from react_agent.custom_tools.mcp_database import load_mongodb_tools, load_toolbox_tools
from react_agent.custom_tools.query_validator import (
    check_query_equivalence,
)
from react_agent.custom_tools.sandbox_tools import (
    download_file_from_sandbox,
    execute_in_sandbox,
)


async def search(query: str) -> dict[str, Any] | None:
    """Search for general web results.

    This function performs a search using the Tavily search engine, which is designed
    to provide comprehensive, accurate, and trusted results. It's particularly useful
    for answering questions about information not available from framework-specific MCPs or documentation.
    """
    # We inject the LangGraph runtime to dynamically fetch configuration settings, 
    # such as the max_search_results parameter set by the user or the environment.
    runtime = get_runtime(Context)
    wrapped = TavilySearch(max_results=runtime.context.max_search_results)
    
    # We cast to dict[str, Any] to explicitly satisfy the type-checker, as Tavily's
    # ainvoke can theoretically return arbitrary structures depending on the LangChain version.
    return cast(dict[str, Any], await wrapped.ainvoke({"query": query}))


# Static tools available without async initialization.
# Database and documentation tools are loaded dynamically in graph nodes.
TOOLS: List[Any] = [
    search,
    validate_java_code,
    validate_dotnet_code,
    check_query_equivalence,
    execute_in_sandbox,
    download_file_from_sandbox,
]

__all__ = [
    "TOOLS",
    "load_mongodb_tools",
    "load_docs_mcp_tools",
    "load_toolbox_tools",
    "search",
]
