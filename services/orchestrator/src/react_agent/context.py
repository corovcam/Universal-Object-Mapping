"""Define the configurable parameters for the agent."""

from __future__ import annotations

import os
from dataclasses import dataclass, field, fields
from typing import Annotated

from react_agent.constants import AvailableModel
from react_agent.prompts import SYSTEM_PROMPT_TRANSLATOR


@dataclass(kw_only=True)
class Context:
    """The context for the agent."""

    system_prompt: str = field(
        default=SYSTEM_PROMPT_TRANSLATOR,
        metadata={
            "description": "The system prompt to use for the agent's interactions. "
            "This prompt sets the context and behavior for the agent."
        },
    )

    model: Annotated[AvailableModel, {"__template_metadata__": {"kind": "llm"}}] = (
        field(
            default=AvailableModel.EINFRA_KIMI_K2_5,
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

    def __post_init__(self) -> None:
        """Fetch env vars for attributes that were not passed as args."""
        for f in fields(self):
            if not f.init:
                continue

            if getattr(self, f.name) == f.default:
                setattr(self, f.name, os.environ.get(f.name.upper(), f.default))
