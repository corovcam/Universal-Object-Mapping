"""Demo coding agent using ACP."""
import logging
import os
import sys
from typing import Any, Callable

from daytona import AsyncDaytona
from deepagents import (
    CompiledSubAgent,
    GeneralPurposeSubagentProfile,
    HarnessProfile,
    ProviderProfile,
    create_deep_agent,
    register_harness_profile,
    register_provider_profile,
)
from deepagents.backends import CompositeBackend, LocalShellBackend, StateBackend
from deepagents_acp.server import AgentSessionContext
from dotenv import find_dotenv, load_dotenv
from langchain.agents.middleware import (
    ModelRequest,
    ModelResponse,
    dynamic_prompt,
    wrap_model_call,
)
from langchain.chat_models import BaseChatModel
from langchain_daytona import DaytonaSandbox
from langgraph.graph.state import Checkpointer

from react_agent.constants import AvailableModel, SandboxType
from react_agent.context import Context
from react_agent.graph import graph
from react_agent.utils import load_chat_model
from react_agent.utils.sandboxes import ValidationSandbox
from react_agent.utils.utils import get_context_dir
from uom_deep_agent.local_context import LocalContextMiddleware

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    stream=sys.stdout,
    level=logging.DEBUG if os.getenv("DEVELOPMENT") else logging.INFO,
)
logger = logging.getLogger(__name__)

FILE_CACHE: dict[str, str] = {}

EFCORE_MONGODB_INPUT = "input-efcore-mongodb.txt"
DAPPER_MONGODB_INPUT = "input-dapper-mongodb.txt"
EFCORE_NEO4J_INPUT = "input-efcore-neo4j.txt"
NHIBERNATE_MONGODB_INPUT = "input-nhibernate-mongodb.txt"

TASK_TOOL_DESCRIPTION = """Launch an ephemeral subagent to handle complex, multi-step independent tasks with isolated context windows.

Available agent types and the tools they have access to:
{available_agents}

When using the Task tool, you must specify a subagent_type parameter to select which agent type to use.

## Usage notes:
1. Launch multiple agents concurrently whenever possible, to maximize performance; to do that, use a single message with multiple tool uses
2. When the agent is done, it will return a single message back to you. The result returned by the agent is not visible to the user. To show the user the result, you should send a text message back to the user with a concise summary of the result.
3. Each agent invocation is stateless. You will not be able to send additional messages to the agent, nor will the agent be able to communicate with you outside of its final report. Therefore, your prompt should contain a highly detailed task description for the agent to perform autonomously and you should specify exactly what information the agent should return back to you in its final and only message to you.
4. The agent's outputs should generally be trusted
5. If the agent description mentions that it should be used proactively, then you should try your best to use it without the user having to ask for it first. Use your judgement.
6. IMPORTANT: When the agent descriptions mention that the user input should be copied fully, verbatim, as-is, do exactly that and put it inside "description" field of Task tool. Do NOT truncate or modify it. Do NOT include any additional text apart from the initial "user input". Expecially if there is any code, you MUST NOT modify it in any way. You MUST include line breaks and formatting verbatim if present.
"""

DEFAULT_HARNESS_PROFILE = HarnessProfile(
    tool_description_overrides={
        "task": TASK_TOOL_DESCRIPTION
    },
    general_purpose_subagent=GeneralPurposeSubagentProfile(enabled=False),
)

def get_example_input(file_name: str) -> str:
    """Load input from a file, with caching."""
    if file_name in FILE_CACHE:
        return FILE_CACHE[file_name]
    path = os.path.join(get_context_dir(), "snippets", file_name)
    with open(path) as f:
        content = f.read()
    FILE_CACHE[file_name] = content
    return content


def _get_interrupt_config(mode_id: str = "ask_before_edits") -> dict:
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


@wrap_model_call()  # ty:ignore[invalid-argument-type]
async def configurable_model(
    request: ModelRequest[Context],
    handler: Callable[[ModelRequest[Context]], ModelResponse],
) -> ModelResponse:
    logger.debug(f"request: {request.__dict__}")
    model_name = request.runtime.context.model
    config = {
        "openai_api_url": os.getenv("OPENAI_API_URL"),
        "openai_api_key": os.getenv("OPENAI_API_KEY"),
        "temperature": request.model_settings.get("temperature"),
        "reasoning": request.model_settings.get("reasoning"),
        "extra_body": request.model_settings.get("extra_body"),
        **request.model_settings,
    }
    model = await load_chat_model(model_name, config)
    return handler(request.override(model=model))


