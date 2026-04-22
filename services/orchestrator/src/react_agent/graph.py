# ty:ignore[invalid-argument-type]
"""Define the Universal Object Mapping orchestrator graph."""

import asyncio
import json
import logging
import os
from datetime import UTC, datetime
from typing import Any, Literal, Union, cast

from langchain.agents import create_agent
from langchain.agents.middleware import (
    ClearToolUsesEdit,
    ContextEditingMiddleware,
    ModelFallbackMiddleware,
    ModelRetryMiddleware,
    ToolRetryMiddleware,
)
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langfuse import get_client
from langfuse.langchain import CallbackHandler
from langgraph.cache.memory import InMemoryCache
from langgraph.graph import START, StateGraph
from langgraph.runtime import Runtime
from langgraph.types import CachePolicy, RetryPolicy
from pydantic import BaseModel, Field

from react_agent.constants import (
    AvailableModel,
    FrameworkType,
    JavaFramework,
    TranslationType,
)
from react_agent.context import Context
from react_agent.custom_tools.mcp_database import load_database_tools
from react_agent.prompts import (
    SYSTEM_PROMPT_EXTRACTION,
    SYSTEM_PROMPT_SCHEMA_INSPECTOR,
    SYSTEM_PROMPT_TRANSLATOR,
)
from react_agent.state import (
    InputState,
    OutputState,
    State,
)
from react_agent.tools import TOOLS
from react_agent.utils import (
    LoggingCallbackHandler,
    get_database_mapping_json,
    get_model,
)
from react_agent.utils.deterministic_checks import (
    _deterministic_feedback_message,
    _deterministic_translation_issues,
    _latest_validation_outcome,
)

logger = logging.getLogger(__name__)


