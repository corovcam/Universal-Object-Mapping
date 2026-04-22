"""Utility & helper functions."""

import logging

import aiofiles
from langchain.agents.middleware import Runtime
from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableConfig
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langgraph.runtime import get_runtime

from react_agent.context import Context
from react_agent.state import FrameworkType

logger = logging.getLogger(__name__)


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

    if provider == "openai" or provider == "einfra":
        config = config or {}
        model_client = ChatOpenAI(
            model=model,  # type: ignore
            base_url=config.get("openai_api_url"),  # type: ignore
            api_key=config.get("openai_api_key"),  # type: ignore
            max_retries=10,
            request_timeout=120,
            stream_usage=True,
        )
    elif provider == "ollama":
        config = config or {}
        model_client = ChatOllama(
            model=model,
            base_url=config.get("ollama_api_url", "http://localhost:11434"),
            temperature=0,
            # reasoning=True,
        )
    else:
        model_client = init_chat_model(
            model,
            model_provider=provider,
            reasoning=True,
            stream_usage=True,
            max_retries=10,
            timeout=120,
        )

    if getattr(model_client, "profile", None) is None:
        import httpx
        from langchain_core.language_models import ModelProfile

        profile: ModelProfile | None = None
        try:
            if provider in ("einfra", "litellm"):
                config = config or {}
                base_url = config.get("openai_api_url")
                if base_url:
                    base_url = base_url.rstrip("/")
                    url = f"{base_url}/model/info"
                    headers = {
                        "Authorization": f"Bearer {config.get('openai_api_key', '')}"
                    }
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
                            max_output = minfo.get("max_output_tokens") or ebody.get(
                                "max_tokens"
                            )

                            p_kwargs = {
                                "name": profile_raw.get("model_name", model),
                                "text_inputs": True,
                                "text_outputs": True,
                            }
                            if max_input is not None:
                                p_kwargs["max_input_tokens"] = int(max_input)
                            if max_output is not None:
                                p_kwargs["max_output_tokens"] = int(max_output)

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
                or "reasoning_output" not in p_kwargs
            ):
                creator_map = {
                    "kimi-k2.5": "moonshotai",
                    "qwen3-coder": "qwen",
                    "qwen3-coder-next": "qwen",
                    "qwen3-coder-30b": "qwen",
                    "qwen3.5": "qwen",
                    "qwen3.5-122b": "qwen",
                    "glm-4.7": "zhipu",
                    "glm-5": "zhipu",
                    "deepseek-v3.2": "deepseek",
                    "deepseek-v3.2-thinking": "deepseek",
                    "mistral-large": "mistralai",
                    "llama-4-scout-17b-16e-instruct": "meta",
                }
                creator = creator_map.get(model)
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
            model_client.profile = profile

    return model_client


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


async def get_database_mapping_json(target_framework: FrameworkType):
    """Get database mapping file."""
    if target_framework == FrameworkType.SPRING_DATA_MONGODB:
        async with aiofiles.open("src/context/mappings/mssql_mongodb.relmig") as f:
            return {
                "source": "Microsoft SQL Server",
                "destination": "MongoDB",
                "mapping": await f.read(),
            }
    elif target_framework == FrameworkType.SPRING_DATA_NEO4J:
        async with aiofiles.open("src/context/mappings/mssql_neo4j.relmig") as f:
            return {
                "source": "Microsoft SQL Server",
                "destination": "Neo4j",
                "mapping": await f.read(),
            }
