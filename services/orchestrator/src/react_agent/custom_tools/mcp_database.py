"""Database tool functions powered by the googleapis/genai-toolbox MCP.

Loads tools from the running MCP Toolbox for Databases server, which provides
prebuilt tools for MSSQL and Neo4j, plus custom MongoDB tools defined in
database_tools.yaml.
"""
import asyncio
import logging
import os
from asyncio import CancelledError
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, cast

import aiofiles
import yaml
from anyio import BrokenResourceError
from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.runtime import get_runtime
from toolbox_langchain import ToolboxClient

from react_agent.context import Context
from react_agent.utils.utils import (
    extract_mssql_connection_info,
    get_config_dir,
    translate_localhost_to_host_gateway,
)

logger = logging.getLogger(__name__)


async def modify_toolbox_sources(context: Context) -> None:
    """Modify the MCP Toolbox for Databases configuration file to set up data sources based on the current runtime context."""
    db_toolbox_path = os.path.join(get_config_dir(), "db_toolbox", "custom_config.yaml")
    mssql_conn_info = extract_mssql_connection_info(translate_localhost_to_host_gateway(context.ms_sql_connection_string))
    data_sources = {
        "mssql-source": {
            "kind": "mssql",
            "host": mssql_conn_info["host"],
            "port": mssql_conn_info["port"],
            "database": mssql_conn_info["database"],
            "user": mssql_conn_info["user"],
            "password": mssql_conn_info["password"],
        },
        "neo4j-source": {
            "kind": "neo4j",
            "uri": translate_localhost_to_host_gateway(context.neo4j_uri),
            "user": context.neo4j_username,
            "password": context.neo4j_password,
            "database": context.neo4j_database,
        },
    }
    try:
        async with aiofiles.open(db_toolbox_path, "w") as f:
            await f.write(yaml.dump({"sources": data_sources}))
        logger.info("Successfully updated MCP Toolbox configuration with data sources.")
    except Exception as e:
        logger.error("Failed to update MCP Toolbox configuration at %s", db_toolbox_path, exc_info=True)
        raise e


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
        # await modify_toolbox_sources(runtime.context)
        # await asyncio.sleep(2)  # Small delay to ensure the toolbox server picks up the config changes
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
