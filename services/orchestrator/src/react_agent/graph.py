# ty:ignore[invalid-argument-type]
"""Define the Universal Object Mapping orchestrator graph."""

import asyncio
import json
import logging
import os
from datetime import UTC, datetime
from typing import Any, Literal, Union

from langchain.agents import AgentState, create_agent
from langchain.agents.middleware import (
    ClearToolUsesEdit,
    ContextEditingMiddleware,
    LLMToolEmulator,
    LLMToolSelectorMiddleware,
    ModelFallbackMiddleware,
    ModelRetryMiddleware,
    SummarizationMiddleware,
    ToolRetryMiddleware,
)
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langfuse import get_client
from langfuse.langchain import CallbackHandler
from langgraph.cache.memory import InMemoryCache
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime
from langgraph.store.memory import InMemoryStore
from langgraph.types import CachePolicy, RetryPolicy
from pydantic import BaseModel, Field

from react_agent.context import AvailableModel, Context
from react_agent.custom_tools.docs_search import load_docs_mcp_tools
from react_agent.custom_tools.mcp_database import load_database_tools
from react_agent.prompts import (
    SYSTEM_PROMPT_EXTRACTION,
    SYSTEM_PROMPT_SCHEMA_INSPECTOR,
    SYSTEM_PROMPT_TRANSLATOR,
)
from react_agent.state import (
    FrameworkType,
    InputState,
    OutputState,
    State,
    TranslationType,
)
from react_agent.tools import TOOLS
from react_agent.utils import get_database_mapping_json, get_model

logger = logging.getLogger(__name__)


class ExtractionOutput(BaseModel):
    """Structured output for identifying user intent from messages."""

    # source_code: str = Field(
    #     description="The source code snippet and/or query mapped by the user.",
    #     min_length=1,
    # )
    source_schema_code: Union[str, None] = Field(
        description="The source schema code.",
        min_length=1,
    )
    source_query_code: Union[str, None] = Field(
        description="The source query code.",
        min_length=1,
    )
    translation_type: TranslationType = Field(
        description="The type of translation to perform.",
    )
    source_target: FrameworkType = Field(description="The identified origin framework.")
    source_target_version: Union[str, None] = Field(
        description="The identified origin framework version."
    )
    destination_target: FrameworkType = Field(
        description="The identified target framework."
    )
    destination_target_version: Union[str, None] = Field(
        description="The identified target framework version."
    )


class TranslationOutput(BaseModel):
    """Structured output for the translated schema and/or queries."""

    translated_schema_code: Union[str, None] = Field(
        description="The precise translated schema definitions (Entities/Models). Do not include any usage queries here."
    )

    translated_query_code: Union[str, None] = Field(
        description="The precise translated queries. Do not include schema definitions here."
    )


def is_input_extracted(state: State) -> bool:
    """Check if the input has been extracted."""
    if state.translation_type == TranslationType.SCHEMA:
        is_code_extracted = state.source_schema_code is not None
    elif state.translation_type == TranslationType.QUERY:
        is_code_extracted = state.source_query_code is not None
    elif state.translation_type == TranslationType.BOTH:
        is_code_extracted = (
            state.source_schema_code is not None and state.source_query_code is not None
        )
    else:
        return False
    return (
        is_code_extracted
        and state.source_target is not None
        and state.destination_target is not None
    )


async def extract_input(
    state: State, config: RunnableConfig, runtime: Runtime[Context]
):
    """Extract raw source code and targets from recent messages if missing from structured input."""
    if is_input_extracted(state):
        return {}

    model = await get_model(config, runtime, AvailableModel.OLLAMA_QWEN3_CODER_30B)
    structured_llm = model.with_structured_output(ExtractionOutput)

    system_prompt = SYSTEM_PROMPT_EXTRACTION.format(
        system_time=datetime.now(tz=UTC).isoformat(),
        origin_frameworks=[f.value for f in FrameworkType],
        destination_frameworks=[f.value for f in FrameworkType],
    )
    already_extracted = {
        "source_schema_code": state.source_schema_code,
        "source_query_code": state.source_query_code,
        "translation_type": state.translation_type,
        "source_target": state.source_target,
        "source_target_version": state.source_target_version,
        "destination_target": state.destination_target,
        "destination_target_version": state.destination_target_version,
    }
    prompt = f"""Analyze the following conversation and extract the source schema/query code, the origin framework, the origin framework version (if available), the destination framework, the destination framework version (if available), and decide if the translation type is schema, query or both:

Already extracted:
{json.dumps(already_extracted)}

Conversation:
{state.messages[-1].content}"""

    extraction = await structured_llm.ainvoke(
        [SystemMessage(content=system_prompt), HumanMessage(content=prompt)]
    )
    assert isinstance(extraction, ExtractionOutput)

    return {
        "source_schema_code": extraction.source_schema_code,
        "source_query_code": extraction.source_query_code,
        "translation_type": extraction.translation_type,
        "source_target": extraction.source_target,
        "source_target_version": extraction.source_target_version,
        "destination_target": extraction.destination_target,
        "destination_target_version": extraction.destination_target_version,
    }


