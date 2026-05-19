"""Define the configurable parameters for the agent."""

from __future__ import annotations

import os
from dataclasses import dataclass, field, fields
from typing import Annotated

from react_agent.constants import AvailableModel


@dataclass(kw_only=True)
class Context:
    """The context for the agent."""

    system_prompt: str = field(
        default="",
        metadata={
            "description": "The system prompt to use for the agent's interactions. "
            "This prompt sets the context and behavior for the agent."
        },
    )

    model: Annotated[AvailableModel, {"__template_metadata__": {"kind": "llm"}}] = (
        field(
            default=AvailableModel(os.environ.get("MODEL", "einfra/kimi-k2.6")),
            metadata={
                "description": "The name of the language model to use for the agent's main translation agent."
            },
        )
    )

    openai_api_url: str = field(
        default=os.environ.get("OPENAI_API_URL", "https://llm.ai.e-infra.cz/v1"),
        metadata={
            "description": "Base URL for OpenAI-compatible providers (like EINFRA)."
        },
    )

    openai_api_key: str = field(
        default=os.environ.get("OPENAI_API_KEY", ""),
        metadata={"description": "API Key for the OpenAI-compatible provider."},
    )

    max_search_results: int = field(
        default=10,
        metadata={
            "description": "The maximum number of search results to return for each search query."
        },
    )

    db_toolbox_uri: str = field(
        default=os.environ.get("DB_TOOLBOX_URI", "http://localhost:5010"),
        metadata={"description": "URI of the MCP Toolbox for Databases server."},
    )
    
    mongodb_mcp_uri: str = field(
        default=os.environ.get("MONGODB_MCP_URI", "http://localhost:3010/mcp"),
        metadata={"description": "URI of the MongoDB MCP server."},
    )
    
    sandbox_execution_timeout: int = field(
        default=480,
        metadata={"description": "Timeout in seconds for executing commands (e.g. database queries) in the Daytona sandbox. Note that, one execution consists of fetching each entity in schema and running all queries, so this should be sufficiently high to allow for that."},
    )
    
    daytona_api_url: str = field(
        default=os.environ.get("DAYTONA_API_URL", "http://localhost:3000/api"),
        metadata={"description": "Base URL for the Daytona API."},
    )
    
    daytona_api_key: str = field(
        default=os.environ.get("DAYTONA_API_KEY", ""),
        metadata={"description": "API Key for authenticating with the Daytona API."},
    )
    
    daytona_target: str = field(
        default=os.environ.get("DAYTONA_TARGET", "us"),
        metadata={"description": "Target region for Daytona sandbox provisioning (e.g., 'us', 'eu')."},
    )
    
    # ms_sql_host: str = field(
    #     default=os.environ.get("MSSQL_HOST", "localhost"),
    #     metadata={"description": "Hostname for Microsoft SQL Server."},
    # )
    
    # ms_sql_port: int = field(
    #     default=int(os.environ.get("MSSQL_PORT", 1333)),
    #     metadata={"description": "Port number for Microsoft SQL Server."},
    # )
    
    ms_sql_connection_string: str = field(
        default=os.environ.get("MSSQL_CONNECTION_STRING", "Server=localhost,1333;Database=WideWorldImporters;User Id=sa;Password=Testingorms123;TrustServerCertificate=True"),
        metadata={"description": "Connection string for Microsoft SQL Server. The connection string must be in the format: 'Server=HOST,PORT;Database=DB_NAME;User Id=USERNAME;Password=PASSWORD;...'."},
    )

    mongodb_uri: str = field(
        default=os.environ.get("MONGODB_URI", "mongodb://localhost:27027"),
        metadata={"description": "Connection URI for MongoDB."},
    )

    mongodb_database: str = field(
        default=os.environ.get("MONGODB_DATABASE", "uom"),
        metadata={"description": "Name of the MongoDB database to use."},
    )
    
    neo4j_uri: str = field(
        default=os.environ.get("NEO4J_URI", "neo4j://localhost:7697"),
        metadata={"description": "Connection URI for Neo4j."},
    )
    
    neo4j_username: str = field(
        default=os.environ.get("NEO4J_USERNAME", "neo4j"),
        metadata={"description": "Username for Neo4j authentication."},
    )
    
    neo4j_password: str = field(
        default=os.environ.get("NEO4J_PASSWORD", "password"),
        metadata={"description": "Password for Neo4j authentication."},
    )
    
    neo4j_database: str = field(
        default=os.environ.get("NEO4J_DATABASE", "neo4j"),
        metadata={"description": "Name of the Neo4j database to use."},
    )
    
    # dotnet_sandbox_dockerfile: str = field(
    #     default=ValidationSandbox.DAYTONA_SANDBOX_IMAGES[SandboxType.DOTNET_10_SANDBOX].dockerfile(),
    #     metadata={"description": "Dockerfile content for the .NET sandbox environment."},
    # )
    
    # java_sandbox_dockerfile: str = field(
    #     default=ValidationSandbox.DAYTONA_SANDBOX_IMAGES[SandboxType.JAVA_25_SANDBOX].dockerfile(),
    #     metadata={"description": "Dockerfile content for the Java sandbox environment."},
    # )

    def __post_init__(self) -> None:
        """Fetch env vars for attributes that were not passed as args."""
        for f in fields(self):
            if not f.init:
                continue

            if getattr(self, f.name) == f.default:
                setattr(self, f.name, os.environ.get(f.name.upper(), f.default))
