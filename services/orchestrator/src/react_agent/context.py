"""Define the configurable parameters for the agent."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field, fields
from typing import Annotated

from daytona import (
    AsyncDaytona,
    AsyncSandbox,
    CreateSandboxFromImageParams,
    Image,
    SandboxState,
)

from react_agent.constants import AvailableModel, SandboxType

logger = logging.getLogger(__name__)

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
            default=AvailableModel.EINFRA_KIMI_K2_6,
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

    mongodb_uri: str = field(
        default=os.environ.get("MONGODB_URI", "mongodb://localhost:27027"),
        metadata={"description": "Connection URI for MongoDB."},
    )

    mongodb_database: str = field(
        default=os.environ.get("MONGODB_DATABASE", "uom"),
        metadata={"description": "Name of the MongoDB database to use."},
    )

    dotnet_service_uri: str = field(
        default=os.environ.get("DOTNET_SERVICE_URI", "http://localhost:5083"),
        metadata={"description": "URI of the .NET service."},
    )

    dotnet_service_ssh_uri: str = field(
        default=os.environ.get("DOTNET_SERVICE_SSH_URI", "ssh://localhost:5022"),
        metadata={"description": "SSH URI of the .NET service."},
    )

    java_service_uri: str = field(
        default=os.environ.get("JAVA_SERVICE_URI", "http://localhost:8090"),
        metadata={"description": "URI of the Java service."},
    )

    java_service_ssh_uri: str = field(
        default=os.environ.get("JAVA_SERVICE_SSH_URI", "ssh://localhost:8022"),
        metadata={"description": "SSH URI of the Java service."},
    )
    
    # dotnet_sandbox_dockerfile: str = field(
    #     default=DAYTONA_SANDBOX_IMAGES[SandboxType.DOTNET_10_SANDBOX].dockerfile(),
    #     metadata={"description": "Dockerfile content for the .NET sandbox environment."},
    # )
    
    # java_sandbox_dockerfile: str = field(
    #     default=DAYTONA_SANDBOX_IMAGES[SandboxType.JAVA_25_SANDBOX].dockerfile(),
    #     metadata={"description": "Dockerfile content for the Java sandbox environment."},
    # )

    def __post_init__(self) -> None:
        """Fetch env vars for attributes that were not passed as args."""
        for f in fields(self):
            if not f.init:
                continue

            if getattr(self, f.name) == f.default:
                setattr(self, f.name, os.environ.get(f.name.upper(), f.default))


class ValidationSandbox:
    SANDBOXES: dict[SandboxType, AsyncSandbox] = {}
    
    DAYTONA_SANDBOX_IMAGES: dict[SandboxType, Image] = {
        SandboxType.DOTNET_10_SANDBOX: Image
            .base(os.getenv("DOTNET_SANDBOX_IMAGE", "mcr.microsoft.com/dotnet/sdk:10.0")),
            # .workdir("/sandbox")
            # .add_local_file(os.path.join(os.getenv("CONTEXT_ABSOLUTE_PATH", ""), "/snippets/efcore-sandbox.csproj") if os.getenv("CONTEXT_ABSOLUTE_PATH") else os.path.join(os.getcwd(), "src/context/snippets/efcore-sandbox.csproj"), "/app/efcore-sandbox.csproj")
            # .dockerfile(),
        SandboxType.JAVA_25_SANDBOX: Image
            .base(os.getenv("JAVA_SANDBOX_IMAGE", "bellsoft/liberica-openjre-debian:25-cds")),
            # .workdir("/sandbox")
            # .add_local_file(os.path.join(os.getenv("CONTEXT_ABSOLUTE_PATH", ""), "/snippets/mongo-pom.xml") if os.getenv("CONTEXT_ABSOLUTE_PATH") else os.path.join(os.getcwd(), "src/context/snippets/mongo-pom.xml"), "mongo-pom.xml")
            # .dockerfile(),
    }
    
    @staticmethod
    async def _create_sandbox(daytona: AsyncDaytona, sandbox_type: SandboxType) -> None:
        pass
  
    @staticmethod
    async def create_validation_sandbox(daytona: AsyncDaytona, sandbox_type: SandboxType) -> None:
        params = CreateSandboxFromImageParams(
            image=ValidationSandbox.DAYTONA_SANDBOX_IMAGES[sandbox_type],
            auto_stop_interval=5, # Sandbox will be stopped after 5 minutes
            auto_archive_interval=5, # Auto-archive after a Sandbox has been stopped for 5 minutes
            auto_delete_interval=0, # Sandbox will be deleted immediately after stopping
            name=f"validation-sandbox-{sandbox_type.value.lower()}"
        )
        try:
            if params.name:
                sandbox_instance = await daytona.get(params.name)
                if sandbox_instance.state == SandboxState.CREATING:
                    pass
                if sandbox_instance.state == SandboxState.UNKNOWN:
                    logger.info(f"Sandbox with name {params.name} already exists. Skipping creation.")
                    return
            sandbox_instance = await daytona.create(params, on_snapshot_create_logs=logger.info, timeout=180)
            logger.info(f"Sandbox created with ID: {sandbox_instance.id}")
            await sandbox_instance.start(timeout=60)
            logger.info(f"Waiting for sandbox {sandbox_instance.id} to start...")
            await sandbox_instance.wait_for_sandbox_start(timeout=60)
            logger.info(f"Sandbox {sandbox_instance.id} started successfully.")
            ValidationSandbox.SANDBOXES[sandbox_type] = sandbox_instance
            logger.debug("Sandbox details:\n%s", sandbox_instance.model_dump_json(indent=2))
        except Exception as e:
            logger.exception(f"Failed to create or start sandbox for {sandbox_type.value}.")
