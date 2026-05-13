"""Core utility & helper functions."""
import logging
import os
import re
from typing import Annotated, Any, Literal, cast

import aiofiles
import httpx
import orjson
from langchain.agents.middleware import Runtime
from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel, ModelProfile
from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableConfig
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from openai import DefaultAsyncHttpxClient, DefaultHttpxClient
from pydantic import BaseModel, Field, create_model

from react_agent.constants import (
    FRAMEWORK_TO_NORMALIZED_NAME,
    AvailableModel,
    FrameworkEnum,
)
from react_agent.context import Context
from react_agent.utils.request_logging import LLMRequestLogger
from react_agent.utils.types import FrameworkType

logger = logging.getLogger(__name__)
llm_request_logger = LLMRequestLogger()


async def get_snippet_content(framework: FrameworkEnum, is_schema: bool = False) -> str:
    """Read a snippet file's content based on framework and type."""
    base_dir = os.path.join(
        os.path.dirname(__file__), "..", "..", "context", "snippets"
    )
    file_map = {
        FrameworkEnum.DOTNET_EFCORE: (
            "EFCoreSchemaValidationEntrypoint.cs",
            "EFCoreQueryEntrypoint.cs",
        ),
        FrameworkEnum.DOTNET_DAPPER: (
            "DapperSchemaValidationEntrypoint.cs",
            "DapperQueryEntrypoint.cs",
        ),
        FrameworkEnum.DOTNET_NHIBERNATE: (
            "NHibernateSchemaValidationEntrypoint.cs",
            "NHibernateQueryEntrypoint.cs",
        ),
        FrameworkEnum.JAVA_SPRING_DATA_MONGODB: (
            "MongoSchemaValidationEntrypoint.java",
            "MongoQueryEntrypoint.java",
        ),
        FrameworkEnum.JAVA_SPRING_DATA_NEO4J: (
            "Neo4jSchemaValidationEntrypoint.java",
            "Neo4jQueryEntrypoint.java",
        ),
    }

    if framework not in file_map:
        logger.warning(f"No snippet file mapping found for framework {framework.value}")
        return ""

    file_name = file_map[framework][0] if is_schema else file_map[framework][1]
    path = os.path.join(base_dir, file_name)
    try:
        async with aiofiles.open(path) as f:
            return await f.read()
    except Exception as e:
        logger.warning(f"Failed to read snippet file {path}: {e}")
        return ""


async def get_framework_config_content(framework: FrameworkEnum) -> str:
    base_dir = os.path.join(
        os.path.dirname(__file__), "..", "..", "context", "snippets"
    )
    file_map = {
        FrameworkEnum.DOTNET_EFCORE: "efcore-sandbox.csproj",
        FrameworkEnum.DOTNET_DAPPER: "dapper-sandbox.csproj",
        FrameworkEnum.DOTNET_NHIBERNATE: "nhibernate-sandbox.csproj",
        FrameworkEnum.JAVA_SPRING_DATA_MONGODB: "mongo-pom.xml",
        FrameworkEnum.JAVA_SPRING_DATA_NEO4J: "neo4j-pom.xml",
    }

    if framework not in file_map:
        logger.error(f"No config file mapping found for framework {framework.value}")
        raise ValueError(f"Unsupported framework: {framework.value}")

    path = os.path.join(base_dir, file_map[framework])
    try:
        async with aiofiles.open(path) as f:
            return await f.read()
    except Exception as e:
        logger.error(f"Failed to read framework config file {path}: {e}")
        raise e


