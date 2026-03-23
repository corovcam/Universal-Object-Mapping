"""Documentation search tools via MCP servers and fallback fetching.

Provides tools for fetching framework documentation from:
1. Microsoft Learn MCP (streamable HTTP)
2. Spring Docs MCP (stdio via npx)
3. Fallback: TavilySearch (if TAVILY_API_KEY is set) or basic httpx fetching
"""

import logging
import os
import shutil
from typing import Any

import httpx
from langchain_core.tools import BaseTool, tool
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
            logger.warning("TavilySearch failed, falling back to HTTP fetch.", exc_info=True)

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
    if any(kw in q_lower for kw in ["efcore", "ef core", "entity framework", "dapper", "nhibernate", "dotnet", ".net", "c#"]):
        urls.append(f"https://learn.microsoft.com/en-us/search/?terms={encoded_query}")

    # Always include a generic search as last resort
    urls.append(f"https://learn.microsoft.com/en-us/search/?terms={encoded_query}")

    return urls


async def load_docs_mcp_tools() -> list[BaseTool]:
    """Load documentation tools from MCP servers.

    Connects to:
    1. Microsoft Learn MCP (streamable HTTP)
    2. Spring Docs MCP (stdio via npx)

    Returns loaded MCP tools + the fallback fetch_web_docs tool.
    Falls back gracefully if MCP servers are unavailable.
    """
    tools: list[BaseTool] = [fetch_web_docs]  # Always include the fallback tool

    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient

        servers: dict[str, Any] = {
            "microsoft_learn": {
                "url": "https://learn.microsoft.com/api/mcp",
                "transport": "streamable_http",
            },
        }

        # Only add Spring Docs MCP if npx is available
        if shutil.which("npx"):
            servers["spring_docs"] = {
                "command": "npx",
                "args": ["@enokdev/springdocs-mcp@latest"],
                "transport": "stdio",
            }

        async with MultiServerMCPClient(servers) as client:
            mcp_tools = await client.get_tools()
            tools.extend(mcp_tools)
            logger.info("Loaded %d MCP documentation tools.", len(mcp_tools))

    except Exception:
        logger.warning(
            "Failed to load MCP documentation tools. "
            "Only fallback fetch_web_docs will be available.",
            exc_info=True,
        )

    return tools
