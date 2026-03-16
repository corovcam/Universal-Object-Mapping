"""Database tool functions powered by the official googleapis/genai-toolbox MCP."""

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator, List

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient


@asynccontextmanager
async def load_database_mcp_tools() -> AsyncGenerator[List[BaseTool], None]:
    """Connects to the database MCP server and returns a list of wrapped LangChain tools.

    This function expects the genai-toolbox to be installed locally (e.g. via npx)
    and uses the environment variables (like MSSQL_HOST) to configure the prebuilt tools.
    You could also define multiple servers dynamically based on the state.
    """
    # Define connection parameters for MS SQL, Mongo, and Neo4j depending on what we need.
    # Note: For this example we define a generic fallback "config". In reality, the orchestrator
    # could spawn different tools dynamically based on configuration.

    server_configs = {
        # Assuming you're running the toolbox executable natively or via node
        # User needs to provide PATH/TO/toolbox or npx command.
        "neo4j": {
            "command": "npx",
            "args": ["-y", "@google/genai-toolbox", "--prebuilt", "neo4j", "--stdio"],
            "env": {
                "NEO4J_URI": os.getenv("NEO4J_URI", "bolt://neo4j:7687"),
                "NEO4J_DATABASE": os.getenv("NEO4J_DATABASE", "neo4j"),
                "NEO4J_USERNAME": os.getenv("NEO4J_USERNAME", "neo4j"),
                "NEO4J_PASSWORD": os.getenv("NEO4J_PASSWORD", "Testingneo4j123"),
                # Make sure to inherit system environment, especially PATH
                **os.environ,
            },
        },
        "mssql": {
            "command": "npx",
            "args": ["-y", "@google/genai-toolbox", "--prebuilt", "mssql", "--stdio"],
            "env": {
                "MSSQL_HOST": os.getenv("MSSQL_HOST", "mssql_db"),
                "MSSQL_PORT": os.getenv("MSSQL_PORT", "1433"),
                "MSSQL_DATABASE": os.getenv("MSSQL_DATABASE", "master"),
                "MSSQL_USER": os.getenv("MSSQL_USER", "sa"),
                "MSSQL_PASSWORD": os.getenv("MSSQL_PASSWORD", "Testingorms123"),
                **os.environ,
            },
        },
    }

    # Initialize the client with standard context management
    async with MultiServerMCPClient(server_configs) as client:  # type: ignore
        # get_tools fetches the server's available capabilities
        tools = client.get_tools()
        yield tools