def get_model_creator_map() -> dict[AvailableModel, str]:
    """Return a mapping of available models to their LangChain creator class names."""
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
    framework: FrameworkType,
) -> str:
    """Normalize framework names into a standardized string format for LLM prompting."""
    return FRAMEWORK_TO_NORMALIZED_NAME[cast(FrameworkEnum, framework)]


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
    fully_specified_name: str, config: dict[str, Any] = {},
) -> BaseChatModel:
    """Load a chat model from a fully specified name.

    Args:
        fully_specified_name (str): String in the format 'provider/model'.
        config (dict): Optional configuration passed from the context to initialize remote parameters like API keys.
    """
    provider, model = fully_specified_name.split("/", maxsplit=1)
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
            request_timeout=120, # type: ignore
            stream_usage=True,
            **({"temperature": config.get("temperature", 0)} if config.get("temperature") is not None else {}),
            # **debug_kwargs,  # type: ignore
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
            **({"temperature": config.get("temperature", 0)} if config.get("temperature") is not None else {}),
            # reasoning=True,
            # **debug_kwargs,  # type: ignore
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
                **config,
                http_client=DefaultHttpxClient(
                    timeout=120,
                    event_hooks={
                        "request": [llm_request_logger.log_request],
                        "response": [llm_request_logger.log_response],
                    },
                ),
                http_async_client=DefaultAsyncHttpxClient(
                    timeout=120,
                    event_hooks={
                        "request": [llm_request_logger.log_request],
                        "response": [llm_request_logger.log_response],
                    },
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
                **config,
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
                creator = creator_map.get(AvailableModel(fully_specified_name))
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


# TODO: remove this, and only use load_chat_model; if "configurable" is set (non-empty), use "init_chat_model" path to initialize (with custom system prompt, model params, etc.)
async def get_model(
    config: RunnableConfig,
    runtime: Runtime[Context],
    model_name_override: str | None = None,
    temperature: float | None = None,
    **chat_model_kwargs,
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
        model_name, config={"openai_api_url": openai_url, "openai_api_key": openai_key, "temperature": temperature, **chat_model_kwargs}
    )


async def get_database_mapping_json(
    target_framework: FrameworkEnum,
) -> dict[Literal["source", "destination", "mapping"], str | object] | None:
    """Load the database mapping JSON for the given target framework."""
    try:
        if target_framework == FrameworkEnum.JAVA_SPRING_DATA_MONGODB:
            async with aiofiles.open("src/context/mappings/mssql_mongodb.json") as f:
                return {
                    "source": "Microsoft SQL Server",
                    "destination": "MongoDB",
                    "mapping": orjson.loads(await f.read()),
                }
        elif target_framework == FrameworkEnum.JAVA_SPRING_DATA_NEO4J:
            async with aiofiles.open("src/context/mappings/mssql_neo4j.json") as f:
                return {
                    "source": "Microsoft SQL Server",
                    "destination": "Neo4j",
                    "mapping": orjson.loads(await f.read()),
                }
    except Exception:
        logger.warning(
            f"Failed to load database mapping for {target_framework.value}",
            exc_info=True,
        )
    return None


async def create_example_for_prompt(
    framework: FrameworkEnum,
    return_schema: bool
) -> str:
    """Create example code snippets for prompts based on the framework."""
    example = f"""
<example framework="{framework.value}">
{await get_snippet_content(framework, is_schema=True) if return_schema else await get_snippet_content(framework, is_schema=False)}
</example>"""
    return example


def override_pydantic_model_schema(model_cls: type[BaseModel], overrides: dict[str, dict[str, Any]], model_name: str | None = None) -> type[BaseModel]:
    """Override the schema of a Pydantic model's fields."""
    new_fields = {}
    for f_name, f_info in model_cls.model_fields.items():
        f_dct = f_info.asdict()
        if f_name in overrides:
            override = overrides[f_name]
            f_dct["annotation"] = override.get("annotation", f_dct["annotation"])
            f_dct["metadata"] =  override.get("metadata", f_dct["metadata"])
            f_dct["attributes"] = {**f_dct["attributes"], **override.get("attributes", {})}
        new_fields[f_name] = (
            Annotated[f_dct["annotation"], *f_dct['metadata'], Field(**f_dct['attributes'])],  # noqa: F821
            None,
        )
    return create_model(
        model_name or model_cls.__name__,
        __base__=model_cls,
        **new_fields,
    )

def identity(x: Any) -> Any:
    return x
