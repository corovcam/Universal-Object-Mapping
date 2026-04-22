# ty:ignore[invalid-argument-type]
"""Define the Universal Object Mapping orchestrator graph."""

import asyncio
import json
import logging
import os
from datetime import UTC, datetime
from typing import Any, Literal, Union

from langchain.agents import create_agent
from langchain.agents.middleware import (
    ClearToolUsesEdit,
    ContextEditingMiddleware,
    ModelFallbackMiddleware,
    ModelRetryMiddleware,
    ToolRetryMiddleware,
)
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langfuse import get_client
from langfuse.langchain import CallbackHandler
from langgraph.cache.memory import InMemoryCache
from langgraph.errors import NodeInterrupt
from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime
from langgraph.types import CachePolicy, RetryPolicy
from pydantic import BaseModel, Field

from react_agent.context import AvailableModel, Context
from react_agent.custom_tools.dotnet_validator import validate_dotnet_code
from react_agent.custom_tools.java_validator import validate_java_code
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
                    await get_model(
                        config, runtime, AvailableModel.OLLAMA_QWEN3_CODER_30B
                    ),
                ),
                ToolRetryMiddleware(),
                # LLMToolSelectorMiddleware(
                #     model=await get_model(
                #         config, runtime, AvailableModel.EINFRA_QWEN3_5
                #     ),
                # ),
                ContextEditingMiddleware(
                    edits=[
                        ClearToolUsesEdit(
                            trigger=100000,
                            keep=3,
                        )
                    ]
                ),
                # SummarizationMiddleware(model, trigger=("fraction", 0.8)),
            ],
            debug=True if os.getenv("DEVELOPMENT") else False,
        )

        message = f"""Inspect the database schemas relevant to translating code from {state.source_target.value}{f" {state.source_target_version}" if state.source_target_version else ""} to {state.destination_target.value}{f" {state.destination_target_version}" if state.destination_target_version else ""}.

{f"Mapping from {database_mapping['source']} to {database_mapping['destination']}:\n<database_mapping>{database_mapping['mapping']}</database_mapping>\n" if database_mapping else ""}
Source code being translated:
{f"<schema_code>{state.source_schema_code}</schema_code>\n" if state.source_schema_code else ""}
{f"<query_code>{state.source_query_code}</query_code>" if state.source_query_code else ""}"""  # ty:ignore[unresolved-attribute]

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
{state.schema_context}"""  # ty:ignore[unresolved-attribute]

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



async def translate_code(
    state: State, config: RunnableConfig, runtime: Runtime[Context]
) -> dict[str, Any]:
    """Call LLM to translate schema and/or query."""
    model = await get_model(config, runtime)

    system_prompt = SYSTEM_PROMPT_TRANSLATOR.format(
        origin_frameworks=[f.value for f in FrameworkType],
        destination_frameworks=[f.value for f in FrameworkType],
        system_time=datetime.now(tz=UTC).isoformat(),
    )

    strategies = "\n".join([r.get("strategy", "") for r in state.council_responses])

    message_content = f"""Translate the following Source Code from {state.source_target.value}{f" {state.source_target_version}" if state.source_target_version else ""} to {state.destination_target.value}{f" {state.destination_target_version}" if state.destination_target_version else ""}.

{f"Strategies to consider:\n{strategies}\n" if strategies else ""}
{f"Database Schema Context:\n{state.schema_context}\n" if state.schema_context else ""}
---

