"""Define the configurable parameters for the agent."""

from __future__ import annotations

import os
from dataclasses import dataclass, field, fields
from typing import Annotated

from react_agent.constants import AvailableModel


@dataclass(kw_only=True)
class Context:
    """The runtime context and configuration parameters for the orchestrator agent.

    This dataclass holds all environment-specific configurations, such as connection strings,
    API keys, URLs, model preferences, and timeouts needed by the LangGraph application.
    Fields are automatically populated from environment variables if not explicitly provided.
    """

    system_prompt: str = field(
        default="",
        metadata={
            "description": "The system prompt to use for the agent's interactions. "
            "This prompt sets the context and behavior for the agent."
        },
    )

    model: Annotated[AvailableModel, {"__template_metadata__": {"kind": "llm"}}] = (
        field(
            default=AvailableModel(os.environ.get("MODEL", "einfra/kimi-k2.7")),
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
    
    ollama_host: str = field(
        default=os.environ.get("OLLAMA_HOST", "http://localhost:11434"),
        metadata={"description": "Base URL for Ollama."},
    )

    # --- Evaluation-only knobs (production-safe: all default to no-ops) -------------------------
    # These exist solely so the offline evaluation harness can vary per-run behaviour WITHOUT
    # touching the production code path. They are carried on Context (set per `ainvoke`) rather than
    # on a module global / mutated env var because `langsmith.aevaluate` runs targets as concurrent
    # async tasks in ONE process — a global would race at max_concurrency >= 2. When left at their
    # defaults (the production case) the graph behaves byte-for-byte as before.
    eval_mode: bool = field(
        default=False,
        metadata={
            "description": "Evaluation mode flag. When True, eval-only behaviours (e.g. a per-run "
            "cache-busting header prepended to every system prompt to defeat provider prompt/KV "
            "caching) are enabled. Off in production."
        },
    )

    translation_model_override: str | None = field(
        default=None,
        metadata={
            "description": "Eval-only: AvailableModel value to force for generate_translation_node "
            "(model sweep). None keeps the production default (einfra/qwen3.5)."
        },
    )

    translation_reasoning_override: bool | None = field(
        default=None,
        metadata={
            "description": "Eval-only: force reasoning on/off for generate_translation_node's model. "
            "None keeps the node's existing reasoning behaviour."
        },
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
        # Iterate over all dataclass fields using reflection.
        for f in fields(self):
            # Skip fields that are explicitly marked as not intended for initialization.
            if not f.init:
                continue

            # If the field value currently equals the default value defined in the class,
            # it means the user did not explicitly override it during instantiation.
            # In this case, we eagerly check the environment variables (e.g. 'OPENAI_API_KEY').
            # This ensures that even if instantiated empty, the context binds securely to the deployment environment.
            if getattr(self, f.name) == f.default:
                setattr(self, f.name, os.environ.get(f.name.upper(), f.default))

        # The reflection loop above pulls env vars as raw strings; coerce the eval-only typed knobs
        # back to their declared types. (Untouched when their env vars are absent → stay at defaults.)
        if isinstance(self.eval_mode, str):
            self.eval_mode = self.eval_mode.strip().lower() in ("1", "true", "yes", "on")
        if isinstance(self.translation_model_override, str) and not self.translation_model_override.strip():
            self.translation_model_override = None
        if isinstance(self.translation_reasoning_override, str):
            val = self.translation_reasoning_override.strip().lower()
            self.translation_reasoning_override = (
                True if val in ("1", "true", "yes", "on")
                else False if val in ("0", "false", "no", "off")
                else None
            )
