# pyright: ignore[reportArgumentType]
# ty:ignore[invalid-argument-type]
# ty:ignore[invalid-type-form]

"""Define the Universal Object Mapping orchestrator graph."""
import json
import logging
import os
from datetime import UTC, datetime
from typing import Any, Literal, Union, cast

import logfire
import orjson
from dotenv import find_dotenv, load_dotenv
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
from langchain_core.callbacks import CallbackManager
from langchain_core.globals import set_llm_cache
from langchain_core.messages import HumanMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_redis import RedisCache
from langfuse import get_client
from langfuse.langchain import CallbackHandler
from langgraph.cache.memory import InMemoryCache
from langgraph.errors import NodeError
from langgraph.graph import START, StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.runtime import Runtime
from langgraph.types import CachePolicy, Command, RetryPolicy
from pydantic import BaseModel, Field, model_validator
from pydantic.experimental.missing_sentinel import MISSING

from react_agent.constants import (
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
from react_agent.custom_tools.mcp_database import load_database_tools
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
    """Structured output for identifying user intent from messages."""

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
    source_target: FrameworkEnum = Field(
        description="The identified origin framework."
    )
    source_target_version: Union[str, None] = Field(
        description="The identified origin framework version."
    )
    destination_target: FrameworkEnum = Field(
        description="The identified target framework."
    )
    destination_target_version: Union[str, None] = Field(
        description="The identified target framework version."
    )
    
    @model_validator(mode='after')
    def join_lists(self):
        if isinstance(self.source_schema_code, list):
            self.source_schema_code = "\n".join(self.source_schema_code)
        if isinstance(self.source_query_code, list):
            self.source_query_code = "\n".join(self.source_query_code)
        return self


class BaseTranslationOutput(BaseModel):
    """Structured output for the translated schema and/or queries."""

    translated_schema_code: Union[list[str], str] = Field(
        min_length=1,
        description="The precise translated schema definitions (entities/models) and context/session/config/bootstrap setup with runtime configs. Plain code only. Do not include usage queries. This corresponds to the example code below `--- Schema and Related Settings ---` comment. See examples in target_validation_schema_code description. Return as a list of strings (one string per line)."
    )
    translated_query_code: Union[list[str], str] = Field(
        min_length=1,
        description=(
            "The precise translated production queries only. Keep query semantics and method shape equivalent to source query "
            "code. Plain code only. Do not include schema definitions, validation harness helpers, or synthetic validator-only "
            "parameters unless they already exist in source query code. This corresponds to the example code methods named `QueryX` or `queryX` inside main entry point class or in own classes. See examples in target_validation_harness_code description. Return as a list of strings (one string per line)."
        )
    )
    source_validation_schema_code: Union[list[str], str] = Field(
        min_length=1,
        description="Source schema validation code. This should include imports, serialization, runtime config, context/session/config/bootstrap setup, and any other code needed to run the query, but should keep "
        "the Schema and Related Settings logic equivalent to the original source_schema_code (without JSON serialization related annotations). Should be fully valid and runnable code with entrypoint. Include simple one-entity fetch queries to validate each entity (see examples). Do not include source query related code here. See examples. Return as a list of strings (one string per line)."
    )
    source_validation_harness_code: Union[list[str], str] = Field(
        min_length=1,
        description=(
            "The full execution harness code for the SOURCE queries, including the source schema, query methods, any necessary helper classes/records, and the main entry point "
            "that executes the source queries and writes the resulting JSON to the environment path. See examples. Return as a list of strings (one string per line)."
        )
    )
    source_validation_entry_type_name: str = Field(
        min_length=1,
        description="The name of the main entry point type (e.g., class) in the source validation code. This is needed to run the code and should be declared in the source_validation_schema_code or source_validation_harness_code. Type name should be just the name of the class/type, without namespace or module prefix. Examples: `EFCoreQueryEntrypoint`, `NHibernateQueryEntrypoint`, `DapperQueryEntrypoint`"
    )
    target_validation_schema_code: Union[list[str], str] = Field(
        min_length=1,
        description="Target schema validation code. This should include imports, serialization, runtime config, context/session/config/bootstrap setup, and any other code needed to run the query, but should keep "
        "the Schema and Related Settings logic equivalent to the original translated_schema_code (without JSON serialization related annotations). Should be fully valid and runnable code with entrypoint. Include simple one-entity fetch queries to validate each entity (see examples). Do not include target query related code here. Return as a list of strings (one string per line)."
    )
    target_validation_harness_code: Union[list[str], str] = Field(
        min_length=1,
        description=(
            "The full execution harness code for the translated TARGET queries, including the translated query methods, any necessary helper classes/records, and the main entry point "
            "that executes the target queries and writes the resulting JSON to the environment path. See examples. Return as a list of strings (one string per line)."
        )
    )
    target_validation_entry_type_name: str = Field(
        min_length=1,
        description="The name of the main entry point type (e.g., class) in the target validation code. This is needed to run the code and should be declared in the source_validation_schema_code or target_validation_harness_code. Type name should be just the name of the class/type, without namespace or module prefix. Examples: `MongoQueryEntrypoint`, `Neo4jQueryEntrypoint`"
    )
    
    @model_validator(mode='after')
    def check_entrypoint_names(self):
        # First, join any list fields into strings
        if isinstance(self.translated_schema_code, list):
            self.translated_schema_code = "\n".join(self.translated_schema_code)
        if isinstance(self.translated_query_code, list):
            self.translated_query_code = "\n".join(self.translated_query_code)
        if isinstance(self.source_validation_schema_code, list):
            self.source_validation_schema_code = "\n".join(self.source_validation_schema_code)
        if isinstance(self.source_validation_harness_code, list):
            self.source_validation_harness_code = "\n".join(self.source_validation_harness_code)
        if isinstance(self.target_validation_schema_code, list):
            self.target_validation_schema_code = "\n".join(self.target_validation_schema_code)
        if isinstance(self.target_validation_harness_code, list):
            self.target_validation_harness_code = "\n".join(self.target_validation_harness_code)

        errors = []
        if "source_validation_harness_code" in self.__dict__:
            if self.source_validation_harness_code is not None and self.source_validation_entry_type_name not in self.source_validation_harness_code:
                errors.append(ValueError("source_validation_entry_type_name must be declared in source_validation_harness_code."))
        if "source_validation_schema_code" in self.__dict__:
            if self.source_validation_schema_code is not None and self.source_validation_entry_type_name not in self.source_validation_schema_code:
                errors.append(ValueError("source_validation_entry_type_name must be declared in source_validation_schema_code."))
        if "target_validation_harness_code" in self.__dict__:
            if self.target_validation_harness_code is not None and self.target_validation_entry_type_name not in self.target_validation_harness_code:
                errors.append(ValueError("target_validation_entry_type_name must be declared in target_validation_harness_code."))
        if "target_validation_schema_code" in self.__dict__:
            if self.target_validation_schema_code is not None and self.target_validation_entry_type_name not in self.target_validation_schema_code:
                errors.append(ValueError("target_validation_entry_type_name must be declared in target_validation_schema_code."))
        if errors:
            raise ExceptionGroup("Validation entry type name checks failed", errors)
        return self
    

async def _create_translation_output_model(state: State) -> type[BaseModel]:
    """Dynamically create a Pydantic model for the translation output based on the input model."""
    assert state.source_target is not None and state.destination_target is not None
    base_model_fields = BaseTranslationOutput.model_fields
    output_schema_overrides = {}
    if state.translation_type == TranslationType.SCHEMA:
        output_schema_overrides = {
            "translated_query_code": {
                "annotation": None | MISSING,
                "attributes": {
                    "default": MISSING,
                    "exclude": True,
                }
            },
            "source_validation_schema_code": {
                "annotation": Union[list[str], str],
                "attributes": {
                    "description": base_model_fields["source_validation_schema_code"].description + 
                    await create_example_for_prompt(state.source_target, True) 
                    if base_model_fields["source_validation_schema_code"].description else None,
                }
            },
            "source_validation_harness_code": {
                "annotation": None | MISSING,
                "attributes": {
                    "default": MISSING,
                    "exclude": True,
                }
            },
            "target_validation_schema_code": {
                "annotation": Union[list[str], str],
                "attributes": {
                    "description": base_model_fields["target_validation_schema_code"].description + 
                    await create_example_for_prompt(state.destination_target, True) 
                    if base_model_fields["target_validation_schema_code"].description else None,
                }
            },
            "target_validation_harness_code": {
                "annotation": None | MISSING,
                "attributes": {
                    "default": MISSING,
                    "exclude": True,
                }
            }
        }
    elif state.translation_type == TranslationType.QUERY or state.translation_type == TranslationType.BOTH:
        output_schema_overrides = {
            "source_validation_schema_code": {
                "annotation": None | MISSING,
                "attributes": {
                    "default": MISSING,
                    "exclude": True,
                }
            },
            "source_validation_harness_code": {
                "annotation": Union[list[str], str],
                "attributes": {
                    "description": base_model_fields["source_validation_harness_code"].description + 
                    await create_example_for_prompt(state.source_target, False) 
                    if base_model_fields["source_validation_harness_code"].description else None,
                }
            },
            "target_validation_schema_code": {
                "annotation": None | MISSING,
                "attributes": {
                    "default": MISSING,
                    "exclude": True,
                }
            },
            "target_validation_harness_code": {
                "annotation": Union[list[str], str],
                "attributes": {
                    "description": base_model_fields["target_validation_harness_code"].description + 
                    await create_example_for_prompt(state.destination_target, False) 
                    if base_model_fields["target_validation_harness_code"].description else None,
                }
            }
        }
    return override_pydantic_model_schema(BaseTranslationOutput, output_schema_overrides, model_name="TranslationOutput")


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
        origin_frameworks=[f.value for f in SourceFramework],
        destination_frameworks=[f.value for f in TargetFramework],
    )

    extraction_agent = create_agent(
        await get_model(config, runtime, AvailableModel.EINFRA_QWEN3_CODER_NEXT, temperature=0),
        system_prompt=system_prompt,
        response_format=ProviderStrategy(ExtractionOutput, strict=True),
        middleware=[
            ModelRetryMiddleware(),
            ModelFallbackMiddleware(
                await get_model(config, runtime, AvailableModel.EINFRA_MINI, temperature=0, reasoning=False),
                await get_model(config, runtime, AvailableModel.OLLAMA_QWEN3_CODER_30B, temperature=0, reasoning=False),
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

        model = await get_model(config, runtime, AvailableModel.EINFRA_DEEPSEEK_V4_PRO, temperature=0.2, reasoning=False)

        if (state.destination_target == FrameworkEnum.JAVA_SPRING_DATA_MONGODB):
            database_mapping = await get_mongodb_standalone_mapping()
        elif (state.destination_target == FrameworkEnum.JAVA_SPRING_DATA_NEO4J):
            database_mapping = await get_neo4j_standalone_mapping()
        else:
            database_mapping = await get_database_mapping_json(cast(FrameworkEnum, state.destination_target))

        agent = create_agent(
            model,
            tools=db_tools,
            system_prompt=SYSTEM_PROMPT_SCHEMA_INSPECTOR,
            middleware=[
                ModelRetryMiddleware(),
                ModelFallbackMiddleware(
                    await get_model(config, runtime, AvailableModel.EINFRA_DEEPSEEK_V4_PRO_THINKING, temperature=0),
                    await get_model(config, runtime, AvailableModel.EINFRA_AGENTIC, temperature=0),
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

{f"Mapping from {database_mapping['source']} to {database_mapping['destination']}:\n<database_mapping>\n{orjson.dumps(database_mapping).decode("utf-8")}\n</database_mapping>\n" if database_mapping else ""}

Source code being translated:
{f"<schema_code>\n{state.source_schema_code}\n</schema_code>\n" if state.source_schema_code else ""}
{f"<query_code>\n{state.source_query_code}\n</query_code>\n" if state.source_query_code else ""}"""

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
                await get_model(config, runtime, AvailableModel.EINFRA_THINKER, temperature=0, reasoning=False),
                await get_model(config, runtime, AvailableModel.OLLAMA_QWEN3_6_27B, temperature=0),
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

    strategies = "\n".join([r.get("strategy", "") for r in state.council_responses])

    message = f"""Translate the following Source Code ({"schema/query" if cast(TranslationType, state.translation_type).value == TranslationType.BOTH else cast(TranslationType, state.translation_type).value}) from {cast(FrameworkEnum, state.source_target).value}{f" {state.source_target_version}" if state.source_target_version else ""} to {cast(FrameworkEnum, state.destination_target).value}{f" {state.destination_target_version}" if state.destination_target_version else ""}.
{f"\nStrategies to consider:\n{strategies}\n" if strategies else ""}{f"\nDatabase Schema Context:\n{state.schema_context}\n" if state.schema_context else ""}---
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
    """Deterministically generate the translation using structured LLM output via a React Agent without tools."""
    TranslationOutput = await _create_translation_output_model(state)
    
    model = await get_model(config, runtime, temperature=0, reasoning=False)

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
                await get_model(config, runtime, AvailableModel.EINFRA_THINKER, temperature=0, reasoning=False),
                await get_model(config, runtime, AvailableModel.OLLAMA_QWEN3_6_27B, temperature=0),
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
        logger.warning("LLM did not return TranslationOutput properly.")
        return updates

    output = response["structured_response"]
    updates.update(output.model_dump(warnings="error", exclude_unset=True))

    updates["translation_messages"] = AIMessage(
        content="Generated translation. Commencing deterministic validation..."
    )

    return updates


async def human_intervention_node(
    state: State, config: RunnableConfig, runtime: Runtime[Context]
) -> dict[str, Any]:
    """A dummy node that acts as a pausing point when loop threshold is reached."""
    return {}


def prep_schema_validation(state: State) -> dict[str, Any]:
    """Inject ToolCalls into state for schema validation."""
    tool_calls = []
    target = state.destination_target
    if target and target.value in DotnetFramework:
        tool_calls.append({
            "name": "validate_dotnet_code",
            "args": {
                "source_code": state.target_validation_harness_code.strip() if state.target_validation_harness_code else "",
                "framework": target.value,
            },
            "id": "schema_val_1",
            "type": "tool_call"
        })
    elif target and target.value in JavaFramework:
        tool_calls.append({
            "name": "validate_java_code",
            "args": {
                "source_code": state.target_validation_harness_code.strip() if state.target_validation_harness_code else "",
                "framework": target.value,
                "entry_type_name": state.target_validation_entry_type_name or "ValidationEntryPoint",
            },
            "id": "schema_val_1",
            "type": "tool_call"
        })
    return {"translation_messages": [AIMessage(content="", tool_calls=tool_calls)]}


def prep_query_validation(state: State) -> dict[str, Any]:
    """Inject ToolCalls into state for parallel query validation."""
    tool_calls = []

    # Source validation
    if state.source_target in [FrameworkEnum.DOTNET_EFCORE, FrameworkEnum.DOTNET_DAPPER]:
        tool_calls.append({
            "name": "validate_dotnet_code",
            "args": {
                "source_code": state.source_validation_harness_code or "",
                "framework": state.source_target.value,
            },
            "id": "source_query_val",
            "type": "tool_call"
        })
    elif state.source_target in [FrameworkEnum.JAVA_SPRING_DATA_MONGODB, FrameworkEnum.JAVA_SPRING_DATA_NEO4J]:
        tool_calls.append({
            "name": "validate_java_code",
            "args": {
                "source_code": state.source_validation_harness_code or "",
                "framework": state.source_target.value,
                "entry_type_name": state.source_validation_entry_type_name or "ValidationEntryPoint",
            },
            "id": "source_query_val",
            "type": "tool_call"
        })

    # Target validation
    if state.destination_target in [FrameworkEnum.DOTNET_EFCORE, FrameworkEnum.DOTNET_DAPPER]:
        tool_calls.append({
            "name": "validate_dotnet_code",
            "args": {
                "source_code": state.target_validation_harness_code or "",
                "framework": state.destination_target.value,
            },
            "id": "target_query_val",
            "type": "tool_call"
        })
    elif state.destination_target in [FrameworkEnum.JAVA_SPRING_DATA_MONGODB, FrameworkEnum.JAVA_SPRING_DATA_NEO4J]:
        tool_calls.append({
            "name": "validate_java_code",
            "args": {
                "source_code": state.target_validation_harness_code or "",
                "framework": state.destination_target.value,
                "entry_type_name": state.target_validation_entry_type_name or "ValidationEntryPoint",
            },
            "id": "target_query_val",
            "type": "tool_call"
        })

    return {"translation_messages": [AIMessage(content="", tool_calls=tool_calls)]}


def prep_query_equivalence(state: State) -> dict[str, Any]:
    """Inject ToolCall for check_query_equivalence if both validations passed."""
    last_msgs = state.translation_messages[-2:] if len(state.translation_messages) >= 2 else []
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
            "type": "tool_call"
        }
    ]
    return {"translation_messages": [AIMessage(content="", tool_calls=tool_calls)]}


def validation_error_handler(e: Exception) -> str:
    """Format exceptions from tools as validation failures."""
    return f"[Validation Failed] Error: {e}"


def equivalence_error_handler(e: Exception) -> str:
    """Format exceptions from equivalence tools as failures."""
    return f"[Query Equivalence Failed] Error: {e}"


validate_schema_node = ToolNode(
    [validate_dotnet_code, validate_java_code], 
    name="validate_schema_node", 
    messages_key="translation_messages",
    handle_tool_errors=validation_error_handler,
)

validate_query_node = ToolNode(
    [validate_dotnet_code, validate_java_code], 
    name="validate_query_node", 
    messages_key="translation_messages",
    handle_tool_errors=validation_error_handler,
)

check_query_equivalence_node = ToolNode(
    [check_query_equivalence], 
    name="check_query_equivalence_node", 
    messages_key="translation_messages",
    handle_tool_errors=equivalence_error_handler,
)


def route_post_query_validation(state: State) -> Literal["prep_query_equivalence", "evaluation_node"]:
    """Route to equivalence check if validations passed, else skip to evaluation."""
    last_msgs = state.translation_messages[-2:] if len(state.translation_messages) >= 2 else []
    if len(last_msgs) >= 2 and state.translation_type in [TranslationType.QUERY, TranslationType.BOTH]:
        src_str = str(last_msgs[0].content)
        tgt_str = str(last_msgs[1].content)
        if "Validation Passed]" in src_str and "Validation Passed]" in tgt_str:
            return "prep_query_equivalence"
    return "evaluation_node"


class EvaluationOutput(BaseModel):
    decision: Literal["ACCEPT", "REJECT"] = Field(
        description="Decision whether to accept or reject the translation."
    )
    explanation: str = Field(description="Explanation for the decision.", min_length=1)


async def evaluation_node(
    state: State, config: RunnableConfig, runtime: Runtime[Context]
) -> dict[str, Any]:
    """Evaluate validation outputs and deepdiff results to decide on translation acceptance."""
    model = await get_model(config, runtime, AvailableModel.EINFRA_KIMI_K2_6)

    last_msgs_str = [
        msg.content if isinstance(msg.content, str) else str(msg.content)
        for msg in state.translation_messages[-4:]
    ]

    prompt = f"""Evaluate the following validation results for a schema/query translation.
Based on the validation output and DeepDiff equivalence results, decide if the translation is ACCEPTABLE or if it should be REJECTED and retried.

Validation Results:
{chr(10).join(last_msgs_str)}
Is the translation logically equivalent and syntactically valid? Provide your reasoning and output ACCEPT or REJECT.
"""
    agent = create_agent(
        model,
        response_format=ProviderStrategy(EvaluationOutput, strict=True),
        middleware=[
            ModelRetryMiddleware(),
            ModelFallbackMiddleware(
                await get_model(config, runtime, AvailableModel.EINFRA_THINKER),
                # await get_model(config, runtime, AvailableModel.OLLAMA_QWEN3_CODER_30B),
            ),
            ToolRetryMiddleware(),
        ],
    )

    try:
        response = await agent.ainvoke({"messages": [HumanMessage(content=prompt)]})
        if "structured_response" not in response:
            return {
                "translation_messages": [
                    HumanMessage(
                        content="[Evaluation Failed] Could not parse LLM evaluation decision."
                    )
                ]
            }

        output = response["structured_response"]

        return {
            "explanation_message": output.explanation,
            "translation_messages": [HumanMessage(content=f"[{output.decision}] {output.explanation}")]
        }
    except Exception as e:
        logger.error(f"Evaluation node failed: {e}")
        return {
            "translation_messages": [HumanMessage(content=f"[Evaluation Error] {e}")]
        }


def route_post_evaluation(
    state: State,
) -> Literal["generate_translation_node", "human_intervention_node", "__end__"]:
    """Route from evaluation to the next node."""
    last_msg = (
        state.translation_messages[-1].content if state.translation_messages else ""
    )
    if (
        "[REJECT]" in last_msg
        or "[Evaluation Failed]" in last_msg
        or "[Evaluation Error]" in last_msg
    ):
        if state.translation_loop_count >= 3:
            return "human_intervention_node"
        return "generate_translation_node"
    return "__end__"


def should_extract_input(state: State) -> Literal["schema_inspection", "extract_input"]:
    """Route execution to extraction until mandatory input fields are present."""
    if is_input_extracted(state):
        return "schema_inspection"
    else:
        return "extract_input"


def route_post_translation(
    state: State,
) -> Literal["prep_schema_validation", "prep_query_validation"]:
    """Route from translation generator to the first applicable validation prep node."""
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
    """Route from validate_schema to validate_query prep or handle validation failure."""
    last_msg = (
        state.translation_messages[-1].content if state.translation_messages else ""
    )
    if "Failed]" in last_msg:
        if state.translation_loop_count >= 3:
            return "human_intervention_node"
        return "generate_translation_node"

    if state.translation_type == TranslationType.BOTH:
        return "prep_query_validation"
    return "__end__"


# Observability
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
logging.basicConfig(handlers=[logfire.LogfireLoggingHandler()])

# Build the graph

# checkpointer = InMemorySaver()
# store = InMemoryStore()
cache = InMemoryCache()
# redis_cache = RedisCache(
#     redis_url="redis://localhost:6389/1" if os.getenv("DEVELOPMENT") else (os.getenv("REDIS_URI", "redis://langgraph-redis:6379").rstrip("/") + "/1"),
#     prefix="llm_cache",
#     # redis_client=redis_client
# )
# set_llm_cache(redis_cache)

# if not os.getenv("DEVELOPMENT"):
#     from langchain_redis import RedisCache
#     # from langchain_community.cache import AsyncRedisCache as NodeRedisCache
#     # from redis.asyncio import Redis
    
#     # redis_client = Redis.from_url(os.getenv("REDIS_URI", "redis://localhost:6379/1"))

#     # # Node Cache for caching graph states (not LLM calls)
#     # cache = NodeRedisCache(redis_=redis_client)

#     # Global LLM Cache for caching LLM calls
#     redis_cache = RedisCache(
#         redis_url=os.getenv("REDIS_URI", "redis://localhost:6379").rstrip("/") + "/1",
#         prefix="llm_cache",
#         # redis_client=redis_client
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
    extract_input,
    cache_policy=CachePolicy(),
    retry_policy=retry_policy,
)
builder.add_node(
    schema_inspection,
    cache_policy=CachePolicy(ttl=900),
    retry_policy=retry_policy,
)
builder.add_node(
    generate_translation_node,
    cache_policy=CachePolicy(),
    retry_policy=retry_policy,
)
builder.add_node(
    human_intervention_node,
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
    retry_policy=retry_policy,
)
builder.add_node(
    validate_query_node,
    retry_policy=retry_policy,
)
builder.add_node(
    prep_query_equivalence,
    retry_policy=retry_policy,
)
builder.add_node(
    check_query_equivalence_node,
    retry_policy=retry_policy,
)
builder.add_node(
    evaluation_node,
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
    interrupt_before=["human_intervention_node"],
    # checkpointer=checkpointer,
    # store=store,
    cache=cache,
    # debug=True if os.getenv("DEVELOPMENT") else False,
)

# logger.info(graph.get_graph().draw_mermaid())
