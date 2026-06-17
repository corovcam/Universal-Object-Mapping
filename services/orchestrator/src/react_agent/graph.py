# pyright: ignore[reportArgumentType]
# ty:ignore[invalid-argument-type]
# ty:ignore[invalid-type-form]

"""Define the Universal Object Mapping orchestrator graph."""
import asyncio
import json
import logging
import os
from typing import Any, Awaitable, Callable, Literal, Union, cast

import logfire
import orjson
from langchain.agents import create_agent
from langchain.agents.middleware import (
    ClearToolUsesEdit,
    ContextEditingMiddleware,
    ModelFallbackMiddleware,
    ModelRetryMiddleware,
    ToolRetryMiddleware,
)
from langchain.agents.structured_output import ProviderStrategy
from langchain.messages import AIMessage
from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.cache.memory import InMemoryCache
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.prebuilt.tool_node import ToolCallRequest
from langgraph.runtime import Runtime
from langgraph.types import CachePolicy, Command, RetryPolicy, interrupt
from pydantic import BaseModel, Field, model_validator
from pydantic.experimental.missing_sentinel import MISSING

from react_agent.constants import (
    FRAMEWORK_TO_LANGUAGE_TYPE,
    MAX_EXTRACTION_LOOPS,
    MAX_TRANSLATION_LOOPS,
    AvailableModel,
    DotnetFramework,
    FrameworkEnum,
    JavaFramework,
    SourceFramework,
    TargetFramework,
    TranslationType,
)
from react_agent.context import Context
from react_agent.custom_tools.dotnet_validator import validate_dotnet_code
from react_agent.custom_tools.java_validator import validate_java_code
from react_agent.custom_tools.mcp_database import load_mongodb_tools, load_toolbox_tools
from react_agent.custom_tools.query_validator import (
    check_query_equivalence,
)
from react_agent.prompts import (
    SYSTEM_PROMPT_EXTRACTION,
    SYSTEM_PROMPT_SCHEMA_INSPECTOR,
    build_system_prompt,
)
from react_agent.state import (
    InputState,
    OutputState,
    State,
)
from react_agent.tools import TOOLS
from react_agent.utils import (
    create_example_for_prompt,
    get_database_mapping_json,
    get_model,
    get_mongodb_standalone_mapping,
    get_neo4j_standalone_mapping,
)
from react_agent.utils.deterministic_checks import (
    _latest_validation_outcome,
)
from react_agent.utils.utils import override_pydantic_model_schema

logger = logging.getLogger(__name__)


class ExtractionOutput(BaseModel):
    """Structured output for identifying user intent from messages.

    This model is used by the initial extraction agent to parse unstructured conversation
    history into a structured representation. It identifies the origin/target frameworks,
    versions, and the raw code blocks intended for translation.
    """

    source_schema_code: Union[list[str], str, None] = Field(
        description="The source schema code. Return as a list of strings (one string per line) to preserve all original newlines and indentation.",
        min_length=1,
    )
    source_query_code: Union[list[str], str, None] = Field(
        description="The source query code. Return as a list of strings (one string per line) to preserve all original newlines and indentation.",
        min_length=1,
    )
    translation_type: TranslationType = Field(
        description="The type of translation to perform.",
    )
    source_target: FrameworkEnum = Field(description="The identified origin framework.")
    source_target_version: Union[str, None] = Field(
        description="The identified origin framework version."
    )
    destination_target: FrameworkEnum = Field(
        description="The identified target framework."
    )
    destination_target_version: Union[str, None] = Field(
        description="The identified target framework version."
    )
    error: Union[str, None] = Field(
        description="The error message if something went wrong with the extraction. For example if source schema or query code is not valid or is not provided. If there is no error, return None.",
        default=None,
    )

    @model_validator(mode="after")
    def join_lists(self):
        """Clean and normalize the fields after validation by joining list inputs into single strings.

        Returns:
            BaseExtractionOutput: The validated and normalized model instance.
        """
        if isinstance(self.source_schema_code, list):
            self.source_schema_code = "\n".join(self.source_schema_code)
        if isinstance(self.source_query_code, list):
            self.source_query_code = "\n".join(self.source_query_code)
        return self