@dynamic_prompt
def custom_system_prompt(request: ModelRequest[Context]) -> str:
    """Always append the system prompt from the runtime context to the system prompt from the request."""
    if len(request.runtime.context.system_prompt) > 0:
        if request.system_prompt and (request.runtime.context.system_prompt not in request.system_prompt):
            return request.runtime.context.system_prompt + f"\n\n{request.system_prompt}"
        else:
            return request.runtime.context.system_prompt
    return request.system_prompt or ""


def _get_compiled_uom_graph() -> CompiledSubAgent:
    return CompiledSubAgent(
        name="universal-object-mapping-translator",
        description="""Migrates code database entity schemas, mappings/context/settings and queries between Object-Relational Mapping (ORM), Object-Graph Mapping (OGM), and Object-Document Mapping (ODM) frameworks by performing LLM-based translation and validation workflow. Currently supports translation from .NET (Entity Framework Core, NHibernate, Dapper) to Java frameworks (Spring Data MongoDB, Spring Data Neo4j).
Translation Workflow:
1. User provides source .NET schema, mappings/context/settings and queries.
2. Orchestrator extracts target frameworks and checks user intent.
3. Orchestrator connects to database via MCP to inspect DB schema mapping context.
4. Generates code and testing harnesses without tools.
5. Systematically validates schema, compiles queries, checks data equivalence, and evaluates if the result is correct (`ACCEPT` or `REJECT`).
6. If rejected, it loops back to correct the code (up to 3 times) before eventually falling back to a human-in-the-loop if unresolved.

Example Input Messages for "universal-object-mapping-translator" sub-agent:
```
{get_example_input(EFCORE_MONGODB_INPUT)}
```
```
{get_example_input(DAPPER_MONGODB_INPUT)}
```
```
{get_example_input(EFCORE_NEO4J_INPUT)}
```
```
{get_example_input(NHIBERNATE_MONGODB_INPUT)}
```
""",
        runnable=graph,
    )
    
def build_deep_agent(
    model: BaseChatModel,
    dotnet_sandbox: DaytonaSandbox,
    java_sandbox: DaytonaSandbox,
    extra_middleware: list[Any] | None = None,
    checkpointer: Checkpointer | None = None,
    context: AgentSessionContext | None = None
):
    load_dotenv(find_dotenv(".env.dev" if os.getenv("DEVELOPMENT") else ".env"))
    logger.debug(f"ENV: {os.environ}")
    
    register_harness_profile("openai", DEFAULT_HARNESS_PROFILE)
    register_harness_profile("ollama", DEFAULT_HARNESS_PROFILE)
    register_provider_profile("openai", ProviderProfile(init_kwargs={"use_responses_api": False}))
    
    if context is not None:
        _root_dir = context.cwd
        interrupt_config = _get_interrupt_config(context.mode)
    else:
        _root_dir = os.getcwd()
        interrupt_config = _get_interrupt_config()

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
    
    system_prompt = """You are an expect coding assistant. Your goal is to aid in translating between Object-Relational Mapping (ORM), Object-Graph Mapping (OGM), and Object-Document Mapping (ODM) frameworks.

IMPORTANT: Always call "universal-object-mapping-translator" sub-agent to perform the translation with the FULL user input message and code as seen above in its `Example Input Messages for "universal-object-mapping-translator" sub-agent` description. Do NOT truncate or modify it. Do NOT include any additional text apart from the initial "user input".

---"""
    
    backend = CompositeBackend(
        default=shell_backend,
        routes={
            "/memories/": ephemeral_backend,
            "/conversation_history/": ephemeral_backend,
            "/dotnet_sandbox/": dotnet_sandbox,
            "/java_sandbox/": java_sandbox,
        },
    )
    
    local_context_middleware = LocalContextMiddleware(backend=backend)

    return create_deep_agent(
        # Falls back to Deep Agent default model if not provided
        model=model,
        system_prompt=system_prompt,
        context_schema=Context,
        subagents=[_get_compiled_uom_graph()],
        backend=backend,
        interrupt_on=interrupt_config,
        checkpointer=checkpointer,
        middleware=[local_context_middleware] + extra_middleware if extra_middleware else [local_context_middleware],
        name="universal-object-mapping-assistant",
    )
    

