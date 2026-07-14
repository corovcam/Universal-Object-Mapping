"""Documentation search tools via MCP servers and fallback fetching.

Provides tools for fetching framework documentation from:
1. Microsoft Learn MCP (streamable HTTP)
2. Spring Docs MCP (stdio via npx)
3. Fallback: TavilySearch (if TAVILY_API_KEY is set) or basic httpx fetching
"""

import logging
import os
from contextlib import AsyncExitStack, asynccontextmanager
from typing import Any, AsyncGenerator

import httpx
from langchain_core.tools import BaseTool, tool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


@asynccontextmanager
async def load_docs_mcp_tools() -> AsyncGenerator[list[BaseTool], None]:
    """Load documentation tools from MCP servers.

    Connects to:
    1. Microsoft Learn MCP (streamable HTTP)
    2. Spring Docs MCP (sse)

    Returns loaded MCP tools.
    """
    servers: dict[str, Any] = {
        "microsoft_learn": {
            "url": "https://learn.microsoft.com/api/mcp",
            "transport": "streamable_http",
        }
    }
    if os.getenv("SPRING_DOCS_MCP_URL"):
        servers["spring_docs"] = {
            "url": os.getenv("SPRING_DOCS_MCP_URL"),
            "transport": "sse",
            "timeout": 60,
        }

    tools: list[BaseTool] = []
    # Sessions are entered on an AsyncExitStack so that (a) a failure to open one server degrades
    # gracefully to whatever tools loaded — possibly an empty list — and (b) teardown failures are
    # CONTAINED. The 2026-07-02 efcore→neo4j run crashed with
    # BaseExceptionGroup(GeneratorExit) raised from the streamable-HTTP session's own task group
    # during `__aexit__` (the remote side had long since idled out after a ~30-minute generation),
    # taking down an otherwise-finished node. A doc-tools cleanup error must never kill the run.
    stack = AsyncExitStack()
    try:
        client = MultiServerMCPClient(servers, tool_name_prefix=True)
        docs_mcp_session = await stack.enter_async_context(
            client.session("microsoft_learn")
        )
        mcp_tools = await load_mcp_tools(docs_mcp_session)
        tools.extend(mcp_tools)
        logger.info(
            "Loaded MCP documentation tools: %s", [tool.name for tool in mcp_tools]
        )
    except Exception:
        logger.warning(
            "Failed to load MCP documentation tools. "
            "Only fallback `search` tool with Tavily will be available.",
            exc_info=True,
        )
    else:
        # The Spring Docs MCP server relies on NPX to run a transient Node.js application process.
        # If the user doesn't have NPX installed or the command fails, we want to catch it gracefully
        # instead of aborting the agent's graph iteration.
        try:
            spring_docs_session = await stack.enter_async_context(
                client.session("spring_docs")
            )
            spring_tools = await load_mcp_tools(spring_docs_session)
            tools.extend(spring_tools)
            logger.info(
                "Loaded Spring Docs MCP tools: %s",
                [tool.name for tool in spring_tools],
            )
        except Exception:
            logger.warning("Failed to load Spring Docs MCP tools.", exc_info=True)

    try:
        yield tools
    finally:
        try:
            await stack.aclose()
        except BaseException as e:  # noqa: BLE001 — includes BaseExceptionGroup(GeneratorExit)
            logger.warning("MCP documentation session teardown failed (ignored): %r", e)
