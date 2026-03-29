"""Documentation search tools via MCP servers and fallback fetching.

Provides tools for fetching framework documentation from:
1. Microsoft Learn MCP (streamable HTTP)
2. Spring Docs MCP (stdio via npx)
3. Fallback: TavilySearch (if TAVILY_API_KEY is set) or basic httpx fetching
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

import httpx
from langchain_core.tools import BaseTool, tool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class DocsSearchInput(BaseModel):
    """Input schema for documentation search tools."""

    query: str = Field(description="The search query for documentation.")
    framework_version: str = Field(
        default="",
        description="Optional framework version to refine the search (e.g., 'EF Core 9', 'Spring Data Neo4j 7.x').",
    )


@tool("fetch_web_docs", args_schema=DocsSearchInput)
async def fetch_web_docs(query: str, framework_version: str = "") -> str:
    """Fetch documentation from the web for any framework.

    Uses Tavily if TAVILY_API_KEY is available, otherwise falls back to
    basic HTTP fetching from official documentation sites.
    """
    search_query = f"{query} {framework_version}".strip()
    tavily_key = os.getenv("TAVILY_API_KEY")

    if tavily_key:
        try:
            from langchain_tavily import TavilySearch

            search = TavilySearch(max_results=5)
            results = await search.ainvoke(search_query)
            return str(results)
        except Exception:
            logger.warning(
                "TavilySearch failed, falling back to HTTP fetch.", exc_info=True
            )

    # Basic HTTP fallback: fetch from official docs sites
    urls = _build_fallback_urls(query, framework_version)
    results = []

    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        for url in urls[:3]:
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    # Take a reasonable snippet of the text content
                    text = resp.text[:5000]
                    results.append(f"--- {url} ---\n{text}")
            except Exception:
                logger.debug("Failed to fetch %s", url, exc_info=True)

    if results:
        return "\n\n".join(results)
    return f"No documentation found for query: {search_query}"


def _build_fallback_urls(query: str, framework_version: str) -> list[str]:
    """Build fallback URLs for common framework documentation sites."""
    encoded_query = query.replace(" ", "+")
    urls = []

    # Detect framework type from query/version
    q_lower = query.lower() + " " + framework_version.lower()

    if any(kw in q_lower for kw in ["spring", "jpa", "mongodb", "neo4j", "java"]):
        urls.append(f"https://docs.spring.io/spring-data/search?q={encoded_query}")
    if any(
        kw in q_lower
        for kw in [
            "efcore",
            "ef core",
            "entity framework",
            "dapper",
            "nhibernate",
            "dotnet",
            ".net",
            "c#",
        ]
    ):
        urls.append(f"https://learn.microsoft.com/en-us/search/?terms={encoded_query}")

    # Always include a generic search as last resort
    urls.append(f"https://learn.microsoft.com/en-us/search/?terms={encoded_query}")

    return urls


@asynccontextmanager
async def load_docs_mcp_tools() -> AsyncGenerator[list[BaseTool], None]:
    """Load documentation tools from MCP servers.

    Connects to:
    1. Microsoft Learn MCP (streamable HTTP)
    2. Spring Docs MCP (stdio via npx)

    Returns loaded MCP tools.
    """
    servers: dict[str, Any] = {
        "microsoft_learn": {
            "url": "https://learn.microsoft.com/api/mcp",
            "transport": "streamable_http",
        },
        "spring_docs": {
            "command": "npx",
            "args": ["@enokdev/springdocs-mcp@latest"],
            "transport": "stdio",
        },
    }
    
    tools: list[BaseTool] = []
    try:
        client = MultiServerMCPClient(servers, tool_name_prefix=True)
        async with client.session("microsoft_learn") as docs_mcp_session:
            mcp_tools = await load_mcp_tools(docs_mcp_session)
            tools.extend(mcp_tools)
            logger.info(
                "Loaded MCP documentation tools: %s", [tool.name for tool in mcp_tools]
            )
            spring_docs_mcp_yielded = False
            try:
                async with client.session("spring_docs") as spring_docs_session:
                    spring_tools = await load_mcp_tools(spring_docs_session)
                    tools.extend(spring_tools)
                    logger.info(
                        "Loaded Spring Docs MCP tools: %s",
                        [tool.name for tool in spring_tools],
                    )
                    yield tools
                    spring_docs_mcp_yielded = True
            except Exception:
                logger.warning(
                    "Failed to load Spring Docs MCP tools.",
                    exc_info=True,
                )
                if not spring_docs_mcp_yielded:
                    yield tools
    except Exception:
        logger.warning(
            "Failed to load MCP documentation tools. "
            "Only fallback fetch_web_docs will be available.",
            exc_info=True,
        )