class ExtractionOutput(BaseModel):
    """Structured output for identifying user intent from messages."""

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
        description="The precise translated schema definitions (entities/models). Plain code only. Do not include usage queries."
    )

    translated_query_code: Union[str, None] = Field(
        description=(
            "The precise translated production queries only. Keep query semantics and method shape equivalent to source query "
            "code. Plain code only. Do not include schema definitions, validation harness helpers, or synthetic validator-only "
            "parameters unless they already exist in source query code."
        )
    )

    validation_harness_code: Union[str, None] = Field(
        description="Dedicated query validation harness code used for validate_source_query/validate_target_query tool calls. Plain code only. Keep separate from translated_query_code."
    )

    validation_sort_by_field: Union[str, None] = Field(
        default=None,
        description="Deterministic sort field for query validation (e.g. 'Id' or 'pickingCompletedWhen'). Required if query is translated.",
    )

    validation_entry_type_name: Union[str, None] = Field(
        default=None,
        description="Name of the class in validation_harness_code (e.g. 'QueryValidationHarness'). Required if query is translated.",
    )

    validation_entry_method_name: Union[str, None] = Field(
        default=None,
        description="Name of the method in validation_harness_code (e.g. 'build' or 'Build'). Required if query is translated.",
    )

    source_validation_harness_code: Union[str, None] = Field(
        default=None,
        description="Dedicated validation harness code for the source query, keeping original logic but wrapped in a static method returning IQueryable or similar. Required if query is translated.",
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

    # model = await get_model(config, runtime, AvailableModel.OLLAMA_QWEN3_CODER_30B)
    # structured_llm = model.with_structured_output(ExtractionOutput)

    system_prompt = SYSTEM_PROMPT_EXTRACTION.format(
        system_time=datetime.now(tz=UTC).isoformat(),
        origin_frameworks=[f.value for f in FrameworkType],
        destination_frameworks=[f.value for f in FrameworkType],
    )

    extraction_agent = create_agent(
        await get_model(config, runtime, AvailableModel.EINFRA_QWEN3_CODER_30B),
        system_prompt=system_prompt,
        response_format=ExtractionOutput,
        middleware=[
            ModelRetryMiddleware(),
            ModelFallbackMiddleware(
                await get_model(config, runtime, AvailableModel.EINFRA_MINI),
                await get_model(config, runtime, AvailableModel.OLLAMA_QWEN3_CODER_30B),
            ),
        ],
        # debug=True if os.getenv("DEVELOPMENT") else False,
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

    response = await extraction_agent.ainvoke(
        {"messages": [HumanMessage(content=prompt)]}
    )

    if "structured_response" not in response:
        logger.warning("Extraction agent did not return structured response.")
        return {}

    extraction: ExtractionOutput = response["structured_response"]
    return extraction.model_dump(warnings="error", exclude_unset=True)


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
            # debug=True if os.getenv("DEVELOPMENT") else False,
        )

        message = f"""Inspect the database schemas relevant to translating code from {state.source_target.value}{f" {state.source_target_version}" if state.source_target_version else ""} to {state.destination_target.value}{f" {state.destination_target_version}" if state.destination_target_version else ""}.

{f"Mapping from {database_mapping['source']} to {database_mapping['destination']}:\n<database_mapping>\n{json.dumps(database_mapping['mapping'])}\n</database_mapping>\n" if database_mapping else ""}

Source code being translated:
{f"<schema_code>\n{state.source_schema_code}\n</schema_code>\n" if state.source_schema_code else ""}
{f"<query_code>\n{state.source_query_code}\n</query_code>\n" if state.source_query_code else ""}"""  # ty:ignore[unresolved-attribute]

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


async def translation_agent(
    state: State, config: RunnableConfig, runtime: Runtime[Context]
) -> dict[str, Any]:
    """Use a ReAct agent to perform translation and validation loops natively.

    Combines static tools (validators, fallback docs) with dynamically loaded
    database and documentation MCP tools.

    !! DEPRECATED
    """
    model = await get_model(config, runtime)

    all_tools = TOOLS

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
                await get_model(config, runtime, AvailableModel.EINFRA_KIMI_K2_5),
                await get_model(config, runtime, AvailableModel.EINFRA_AGENTIC),
                await get_model(config, runtime, AvailableModel.OLLAMA_QWEN3_CODER_30B),
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
            # LLMToolEmulator(
            #     tools=["validate_java_code", "dotnet_validator", "validate_source_query", "validate_target_query", "check_query_equivalence"],
            #     model=await get_model(config, runtime, AvailableModel.EINFRA_MINI),
            # ),
        ],
        # debug=True if os.getenv("DEVELOPMENT") else False,
    )

    strategies = "\n".join([r.get("strategy", "") for r in state.council_responses])

    message = f"""Translate the following Source Code ({"schema/query" if state.translation_type.value == TranslationType.BOTH else state.translation_type.value}) from {state.source_target.value}{f" {state.source_target_version}" if state.source_target_version else ""} to {state.destination_target.value}{f" {state.destination_target_version}" if state.destination_target_version else ""}.
{f"\nStrategies to consider:\n{strategies}\n" if strategies else ""}{f"\nDatabase Schema Context:\n{state.schema_context}\n" if state.schema_context else ""}---
Source Code:
{f"<source_schema_code>\n{state.source_schema_code.strip()}\n</source_schema_code>" if state.source_schema_code else ""}{f"\n<source_query_code>\n{state.source_query_code.strip()}\n</source_query_code>" if state.source_query_code else ""}
"""  # ty:ignore[unresolved-attribute]

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
        source_validation = _latest_validation_outcome(
            list(response["messages"]),
            "[Source Query Validation Passed]",
            "[Source Query Validation Failed]",
        )
        if (
            state.translation_type in {TranslationType.QUERY, TranslationType.BOTH}
            and source_validation == "failed"
        ):
            return {
                "messages": response["messages"],
                "translation_messages": response["messages"],
                "translated_schema_code": None,
                "translated_query_code": None,
                "validation_harness_code": None,
            }

        logger.warning("No structured response available.")
        feedback = HumanMessage(
            content=(
                "Return a structured_response with translated_schema_code and/or translated_query_code. "
                "If translation_type includes query, run validate_source_query, validate_target_query, "
                "and check_query_equivalence before finalizing."
            )
        )
        updated_messages = [*response["messages"], feedback]
        return {
            "messages": updated_messages,
            "translation_messages": updated_messages,
            "translated_schema_code": None,
            "translated_query_code": None,
            "validation_harness_code": None,
        }

    # Extract structured output if available
    output = cast(TranslationOutput, response["structured_response"])
    updates: dict[str, Any] = {
        "messages": response["messages"],
        "translation_messages": response["messages"],
    }
    updates.update(output.model_dump(exclude_unset=True, exclude_defaults=True))

    return updates