async def schema_inspection(
    state: State, config: RunnableConfig, runtime: Runtime[Context]
) -> dict[str, Any]:
    """Inspect source and target database schemas using database tools.

    Runs a lightweight ReAct agent with only database tools to examine
    the relevant database schemas before translation begins.
    """
    # Load database tools asynchronously
    async with load_database_tools() as db_tools:
        if not db_tools:
            logger.warning("No database tools available for schema inspection.")
            return {
                "schema_context": "No database tools available. Schema inspection skipped."
            }

        model = await get_model(config, runtime, AvailableModel.EINFRA_KIMI_K2_5)

        system_prompt = SYSTEM_PROMPT_SCHEMA_INSPECTOR.format(
            system_time=datetime.now(tz=UTC).isoformat(),
        )

        database_mapping = await get_database_mapping_json(state.destination_target)

        agent = create_agent(
            model,
            tools=db_tools,
            system_prompt=system_prompt,
            middleware=[
                ModelRetryMiddleware(),
                ModelFallbackMiddleware(
                    await get_model(config, runtime, AvailableModel.EINFRA_GLM_5),
                    await get_model(config, runtime, AvailableModel.EINFRA_AGENTIC),
                    await get_model(config, runtime, AvailableModel.OLLAMA_QWEN3_CODER_30B),
                ),
                ToolRetryMiddleware(),
                LLMToolSelectorMiddleware(
                    model=await get_model(config, runtime, AvailableModel.EINFRA_QWEN3_5),
                ),
                ContextEditingMiddleware(
                    edits=[
                        ClearToolUsesEdit(
                            trigger=100000,
                            keep=3,
                        )
                    ]
                ),
                SummarizationMiddleware(model, trigger=("fraction", 0.8)),
            ],
            debug=True if os.getenv("DEVELOPMENT") else False,
        )

        message = f"""Inspect the database schemas relevant to translating code from {state.source_target.value}{f" {state.source_target_version}" if state.source_target_version else ""} to {state.destination_target.value}{f" {state.destination_target_version}" if state.destination_target_version else ""}.

{f"Mapping from {database_mapping['source']} to {database_mapping['destination']}:\n{database_mapping['mapping']}\n" if database_mapping else ""}
Source code being translated:
{state.source_code}
"""

        try:
            response = await agent.ainvoke(
                {"messages": [HumanMessage(content=message)]}
            )
            # Extract the final assistant response as schema context
            schema_summary = (
                response["messages"][-1].content if response["messages"] else ""
            )
            return {"schema_context": str(schema_summary)}
        except Exception:
            logger.warning("Schema inspection failed.", exc_info=True)
            return {
                "schema_context": "Schema inspection encountered an error. Proceeding without schema context."
            }


async def _generate_council_strategy(
    model_name: str,
    state: State,
    config: RunnableConfig,
    runtime: Runtime[Context],
) -> dict:
    """Helper to generate a single strategy asynchronously."""
    llm = await get_model(config, runtime, model_name_override=model_name)

    prompt = f"""Brainstorm a translation strategy for:
{f"Schema:\n{state.source_schema_code}\n" if state.source_schema_code else ""}
{f"Query:\n{state.source_query_code}\n" if state.source_query_code else ""}
From {state.source_target.value}{f" {state.source_target_version}" if state.source_target_version else ""} to {state.destination_target.value}{f" {state.destination_target_version}" if state.destination_target_version else ""}.

Database schema context:
{state.schema_context}"""

    response = await llm.ainvoke([HumanMessage(content=prompt)])
    return {"model": model_name, "strategy": str(response.content)}


async def council_of_models(
    state: State, config: RunnableConfig, runtime: Runtime[Context]
) -> dict[str, Any]:
    """Generate advice from multiple LLMs leveraging asyncio for parallel execution."""
    council_targets = [
        AvailableModel.EINFRA_GLM_5,
        AvailableModel.OLLAMA_QWEN3_CODER_30B,
    ]

    tasks = [
        _generate_council_strategy(t, state, config, runtime) for t in council_targets
    ]
    responses = await asyncio.gather(*tasks, return_exceptions=True)

    valid_responses = [r for r in responses if isinstance(r, dict)]

    return {"council_responses": valid_responses}