# async def build_deep_agent(model: BaseChatModel, context: AgentSessionContext | None = None):
#     load_dotenv(find_dotenv(".env.dev" if os.getenv("DEVELOPMENT") else ".env"))
#     logger.debug(f"ENV: {os.environ}")
#     if context is not None:
#         _root_dir = context.cwd
#         interrupt_config = _get_interrupt_config(context.mode)
#     else:
#         _root_dir = os.getcwd()
#         interrupt_config = _get_interrupt_config()

#     async with AsyncDaytona() as daytona:
#         ephemeral_backend = StateBackend()
#         shell_env = os.environ.copy()
        
#         dotnet_sandbox = DaytonaSandbox(sandbox = await ValidationSandbox.get_sandbox(daytona, SandboxType.DOTNET_10_SANDBOX, print))  # ty:ignore[invalid-argument-type]
#         java_sandbox = DaytonaSandbox(sandbox = await ValidationSandbox.get_sandbox(daytona, SandboxType.JAVA_25_SANDBOX, print))  # ty:ignore[invalid-argument-type]

#         # Use CLIShellBackend for filesystem + shell execution.
#         # Provides `execute` tool via FilesystemMiddleware with per-command
#         # timeout support.
#         shell_backend = LocalShellBackend(
#             root_dir=_root_dir,
#             inherit_env=True,
#             env=shell_env,
#         )
#         backend = CompositeBackend(
#             default=shell_backend,
#             routes={
#                 "/memories/": ephemeral_backend,
#                 "/conversation_history/": ephemeral_backend,
#                 "/dotnet_sandbox/": dotnet_sandbox,
#                 "/java_sandbox/": java_sandbox,
#             },
#         )
        
#         system_prompt = """You are an expect coding assistant. Your goal is to aid in translating between Object-Relational Mapping (ORM), Object-Graph Mapping (OGM), and Object-Document Mapping (ODM) frameworks.
# Allowed origin frameworks: {origin_frameworks}
# Allowed destination frameworks: {destination_frameworks}

# IMPORTANT: Always call "universal-object-mapping-translator" sub-agent to perform the translation with the FULL user input message and code. Do NOT truncate or modify it.
# """

#         return create_deep_agent(
#             # Falls back to Deep Agent default model if not provided
#             model=model,
#             system_prompt=system_prompt,
#             context_schema=Context,
#             subagents=[_get_compiled_uom_graph()],
#             backend=backend,
#             interrupt_on=interrupt_config,
#             middleware=[
#                 LocalContextMiddleware(backend=backend),
#                 custom_system_prompt,
#                 # configurable_model
#             ],  # ty:ignore[invalid-argument-type]
#             name="universal-object-mapping-assistant",
#         )


async def build_uom_agent():
    async with AsyncDaytona() as daytona:
        dotnet_sandbox = DaytonaSandbox(sandbox = await ValidationSandbox.get_sandbox(daytona, SandboxType.DOTNET_10_SANDBOX, print))  # ty:ignore[invalid-argument-type]
        java_sandbox = DaytonaSandbox(sandbox = await ValidationSandbox.get_sandbox(daytona, SandboxType.JAVA_25_SANDBOX, print))  # ty:ignore[invalid-argument-type]
        
        model = await load_chat_model(
            AvailableModel.EINFRA_DEEPSEEK_V4_PRO_THINKING.value,
            config={
                "openai_api_url": os.getenv("OPENAI_API_URL"),
                "openai_api_key": os.getenv("OPENAI_API_KEY"),
                "temperature": 0.2
            },
        )
        return build_deep_agent(model=model, dotnet_sandbox=dotnet_sandbox, java_sandbox=java_sandbox, extra_middleware=[custom_system_prompt])