class BaseTranslationOutput(BaseModel):
    """Structured output for the translated schema and/or queries.

    This acts as the base Pydantic schema for the primary translation LLM node. It dynamically
    expands based on whether the `translation_type` is SCHEMA, QUERY, or BOTH. It mandates that
    the agent provide both the translated raw code and fully functional execution harnesses
    (with explicitly declared entry points) for downstream sandbox validation.
    """

    translated_schema_code: Union[list[str], str] = Field(
        min_length=1,
        description="The precise translated schema definitions (entities/models) and context/session/config/bootstrap setup with runtime configs. Plain code only. Do not include usage queries. This corresponds to the example code below `--- Schema and Related Settings ---` comment. See examples in target_validation_schema_code description. Return as a list of strings (one string per line).",
    )
    translated_query_code: Union[list[str], str] = Field(
        min_length=1,
        description=(
            "The precise translated production queries only. Keep query semantics and method shape equivalent to source query "
            "code. Plain code only. Do not include schema definitions, validation harness helpers, or synthetic validator-only "
            "parameters unless they already exist in source query code. This corresponds to the example code methods named `QueryX` or `queryX` inside main entry point class or in own classes. See examples in target_validation_harness_code description. Return as a list of strings (one string per line)."
        ),
    )
    source_validation_schema_code: Union[list[str], str] = Field(
        min_length=1,
        description="Source schema validation code. This should include imports, serialization, runtime config, context/session/config/bootstrap setup, and any other code needed to run the query, but should keep "
        "the Schema and Related Settings logic equivalent to the original source_schema_code (without JSON serialization related annotations). Should be fully valid and runnable code with entrypoint. Include simple one-entity fetch queries to validate each entity (see examples). Do not include source query related code here. See examples. Return as a list of strings (one string per line).",
    )
    source_validation_harness_code: Union[list[str], str] = Field(
        min_length=1,
        description=(
            "The full execution harness code for the SOURCE queries, including the source schema, query methods, any necessary helper classes/records, and the main entry point "
            "that executes the source queries and writes the resulting JSON to the environment path. See examples. Return as a list of strings (one string per line)."
        ),
    )
    source_validation_entry_type_name: str = Field(
        min_length=1,
        description="The name of the main entry point type (e.g., class) in the source validation code. This is needed to run the code and should be declared in the source_validation_schema_code or source_validation_harness_code. Type name should be just the name of the class/type, without namespace or module prefix. Examples: `EFCoreQueryEntrypoint`, `NHibernateQueryEntrypoint`, `DapperQueryEntrypoint`",
    )
    target_validation_schema_code: Union[list[str], str] = Field(
        min_length=1,
        description="Target schema validation code. This should include imports, serialization, runtime config, context/session/config/bootstrap setup, and any other code needed to run the query, but should keep "
        "the Schema and Related Settings logic equivalent to the original translated_schema_code (without JSON serialization related annotations). Should be fully valid and runnable code with entrypoint. Include simple one-entity fetch queries to validate each entity (see examples). Do not include target query related code here. Return as a list of strings (one string per line).",
    )
    target_validation_harness_code: Union[list[str], str] = Field(
        min_length=1,
        description=(
            "The full execution harness code for the translated TARGET queries, including the translated query methods, any necessary helper classes/records, and the main entry point "
            "that executes the target queries and writes the resulting JSON to the environment path. See examples. Return as a list of strings (one string per line)."
        ),
    )
    target_validation_entry_type_name: str = Field(
        min_length=1,
        description="The name of the main entry point type (e.g., class) in the target validation code. This is needed to run the code and should be declared in the source_validation_schema_code or target_validation_harness_code. Type name should be just the name of the class/type, without namespace or module prefix. Examples: `MongoQueryEntrypoint`, `Neo4jQueryEntrypoint`",
    )

    @model_validator(mode="after")
    def check_entrypoint_names(self):
        """Clean, normalize, and validate that the entrypoint class names exist in the generated harness code.

        Returns:
            BaseTranslationOutput: The validated and normalized model instance.

        Raises:
            ValueError: If the entrypoint type name is missing from the harness/schema code.
        """
        # First, join any list fields into strings
        if isinstance(self.translated_schema_code, list):
            self.translated_schema_code = "\n".join(self.translated_schema_code)
        if isinstance(self.translated_query_code, list):
            self.translated_query_code = "\n".join(self.translated_query_code)
        if isinstance(self.source_validation_schema_code, list):
            self.source_validation_schema_code = "\n".join(
                self.source_validation_schema_code
            )
        if isinstance(self.source_validation_harness_code, list):
            self.source_validation_harness_code = "\n".join(
                self.source_validation_harness_code
            )
        if isinstance(self.target_validation_schema_code, list):
            self.target_validation_schema_code = "\n".join(
                self.target_validation_schema_code
            )
        if isinstance(self.target_validation_harness_code, list):
            self.target_validation_harness_code = "\n".join(
                self.target_validation_harness_code
            )

        # Validate that each entrypoint type name is declared in its corresponding code field.
        # Fields stripped by `_create_translation_output_model` (e.g. the harness code during a
        # SCHEMA-only translation) carry the pydantic MISSING sentinel rather than `None`, so a
        # plain `is not None` guard would still fall through to the membership test and raise
        # `TypeError: argument of type 'Sentinel' is not a container or iterable`. Guarding on
        # `isinstance(code, str)` skips both excluded (MISSING) and unset (None) fields, since a
        # populated code field is always a string by this point (lists are joined above).
        errors = []
        entrypoint_checks = (
            ("source_validation_entry_type_name", "source_validation_harness_code"),
            ("source_validation_entry_type_name", "source_validation_schema_code"),
            ("target_validation_entry_type_name", "target_validation_harness_code"),
            ("target_validation_entry_type_name", "target_validation_schema_code"),
        )
        for entry_field, code_field in entrypoint_checks:
            entry_name = getattr(self, entry_field, None)
            code = getattr(self, code_field, None)
            if (
                isinstance(code, str)
                and isinstance(entry_name, str)
                and entry_name not in code
            ):
                errors.append(
                    ValueError(f"{entry_field} must be declared in {code_field}.")
                )
        if errors:
            raise ExceptionGroup("Validation entry type name checks failed", errors)
        return self


async def _create_translation_output_model(state: State) -> type[BaseModel]:
    """Dynamically create a Pydantic model for the translation output based on the input state.

    Since the LLM should not waste tokens generating query code or validation harnesses when
    only schema translation is requested (and vice versa), this function modifies the schema
    of `BaseTranslationOutput` at runtime to exclude irrelevant fields based on the current
    `translation_type` in the state.

    Args:
        state (State): The current graph state containing the `translation_type`.

    Returns:
        type[BaseModel]: A customized Pydantic model class for structured LLM output generation.
    """
    assert state.source_target is not None and state.destination_target is not None
    
    # We dynamically construct the Pydantic schema using the base model's fields as a template.
    base_model_fields = BaseTranslationOutput.model_fields
    output_schema_overrides = {}
    
    # If the user only wants to translate the schema, we strip out query-related fields.
    # This prevents the LLM from hallucinating queries or validation harnesses it doesn't need to write, saving tokens.
    if state.translation_type == TranslationType.SCHEMA:
        output_schema_overrides = {
            "translated_query_code": {
                "annotation": None | MISSING,
                "attributes": {
                    "default": MISSING,
                    "exclude": True,
                },
            },
            "source_validation_schema_code": {
                "attributes": {
                    "description": base_model_fields[
                        "source_validation_schema_code"
                    ].description
                    + await create_example_for_prompt(state.source_target, True)
                    if base_model_fields["source_validation_schema_code"].description
                    else None,
                },
            },
            "source_validation_harness_code": {
                "annotation": None | MISSING,
                "attributes": {
                    "default": MISSING,
                    "exclude": True,
                },
            },
            "target_validation_schema_code": {
                "attributes": {
                    "description": base_model_fields[
                        "target_validation_schema_code"
                    ].description
                    + await create_example_for_prompt(state.destination_target, True)
                    if base_model_fields["target_validation_schema_code"].description
                    else None,
                },
            },
            "target_validation_harness_code": {
                "annotation": None | MISSING,
                "attributes": {
                    "default": MISSING,
                    "exclude": True,
                },
            },
        }
    elif (
        state.translation_type == TranslationType.QUERY
        or state.translation_type == TranslationType.BOTH
    ):
        output_schema_overrides = {
            "source_validation_schema_code": {
                "annotation": None | MISSING,
                "attributes": {
                    "default": MISSING,
                    "exclude": True,
                },
            },
            "source_validation_harness_code": {
                "attributes": {
                    "description": base_model_fields[
                        "source_validation_harness_code"
                    ].description
                    + await create_example_for_prompt(state.source_target, False)
                    if base_model_fields["source_validation_harness_code"].description
                    else None,
                },
            },
            "target_validation_schema_code": {
                "annotation": None | MISSING,
                "attributes": {
                    "default": MISSING,
                    "exclude": True,
                },
            },
            "target_validation_harness_code": {
                "attributes": {
                    "description": base_model_fields[
                        "target_validation_harness_code"
                    ].description
                    + await create_example_for_prompt(state.destination_target, False)
                    if base_model_fields["target_validation_harness_code"].description
                    else None,
                },
            },
        }
    
    # Use Pydantic's `create_model` to generate a completely new class dynamically at runtime.
    # We pass the __base__ class to inherit standard fields, and override specific ones with `MISSING` to exclude them from the LLM JSON schema.
    return override_pydantic_model_schema(
        BaseTranslationOutput, output_schema_overrides, model_name="TranslationOutput"
    )


