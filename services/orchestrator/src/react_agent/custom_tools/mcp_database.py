"""Database tool functions powered by the googleapis/genai-toolbox MCP.

Loads tools from the running MCP Toolbox for Databases server, which provides
prebuilt tools for MSSQL and Neo4j, plus custom MongoDB tools defined in
database_tools.yaml.

Also provides a native Python tool for listing MongoDB collections, since
the genai-toolbox does not support $listCollections as an aggregate stage.
"""
import logging
from asyncio import CancelledError
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from anyio import BrokenResourceError
from langchain_core.tools import BaseTool, tool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.runtime import get_runtime
from pymongo import AsyncMongoClient
from toolbox_langchain import ToolboxClient

from react_agent.context import Context

logger = logging.getLogger(__name__)


@tool("list_mongodb_collections")
async def list_mongodb_collections() -> str:
    """List all collection names in the MongoDB database.

    Use this tool first to discover which collections exist before
    inspecting their schemas or querying documents.
    """
    runtime = get_runtime(Context)
    uri = runtime.context.mongodb_uri
    db_name = runtime.context.mongodb_database

    try:
        async with AsyncMongoClient(uri) as client:
            db = client[db_name]
            collections = await db.list_collection_names()
        logger.info("Collections in '%s': %s", db_name, collections)

        if not collections:
            return f"No collections found in database '{db_name}'."

        return f"Collections in '{db_name}': {collections}"
    except Exception as e:
        logger.warning("Failed to list MongoDB collections.", exc_info=True)
        return f"Error listing collections: {e}"


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

    custom_db_mcp_servers: dict[str, Any] = {
        "mongodb": {
            "transport": "stdio",
            "command": "npx",
            "args": ["-y", "mongodb-mcp-server@latest", "--readOnly"],
            "env": {
                "MDB_MCP_CONNECTION_STRING": runtime.context.mongodb_uri,
                "MDB_MCP_DISABLED_TOOLS": "create,update,delete",
            },
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
                db_mcp_client = MultiServerMCPClient(custom_db_mcp_servers, tool_name_prefix=True)
                async with db_mcp_client.session("mongodb") as db_mcp_session:
                    db_tools = await load_mcp_tools(db_mcp_session)
                    tools.extend(db_tools)
                    logger.info(
                        "Loaded database tools from mongodb mcp server: %s",
                        [tool.name for tool in db_tools],
                    )
                    yield tools
                    mcp_client_yielded = True
            except* (BrokenResourceError, CancelledError, Exception):
                if not mcp_client_yielded:
                    logger.warning(
                        "Failed to load tools from MongoDB MCP server with URI %s.",
                        runtime.context.mongodb_uri,
                        exc_info=True,
                    )
                    yield tools  # Yield toolbox tools even if MCP tools failed
                else:
                    logger.debug(
                        "Error details for MongoDB MCP server failure with URI %s.",
                        runtime.context.mongodb_uri,
                        exc_info=True,
                    )
    except Exception:
        logger.warning(
            "Failed to load database tools from toolbox server at %s.",
            toolbox_uri,
            exc_info=True,
        )
