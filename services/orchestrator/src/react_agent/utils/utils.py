"""Core utility & helper functions."""

import json
import logging
import os
import re
from typing import Literal, cast

import aiofiles
import httpx
from langchain.agents.middleware import Runtime
from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel, ModelProfile
from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableConfig
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langgraph.runtime import get_runtime
from openai import DefaultAsyncHttpxClient, DefaultHttpxClient

from react_agent.constants import (
    FRAMEWORK_TO_NORMALIZED_NAME,
    AvailableModel,
    DotnetFramework,
    FrameworkType,
    JavaFramework,
    SourceFramework,
    TargetFramework,
)
from react_agent.context import Context
from react_agent.utils.request_logging import LLMRequestLogger

logger = logging.getLogger(__name__)
llm_request_logger = LLMRequestLogger()


def get_model_creator_map() -> dict[AvailableModel, str]:
    creator_map = {}
    for provider_model in AvailableModel:
        _, model = provider_model.value.split("/", maxsplit=1)
        if re.search("kimi", model, re.IGNORECASE):
            creator_map[model] = "moonshotai"
        elif re.search("qwen", model, re.IGNORECASE):
            creator_map[model] = "alibaba"
        elif re.search("glm", model, re.IGNORECASE):
            creator_map[model] = "zai"
        elif re.search("deepseek", model, re.IGNORECASE):
            creator_map[model] = "deepseek"
        elif re.search("mistral", model, re.IGNORECASE):
            creator_map[model] = "mistral"
        elif re.search("llama", model, re.IGNORECASE):
            creator_map[model] = "meta"
    return creator_map


def get_normalized_framework_name(
    framework: DotnetFramework
    | JavaFramework
    | SourceFramework
    | TargetFramework
    | FrameworkType,
) -> str:
    return FRAMEWORK_TO_NORMALIZED_NAME[cast(FrameworkType, framework)]


def get_message_text(msg: BaseMessage) -> str:
    """Get the text content of a message."""
    content = msg.content
    if isinstance(content, str):
        return content
    elif isinstance(content, dict):
        return content.get("text", "")
    else:
        txts = [c if isinstance(c, str) else (c.get("text") or "") for c in content]
        return "".join(txts).strip()