def is_input_extracted(state: State | ExtractionOutput) -> bool:
    """Check if the necessary structured input has been successfully extracted from conversation.

    Validates that based on the `translation_type`, the corresponding source code fields
    (schema, query, or both) and the framework targets are present.

    Args:
        state (State | ExtractionOutput): The current graph state or extraction output model.

    Returns:
        bool: True if all required fields are present, False otherwise.
    """
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
    """Extract raw source code and targets from recent messages if missing from structured input.

    This node uses a specialized ReAct agent to analyze the conversation history and extract
    the necessary parameters (origin framework, destination framework, and the raw source code
    snippets) needed to begin the translation process. If it fails, it updates the extraction
    loop counter and may terminate the graph if the maximum retry limit is reached.

    Args:
        state (State): The current state of the graph.
        config (RunnableConfig): Configuration parameters for the run.
        runtime (Runtime[Context]): The execution runtime containing context.

    Returns:
        dict[str, Any] | Command: State updates with extracted parameters or a Command to
        terminate the graph on failure.
    """
    # model = await get_model(config, runtime, AvailableModel.OLLAMA_QWEN3_CODER_30B)
    # structured_llm = model.with_structured_output(ExtractionOutput)

    system_prompt = SYSTEM_PROMPT_EXTRACTION.format(
        origin_frameworks=[f.value for f in SourceFramework],
        destination_frameworks=[f.value for f in TargetFramework],
    )

    extraction_agent = create_agent(
        await get_model(
            config, runtime, AvailableModel.EINFRA_QWEN3_CODER_NEXT, temperature=0
        ),
        system_prompt=system_prompt,
        response_format=ProviderStrategy(ExtractionOutput, strict=True),
        middleware=[
            ModelRetryMiddleware(),
            ModelFallbackMiddleware(
                await get_model(
                    config,
                    runtime,
                    AvailableModel.EINFRA_MINI,
                    temperature=0,
                    reasoning=False,
                ),
                await get_model(
                    config,
                    runtime,
                    AvailableModel.OLLAMA_QWEN3_CODER_30B,
                    temperature=0,
                    reasoning=False,
                ),
                await get_model(config, runtime),
            ),
        ],
        # debug=True if os.getenv("DEVELOPMENT") else False,
    )
    
    # We prepopulate a dictionary of already extracted fields so the LLM doesn't redundantly extract 
    # things we already know, speeding up generation and reducing errors in multi-turn conversations.
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
        return {
            "messages": [
                *response["messages"],
                AIMessage(content="Extraction agent did not return structured response.")],
            "extraction_loop_count": state.extraction_loop_count + 1,
        }

    extraction: ExtractionOutput = response["structured_response"]
    if extraction.error:
        return Command(
            update={
                "messages": [
                    *response["messages"],
                    AIMessage(content=extraction.error),
                ],
                "extraction_loop_count": state.extraction_loop_count + 1,
            },
            goto=END,
        )
    
    # Verification gate: ensure the extracted output contains the absolute minimum requirements
    # (framework targets and source code) to actually perform a translation.
    if is_input_extracted(extraction):
        msg = [
            *response["messages"][:-1],
            AIMessage(
                content=f"""Successfully extracted inputs:

```json
{orjson.dumps(extraction.model_dump(mode="json", exclude_unset=True, exclude={"error"}), option=orjson.OPT_INDENT_2).decode('utf-8')}
```
"""
        )]
    else:
        if state.extraction_loop_count >= MAX_EXTRACTION_LOOPS - 1:
            return Command(
                update={
                    "messages": [
                        *response["messages"],
                        AIMessage(content=f"Extraction agent has reached the maximum number of {MAX_EXTRACTION_LOOPS} loops. Please fix your input message or provide the structured input manually."),
                    ]
                },
                goto=END,
            )
        msg = [*response["messages"], AIMessage(content="Extraction agent could not extract inputs.")]
    
    updates = {
        "messages": [
            *msg
        ],
        "extraction_loop_count": state.extraction_loop_count + 1,
        **extraction.model_dump(warnings="error", exclude_unset=True, exclude={"error"}),
    }
    return updates


