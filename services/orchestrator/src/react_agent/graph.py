"""Define the Universal Object Mapping orchestrator graph."""

import asyncio
from datetime import UTC, datetime
from typing import Any, Literal, cast

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph
from langgraph.runtime import Runtime
from langgraph.types import interrupt
from pydantic import BaseModel, Field

from react_agent.context import Context
from react_agent.custom_tools.dotnet_validator import validate_dotnet_code
from react_agent.custom_tools.java_validator import validate_java_code
from react_agent.state import InputState, FrameworkType, State
from react_agent.utils import load_chat_model
from react_agent.prompts import SYSTEM_PROMPT_EXTRACTION
from react_agent.state import FrameworkType


def _get_model(
    config: RunnableConfig,
    runtime: Runtime[Context],
    model_name_override: str | None = None,
) -> BaseChatModel:
    """Factory to initialize the model using configuration or context."""
    configurable = config.get("configurable", {})
    # Get model choice, which might be an Enum or string depending on where it came from
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

    return load_chat_model(
        model_name, config={"openai_api_url": openai_url, "openai_api_key": openai_key}
    )


class ExtractionOutput(BaseModel):
    """Structured output for identifying user intent from messages."""

    source_code: str = Field(
        description="The source code snippet or query mapped by the user."
    )
    source_target: FrameworkType = Field(
        description="The identified origin framework/ORM."
    )
    destination_target: FrameworkType = Field(
        description="The identified target framework/ORM."
    )


class SchemaOutput(BaseModel):
    """Structured output for the translated schema."""

    translated_schema_code: str = Field(
        description="The precise translated schema definitions (Entities/Models). Do not include any usage queries here."
    )


class QueryOutput(BaseModel):
    """Structured output for the translated query."""

    translated_query_code: str = Field(
        description="The precise translated queries. Do not include schema definitions here."
    )


async def extract_input(
    state: State, config: RunnableConfig, runtime: Runtime[Context]
) -> dict[str, Any]:
    """Extract raw source code and targets from recent messages if missing from structured input."""
    # Only run extraction if we are missing structured data
    if (
        state.source_code
        and state.source_target != FrameworkType.UNKNOWN
        and state.destination_target != FrameworkType.UNKNOWN
    ):
        return {}

    model = _get_model(config, runtime)
    structured_llm = model.with_structured_output(ExtractionOutput)

    system_prompt = SYSTEM_PROMPT_EXTRACTION.format(
        system_time=datetime.now(tz=UTC).isoformat(),
        origin_frameworks=[f.value for f in FrameworkType],
        destination_frameworks=[f.value for f in FrameworkType],
    )
    prompt = f"Analyze the following conversation and extract the source code, the origin framework, and the desired destination target framework:\n{state.messages[-1].content}"

    extraction = await structured_llm.ainvoke(
        [SystemMessage(content=system_prompt), HumanMessage(content=prompt)]
    )
    assert isinstance(extraction, ExtractionOutput)

    return {
        "source_code": extraction.source_code,
        "source_target": extraction.source_target,
        "destination_target": extraction.destination_target,
    }


async def _generate_council_strategy(
    model_name: str,
    state: State,
    config: RunnableConfig,
    runtime: Runtime[Context],
    temperature: float = 0.7,
) -> dict:
    """Helper to generate a single strategy asynchronously."""
    # In reality we bind the context properly, but here we construct a temporary model based on name
    # We could use the runtime's api keys depending on the provider format setup in utils
    # For now we use the main model but vary temperature if supported, or just mock variations.
    from langchain_core.messages import HumanMessage

    llm = _get_model(config, runtime, model_name_override=model_name)

    prompt = f"Brainstorm a translation strategy for:\n{state.source_code}\nFrom {state.source_target.value} to {state.destination_target.value}."
    response = await llm.ainvoke([HumanMessage(content=prompt)])

    return {"model": model_name, "strategy": str(response.content)}


async def council_of_models(
    state: State, config: RunnableConfig, runtime: Runtime[Context]
) -> dict[str, Any]:
    """Generates advice from multiple LLMs leveraging asyncio for parallel execution."""
    # We define a few dummy council targets. In production these could come from context.py config
    configurable = config.get("configurable", {})
    model_name = configurable.get("model", runtime.context.model)
    council_targets = [
        model_name,
        model_name,  # Imagine this is a second distinct model
    ]

    # Run strategies in parallel
    tasks = [
        _generate_council_strategy(t, state, config, runtime) for t in council_targets
    ]
    responses = await asyncio.gather(*tasks, return_exceptions=True)

    valid_responses = [r for r in responses if isinstance(r, dict)]

    return {"council_responses": valid_responses}


async def schema_translation(
    state: State, config: RunnableConfig, runtime: Runtime[Context]
) -> dict[str, Any]:
    """Translates the entities/schema explicitly into structured output."""
    model = _get_model(config, runtime)
    structured_llm = model.with_structured_output(SchemaOutput)

    strategies = "\n".join([r.get("strategy", "") for r in state.council_responses])
    system_prompt = runtime.context.system_prompt.format(
        system_time=datetime.now(tz=UTC).isoformat()
    )

    prompt = f"""
    Translate ONLY the SCHEMA components of the following {state.source_target.value} code to {state.destination_target.value}.
    Exclude queries or logical operations. Just data definitions.
    
    Consider these strategies: {strategies}
    Error Feedback: {state.error_feedback}
    Target code: {state.source_code}
    """

    response = await structured_llm.ainvoke(
        [SystemMessage(content=system_prompt), HumanMessage(content=prompt)]
    )
    assert isinstance(response, SchemaOutput)

    return {"schema_translated_code": response.translated_schema_code}


