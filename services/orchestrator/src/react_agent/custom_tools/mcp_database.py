"""Database tool functions powered by the googleapis/genai-toolbox MCP.

Loads tools from the running MCP Toolbox for Databases server, which provides
prebuilt tools for MSSQL and Neo4j, plus custom MongoDB tools defined in
database_tools.yaml.
"""

import logging
from asyncio import CancelledError
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from anyio import BrokenResourceError
from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.runtime import get_runtime
from toolbox_langchain import ToolboxClient

from react_agent.context import Context

logger = logging.getLogger(__name__)


@asynccontextmanager
async def load_database_tools() -> AsyncGenerator[list[BaseTool], None]:
    """Load all database tools from the MCP Toolbox for Databases Server and MongoDB MCP Server.

    Connects to the toolbox and mongodb mcp server and loads every available tool
    (prebuilt mssql/neo4j + mongodb tools).

    Returns:
        A list of LangChain-compatible tool objects.
        Returns fallback tools if the toolbox server is unreachable.
    """
    runtime = get_runtime(Context)
    toolbox_uri = runtime.context.db_toolbox_uri
    mongodb_mcp_uri = runtime.context.mongodb_mcp_uri

    custom_db_mcp_servers: dict[str, Any] = {
        "mongodb": {
            "transport": "streamable_http",
            "url": mongodb_mcp_uri,
        }
    }

    tools: list[BaseTool] = []
    try:
        async with ToolboxClient(toolbox_uri) as toolbox_client:
            toolbox_tools = await toolbox_client.aload_toolset()
            tools.extend(toolbox_tools)
            logger.info(
                "Loaded database tools from toolbox at %s: %s",
                toolbox_uri,
                [tool.name for tool in toolbox_tools],
            )
            mcp_client_yielded = False
            try:
                db_mcp_client = MultiServerMCPClient(
                    custom_db_mcp_servers, tool_name_prefix=True
                )
                async with db_mcp_client.session("mongodb") as db_mcp_session:
                    db_tools = await load_mcp_tools(db_mcp_session)
                    tools.extend(db_tools)
                    logger.info(
                        "Loaded database tools from mongodb mcp server: %s",
                        [tool.name for tool in db_tools],
                    )
                    yield tools
                    mcp_client_yielded = True
            except* (BrokenResourceError, CancelledError, RuntimeError, Exception):
                if not mcp_client_yielded:
                    logger.warning(
                        "Failed to load tools from MongoDB MCP server with URI %s.",
                        mongodb_mcp_uri,
                        exc_info=True,
                    )
                    yield tools  # Yield toolbox tools even if MCP tools failed
                else:
                    logger.debug(
                        "Error details for MongoDB MCP server failure with URI %s.",
                        mongodb_mcp_uri,
                        exc_info=True,
                    )
    except Exception:
        logger.warning(
            "Failed to load database tools from toolbox server at %s.",
            toolbox_uri,
            exc_info=True,
        )
