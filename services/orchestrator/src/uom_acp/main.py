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
from daytona import AsyncDaytona
from deepagents_acp.server import AgentServerACP, AgentSessionContext
from dotenv import find_dotenv, load_dotenv
from langchain.chat_models import BaseChatModel
from langchain_daytona import DaytonaSandbox
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.state import Checkpointer, CompiledStateGraph

from react_agent.constants import AvailableModel, SandboxType
from react_agent.utils import load_chat_model
from react_agent.utils.sandboxes import ValidationSandbox
from uom_deep_agent.uom_agent import build_deep_agent

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    stream=sys.stdout,
    level=logging.DEBUG if os.getenv("DEVELOPMENT") else logging.INFO,
)
logger = logging.getLogger(__name__)
MODELS: dict[str, BaseChatModel] = {}


async def _serve_uom_deep_agent() -> None:
    """Run example agent from the root of the repository with ACP integration."""
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
                "temperature": 0.2
            },
        )
        MODELS[m.value] = model

    logger.debug(f"MODELS: {MODELS}")
    
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
    
    async with AsyncDaytona() as daytona:
        dotnet_sandbox = DaytonaSandbox(sandbox = await ValidationSandbox.get_sandbox(daytona, SandboxType.DOTNET_10_SANDBOX, print))  # ty:ignore[invalid-argument-type]
        java_sandbox = DaytonaSandbox(sandbox = await ValidationSandbox.get_sandbox(daytona, SandboxType.JAVA_25_SANDBOX, print))  # ty:ignore[invalid-argument-type]
        
        model = MODELS[AvailableModel.EINFRA_DEEPSEEK_V4_PRO_THINKING.value]

        def build_agent(context: AgentSessionContext) -> CompiledStateGraph:
            """Agent factory based in the given root directory."""
            logger.debug(f"context: {context}")
            uom_agent = build_deep_agent(model=model, dotnet_sandbox=dotnet_sandbox, java_sandbox=java_sandbox, checkpointer=checkpointer, context=context)
            logger.debug(f"agent: {uom_agent}")
            return uom_agent


        acp_agent = AgentServerACP(
            agent=build_agent,
            modes=modes,
            models=models,
        )
        await run_acp_agent(acp_agent)


def main() -> None:
    """Run the UOM deep agent."""
    load_dotenv(find_dotenv(".env.dev" if os.getenv("DEVELOPMENT") else ".env"))
    logger.debug(f"ENV: {os.environ}")
    asyncio.run(_serve_uom_deep_agent())


if __name__ == "__main__":
    main()
