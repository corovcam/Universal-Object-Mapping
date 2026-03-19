"""Define the Universal Object Mapping orchestrator graph."""

import asyncio
from datetime import UTC, datetime
from typing import Any

from langchain.agents import create_agent
from langchain.agents.middleware import (
    LLMToolEmulator,
    ModelFallbackMiddleware,
    ModelRetryMiddleware,
    ToolRetryMiddleware,
)
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph
from langgraph.runtime import Runtime
from pydantic import BaseModel, Field

from react_agent.context import AvailableModel, Context
from react_agent.prompts import SYSTEM_PROMPT_EXTRACTION, SYSTEM_PROMPT_TRANSLATOR
from react_agent.state import FrameworkType, InputState, State
from react_agent.tools import TOOLS
from react_agent.utils import load_chat_model


def _get_model(
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


class TranslationOutput(BaseModel):
    """Structured output for the translated schema and/or queries."""

    translated_schema_code: str | None = Field(
        description="The precise translated schema definitions (Entities/Models). Do not include any usage queries here."
    )

    translated_query_code: str | None = Field(
        description="The precise translated queries. Do not include schema definitions here."
    )


async def extract_input(
    state: State, config: RunnableConfig, runtime: Runtime[Context]
) -> dict[str, Any]:
    """Extract raw source code and targets from recent messages if missing from structured input."""
    if (
        state.source_code
        and state.source_target != FrameworkType.UNKNOWN
        and state.destination_target != FrameworkType.UNKNOWN
    ):
        return {}

    model = _get_model(config, runtime, AvailableModel.OLLAMA_QWEN3_CODER_30B)
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
) -> dict:
    """Helper to generate a single strategy asynchronously."""
    # We construct a temporary model based on name
    llm = _get_model(config, runtime, model_name_override=model_name)

    prompt = f"Brainstorm a translation strategy for:\n{state.source_code}\nFrom {state.source_target.value} to {state.destination_target.value}."
    response = await llm.ainvoke([HumanMessage(content=prompt)])

    return {"model": model_name, "strategy": str(response.content)}


async def council_of_models(
    state: State, config: RunnableConfig, runtime: Runtime[Context]
) -> dict[str, Any]:
    """Generates advice from multiple LLMs leveraging asyncio for parallel execution."""
    # configurable = config.get("configurable", {})
    # model_name = configurable.get("model", runtime.context.model)
    council_targets = [
        AvailableModel.EINFRA_GLM_4_7,
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
    """Uses a ReAct agent to perform translation and validation loops natively."""
    model = _get_model(config, runtime)

    system_prompt = SYSTEM_PROMPT_TRANSLATOR.format(
        origin_frameworks=[f.value for f in FrameworkType],
        destination_frameworks=[f.value for f in FrameworkType],
        system_time=datetime.now(tz=UTC).isoformat(),
    )

    # Create the ReAct agent
    agent = create_agent(
        model,
        tools=TOOLS,
        response_format=TranslationOutput,
        system_prompt=system_prompt,
        middleware=[
            ModelRetryMiddleware(),
            ModelFallbackMiddleware(
                _get_model(config, runtime, AvailableModel.OLLAMA_QWEN3_CODER_30B),
            ),
            ToolRetryMiddleware(),
            LLMToolEmulator(
                model=_get_model(
                    config, runtime, AvailableModel.OLLAMA_QWEN3_CODER_30B
                ),
            ),
        ],
        debug=True,
    )

    strategies = "\n".join([r.get("strategy", "") for r in state.council_responses])

    message = f"""Translate the following code from {state.source_target.value} to {state.destination_target.value}.
    
Strategies to consider:
{strategies}

---

Source Code:
{state.source_code}
"""
    # Invoke the agent. It manages its own messages and tool calls loops.
    # We extract the output messages to append them to the global state.
    response = await agent.ainvoke({"messages": [HumanMessage(content=message)]})

    # Extract only the messages generated by the sub-agent (avoiding duplicating history if needed,
    # but here we just append the newly generated system message + tool calls + assistant responses)
    return {"messages": response["messages"]}


# Build the graph
builder = StateGraph(State, input_schema=InputState, context_schema=Context)

builder.add_node("extract_input", extract_input)  # type: ignore
builder.add_node("council_of_models", council_of_models)  # type: ignore
builder.add_node("translation_agent", translation_agent)  # type: ignore

builder.add_edge("__start__", "extract_input")
builder.add_edge("extract_input", "council_of_models")
builder.add_edge("council_of_models", "translation_agent")
builder.add_edge("translation_agent", "__end__")

graph = builder.compile(name="UOM Orchestrator Workflow", debug=True)