async def load_chat_model(
    fully_specified_name: str, config: dict | None = None
) -> BaseChatModel:
    """Load a chat model from a fully specified name.

    Args:
        fully_specified_name (str): String in the format 'provider/model'.
        config (dict): Optional configuration passed from the context to initialize remote parameters like API keys.
    """
    provider, model = fully_specified_name.split("/", maxsplit=1)
    config = config or {}
    debugging = True if os.getenv("DEVELOPMENT") else False
    # log_http_transport = llm_request_logger.LogTransport(httpx.HTTPTransport())
    # async_log_http_transport = llm_request_logger.AsyncLogTransport(httpx.AsyncHTTPTransport())

    if provider == "openai" or provider == "einfra":
        debug_kwargs = {}
        if debugging:
            debug_kwargs = {
                "http_client": DefaultHttpxClient(
                    timeout=120,
                    event_hooks={
                        "request": [llm_request_logger.log_request],
                        "response": [llm_request_logger.log_response],
                    },
                ),
                "http_async_client": DefaultAsyncHttpxClient(
                    timeout=120,
                    event_hooks={
                        "request": [llm_request_logger.log_request],
                        "response": [llm_request_logger.log_response],
                    },
                ),
            }
        model_client = ChatOpenAI(
            model=model,  # type: ignore
            base_url=config.get("openai_api_url"),  # type: ignore
            api_key=config.get("openai_api_key"),  # type: ignore
            max_retries=10,
            request_timeout=120,  # type: ignore
            stream_usage=True,
            # **debug_kwargs,  # ty:ignore[invalid-argument-type]
        )
    elif provider == "ollama":
        debug_kwargs = {}
        if debugging:
            debug_kwargs = {
                "sync_client_kwargs": {
                    "event_hooks": {
                        "request": [llm_request_logger.log_request],
                        "response": [llm_request_logger.log_response],
                    },
                    # "transport": log_http_transport
                },
                "async_client_kwargs": {
                    "event_hooks": {
                        "request": [llm_request_logger.log_request],
                        "response": [llm_request_logger.log_response],
                    },
                    # "transport": async_log_http_transport
                },
            }
        model_client = ChatOllama(
            model=model,
            base_url=config.get("ollama_api_url", "http://localhost:11434"),
            temperature=0,
            # reasoning=True,
            **debug_kwargs,  # type: ignore
        )
    else:
        if debugging:
            # TODO: make init_chat_model the only branch, do not use provider-specific clients here, so that we can use configurable model params
            model_client = init_chat_model(
                model,
                model_provider=provider,
                base_url=config.get("openai_api_url"),
                api_key=config.get("openai_api_key"),
                reasoning=True,
                stream_usage=True,
                max_retries=10,
                timeout=120,
                configurable_fields="any",
                http_client=httpx.Client(
                    event_hooks={
                        "request": [llm_request_logger.log_request],
                        "response": [llm_request_logger.log_response],
                    }
                ),
                http_async_client=httpx.AsyncClient(
                    event_hooks={
                        "request": [llm_request_logger.log_request],
                        "response": [llm_request_logger.log_response],
                    }
                ),
                sync_client_kwargs={
                    "event_hooks": {
                        "request": [llm_request_logger.log_request],
                        "response": [llm_request_logger.log_response],
                    },
                },
                async_client_kwargs={
                    "event_hooks": {
                        "request": [llm_request_logger.log_request],
                        "response": [llm_request_logger.log_response],
                    },
                },
            )
        else:
            model_client = init_chat_model(
                model,
                model_provider=provider,
                reasoning=True,
                stream_usage=True,
                max_retries=10,
                timeout=120,
                configurable_fields="any",
            )

    if getattr(model_client, "profile", None) is None:
        profile: ModelProfile | None = None
        try:
            p_kwargs = {}
            if provider in ("einfra", "litellm"):
                config = config or {}
                base_url = config.get("openai_api_url")
                if base_url:
                    base_url = base_url.rstrip("/")
                    url = f"{base_url}/model/info"
                    headers = {}
                    api_key = config.get("openai_api_key")
                    if api_key:
                        headers["Authorization"] = f"Bearer {api_key}"
                    async with httpx.AsyncClient() as client:
                        response = await client.get(
                            url,
                            params={"model_name": model},
                            headers=headers,
                            timeout=10.0,
                        )
                    if response.status_code == 200:
                        data = response.json()
                        profile_raw = None
                        if "data" in data and isinstance(data["data"], list):
                            for model_entry in data["data"]:
                                if model_entry.get("model_name") == model:
                                    profile_raw = model_entry
                                    break
                        elif "model_info" in data and isinstance(
                            data["model_info"], list
                        ):
                            for model_entry in data["model_info"]:
                                if model_entry.get("model_name") == model:
                                    profile_raw = model_entry
                                    break

                        if profile_raw:
                            minfo = profile_raw.get("model_info", {})
                            lparams = profile_raw.get("litellm_params", {})
                            supported = minfo.get("supported_openai_params", [])
                            ebody = lparams.get("extra_body", {})

                            max_input = minfo.get("max_input_tokens") or minfo.get(
                                "context_length"
                            )
                            # max_output = minfo.get("max_output_tokens") or ebody.get(
                            #     "max_tokens"
                            # )

                            p_kwargs = {
                                "name": profile_raw.get("model_name", model),
                                "text_inputs": True,
                                "text_outputs": True,
                            }
                            if max_input is not None:
                                p_kwargs["max_input_tokens"] = int(max_input)
                            # if max_output is not None:
                            #     p_kwargs["max_output_tokens"] = int(max_output)

                            for key, check in [
                                (
                                    "tool_calling",
                                    "tools" in supported or "functions" in supported,
                                ),
                                ("tool_choice", "tool_choice" in supported),
                                ("structured_output", "response_format" in supported),
                                (
                                    "reasoning_output",
                                    "reasoning_effort" in supported
                                    or "thinking"
                                    in ebody.get("chat_template_kwargs", {}),
                                ),
                                ("temperature", "temperature" in supported),
                            ]:
                                if check:
                                    p_kwargs[key] = True

            elif provider == "ollama":
                config = config or {}
                base_url = config.get(
                    "ollama_api_url", "http://localhost:11434"
                ).rstrip("/")
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{base_url}/api/show", json={"model": model}, timeout=10.0
                    )
                if response.status_code == 200:
                    profile_raw = response.json()
                    details = profile_raw.get("details", {})
                    family = details.get("family", "llama")
                    model_info = profile_raw.get("model_info", {})
                    max_input = model_info.get(f"{family}.context_length")
                    capabilities = profile_raw.get("capabilities", [])

                    p_kwargs = {
                        "name": profile_raw.get("model", model),
                        "text_inputs": True,
                        "text_outputs": True,
                    }
                    if max_input is not None:
                        p_kwargs["max_input_tokens"] = int(max_input)

                    if "vision" in capabilities:
                        p_kwargs["image_inputs"] = True
                    if "tools" in capabilities or "tool_calling" in capabilities:
                        p_kwargs["tool_calling"] = True

            # Try to get missing info from AI Gateway
            if (
                not p_kwargs.get("max_input_tokens")
                or not p_kwargs.get("max_output_tokens")
                or "reasoning_output" not in p_kwargs
            ):
                creator_map = get_model_creator_map()
                creator = creator_map.get(AvailableModel(model))
                if creator:
                    gateway_url = (
                        f"https://ai-gateway.vercel.sh/v1/models/{creator}/{model}"
                    )
                    try:
                        async with httpx.AsyncClient() as client:
                            gw_resp = await client.get(gateway_url, timeout=5.0)
                        if gw_resp.status_code == 200:
                            gw_data = gw_resp.json()

                            if (
                                not p_kwargs.get("max_input_tokens")
                                and "context_window" in gw_data
                            ):
                                p_kwargs["max_input_tokens"] = gw_data["context_window"]

                            if (
                                not p_kwargs.get("max_output_tokens")
                                and "max_tokens" in gw_data
                            ):
                                p_kwargs["max_output_tokens"] = gw_data["max_tokens"]

                            tags = gw_data.get("tags", [])
                            if (
                                "reasoning_output" not in p_kwargs
                                and "reasoning" in tags
                            ):
                                p_kwargs["reasoning_output"] = True
                            if "image_inputs" not in p_kwargs and "vision" in tags:
                                p_kwargs["image_inputs"] = True
                            if "tool_calling" not in p_kwargs and "tool-use" in tags:
                                p_kwargs["tool_calling"] = True
                    except Exception as e:
                        logger.debug(
                            f"Could not fetch AI Gateway profile for {creator}/{model}: {e}"
                        )
            profile = ModelProfile(**p_kwargs)

        except Exception as e:
            logger.warning(f"Failed to fetch model profile for {provider}/{model}: {e}")

        if profile is not None:
            model_client.profile = profile  # type: ignore

    return model_client  # type: ignore


