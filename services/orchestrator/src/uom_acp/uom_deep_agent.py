"""Demo coding agent using ACP."""

import asyncio
import logging
import os
import sys

from acp import (
    run_agent as run_acp_agent,
)
from acp.schema import (
    SessionMode,
    SessionModeState,
)
from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, LocalShellBackend, StateBackend
from deepagents_acp.server import AgentServerACP, AgentSessionContext
from dotenv import find_dotenv, load_dotenv
from langchain.chat_models import BaseChatModel
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.state import Checkpointer, CompiledStateGraph

from react_agent.constants import AvailableModel
from react_agent.utils import load_chat_model
from uom_acp.local_context import LocalContextMiddleware

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    stream=sys.stdout,
    level=logging.DEBUG if os.getenv("DEVELOPMENT") else logging.INFO,
)
logger = logging.getLogger(__name__)
MODELS: dict[str, BaseChatModel] = {}


def _get_interrupt_config(mode_id: str) -> dict:
    """Get interrupt configuration for a given mode."""
    mode_to_interrupt = {
        "ask_before_edits": {
            "edit_file": {"allowed_decisions": ["approve", "reject"]},
            "write_file": {"allowed_decisions": ["approve", "reject"]},
            "write_todos": {"allowed_decisions": ["approve", "reject"]},
            "execute": {"allowed_decisions": ["approve", "reject"]},
        },
        "accept_edits": {
            "write_todos": {"allowed_decisions": ["approve", "reject"]},
            "execute": {"allowed_decisions": ["approve", "reject"]},
        },
        "accept_everything": {},
    }
    return mode_to_interrupt.get(mode_id, {})


async def _serve_uom_deep_agent() -> None:
    """Run example agent from the root of the repository with ACP integration."""
    load_dotenv(find_dotenv(".env.dev" if os.getenv("DEVELOPMENT") else ".env"))

    checkpointer: Checkpointer = MemorySaver()

    for m in [
        AvailableModel.EINFRA_DEEPSEEK_V4_PRO_THINKING,
        AvailableModel.EINFRA_KIMI_K2_6,
    ]:
        model = await load_chat_model(
            m.value,
            config={
                "openai_api_url": os.getenv("OPENAI_API_URL"),
                "openai_api_key": os.getenv("OPENAI_API_KEY"),
            },
        )
        MODELS[m.value] = model

    logger.debug(f"MODELS: {MODELS}")

    def build_agent(context: AgentSessionContext) -> CompiledStateGraph:
        """Agent factory based in the given root directory."""
        _root_dir = context.cwd
        interrupt_config = _get_interrupt_config(context.mode)

        ephemeral_backend = StateBackend()
        shell_env = os.environ.copy()

        # Use CLIShellBackend for filesystem + shell execution.
        # Provides `execute` tool via FilesystemMiddleware with per-command
        # timeout support.
        shell_backend = LocalShellBackend(
            root_dir=_root_dir,
            inherit_env=True,
            env=shell_env,
        )
        backend = CompositeBackend(
            default=shell_backend,
            routes={
                "/memories/": ephemeral_backend,
                "/conversation_history/": ephemeral_backend,
            },
        )

        logger.debug(f"context: {context}")
        agent = create_deep_agent(
            # Falls back to Deep Agent default model if not provided
            model=MODELS[
                context.model or AvailableModel.EINFRA_DEEPSEEK_V4_PRO_THINKING.value
            ],
            checkpointer=checkpointer,
            backend=backend,
            interrupt_on=interrupt_config,
            middleware=[LocalContextMiddleware(backend=backend)],
        )
        logger.debug(f"agent: {agent}")
        return agent

    modes = SessionModeState(
        current_mode_id="accept_edits",
        available_modes=[
            SessionMode(
                id="ask_before_edits",
                name="Ask before edits",
                description="Ask permission before edits, writes, shell commands, and plans",
            ),
            SessionMode(
                id="accept_edits",
                name="Accept edits",
                description="Auto-accept edit operations, but ask before shell commands and plans",
            ),
            SessionMode(
                id="accept_everything",
                name="Accept everything",
                description="Auto-accept all operations without asking permission",
            ),
        ],
    )

    # Define available models for dynamic switching
    models = [{"value": name, "name": name} for name in MODELS]
    acp_agent = AgentServerACP(
        agent=build_agent,
        modes=modes,
        models=models,
    )
    await run_acp_agent(acp_agent)


def main() -> None:
    """Run the UOM deep agent."""
    logger.debug(f"ENV: {os.environ}")
    asyncio.run(_serve_uom_deep_agent())


if __name__ == "__main__":
    main()
