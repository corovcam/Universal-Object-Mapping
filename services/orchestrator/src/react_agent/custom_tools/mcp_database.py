"""Database tool functions powered by the googleapis/genai-toolbox MCP.

Loads tools from the running MCP Toolbox for Databases server, which provides
prebuilt tools for MSSQL and Neo4j, plus custom MongoDB tools defined in
database_tools.yaml.

Also provides a native Python tool for listing MongoDB collections, since
the genai-toolbox does not support $listCollections as an aggregate stage.
"""

import logging
import os
from typing import Any

from langchain_core.tools import BaseTool, tool
from langgraph.runtime import get_runtime
from motor.motor_asyncio import AsyncIOMotorClient
from toolbox_langchain import ToolboxClient

from react_agent.context import Context

logger = logging.getLogger(__name__)


@tool("list_mongodb_collections")
async def list_mongodb_collections() -> str:
    """List all collection names in the MongoDB database.

    Use this tool first to discover which collections exist before
    inspecting their schemas or querying documents.
    """
    uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    db_name = os.getenv("MONGODB_DATABASE", "uom")

    try:
        client: AsyncIOMotorClient = AsyncIOMotorClient(uri)
        db = client[db_name]
        collections = await db.list_collection_names()
        await client.close()

        if not collections:
            return f"No collections found in database '{db_name}'."

        return f"Collections in '{db_name}':\n" + "\n".join(
            f"  - {name}" for name in sorted(collections)
        )
    except Exception as e:
        logger.warning("Failed to list MongoDB collections.", exc_info=True)
        return f"Error listing collections: {e}"


async def load_database_toolbox_tools() -> list[BaseTool]:
    """Load all database tools from the MCP Toolbox for Databases server.

    Connects to the toolbox server and loads every available tool
    (prebuilt mssql/neo4j + custom mongodb tools from database_tools.yaml).
    Also includes the native list_mongodb_collections tool.

    Returns:
        A list of LangChain-compatible tool objects.
        Returns fallback tools if the toolbox server is unreachable.
    """
    runtime = get_runtime(Context)
    toolbox_uri = runtime.context.db_toolbox_uri

    # Always include native tools that don't depend on the toolbox
    tools: list[BaseTool] = [list_mongodb_collections]

    try:
        async with ToolboxClient(toolbox_uri) as client:
            toolbox_tools: list[Any] = await client.aload_toolset()
            tools.extend(toolbox_tools)
            logger.info(
                "Loaded %d database tools from toolbox at %s",
                len(toolbox_tools),
                toolbox_uri,
            )
    except Exception:
        logger.warning(
            "Failed to connect to database toolbox at %s. "
            "Only native database tools will be available.",
            toolbox_uri,
            exc_info=True,
        )

    return tools
