"""Define the configurable parameters for the agent."""

from __future__ import annotations

import os
from dataclasses import dataclass, field, fields
from enum import Enum
from typing import Annotated

from . import prompts


class AvailableModel(str, Enum):
    """Available models from Ollama and EINFRA for UI dropdown selection."""

    # # Local Models
    # LOCAL_OLLAMA_GEMMA3_4B = "ollama/gemma3:4b"
    # LOCAL_OLLAMA_SMOLLM2 = "ollama/smollm2"

    # Ollama Models
    OLLAMA_GPT_OSS = "ollama/gpt-oss:latest"
    OLLAMA_QWEN3_CODER_30B = "ollama/qwen3-coder:30b"
    OLLAMA_MISTRAL_SMALL_3_2 = "ollama/mistral-small3.2:latest"
    OLLAMA_QWEN3_EMBEDDING = "ollama/qwen3-embedding:latest"

    # EINFRA Models (OpenAI compatible)
    EINFRA_MINI = "openai/mini"
    EINFRA_CODER = "openai/coder"
    EINFRA_AGENTIC = "openai/agentic"
    EINFRA_THINKER = "openai/thinker"
    EINFRA_QWEN3_CODER = "openai/qwen3-coder"
    EINFRA_QWEN3_CODER_30B = "openai/qwen3-coder-30b"
    EINFRA_GPT_OSS_120B = "openai/gpt-oss-120b"
    EINFRA_QWEN3_RERANKER_4B = "openai/qwen3-reranker-4b"
    EINFRA_QWEN3_EMBEDDING_4B = "openai/qwen3-embedding-4b"
    EINFRA_LLAMA_4_SCOUT_17B = "openai/llama-4-scout-17b-16e-instruct"
    EINFRA_MXBAI_EMBED_LARGE = "openai/mxbai-embed-large:latest"
    EINFRA_MULTILINGUAL_E5 = "openai/multilingual-e5-large-instruct"
    EINFRA_NOMIC_EMBED_V2 = "openai/nomic-embed-text-v2-moe"
    EINFRA_NOMIC_EMBED_V1_5 = "openai/nomic-embed-text-v1.5"
    EINFRA_DEEPSEEK_V3_2 = "openai/deepseek-v3.2"
    EINFRA_MISTRAL_LARGE = "openai/mistral-large"
    EINFRA_DEEPSEEK_V3_2_THINKING = "openai/deepseek-v3.2-thinking"
    EINFRA_KIMI_K2_5 = "openai/kimi-k2.5"
    EINFRA_QWEN3_5 = "openai/qwen3.5"
    EINFRA_QWEN3_CODER_NEXT = "openai/qwen3-coder-next"
    EINFRA_GLM_4_7 = "openai/glm-4.7"
    EINFRA_GLM_5 = "openai/glm-5"


@dataclass(kw_only=True)
class Context:
    """The context for the agent."""

    system_prompt: str = field(
        default=prompts.SYSTEM_PROMPT_TRANSLATOR,
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
        default=os.environ.get("DB_TOOLBOX_URI", "http://localhost:5000"),
        metadata={"description": "URI of the MCP Toolbox for Databases server."},
    )

    mongodb_uri: str = field(
        default=os.environ.get("MONGODB_URI", "mongodb://localhost:27017"),
        metadata={"description": "Connection URI for MongoDB."},
    )

    mongodb_database: str = field(
        default=os.environ.get("MONGODB_DATABASE", "uom"),
        metadata={"description": "Name of the MongoDB database to use."},
    )

    def __post_init__(self) -> None:
        """Fetch env vars for attributes that were not passed as args."""
        for f in fields(self):
            if not f.init:
                continue

            if getattr(self, f.name) == f.default:
                setattr(self, f.name, os.environ.get(f.name.upper(), f.default))