async def generate_translation_node(
    state: State, config: RunnableConfig, runtime: Runtime[Context]
) -> dict[str, Any]:
    """Deterministically generate the translation using structured LLM output."""
    model = await get_model(config, runtime)
    structured_llm = model.with_structured_output(TranslationOutput)

    system_prompt = SYSTEM_PROMPT_TRANSLATOR.format(
        origin_frameworks=[f.value for f in FrameworkType],
        target_frameworks=[f.value for f in FrameworkType],
        system_time=datetime.now(tz=UTC).isoformat(),
    )

    message = f"""Translate the following Source Code ({"schema/query" if state.translation_type and state.translation_type.value == TranslationType.BOTH else (state.translation_type.value if state.translation_type else "schema")}) from {state.source_target.value if state.source_target else "Unknown"}{f" {state.source_target_version}" if state.source_target_version else ""} to {state.destination_target.value if state.destination_target else "Unknown"}{f" {state.destination_target_version}" if state.destination_target_version else ""}.
{f"\nDatabase Schema Context:\n{state.schema_context}\n" if state.schema_context else ""}---
Source Code:
{f"<source_schema_code>\n{state.source_schema_code}\n</source_schema_code>" if state.source_schema_code else ""}{f"\n<source_query_code>\n{state.source_query_code}\n</source_query_code>" if state.source_query_code else ""}
"""

    messages = [
        {"role": "system", "content": system_prompt},
        *state.translation_messages,
    ]
    if len(state.translation_messages) == 0:
        messages.append(HumanMessage(content=message))

    # Invoke LLM
    response = await structured_llm.ainvoke(messages)

    updates: dict[str, Any] = {
        "translation_loop_count": state.translation_loop_count + 1,
    }

    if not isinstance(response, TranslationOutput):
        logger.warning("LLM did not return TranslationOutput properly.")
        return updates

    updates.update(response.model_dump(exclude_unset=True, exclude_none=True))

    # Add AI response to the history so next iterations have the context
    from langchain_core.messages import AIMessage

    updates["translation_messages"] = [
        AIMessage(
            content="Generated translation. Commencing deterministic validation..."
        )
    ]

    return updates


async def human_intervention_node(
    state: State, config: RunnableConfig, runtime: Runtime[Context]
) -> dict[str, Any]:
    """A dummy node that acts as a pausing point when loop threshold is reached."""
    return {}


async def validate_schema_node(
    state: State, config: RunnableConfig, runtime: Runtime[Context]
) -> dict[str, Any]:
    """Execute schema validation deterministically outside the LLM."""
    from react_agent.custom_tools.dotnet_validator import validate_dotnet_code
    from react_agent.custom_tools.java_validator import validate_java_code

    code = state.translated_schema_code
    if not code:
        return {}

    target = state.destination_target
    if not target:
        return {}

    if target in JavaFramework:
        res = await validate_java_code.ainvoke(
            {"source_code": code, "framework": target, "validate_schema": True}
        )
    else:
        res = await validate_dotnet_code.ainvoke(
            {"source_code": code, "framework": target}
        )

    return {"translation_messages": [HumanMessage(content=str(res))]}


async def validate_query_node(
    state: State, config: RunnableConfig, runtime: Runtime[Context]
) -> dict[str, Any]:
    """Execute query validation tools in parallel deterministically outside the LLM."""
    from react_agent.custom_tools.query_validator import (
        check_query_equivalence,
        validate_source_query,
        validate_target_query,
    )

    msgs = []

    if not state.translated_query_code:
        return {}

    if not state.source_target or not state.destination_target:
        return {}

    src_task = validate_source_query.ainvoke(
        {
            "validation_schema_code": state.source_schema_code,
            "validation_harness_code": state.source_validation_harness_code or "",
            "framework": state.source_target,
            "sort_by_field": state.validation_sort_by_field or "id",
            "entry_type_name": state.validation_entry_type_name or "QueryEntrypoint",
            "entry_method_name": state.validation_entry_method_name or "Build",
        }
    )

    tgt_task = validate_target_query.ainvoke(
        {
            "validation_schema_code": state.translated_schema_code,
            "validation_harness_code": state.validation_harness_code or "",
            "framework": state.destination_target,
            "sort_by_field": state.validation_sort_by_field or "id",
            "entry_type_name": state.validation_entry_type_name
            or "QueryValidationHarness",
            "entry_method_name": state.validation_entry_method_name or "build",
        }
    )

    src_res, tgt_res = await asyncio.gather(src_task, tgt_task, return_exceptions=True)

    src_str = (
        str(src_res)
        if not isinstance(src_res, Exception)
        else f"[Source Query Validation Failed] {src_res}"
    )
    tgt_str = (
        str(tgt_res)
        if not isinstance(tgt_res, Exception)
        else f"[Target Query Validation Failed] {tgt_res}"
    )

    msgs.append(HumanMessage(content=src_str))
    msgs.append(HumanMessage(content=tgt_str))

    if (
        "[Source Query Validation Passed]" in src_str
        and "[Target Query Validation Passed]" in tgt_str
    ):
        equiv_res = await check_query_equivalence.ainvoke(
            {
                "source_orm": state.source_target.value,
                "target_framework": state.destination_target.value,
            }
        )
        equiv_str = (
            str(equiv_res)
            if not isinstance(equiv_res, Exception)
            else f"Error: {equiv_res}"
        )
        msgs.append(HumanMessage(content=equiv_str))

    return {"translation_messages": msgs}