async def translation_agent(
    state: State, config: RunnableConfig, runtime: Runtime[Context]
) -> dict[str, Any]:
    """Use a ReAct agent to perform translation and validation loops natively.

    Combines static tools (validators, fallback docs) with dynamically loaded
    database and documentation MCP tools.
    """
    model = await get_model(config, runtime)

    async with load_database_tools() as db_tools:
        all_tools = TOOLS + db_tools

        system_prompt = SYSTEM_PROMPT_TRANSLATOR.format(
            origin_frameworks=[f.value for f in FrameworkType],
            destination_frameworks=[f.value for f in FrameworkType],
            system_time=datetime.now(tz=UTC).isoformat(),
        )

        # Create the ReAct agent
        agent = create_agent(
            model,
            tools=all_tools,
            response_format=TranslationOutput,
            system_prompt=system_prompt,
            middleware=[
                ModelRetryMiddleware(),
                ModelFallbackMiddleware(
                    await get_model(config, runtime, AvailableModel.EINFRA_GLM_5),
                    await get_model(config, runtime, AvailableModel.EINFRA_AGENTIC),
                    await get_model(config, runtime, AvailableModel.OLLAMA_QWEN3_CODER_30B),
                ),
                ToolRetryMiddleware(),
                LLMToolSelectorMiddleware(
                    model=await get_model(config, runtime, AvailableModel.EINFRA_QWEN3_5),
                    always_include=["search"],
                ),
                ContextEditingMiddleware(
                    edits=[
                        ClearToolUsesEdit(
                            trigger=100000,
                            keep=3,
                        )
                    ]
                ),
                SummarizationMiddleware(model, trigger=("fraction", 0.8)),
                LLMToolEmulator(
                    tools=["dotnet_validator"],
                    model=await get_model(
                        config, runtime, AvailableModel.OLLAMA_QWEN3_CODER_30B
                    ),
                ),
            ],
            debug=True if os.getenv("DEVELOPMENT") else False,
        )

        strategies = "\n".join([r.get("strategy", "") for r in state.council_responses])

        message = f"""Translate the following Source Code from {state.source_target.value}{f" {state.source_target_version}" if state.source_target_version else ""} to {state.destination_target.value}{f" {state.destination_target_version}" if state.destination_target_version else ""}.

{f"Strategies to consider:\n{strategies}\n" if strategies else ""}
{f"Database Schema Context:\n{state.schema_context}\n" if state.schema_context else ""}
---

Source Code:
{f"Schema:\n{state.source_schema_code}\n" if state.source_schema_code else ""}
{f"Query:\n{state.source_query_code}" if state.source_query_code else ""}
"""
        # summarization_middleware = SummarizationMiddleware(model, trigger=("messages", 1))
        # summarized_messages: dict[str, Any] | None = await summarization_middleware.abefore_model(AgentState(messages=[*state.translation_messages]), Runtime())

        # Invoke the agent. It manages its own messages and tool calls loops.
        response = await agent.ainvoke(
            {
                "messages": [*state.translation_messages]
                if len(state.translation_messages) > 0
                else [HumanMessage(content=message)]
            }
        )
        logger.debug("Translation response: %s", response)

    if "structured_response" not in response:
        logger.warning("No structured response available.")
        return {
            "messages": response["messages"],
            "translation_messages": response["messages"],
        }

    # Extract structured output if available
    updates: dict[str, Any] = {
        "messages": response["messages"],
        "translation_messages": response["messages"],
    }
    output = response["structured_response"]
    if output.translated_schema_code:
        updates["translated_schema_code"] = output.translated_schema_code
    if output.translated_query_code:
        updates["translated_query_code"] = output.translated_query_code

    return updates


def should_extract_input(state: State) -> str:
    if is_input_extracted(state):
        return "schema_inspection"
    else:
        return "extract_input"


def should_continue_translation(state: State) -> str:
    if state.translation_type == TranslationType.SCHEMA:
        is_translated = state.translated_schema_code is not None
    elif state.translation_type == TranslationType.QUERY:
        is_translated = state.translated_query_code is not None
    elif state.translation_type == TranslationType.BOTH:
        is_translated = (
            state.translated_schema_code is not None
            and state.translated_query_code is not None
        )
    else:
        return "translation_agent"
    if is_translated:
        return END
    else:
        return "translation_agent"


langfuse = get_client()

# Verify connection
if langfuse.auth_check():
    logger.info("Langfuse client is authenticated and ready!")
else:
    logger.error(
        "Langfuse authentication failed. Please check your credentials and host."
    )

# Initialize Langfuse CallbackHandler for Langchain (tracing)
langfuse_handler = CallbackHandler()

# Build the graph
checkpointer = InMemorySaver()
store = InMemoryStore()
cache = InMemoryCache()
builder = StateGraph(
    State,
    input_schema=InputState,
    output_schema=OutputState,
    context_schema=Context,
    checkpointer=checkpointer,
    store=store,
)


builder.add_node(extract_input, retry_policy=RetryPolicy(max_attempts=3))
builder.add_node(
    schema_inspection,
    cache_policy=CachePolicy(ttl=300),
    retry_policy=RetryPolicy(max_attempts=3),
)
# builder.add_node("council_of_models", council_of_models)
builder.add_node(
    translation_agent,
    cache_policy=CachePolicy(ttl=300),
    retry_policy=RetryPolicy(max_attempts=3),
)

builder.add_conditional_edges(START, should_extract_input)
builder.add_edge("extract_input", "schema_inspection")
# builder.add_edge("schema_inspection", "council_of_models")
# builder.add_edge("council_of_models", "translation_agent")
builder.add_edge("schema_inspection", "translation_agent")
builder.add_conditional_edges("translation_agent", should_continue_translation)

graph = builder.compile(
    name="UOM Orchestrator Workflow",
    checkpointer=checkpointer,
    store=store,
    cache=cache,
    debug=True if os.getenv("DEVELOPMENT") else False,
).with_config({"callbacks": [langfuse_handler]})

logger.info(graph.get_graph().draw_mermaid())
