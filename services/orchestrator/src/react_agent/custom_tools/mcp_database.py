"""Database tool functions powered by the googleapis/genai-toolbox MCP.

Loads tools from the running MCP Toolbox for Databases server, which provides
prebuilt tools for MSSQL and Neo4j, plus custom MongoDB tools defined in
database_tools.yaml.
"""

import logging
from asyncio import CancelledError
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, cast

from anyio import BrokenResourceError
from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.runtime import get_runtime
from toolbox_langchain import ToolboxClient

from react_agent.context import Context

logger = logging.getLogger(__name__)


@asynccontextmanager
async def load_toolbox_tools() -> AsyncGenerator[list[BaseTool], None]:
    """Load database tools from the MCP Toolbox for Databases server.

    Returns:
        A list of LangChain-compatible tool objects.
        Returns an empty list if the toolbox server is unreachable.
    """
    runtime = get_runtime(Context)
    toolbox_uri = runtime.context.db_toolbox_uri
    try:
        async with ToolboxClient(toolbox_uri) as toolbox_client:
            toolbox_tools = await toolbox_client.aload_toolset()
            logger.info(
                "Loaded database tools from toolbox at %s: %s",
                toolbox_uri,
                [tool.name for tool in toolbox_tools],
            )
            yield cast(list[BaseTool], toolbox_tools)
    except* (BrokenResourceError, CancelledError, RuntimeError, Exception):
        logger.warning(
            "Failed to load database tools from toolbox server at %s.",
            toolbox_uri,
            exc_info=True,
        )
        yield []


@asynccontextmanager
async def load_mongodb_tools() -> AsyncGenerator[list[BaseTool], None]:
    """Load database tools from the MongoDB MCP server.

    Returns:
        A list of LangChain-compatible tool objects.
        Returns an empty list if the MongoDB MCP server is unreachable.
    """
    runtime = get_runtime(Context)
    mongodb_mcp_uri = runtime.context.mongodb_mcp_uri

    custom_db_mcp_servers: dict[str, Any] = {
        "mongodb": {
            "transport": "streamable_http",
            "url": mongodb_mcp_uri,
        }
    }

    try:
        db_mcp_client = MultiServerMCPClient(
            custom_db_mcp_servers, tool_name_prefix=True
        )
        async with db_mcp_client.session("mongodb") as db_mcp_session:
            db_tools = await load_mcp_tools(db_mcp_session)
            logger.info(
                "Loaded database tools from mongodb mcp server: %s",
                [tool.name for tool in db_tools],
            )
            yield db_tools
    except* (BrokenResourceError, CancelledError, RuntimeError, Exception):
        logger.warning(
            "Failed to load tools from MongoDB MCP server with URI %s.",
            mongodb_mcp_uri,
            exc_info=True,
        )
        yield []
