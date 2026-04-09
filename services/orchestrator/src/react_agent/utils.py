"""Utility & helper functions."""

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langgraph.runtime import get_runtime

from react_agent.context import Context


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


def load_chat_model(
    fully_specified_name: str, config: dict | None = None
) -> BaseChatModel:
    """Load a chat model from a fully specified name.

    Args:
        fully_specified_name (str): String in the format 'provider/model'.
        config (dict): Optional configuration passed from the context to initialize remote parameters like API keys.
    """
    provider, model = fully_specified_name.split("/", maxsplit=1)

    if provider == "openai":
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
        model_client = ChatOllama(
            model=model,
            # base_url=config.get("ollama_api_url"),
            reasoning=True,
        )
    else:
        model_client = init_chat_model(
            model, model_provider=provider, max_retries=10, timeout=120
        )

    # if (not model_client.profile):

    return model_client


def get_ssh_host_and_port(service_name: str) -> tuple[str, int]:
    """Get the SSH host and port for a service from SSH URI in .env file."""
    runtime = get_runtime(Context)
    uri = getattr(runtime.context, f"{service_name.replace('-', '_')}_ssh_uri")
    host, port = uri.replace("ssh://", "").rsplit(":", 1)
    return host, int(port)