async def evaluate_translation_node(
    state: State, config: RunnableConfig, runtime: Runtime[Context]
) -> dict[str, Any]:
    """Evaluate structural output and validation results to provide feedback if needed."""
    issues, schema_ok, query_ok = _deterministic_translation_issues(
        state,
        state.translated_schema_code,
        state.translated_query_code,
        state.validation_harness_code,
        list(state.translation_messages),
    )

    updates: dict[str, Any] = {}
    if issues:
        feedback = _deterministic_feedback_message(issues)
        updates["translation_messages"] = [feedback]

        if not schema_ok:
            updates["translated_schema_code"] = None
        if not query_ok:
            updates["translated_query_code"] = None
            updates["validation_harness_code"] = None

    return updates


def should_extract_input(state: State) -> Literal["schema_inspection", "extract_input"]:
    """Route execution to extraction until mandatory input fields are present."""
    if is_input_extracted(state):
        return "schema_inspection"
    else:
        return "extract_input"


def route_post_translation(
    state: State,
) -> Literal[
    "validate_schema_node", "validate_query_node", "evaluate_translation_node"
]:
    """Route from translation_agent to the first applicable validation node."""
    if state.translation_type in {TranslationType.SCHEMA, TranslationType.BOTH}:
        return "validate_schema_node"
    if state.translation_type == TranslationType.QUERY:
        return "validate_query_node"
    return "evaluate_translation_node"


def route_post_schema_validation(
    state: State,
) -> Literal["validate_query_node", "evaluate_translation_node"]:
    """Route from validate_schema to validate_query or deterministic evaluation."""
    if state.translation_type == TranslationType.BOTH:
        return "validate_query_node"
    return "evaluate_translation_node"


def should_continue_translation(
    state: State,
) -> Literal["generate_translation_node", "human_intervention_node", "__end__"]:
    """Route back to translation until deterministic completion criteria are met."""
    if state.translation_type is None:
        return "generate_translation_node"

    issues, _, _ = _deterministic_translation_issues(
        state,
        state.translated_schema_code,
        state.translated_query_code,
        state.validation_harness_code,
        list(state.translation_messages),
    )

    if len(issues) == 0:
        return "__end__"

    if state.translation_loop_count >= 3:
        return "human_intervention_node"

    return "generate_translation_node"


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


builder.add_node(extract_input, retry_policy=RetryPolicy(max_attempts=3))  # type: ignore
builder.add_node(
    schema_inspection,  # type: ignore
    cache_policy=CachePolicy(ttl=300),
    retry_policy=RetryPolicy(max_attempts=3),
)
builder.add_node(
    generate_translation_node,
    cache_policy=CachePolicy(ttl=300),
    retry_policy=RetryPolicy(max_attempts=3),
)
builder.add_node(human_intervention_node)

builder.add_node(validate_schema_node, retry_policy=RetryPolicy(max_attempts=3))
builder.add_node(validate_query_node, retry_policy=RetryPolicy(max_attempts=3))
builder.add_node(
    evaluate_translation_node,
)

builder.add_conditional_edges(START, should_extract_input)
builder.add_conditional_edges("extract_input", should_extract_input)
builder.add_edge("schema_inspection", "generate_translation_node")

builder.add_conditional_edges("generate_translation_node", route_post_translation)
builder.add_conditional_edges("validate_schema_node", route_post_schema_validation)
builder.add_edge("validate_query_node", "evaluate_translation_node")
builder.add_conditional_edges("evaluate_translation_node", should_continue_translation)
builder.add_edge("human_intervention_node", "generate_translation_node")

graph = builder.compile(
    name="UOM Orchestrator Workflow",
    interrupt_before=["human_intervention_node"],
    # checkpointer=checkpointer,
    # store=store,
    cache=cache,
    # debug=True if os.getenv("DEVELOPMENT") else False,
).with_config({"callbacks": [langfuse_handler, LoggingCallbackHandler()]})

# logger.info(graph.get_graph().draw_mermaid())
if os.getenv("DEVELOPMENT"):
    logging.getLogger("watchfiles.main").setLevel(logging.WARNING)