async def get_model(
    config: RunnableConfig,
    runtime: Runtime[Context],
    model_name_override: str | None = None,
) -> BaseChatModel:
    """Factory to initialize the model using configuration or context."""
    configurable = config.get("configurable", {})
    model_choice = model_name_override or configurable.get(
        "model", runtime.context.model
    )
    model_name = getattr(model_choice, "value", str(model_choice))

    openai_url = configurable.get(
        "openai_api_url", getattr(runtime.context, "openai_api_url", None)
    )
    openai_key = configurable.get(
        "openai_api_key", getattr(runtime.context, "openai_api_key", None)
    )

    return await load_chat_model(
        model_name, config={"openai_api_url": openai_url, "openai_api_key": openai_key}
    )


def get_ssh_host_and_port(service_name: str) -> tuple[str, int]:
    """Get the SSH host and port for a service from SSH URI in .env file."""
    runtime = get_runtime(Context)
    uri = getattr(runtime.context, f"{service_name.replace('-', '_')}_ssh_uri")
    host, port = uri.replace("ssh://", "").rsplit(":", 1)
    return host, int(port)


async def get_database_mapping_json(
    target_framework: FrameworkType,
) -> dict[Literal["source", "destination", "mapping"], str | object] | None:
    """Load the database mapping JSON for the given target framework."""
    try:
        if target_framework == FrameworkType.JAVA_SPRING_DATA_MONGODB:
            async with aiofiles.open("src/context/mappings/mssql_mongodb.json") as f:
                return {
                    "source": "Microsoft SQL Server",
                    "destination": "MongoDB",
                    "mapping": json.loads(await f.read()),
                }
        elif target_framework == FrameworkType.JAVA_SPRING_DATA_NEO4J:
            async with aiofiles.open("src/context/mappings/mssql_neo4j.json") as f:
                return {
                    "source": "Microsoft SQL Server",
                    "destination": "Neo4j",
                    "mapping": json.loads(await f.read()),
                }
    except Exception:
        logger.warning(
            f"Failed to load database mapping for {target_framework.value}",
            exc_info=True,
        )
    return None