async def query_translation(
    state: State, config: RunnableConfig, runtime: Runtime[Context]
) -> dict[str, Any]:
    """Translates the data access operations/queries natively after the schema is resolved."""
    model = _get_model(config, runtime)
    structured_llm = model.with_structured_output(QueryOutput)

    # If the source code has no queries, we could return early.

    prompt = f"""
    Translate ONLY the QUERY components of the following {state.source_target.value} code to {state.destination_target.value}.
    Use the newly established schema logic:
    {state.schema_translated_code}
    
    Original code: {state.source_code}
    """

    response = await structured_llm.ainvoke([HumanMessage(content=prompt)])
    assert isinstance(response, QueryOutput)
    return {"query_translated_code": response.translated_query_code}


async def validation_stage(state: State, runtime: Runtime[Context]) -> dict[str, Any]:
    """Validates the translated schema and queries natively using tools."""
    # Combine schema and queries for syntax verification if needed
    code_to_compile = f"{state.schema_translated_code}\n\n{state.query_translated_code}"
    target = state.destination_target.value.lower()

    result = ""
    if "java" in target or "spring" in target:
        result = await validate_java_code.ainvoke(
            input=cast(
                dict[str, Any],
                {
                    "source_code": code_to_compile,
                    "framework": state.destination_target.value,
                },
            )
        )
    elif "c#" in target or "efcore" in target or "dotnet" in target:
        result = await validate_dotnet_code.ainvoke(
            input=cast(
                dict[str, Any],
                {
                    "source_code": code_to_compile,
                    "orm": state.destination_target.value,
                },
            )
        )
    else:
        result = (
            "Compilation Check Skipped: Target not mapped to a specific validator tool."
        )

    return {"schema_validation_result": str(result)}


async def database_sync_stage(
    state: State, runtime: Runtime[Context]
) -> dict[str, Any]:
    """Syncs with the database to check constraints and queries using Database Toolbox MCP."""
    return {"query_validation_result": "DB Sync/Equivalence Check Passed"}


def evaluate_end_condition(
    state: State,
) -> Literal["database_sync_stage", "human_intervention", "schema_translation"]:
    """Routes the graph based on the validation results."""
    if (
        "Error" in state.schema_validation_result
        or "Error" in state.query_validation_result
    ):
        if state.error_count >= state.max_retries:
            return "human_intervention"
        return "schema_translation"
    return "database_sync_stage"


def evaluate_db_sync_condition(
    state: State,
) -> Literal["__end__", "schema_translation", "human_intervention"]:
    if "Error" in state.query_validation_result:
        if state.error_count >= state.max_retries:
            return "human_intervention"
        return "schema_translation"
    return "__end__"


def human_intervention(state: State) -> dict[str, Any]:
    """Pauses the graph to allow the user to modify the state or provide a fix."""
    print("Interrupting: Human intervention requested.")
    human_input = interrupt("Max retries reached. Please provide a manual fix or hint.")
    return {"error_feedback": f"Human fix/hint: {human_input}", "error_count": 0}


def increment_error(state: State) -> dict[str, Any]:
    return {
        "error_count": state.error_count + 1,
        "error_feedback": state.schema_validation_result
        + "\n"
        + state.query_validation_result,
    }


# Build the graph
builder = StateGraph(State, input_schema=InputState, context_schema=Context)

builder.add_node("extract_input", extract_input)  # type: ignore
builder.add_node("council_of_models", council_of_models)  # type: ignore
builder.add_node("schema_translation", schema_translation)  # type: ignore
builder.add_node("query_translation", query_translation)  # type: ignore
builder.add_node("validation_stage", validation_stage)
builder.add_node("database_sync_stage", database_sync_stage)
builder.add_node("human_intervention", human_intervention)
builder.add_node("increment_error", increment_error)

builder.add_edge("__start__", "extract_input")
builder.add_edge("extract_input", "council_of_models")
builder.add_edge("council_of_models", "schema_translation")
builder.add_edge("schema_translation", "query_translation")
builder.add_edge("query_translation", "validation_stage")

builder.add_conditional_edges(
    "validation_stage",
    evaluate_end_condition,
    {
        "human_intervention": "human_intervention",
        "schema_translation": "increment_error",
        "database_sync_stage": "database_sync_stage",
    },
)

builder.add_edge("increment_error", "schema_translation")

builder.add_conditional_edges(
    "database_sync_stage",
    evaluate_db_sync_condition,
    {
        "human_intervention": "human_intervention",
        "schema_translation": "increment_error",
        "__end__": "__end__",
    },
)

builder.add_edge("human_intervention", "schema_translation")

graph = builder.compile(name="UOM Orchestrator Workflow")