async def schema_inspection(
    state: State, config: RunnableConfig, runtime: Runtime[Context]
) -> dict[str, Any]:
    """Inspect source and target database schemas using database tools.

    Runs a lightweight ReAct agent equipped with database inspection tools (MCP) to examine
    the relevant database schemas before translation begins. This gathers contextual data
    that is then injected into the main translation prompt to ensure accuracy.

    Args:
        state (State): The current state of the graph.
        config (RunnableConfig): Configuration parameters for the run.
        runtime (Runtime[Context]): The execution runtime containing context.

    Returns:
        dict[str, Any]: State updates containing the extracted `schema_context` string.
    """
    async with (
        load_toolbox_tools() as toolbox_tools,
        load_mongodb_tools() as mongodb_tools,
    ):
        db_tools = toolbox_tools + mongodb_tools
        if not db_tools:
            logger.warning("No database tools available for schema inspection.")
            return {
                "messages": AIMessage(
                    content="No database tools available. Skipping schema inspection."
                ),
            }

        if state.destination_target == FrameworkEnum.JAVA_SPRING_DATA_MONGODB:
            database_mapping = await get_mongodb_standalone_mapping()
        elif state.destination_target == FrameworkEnum.JAVA_SPRING_DATA_NEO4J:
            database_mapping = await get_neo4j_standalone_mapping()
        else:
            database_mapping = await get_database_mapping_json(
                cast(FrameworkEnum, state.destination_target)
            )

        agent = create_agent(
            await get_model(
                config,
                runtime,
                AvailableModel.EINFRA_DEEPSEEK_V4_PRO_THINKING,
                temperature=0,
            ),
            tools=db_tools,
            system_prompt=SYSTEM_PROMPT_SCHEMA_INSPECTOR,
            middleware=[
                ModelRetryMiddleware(),
                ModelFallbackMiddleware(
                    await get_model(
                        config, runtime, AvailableModel.EINFRA_AGENTIC, temperature=0
                    ),
                    await get_model(
                        config, runtime, AvailableModel.OLLAMA_QWEN3_6_27B, temperature=0
                    ),
                    await get_model(config, runtime),
                    # await get_model(
                    #     config, runtime, AvailableModel.OLLAMA_QWEN3_CODER_30B, temperature=0
                    # ),
                ),
                ToolRetryMiddleware(),
                # LLMToolSelectorMiddleware(
                #     model=await get_model(
                #         config, runtime, AvailableModel.EINFRA_QWEN3_5
                #     ),
                # ),
                ContextEditingMiddleware(
                    edits=[
                        # This clear-tool-uses edit prevents the chat context from bloating if the agent
                        # executes hundreds of database inspection queries (common in complex schemas).
                        # It keeps only the last 3 tool invocations in context if the token trigger is exceeded.
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

        message = f"""Inspect the database schemas relevant to translating code from {cast(FrameworkEnum, state.source_target).value}{f" {state.source_target_version}" if state.source_target_version else ""} to {cast(FrameworkEnum, state.destination_target).value}{f" {state.destination_target_version}" if state.destination_target_version else ""}.

{f"Mapping from {database_mapping['databases']['source']} to {database_mapping['databases']['destination']}:\n<database_mapping>\n{orjson.dumps(database_mapping).decode('utf-8')}\n</database_mapping>\n" if database_mapping else ""}

Source code being translated:
{f"<schema_code>\n{state.source_schema_code}\n</schema_code>\n" if state.source_schema_code else ""}
{f"<query_code>\n{state.source_query_code}\n</query_code>\n" if state.source_query_code else ""}"""

        response = None
        try:
            response = await agent.ainvoke(
                {"messages": [HumanMessage(content=message)]}
            )
            # Extract the final assistant response as schema context
            msg = response["messages"][-1] if response and "messages" in response and len(response["messages"]) > 0 else None
            schema_summary = ""
            if isinstance(msg, AIMessage):
                schema_summary = "".join(
                    block.get("text", "") 
                    for block in msg.content_blocks
                    if block.get("type") == "text"
                ) or ""
            return {
                "schema_context": str(schema_summary),
                "messages": [
                    *response["messages"][:-1],
                    AIMessage(
                        content=f"Schema inspection completed successfully:\n\n{schema_summary}"
                    )
                ],
            }
        except Exception:
            logger.warning("Schema inspection failed.", exc_info=True)
            return {
                "messages": [
                    *(response["messages"] if response and "messages" in response else []),
                    AIMessage(
                        content="Schema inspection failed. Could not extract schema context."
                    ),
                ]
            }


async def translation_agent(
    state: State, config: RunnableConfig, runtime: Runtime[Context]
) -> dict[str, Any]:
    """Use a ReAct agent to perform translation and validation loops natively.

    Combines static tools (validators, fallback docs) with dynamically loaded
    database and documentation MCP tools.

    Warning:
        This node is DEPRECATED in favor of `generate_translation_node` coupled with
        explicit state machine nodes for validation and evaluation, which provides
        better determinism and observability.

    Args:
        state (State): The current state of the graph.
        config (RunnableConfig): Configuration parameters for the run.
        runtime (Runtime[Context]): The execution runtime containing context.

    Returns:
        dict[str, Any]: State updates containing the translation output.
    """
    model = await get_model(config, runtime, temperature=0, reasoning=False)

    all_tools = TOOLS

    system_prompt = await build_system_prompt(state)

    # Create the ReAct agent
    agent = create_agent(
        model,
        tools=all_tools,
        response_format=ProviderStrategy(BaseTranslationOutput, strict=True),
        system_prompt=system_prompt,
        middleware=[
            ModelRetryMiddleware(),
            ModelFallbackMiddleware(
                await get_model(
                    config,
                    runtime,
                    AvailableModel.EINFRA_THINKER,
                    temperature=0,
                    reasoning=False,
                ),
                await get_model(
                    config, runtime, AvailableModel.OLLAMA_QWEN3_6_27B, temperature=0
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

    message = f"""Translate the following Source Code ({"schema/query" if cast(TranslationType, state.translation_type).value == TranslationType.BOTH else cast(TranslationType, state.translation_type).value}) from {cast(FrameworkEnum, state.source_target).value}{f" {state.source_target_version}" if state.source_target_version else ""} to {cast(FrameworkEnum, state.destination_target).value}{f" {state.destination_target_version}" if state.destination_target_version else ""}.
{f"\nDatabase Schema Context:\n{state.schema_context}\n" if state.schema_context else ""}---
Source Code:
{f"<source_schema_code>\n{state.source_schema_code.strip()}\n</source_schema_code>" if state.source_schema_code else ""}{f"\n<source_query_code>\n{state.source_query_code.strip()}\n</source_query_code>" if state.source_query_code else ""}
"""

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
        }

    # Extract structured output if available
    output = cast(BaseTranslationOutput, response["structured_response"])
    updates: dict[str, Any] = {
        "messages": response["messages"],
        "translation_messages": response["messages"],
    }
    updates.update(output.model_dump(warnings="error", exclude_unset=True))

    return updates


async def generate_translation_node(
    state: State, config: RunnableConfig, runtime: Runtime[Context]
) -> dict[str, Any]:
    """Deterministically generate the translation using structured LLM output via a React Agent without tools.

    This node acts as the core "Generation" step in the iterative translation loop.
    It takes the extracted source code, the schema context, and the previous translation
    attempts/feedback (if any) and generates the translated code and execution harnesses
    using a strongly-typed Pydantic model (`TranslationOutput`).

    Args:
        state (State): The current state of the graph.
        config (RunnableConfig): Configuration parameters for the run.
        runtime (Runtime[Context]): The execution runtime containing context.

    Returns:
        dict[str, Any]: State updates containing the generated translation outputs.
    """
    TranslationOutput = await _create_translation_output_model(state)

    model = await get_model(config, runtime, temperature=0)

    system_prompt = await build_system_prompt(state)

    message = f"""Translate the following Source Code ({"schema/query" if state.translation_type and state.translation_type.value == TranslationType.BOTH else (state.translation_type.value if state.translation_type else "schema")}) from {state.source_target.value if state.source_target else "Unknown"}{f" {state.source_target_version}" if state.source_target_version else ""} to {state.destination_target.value if state.destination_target else "Unknown"}{f" {state.destination_target_version}" if state.destination_target_version else ""}.
{f"\nDatabase Schema Context:\n{state.schema_context}\n" if state.schema_context else ""}---
Source Code:
{f"<source_schema_code>\n{state.source_schema_code}\n</source_schema_code>" if state.source_schema_code else ""}{f"\n<source_query_code>\n{state.source_query_code}\n</source_query_code>" if state.source_query_code else ""}
"""

    agent = create_agent(
        model,
        response_format=ProviderStrategy(TranslationOutput, strict=True),
        system_prompt=system_prompt,
        middleware=[
            ModelRetryMiddleware(),
            ModelFallbackMiddleware(
                await get_model(
                    config, runtime, AvailableModel.EINFRA_THINKER, temperature=0
                ),
                await get_model(
                    config, runtime, AvailableModel.OLLAMA_QWEN3_6_27B, temperature=0
                ),
            ),
            ToolRetryMiddleware(),
        ],
    )

    # Invoke the agent
    response = await agent.ainvoke(
        {
            "messages": [*state.translation_messages]
            if len(state.translation_messages) > 0
            else [HumanMessage(content=message)]
        }
    )

    updates: dict[str, Any] = {
        "translation_loop_count": state.translation_loop_count + 1,
    }

    if "structured_response" not in response:
        logger.error("LLM did not return TranslationOutput properly.")
        messages = [
            *response["messages"],
            AIMessage(
                content="Failed to generate translation. LLM did not return structured response in expected format."
            ),
        ]
        raise Exception("\n".join([str(msg.content) for msg in messages]))
        # updates["messages"] = messages
        # updates["translation_messages"] = messages
        # return updates

    output = response["structured_response"]
    updates.update(output.model_dump(warnings="error", exclude_unset=True))

    msg = [*response["messages"][:-1],
           AIMessage(content=f"""Translation generated successfully. Here's the translated code:
                    
```json
{orjson.dumps(output.model_dump(mode="json", exclude_unset=False), option=orjson.OPT_INDENT_2).decode('utf-8')}
```
""")]
    updates["messages"] = msg
    updates["translation_messages"] = msg

    return updates


class HumanInterventionResponse(BaseModel):
    """Pydantic model representing the feedback and decision from a human-in-the-loop intervention.

    Attributes:
        decision: The logical decision, either "accept" to commit the translation or "reject" to loop back with feedback.
        feedback: Text description or critique describing necessary adjustments.
    """

    decision: Literal["accept", "reject"]
    feedback: str


async def human_intervention_node(state: State):
    """Pause the graph execution to request human-in-the-loop (HITL) feedback.

    This node interrupts the state machine, surfacing the current translation code and validation
    results (including deep diffs) to the user via the `interrupt` LangGraph API. The user can
    either 'accept' the translation to terminate successfully, or 'reject' it with feedback to
    trigger another generation loop.

    Args:
        state (State): The current state of the graph.

    Returns:
        dict[str, Any] | Command: State updates appending the user's feedback to messages,
        or a Command to end the graph if accepted.
    """
    response = interrupt(
        {
            "instruction": "Review the current state, generated translation and validation results. Decide if the translation is correct or if another translation attempt is needed and provide feedback on what needs to be improved in the next attempt.",
            "state": {
                "translated_query_code": state.translated_query_code,
                "translated_schema_code": state.translated_schema_code,
                "explanation_message": state.explanation_message,
                "query_equivalence_deep_diffs": state.query_equivalence_deep_diffs,
            },
        }
    )
    output = HumanInterventionResponse.model_validate(response)

    if output.decision == "reject":
        if output.feedback:
            feedback_message = HumanMessage(
                content=f"User rejected the translation with feedback:\n{output.feedback}"
            )
        else:
            feedback_message = HumanMessage(
                content="User rejected the translation without providing feedback."
            )
        return {
            "messages": feedback_message,
            "translation_messages": feedback_message,
        }
    else:
        feedback_message = HumanMessage(content="Translation was accepted.")
        return Command(
            update={
                "messages": feedback_message,
                "translation_messages": feedback_message,
            },
            goto=END,
        )


def prep_schema_validation(state: State) -> dict[str, Any]:
    """Inject ToolCalls into the message history to trigger schema compilation validation.

    Prepares the state for the `validate_schema_node` by appending an AIMessage with explicitly
    defined tool calls (`validate_dotnet_code` or `validate_java_code`) containing the target
    schema harness code.

    Args:
        state (State): The current state of the graph.

    Returns:
        dict[str, Any]: State updates with the injected validation tool calls.
    """
    tool_calls = []
    target = state.destination_target
    if target and target.value in DotnetFramework:
        tool_calls.append(
            {
                "name": "validate_dotnet_code",
                "args": {
                    "source_code": state.target_validation_harness_code.strip()
                    if state.target_validation_harness_code
                    else "",
                    "framework": target.value,
                },
                "id": "schema_val_1",
                "type": "tool_call",
            }
        )
    elif target and target.value in JavaFramework:
        tool_calls.append(
            {
                "name": "validate_java_code",
                "args": {
                    "source_code": state.target_validation_harness_code.strip()
                    if state.target_validation_harness_code
                    else "",
                    "framework": target.value,
                    "entry_type_name": state.target_validation_entry_type_name
                    or "ValidationEntryPoint",
                },
                "id": "schema_val_1",
                "type": "tool_call",
            }
        )
    message = AIMessage(
        content="Commencing validation of translated schema and related settings...",
        tool_calls=tool_calls,
    )
    return {
        "messages": message,
        "translation_messages": message,
    }


def prep_query_validation(state: State) -> dict[str, Any]:
    """Inject ToolCalls into the message history for parallel source and target query validation.

    Prepares the state for the `validate_query_node` by appending an AIMessage with multiple
    tool calls to run both the source validation harness and the target validation harness in
    sandbox environments concurrently.

    Args:
        state (State): The current state of the graph.

    Returns:
        dict[str, Any]: State updates with the injected validation tool calls.
    """
    tool_calls = []
    assert state.source_target is not None and state.destination_target is not None

    # Source validation
    if state.source_target in [
        FrameworkEnum.DOTNET_EFCORE,
        FrameworkEnum.DOTNET_DAPPER,
    ]:
        tool_calls.append(
            {
                "name": "validate_dotnet_code",
                "args": {
                    "source_code": state.source_validation_harness_code or "",
                    "framework": state.source_target.value,
                },
                "id": "source_query_val",
                "type": "tool_call",
            }
        )
    elif state.source_target in [
        FrameworkEnum.JAVA_SPRING_DATA_MONGODB,
        FrameworkEnum.JAVA_SPRING_DATA_NEO4J,
    ]:
        tool_calls.append(
            {
                "name": "validate_java_code",
                "args": {
                    "source_code": state.source_validation_harness_code or "",
                    "framework": state.source_target.value,
                    "entry_type_name": state.source_validation_entry_type_name
                    or "ValidationEntryPoint",
                },
                "id": "source_query_val",
                "type": "tool_call",
            }
        )

    # Target validation
    if state.destination_target in [
        FrameworkEnum.DOTNET_EFCORE,
        FrameworkEnum.DOTNET_DAPPER,
    ]:
        tool_calls.append(
            {
                "name": "validate_dotnet_code",
                "args": {
                    "source_code": state.target_validation_harness_code or "",
                    "framework": state.destination_target.value,
                },
                "id": "target_query_val",
                "type": "tool_call",
            }
        )
    elif state.destination_target in [
        FrameworkEnum.JAVA_SPRING_DATA_MONGODB,
        FrameworkEnum.JAVA_SPRING_DATA_NEO4J,
    ]:
        tool_calls.append(
            {
                "name": "validate_java_code",
                "args": {
                    "source_code": state.target_validation_harness_code or "",
                    "framework": state.destination_target.value,
                    "entry_type_name": state.target_validation_entry_type_name
                    or "ValidationEntryPoint",
                },
                "id": "target_query_val",
                "type": "tool_call",
            }
        )

    message = AIMessage(
        content="Commencing parallel validation of source and target queries...",
        tool_calls=tool_calls,
    )
    return {"messages": message, "translation_messages": message}


def prep_query_equivalence(state: State) -> dict[str, Any]:
    """Inject a ToolCall into the message history to run the query equivalence checker.

    Prepares the state for the `check_query_equivalence_node`. It parses the JSON validation
    outputs from the previous query validation step and issues a tool call for `DeepDiff`
    equivalence testing.

    Args:
        state (State): The current state of the graph.

    Returns:
        dict[str, Any]: State updates with the injected equivalence tool call.
    """
    last_msgs = (
        state.translation_messages[-2:] if len(state.translation_messages) >= 2 else []
    )
    src_str = str(last_msgs[0].content) if len(last_msgs) >= 2 else ""
    tgt_str = str(last_msgs[1].content) if len(last_msgs) >= 2 else ""

    tool_calls = [
        {
            "name": "check_query_equivalence",
            "args": {
                "source_validation_output": src_str,
                "target_validation_output": tgt_str,
            },
            "id": "query_equiv_1",
            "type": "tool_call",
        }
    ]
    message = AIMessage(
        content="Commencing query equivalence check between source and target queries...",
        tool_calls=tool_calls,
    )
    return {"messages": message, "translation_messages": message}


async def custom_tool_node_wrapper(
    request: ToolCallRequest,
    execute: Callable[[ToolCallRequest], Awaitable[Union[ToolMessage, Command]]],
) -> Union[ToolMessage, Command]:
    """Wrap tool execution to provide robust retries against transient infrastructure errors.

    Used by `ToolNode` to intercept and retry tool calls (like Daytona sandbox provisioning)
    with an exponential backoff. If max retries are exceeded, it gracefully injects an error
    ToolMessage into the state rather than crashing the graph.

    Args:
        request (ToolCallRequest): The requested tool call payload.
        execute (Callable): The underlying ToolNode execution function.

    Returns:
        Union[ToolMessage, Command]: The result of the tool execution or an error ToolMessage.
    """
    max_retries = 4
    base_delay = 1.0

    for attempt in range(1, max_retries + 1):
        try:
            # We await the underlying ToolNode execution.
            # If a transient infrastructure error occurs (e.g. Docker timeout), it will raise here.
            res = await execute(request)
            if isinstance(res, ToolMessage):
                return Command(
                    update={
                        "messages": res,
                        "translation_messages": res,
                    }
                )
            elif isinstance(res, Command):
                if res.update and "messages" in res.update:
                    messages = res.update.get("messages", [])
                    return Command(
                        update={
                            **res.update,
                            "messages": messages,
                            "translation_messages": messages,
                        }
                    )
                return res
            else:
                return res
        except Exception as e:
            if attempt == max_retries:
                logger.error(
                    f"Tool {request.tool_call['name']} failed after {max_retries} attempts: {e}"
                )
                # Instead of crashing the whole graph (which would lose state), we gracefully capture
                # the exception as a structured ToolMessage. The graph will evaluate this string output
                # and loop back to the generation node with the error context so the LLM can try to fix it.
                if request.tool_call["name"] in [
                    "validate_dotnet_code",
                    "validate_java_code",
                ]:
                    return ToolMessage(
                        content=f"[Validation Failed] Error: {e}",
                        tool_call_id=request.tool_call["id"],
                        name=request.tool_call["name"],
                    )
                elif request.tool_call["name"] == "check_query_equivalence":
                    return ToolMessage(
                        content=f"[Query Equivalence Failed] Error: {e}",
                        tool_call_id=request.tool_call["id"],
                        name=request.tool_call["name"],
                    )
                else:
                    return ToolMessage(
                        content=f"[Tool Error] {type(e).__name__}: {e}",
                        tool_call_id=request.tool_call["id"],
                        name=request.tool_call["name"],
                    )

            delay = base_delay * (2 ** (attempt - 1))
            logger.warning(
                f"Tool {request.tool_call['name']} threw infrastructure exception {type(e).__name__}. Retrying in {delay} seconds... (Attempt {attempt}/{max_retries})",
                exc_info=True,
            )
            await asyncio.sleep(delay)
            continue

    return ToolMessage(
        content=f"[Tool Error] Failed after {max_retries} attempts. Please check the infrastructure and try again later. ToolCallRequest: {request.tool_call}",
        tool_call_id=request.tool_call["id"],
        name=request.tool_call["name"],
    )


validate_schema_node = ToolNode(
    [validate_dotnet_code, validate_java_code],
    name="validate_schema_node",
    awrap_tool_call=custom_tool_node_wrapper,
)

validate_query_node = ToolNode(
    [validate_dotnet_code, validate_java_code],
    name="validate_query_node",
    awrap_tool_call=custom_tool_node_wrapper,
)

check_query_equivalence_node = ToolNode(
    [check_query_equivalence],
    name="check_query_equivalence_node",
    awrap_tool_call=custom_tool_node_wrapper,
)


def route_post_query_validation(
    state: State,
) -> Literal["prep_query_equivalence", "evaluation_node"]:
    """Determine the next state transition after parallel query validation.

    If both the source and target query validations completed successfully (indicated by
    '[Validation Passed]' in their tool output), it routes to `prep_query_equivalence`.
    Otherwise, it skips equivalence checking and routes directly to the `evaluation_node`
    to analyze the validation failures.

    Args:
        state (State): The current state of the graph.

    Returns:
        Literal["prep_query_equivalence", "evaluation_node"]: The name of the next node.
    """
    last_msgs = (
        state.translation_messages[-2:] if len(state.translation_messages) >= 2 else []
    )
    if len(last_msgs) >= 2 and state.translation_type in [
        TranslationType.QUERY,
        TranslationType.BOTH,
    ]:
        src_str = str(last_msgs[0].content)
        tgt_str = str(last_msgs[1].content)
        
        # We strictly require both validators to report "Validation Passed]". 
        # If one fails (e.g., C# compiled but Java threw an exception), we must route to 'evaluation_node'
        # so the LLM can read the compiler output and fix the syntax errors.
        if "Validation Passed]" in src_str and "Validation Passed]" in tgt_str:
            return "prep_query_equivalence"
    return "evaluation_node"


class EvaluationOutput(BaseModel):
    """Pydantic model representing the LLM evaluation outcome for translation acceptance.

    Attributes:
        decision: The logical decision, either ACCEPT to complete the process or REJECT to loop back for correction.
        explanation: Detailed textual reasoning explaining the decision, citing specific equivalence or compiler errors.
    """

    decision: Literal["ACCEPT", "REJECT"] = Field(
        description="Decision whether to accept or reject the translation."
    )
    explanation: str = Field(description="Explanation for the decision.", min_length=1)


async def evaluation_node(
    state: State, config: RunnableConfig, runtime: Runtime[Context]
) -> dict[str, Any]:
    """Evaluate validation and equivalence testing results to decide on translation acceptance.

    This node uses a specialized evaluation LLM to act as a judge. It reviews the compiler
    outputs from the sandboxes and the JSON DeepDiff equivalence results. Based on this, it
    generates a structured `EvaluationOutput` deciding whether to 'ACCEPT' the translation
    or 'REJECT' it (which triggers another generation iteration with feedback).

    Args:
        state (State): The current state of the graph.
        config (RunnableConfig): Configuration parameters for the run.
        runtime (Runtime[Context]): The execution runtime containing context.

    Returns:
        dict[str, Any]: State updates containing the evaluation decision and explanation.
    """
    model = await get_model(config, runtime, AvailableModel.EINFRA_KIMI_K2_6)

    last_msgs = [str(msg) for msg in state.translation_messages[-4:]]

    prompt = f"""Evaluate the following validation results for a schema/query translation.
Based on the validation output and DeepDiff equivalence results, decide if the translation is ACCEPTABLE or if it should be REJECTED and retried.

<validation_results>
{"\n".join(last_msgs)}
</validation_results>

Is the translation logically equivalent and syntactically valid? Provide your reasoning and output ACCEPT or REJECT.
"""
    agent = create_agent(
        model,
        response_format=ProviderStrategy(EvaluationOutput, strict=True),
        middleware=[
            ModelRetryMiddleware(),
            ModelFallbackMiddleware(
                await get_model(config, runtime, AvailableModel.EINFRA_THINKER),
                await get_model(config, runtime, AvailableModel.OLLAMA_QWEN3_6_27B),
                await get_model(config, runtime)
            ),
            ToolRetryMiddleware(),
        ],
    )

    response = None
    response = await agent.ainvoke({"messages": [HumanMessage(content=prompt)]})
    messages = response["messages"] if response and response.get("messages") else []
    if "structured_response" not in response:
        messages = [
            *messages,
            AIMessage(
                content="[Structured Output Error] Evaluation may have failed: LLM did not return structured response in expected format. Check translated code manually."
            ),
        ]
        return {
            "messages": messages,
            "translation_messages": messages,
        }

    assert state.translation_type is not None and state.destination_target is not None
    output: EvaluationOutput = response["structured_response"]
    messages = cast(list[BaseMessage], response.get("messages"))[:-1] if response and response.get("messages") else []
    if (output.decision == "ACCEPT"):
        markdown_lang = FRAMEWORK_TO_LANGUAGE_TYPE[state.destination_target].value
        messages = messages + [
            AIMessage(content=f"""The translation is accepted. Here is the final translated code:

Translated schema:
```{markdown_lang}
{state.translated_schema_code if state.translation_type in [TranslationType.SCHEMA, TranslationType.BOTH] else ""}
```

{f"Translated query:\n```{markdown_lang}\n{state.translated_query_code}\n```\n" if state.translation_type in [TranslationType.QUERY, TranslationType.BOTH] else ""}
Evaluation:
{output.explanation}
""")
        ]
    else:
        messages = messages + [
            AIMessage(content=f"[{output.decision}] {output.explanation}"),
        ]
        
    return {
        "explanation_message": output.explanation,
        "messages": messages,
        "translation_messages": messages,
    }


def route_post_evaluation(
    state: State,
) -> Literal["generate_translation_node", "human_intervention_node", "__end__"]:
    """Determine the next state transition after evaluation.

    If the evaluation was rejected or failed, it routes back to `generate_translation_node`
    to retry. If the maximum translation loop count is reached, it routes to
    `human_intervention_node` instead. If accepted, it routes to `__end__`.

    Args:
        state (State): The current state of the graph.

    Returns:
        Literal["generate_translation_node", "human_intervention_node", "__end__"]: The next node.
    """
    last_msg = (
        state.translation_messages[-1].content if state.translation_messages else ""
    )
    if (
        "[REJECT]" in last_msg
        or "[Evaluation Failed]" in last_msg
        or "[Evaluation Error]" in last_msg
        or "[Structured Output Error]" in last_msg
    ):
        # We check the translation_loop_count to prevent infinite loops of failing compilation.
        # If [Structured Output Error] occured in this last evaluation stage, we don't want to run expensive translation again, we let the user decide.
        # If it exceeds the maximum (typically 3), we route to 'human_intervention_node' to let the user fix the issue manually.
        if state.translation_loop_count >= MAX_TRANSLATION_LOOPS or "[Structured Output Error]" in last_msg:
            return "human_intervention_node"
        return "generate_translation_node"
    return "__end__"


def should_extract_input(state: State) -> Literal["schema_inspection", "extract_input", "__end__"]:
    """Determine the next state transition during the initial extraction phase.

    Checks if all required structured inputs have been successfully parsed. If so, it routes
    to `schema_inspection`. If not, it routes back to `extract_input` up to a maximum
    retry limit, after which it routes to `__end__` to terminate the graph gracefully.

    Args:
        state (State): The current state of the graph.

    Returns:
        Literal["schema_inspection", "extract_input", "__end__"]: The next node.
    """
    if is_input_extracted(state):
        return "schema_inspection"
    elif state.extraction_loop_count < MAX_EXTRACTION_LOOPS:
        return "extract_input"
    else:
        logger.error(f"Failed to extract input after {MAX_EXTRACTION_LOOPS} attempts.")
        return "__end__"


def route_post_translation(
    state: State,
) -> Literal["prep_schema_validation", "prep_query_validation"]:
    """Determine the next validation state transition after code generation.

    Routes to `prep_schema_validation` if the translation type is SCHEMA. For QUERY or BOTH
    translation types, it routes to `prep_query_validation`.

    Args:
        state (State): The current state of the graph.

    Returns:
        Literal["prep_schema_validation", "prep_query_validation"]: The next node.
    """
    if state.translation_type == TranslationType.SCHEMA:
        return "prep_schema_validation"
    return "prep_query_validation"


def route_post_schema_validation(
    state: State,
) -> Literal[
    "prep_query_validation",
    "generate_translation_node",
    "human_intervention_node",
    "__end__",
]:
    """Determine the next state transition after schema validation.

    If schema compilation failed, it routes back to `generate_translation_node` (or
    `human_intervention_node` if max retries exceeded) without proceeding further.
    If it passed and the translation type is BOTH, it routes to `prep_query_validation`.
    Otherwise, it terminates execution (`__end__`).

    Args:
        state (State): The current state of the graph.

    Returns:
        Literal["prep_query_validation", "generate_translation_node", "human_intervention_node", "__end__"]: The next node.
    """
    last_msg = (
        state.translation_messages[-1].content if state.translation_messages else ""
    )
    if "Failed]" in last_msg:
        if state.translation_loop_count >= MAX_TRANSLATION_LOOPS:
            return "human_intervention_node"
        return "generate_translation_node"

    if state.translation_type == TranslationType.BOTH:
        return "prep_query_validation"
    return "__end__"


# Observability

# structlog.stdlib.recreate_defaults(log_level=None)
# structlog.configure(
#     processors=[
#         structlog.dev.ConsoleRenderer(
#             exception_formatter=structlog.dev.RichTracebackFormatter(show_locals=False)
#         ),
#     ],
# )

# langfuse = get_client()

# # Verify connection
# if langfuse.auth_check():
#     logger.info("Langfuse client is authenticated and ready!")
# else:
#     logger.error(
#         "Langfuse authentication failed. Please check your credentials and host."
#     )

# # Initialize Langfuse CallbackHandler for Langchain (tracing)
# langfuse_handler = CallbackHandler()

logfire.configure(
    # sampling=logfire.SamplingOptions.level_or_duration(background_rate=0.3),
    console=False,
    scrubbing=False,
)
# logfire.install_auto_tracing(modules=['react_agent'], min_duration=0.01, check_imported_modules='ignore')
logfire.instrument_openai(suppress_other_instrumentation=False)
logfire.instrument_requests(capture_all=True)
logfire.instrument_httpx(capture_all=True)
logfire.instrument_aiohttp_client(capture_all=True)
# logging.basicConfig(handlers=[logfire.LogfireLoggingHandler()])

# Build the graph

# checkpointer = InMemorySaver()
# store = InMemoryStore()
# cache = InMemoryCache()
# redis_cache = RedisCache(
#     redis_url="redis://localhost:6389" if os.getenv("DEVELOPMENT") else (os.getenv("REDIS_URI", "redis://langgraph-redis:6379")),
#     prefix="llm_cache",
#     # redis_client=redis_client
# )
# set_llm_cache(redis_cache)

node_cache = InMemoryCache()
# if os.getenv("DEVELOPMENT"):
#     node_cache = InMemoryCache()
# else:
#     from langchain_core.globals import set_llm_cache
#     from langchain_redis import RedisCache
#     from langgraph.cache.redis import RedisCache as NodeRedisCache

#     # from langchain_community.cache import AsyncRedisCache as NodeRedisCache
#     from redis import Redis

#     redis_client = Redis.from_url(os.getenv("REDIS_URI", "redis://localhost:6379"))
#     # Node Cache for caching graph states (not LLM calls)
#     node_cache = NodeRedisCache(redis_client)

#     # Global LLM Cache for caching LLM calls
#     redis_cache = RedisCache(
#         redis_url=os.getenv("REDIS_URI", "redis://localhost:6379"),
#         prefix="langgraph:llm_cache:",
#         redis_client=redis_client,
#     )
#     set_llm_cache(redis_cache)

builder = StateGraph(
    State,
    input_schema=InputState,
    output_schema=OutputState,
    context_schema=Context,
)

retry_policy = RetryPolicy(
    max_attempts=3,
)

builder.add_node(
    extract_input,  # type: ignore
    cache_policy=CachePolicy(),
    retry_policy=retry_policy,
)
builder.add_node(
    schema_inspection,  # type: ignore
    cache_policy=CachePolicy(ttl=900),
    retry_policy=retry_policy,
)
builder.add_node(
    generate_translation_node,  # type: ignore
    cache_policy=CachePolicy(),
    retry_policy=retry_policy,
)
builder.add_node(
    human_intervention_node,  # type: ignore
    retry_policy=retry_policy,
)

builder.add_node(
    prep_schema_validation,
    retry_policy=retry_policy,
)
builder.add_node(
    prep_query_validation,
    retry_policy=retry_policy,
)
builder.add_node(
    validate_schema_node,
)
builder.add_node(
    validate_query_node,
)
builder.add_node(
    prep_query_equivalence,
    retry_policy=retry_policy,
)
builder.add_node(
    check_query_equivalence_node,
)
builder.add_node(
    evaluation_node,  # type: ignore
    retry_policy=retry_policy,
)

builder.add_conditional_edges(START, should_extract_input)
builder.add_conditional_edges("extract_input", should_extract_input)
builder.add_edge("schema_inspection", "generate_translation_node")

builder.add_conditional_edges("generate_translation_node", route_post_translation)
builder.add_edge("prep_schema_validation", "validate_schema_node")
builder.add_conditional_edges("validate_schema_node", route_post_schema_validation)

builder.add_edge("prep_query_validation", "validate_query_node")
builder.add_conditional_edges("validate_query_node", route_post_query_validation)
builder.add_edge("prep_query_equivalence", "check_query_equivalence_node")
builder.add_edge("check_query_equivalence_node", "evaluation_node")

builder.add_conditional_edges("evaluation_node", route_post_evaluation)
builder.add_edge("human_intervention_node", "generate_translation_node")

graph = builder.compile(
    name="Universal Object Mapping Translator",
    # checkpointer=checkpointer,
    cache=node_cache,
    # debug=True if os.getenv("DEVELOPMENT") else False,
)

# logger.info(graph.get_graph().draw_mermaid())