Source Code:
{f"Schema:\n{state.source_schema_code}\n" if state.source_schema_code else ""}
{f"Query:\n{state.source_query_code}" if state.source_query_code else ""}
"""

    messages = [SystemMessage(content=system_prompt)]
    if len(state.translation_messages) > 0:
        messages.extend(state.translation_messages)
    else:
        messages.append(HumanMessage(content=message_content))

    # Invoke model with structured output
    structured_model = model.with_structured_output(TranslationOutput)
    response = await structured_model.ainvoke(messages)

    # response is TranslationOutput
    updates: dict[str, Any] = {
        "translation_messages": messages + [AIMessage(content=f"Translated Output:\nSchema: {response.translated_schema_code}\nQuery: {response.translated_query_code}")],
    }

    if response.translated_schema_code:
        updates["translated_schema_code"] = response.translated_schema_code
    if response.translated_query_code:
        updates["translated_query_code"] = response.translated_query_code

    return updates

async def validate_schema(state: State) -> dict[str, Any]:
    """Validate the translated schema."""
    if not state.translated_schema_code:
        return {}

    code = state.translated_schema_code
    dest = state.destination_target.value if state.destination_target else ""

    # We call the appropriate validator based on the destination framework
    if "Java" in dest:
        # Needs use_maven or standard javac depending on the complexity
        validation_result = await validate_java_code.ainvoke(
            {"source_code": code, "framework": "none"} # Could pass correct framework mapping here
        )
    elif "C#" in dest:
        validation_result = await validate_dotnet_code.ainvoke(
            {"source_code": code}
        )
    else:
        validation_result = "No matching validator for destination framework."

    passed = "Passed" in validation_result or "successfully" in validation_result.lower()

    msg = HumanMessage(content=f"Schema Validation Result:\n{validation_result}")

    if not passed:
        return {
            "translation_messages": [msg],
            "loop_count": state.loop_count + 1
        }

    return {
        "translation_messages": [msg]
    }

async def validate_query(state: State) -> dict[str, Any]:
    """Validate the translated query."""
    if not state.translated_query_code:
        return {}

    code = state.translated_query_code
    dest = state.destination_target.value if state.destination_target else ""

    if "Java" in dest:
        validation_result = await validate_java_code.ainvoke(
            {"source_code": code, "framework": "none"}
        )
    elif "C#" in dest:
        validation_result = await validate_dotnet_code.ainvoke(
            {"source_code": code}
        )
    else:
        validation_result = "No matching validator for destination framework."

    passed = "Passed" in validation_result or "successfully" in validation_result.lower()

    msg = HumanMessage(content=f"Query Validation Result:\n{validation_result}")

    if not passed:
        return {
            "translation_messages": [msg],
            "loop_count": state.loop_count + 1
        }

    return {
        "translation_messages": [msg]
    }

async def check_equivalence(state: State) -> dict[str, Any]:
    """Check equivalence of translated query."""
    # Scaffold: for now just pass
    return {
        "translation_messages": [HumanMessage(content="Equivalence Check Passed.")]
    }

def should_extract_input(state: State) -> Literal["schema_inspection", "extract_input"]:
    """Determine whether input needs to be extracted."""
    if is_input_extracted(state):
        return "schema_inspection"
    else:
        return "extract_input"

def route_after_translation(state: State) -> Literal["validate_schema", "validate_query", "check_equivalence", END]: # ty:ignore[invalid-type-form]
    """Route execution after code translation based on translation type."""
    if state.translation_type == TranslationType.SCHEMA or state.translation_type == TranslationType.BOTH:
        return "validate_schema"
    elif state.translation_type == TranslationType.QUERY:
        return "validate_query"
    return END

def handle_loop_interrupt(state: State, context: Context):
    """Handle looping logic and interrupt if max attempts are reached."""
    if state.loop_count >= context.max_loop_count:
        raise NodeInterrupt(f"Max loop count ({context.max_loop_count}) reached. Pausing for human-in-the-loop.")
    return "translate_code"

def route_after_schema_validation(state: State, config: RunnableConfig, runtime: Runtime[Context]) -> Literal["translate_code", "validate_query", "check_equivalence", END]: # ty:ignore[invalid-type-form]
    """Route after schema validation."""
    last_msg = state.translation_messages[-1].content
    if isinstance(last_msg, str) and ("Failed" in last_msg or "Error" in last_msg):
        return handle_loop_interrupt(state, runtime.context)

    if state.translation_type == TranslationType.BOTH:
        return "validate_query"
    return END

def route_after_query_validation(state: State, config: RunnableConfig, runtime: Runtime[Context]) -> Literal["translate_code", "check_equivalence"]: # ty:ignore[invalid-type-form]
    """Route after query validation."""
    last_msg = state.translation_messages[-1].content
    if isinstance(last_msg, str) and ("Failed" in last_msg or "Error" in last_msg):
        return handle_loop_interrupt(state, runtime.context)

    return "check_equivalence"

def route_after_equivalence(state: State, config: RunnableConfig, runtime: Runtime[Context]) -> Literal["translate_code", END]: # ty:ignore[invalid-type-form]
    """Route after equivalence check."""
    last_msg = state.translation_messages[-1].content
    if isinstance(last_msg, str) and ("Failed" in last_msg or "Error" in last_msg):
        return handle_loop_interrupt(state, runtime.context)

    return END

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
# checkpointer = InMemorySaver()
# store = InMemoryStore()
cache = InMemoryCache()
builder = StateGraph(
    State,
    input_schema=InputState,
    output_schema=OutputState,
    context_schema=Context,
)

builder.add_node(extract_input, retry_policy=RetryPolicy(max_attempts=3))
builder.add_node(
    schema_inspection,
    cache_policy=CachePolicy(ttl=300),
    retry_policy=RetryPolicy(max_attempts=3),
)

builder.add_node(translate_code, retry_policy=RetryPolicy(max_attempts=3))
builder.add_node(validate_schema)
builder.add_node(validate_query)
builder.add_node(check_equivalence)

builder.add_conditional_edges(START, should_extract_input)
builder.add_edge("extract_input", "schema_inspection")
builder.add_edge("schema_inspection", "translate_code")

builder.add_conditional_edges("translate_code", route_after_translation)
builder.add_conditional_edges("validate_schema", route_after_schema_validation)
builder.add_conditional_edges("validate_query", route_after_query_validation)
builder.add_conditional_edges("check_equivalence", route_after_equivalence)

graph = builder.compile(
    name="UOM Orchestrator Workflow",
    # checkpointer=checkpointer,
    # store=store,
    cache=cache,
    debug=True if os.getenv("DEVELOPMENT") else False,
).with_config({"callbacks": [langfuse_handler]})

logger.info(graph.get_graph().draw_mermaid())
