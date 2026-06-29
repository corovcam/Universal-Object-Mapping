# pyright: ignore[reportArgumentType]
# ty:ignore[invalid-argument-type]
# ty:ignore[invalid-type-form]

"""Define the Universal Object Mapping orchestrator graph."""
import asyncio
import json
import logging
import re
from datetime import UTC, datetime
from typing import Any, Awaitable, Callable, Literal, Union, cast

import logfire
import orjson
from langchain.agents import create_agent
from langchain.agents.middleware import (
    AgentMiddleware,
    ClearToolUsesEdit,
    ContextEditingMiddleware,
    ModelFallbackMiddleware,
    ModelRetryMiddleware,
    SummarizationMiddleware,
    ToolRetryMiddleware,
)
from langchain.agents.middleware.types import ModelRequest, ModelResponse
from langchain.agents.structured_output import (
    ProviderStrategy,
    StructuredOutputValidationError,
)
from langchain.messages import AIMessage
from langchain_core.messages import (
    AnyMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.runnables import RunnableConfig
from langchain_daytona import DaytonaSandbox
from langgraph.cache.memory import InMemoryCache
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.prebuilt.tool_node import ToolCallRequest
from langgraph.runtime import Runtime
from langgraph.types import (
    CachePolicy,
    Command,
    RetryPolicy,
    default_retry_on,
    interrupt,
)
from pydantic import BaseModel, Field, ValidationError, model_validator
from pydantic.experimental.missing_sentinel import MISSING

from react_agent.constants import (
    FRAMEWORK_TO_LANGUAGE_TYPE,
    MAX_EXTRACTION_LOOPS,
    MAX_STRUCTURED_OUTPUT_RETRIES,
    MAX_TRANSLATION_LOOPS,
    AvailableModel,
    DotnetFramework,
    FrameworkEnum,
    JavaFramework,
    SandboxType,
    SourceFramework,
    TargetFramework,
    TranslationType,
)
from react_agent.context import Context
from react_agent.custom_tools.docs_search import load_docs_mcp_tools
from react_agent.custom_tools.dotnet_validator import validate_dotnet_code
from react_agent.custom_tools.java_validator import validate_java_code
from react_agent.custom_tools.mcp_database import load_mongodb_tools, load_toolbox_tools
from react_agent.custom_tools.query_validator import (
    check_query_equivalence,
)
from react_agent.custom_tools.sandbox_tools import ValidationSandbox
from react_agent.prompts import (
    SYSTEM_PROMPT_EXTRACTION,
    SYSTEM_PROMPT_FINALIZE,
    SYSTEM_PROMPT_SCHEMA_INSPECTOR,
    build_system_prompt,
    build_translation_user_message,
    eval_cache_bust_header,
)
from react_agent.state import (
    InputState,
    OutputState,
    State,
)
from react_agent.tools import TOOLS, search
from react_agent.translation_draft import (
    TranslationDraftMiddleware,
    build_save_translation_tool,
    required_draft_fields,
)
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
from react_agent.utils.harness_assembler import assemble_validation_code
from react_agent.utils.utils import get_snippet_content, override_pydantic_model_schema

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
            ValueError: If any entrypoint type name is missing from its harness/schema code.
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
                errors.append(f"{entry_field} must be declared in {code_field}.")
        if errors:
            # Raise a single ValueError (not an ExceptionGroup) so pydantic wraps it into a
            # ValidationError whose string carries every message. ExceptionGroup's str only
            # reports a sub-exception count, so the actionable detail was being lost when the
            # error was surfaced to the model for self-correction (see
            # StructuredOutputRetryMiddleware).
            raise ValueError("\n".join(errors))
        return self


def _format_structured_output_error(exc: StructuredOutputValidationError) -> str:
    """Render a concise, model-actionable description of a structured-output failure.

    Prefers the underlying pydantic `ValidationError` (extracting just the `loc` + `msg` of each
    error, without echoing the model's potentially huge/truncated input) and otherwise falls back
    to the raw source error string (e.g. JSON decode failures from output truncation).

    Args:
        exc (StructuredOutputValidationError): The error raised by the provider strategy when the
            native structured response failed to parse or validate.

    Returns:
        str: A newline-separated, human/LLM-readable summary of what went wrong.
    """
    source: BaseException = getattr(exc, "source", None) or exc
    cause = getattr(source, "__cause__", None)
    if isinstance(cause, ValidationError):
        lines = []
        for err in cause.errors(include_url=False, include_input=False):
            loc = ".".join(str(part) for part in err.get("loc", ()))
            msg = err.get("msg", "")
            lines.append(f"{loc}: {msg}" if loc else msg)
        if lines:
            return "\n".join(lines)
    return str(source)


#: Content-block types that carry a reasoning model's *thinking* trace. These must NOT be sent back
#: to the provider on later turns: they break LangChain's string-delta merge (so the AIMessage
#: content stays a list of dicts), and litellm then drops them, leaving `content` as a list of bare
#: strings — which OpenAI-compatible servers (sglang/vLLM) reject with a 400 (content list elements
#: must be objects with a `type`, or content must be a plain string).
_REASONING_BLOCK_TYPES = frozenset(
    {"thinking", "reasoning", "reasoning_content", "redacted_thinking"}
)


def _flatten_message_content(message: AnyMessage) -> AnyMessage:
    """Collapse a reasoning model's list-form AIMessage content into a plain text string.

    A streamed reasoning turn accumulates into ``content`` as a list mixing bare text deltas
    (e.g. ``""``, ``"\\n\\n"``) with ``{"type": "thinking", ...}`` dicts. Re-sending that list on
    the next turn 400s (see ``_REASONING_BLOCK_TYPES``). We rebuild a single string from the text
    parts (bare strings + ``{"type": "text"}`` blocks) and drop the thinking blocks. Tool calls live
    on ``message.tool_calls``, not in ``content``, so an emptied-out content with tool calls stays
    valid. Only ``AIMessage`` list content is touched; everything else is returned unchanged.

    Args:
        message (BaseMessage): A message from the outgoing request.

    Returns:
        BaseMessage: The original message, or a copy whose list content is flattened to a string.
    """
    if not isinstance(message, AIMessage) or not isinstance(message.content, list):
        return message
    text_parts: list[str] = []
    for block in message.content:
        if isinstance(block, str):
            text_parts.append(block)
        elif isinstance(block, dict):
            btype = block.get("type")
            if btype == "text":
                text_parts.append(block.get("text", ""))
            elif btype in _REASONING_BLOCK_TYPES:
                continue  # never replay thinking back to the provider
            # any other block type (e.g. tool_use) is represented on .tool_calls; drop from content
    return message.model_copy(update={"content": "".join(text_parts)})


def _sanitize_request_messages(messages: list[AnyMessage]) -> list[AnyMessage]:
    """Apply :func:`_flatten_message_content` to every message in an outgoing request."""
    return [_flatten_message_content(m) for m in messages]


class ReasoningContentSanitizerMiddleware(AgentMiddleware):
    """Flatten reasoning model list-content messages before each provider call.

    Reasoning models (qwen3.5 / the EINFRA thinker, served via sglang/vLLM through litellm) return
    an AIMessage whose ``content`` is a list of text deltas + ``thinking`` blocks. Sent back
    verbatim on the next agent turn, litellm strips the thinking blocks and leaves a list of bare
    strings, which the server rejects with a 400. This middleware rewrites the request's messages so
    those AIMessages carry a plain text string instead — keeping reasoning ON without poisoning the
    history.

    It is placed LAST in each agent's middleware list (innermost, closest to the model) so it runs
    after message-transforming middleware (summarization, context editing) and re-applies on every
    ``ModelFallbackMiddleware`` retry — otherwise a fallback model would just hit the same 400.
    """

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        """Flatten list-form reasoning content in the request, then delegate to the handler."""
        return await handler(
            request.override(messages=_sanitize_request_messages(request.messages))
        )

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """Sync counterpart of :meth:`awrap_model_call`."""
        return handler(
            request.override(messages=_sanitize_request_messages(request.messages))
        )


class StructuredOutputRetryMiddleware(AgentMiddleware):
    """Retry provider-native structured output on the SAME model, feeding the error back.

    `ProviderStrategy` is faster and more reliable than `ToolStrategy` for strict structured
    output, but (unlike `ToolStrategy.handle_errors`) it offers no retry hook: when the generated
    JSON fails schema or `@model_validator` checks the agent raises
    `StructuredOutputValidationError` and gives up. Plain `ModelRetryMiddleware` would re-call the
    model with the *identical* prompt; this middleware instead appends a concise description of the
    failure and re-invokes, so the model can self-correct — mirroring `ToolStrategy`'s error loop
    while keeping native strict structured output.

    Only `StructuredOutputValidationError` is retried, and always against the *same* model:
    validation failures mean the model got the schema wrong, not that the model is unavailable, so
    escalating to a (typically weaker) fallback rarely helps and burns the token/latency budget. To
    guarantee that, on exhaustion this middleware returns a normal `ModelResponse` carrying an
    `ERROR_PREFIX` message instead of raising — a raised exception would be caught by the
    surrounding `ModelFallbackMiddleware` and bounced to the fallback models. Genuine failures
    (transient API errors, outages) raise other exception types, which propagate untouched to
    `ModelFallbackMiddleware` as intended.
    """

    #: Prefix marking a surfaced structured-output failure in the message stream. Downstream
    #: handling (and the UI) key on this to recognise a generation failure.
    ERROR_PREFIX = "[Structured Output Error]"

    def __init__(self, *, max_retries: int = MAX_STRUCTURED_OUTPUT_RETRIES) -> None:
        """Initialize the middleware.

        Args:
            max_retries (int): Maximum number of *additional* attempts after the initial call.
        """
        super().__init__()
        self.max_retries = max_retries
        self.tools = []

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        """Invoke the model, retrying structured-output failures (same model) with error feedback.

        Args:
            request (ModelRequest): The model request (messages, model, response format, ...).
            handler (Callable): Executes the model + structured-output parsing; may be called
                multiple times.

        Returns:
            ModelResponse: The first successful response, or — once retries are exhausted — a
            response whose single message is a surfaced ``ERROR_PREFIX`` error (never raised, so
            fallback models are not triggered for validation failures).
        """
        last_exc: StructuredOutputValidationError | None = None
        for attempt in range(self.max_retries + 1):
            if attempt == 0 or last_exc is None:
                current_request = request
            else:
                # Rebuild from the original messages + a single latest-error note rather than
                # accumulating feedback (and the bulky invalid output) every round, which would
                # grow context and make output truncation on capped models more likely.
                feedback = HumanMessage(
                    content=(
                        "Your previous response failed structured output validation:\n"
                        f"{_format_structured_output_error(last_exc)}\n\n"
                        "Regenerate the complete structured output, fixing exactly these issues. "
                        "Return all required fields."
                    )
                )
                current_request = request.override(
                    messages=[*request.messages, feedback]
                )
            try:
                return await handler(current_request)
            except StructuredOutputValidationError as exc:
                last_exc = exc
                logger.warning(
                    "Structured output validation failed (attempt %d/%d): %s",
                    attempt + 1,
                    self.max_retries + 1,
                    _format_structured_output_error(exc),
                )
        assert last_exc is not None
        attempts = self.max_retries + 1
        logger.error(
            "Structured output validation failed after %d attempts; surfacing error to the user.",
            attempts,
        )
        return ModelResponse(
            result=[
                AIMessage(
                    content=(
                        f"{self.ERROR_PREFIX} The model could not produce a valid structured "
                        f"response after {attempts} attempts. Validation errors:\n"
                        f"{_format_structured_output_error(last_exc)}"
                    )
                )
            ]
        )


def _retry_on_excluding_structured_output(exc: Exception) -> bool:
    """Node retry predicate that never re-runs the whole node on a structured-output failure.

    `StructuredOutputRetryMiddleware` already retries the model (with feedback) and surfaces a
    failure message rather than raising, so a `StructuredOutputValidationError` reaching the node
    boundary should not trigger an expensive full-node re-run. Everything else defers to LangGraph's
    default retry behavior (transient connection/5xx errors, etc.).

    Args:
        exc (Exception): The exception raised by the node.

    Returns:
        bool: Whether LangGraph should retry the node.
    """
    if isinstance(exc, StructuredOutputValidationError):
        return False
    return default_retry_on(exc)


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

    system_prompt = eval_cache_bust_header(runtime, config) + SYSTEM_PROMPT_EXTRACTION.format(
        origin_frameworks=[f.value for f in SourceFramework],
        destination_frameworks=[f.value for f in TargetFramework],
    )

    extraction_agent = create_agent(
        await get_model(
            config, runtime, AvailableModel.EINFRA_QWEN3_5_122B, temperature=0
        ),
        system_prompt=system_prompt,
        response_format=ProviderStrategy(ExtractionOutput, strict=True),
        middleware=[
            ModelRetryMiddleware(),
            ModelFallbackMiddleware(
                await get_model(
                    config,
                    runtime,
                    AvailableModel.EINFRA_GPT_OSS_120B,
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
            # Innermost (last): flatten reasoning list-content so re-sent turns don't 400.
            ReasoningContentSanitizerMiddleware(),
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
            ),
            tools=db_tools,
            system_prompt=eval_cache_bust_header(runtime, config)
            + SYSTEM_PROMPT_SCHEMA_INSPECTOR.format(system_time=datetime.now(tz=UTC).isoformat()),
            middleware=[
                ModelRetryMiddleware(),
                ModelFallbackMiddleware(
                    await get_model(
                        config, runtime, AvailableModel.EINFRA_KIMI_K2_7
                    ),
                    await get_model(
                        config, runtime, AvailableModel.OLLAMA_QWEN3_6_27B
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
                # Innermost (last): flatten reasoning list-content so re-sent turns don't 400.
                ReasoningContentSanitizerMiddleware(),
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

    system_prompt = eval_cache_bust_header(runtime, config) + await build_system_prompt(state)

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
                    AvailableModel.EINFRA_DEEPSEEK_V4_PRO_THINKING,
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
            # Innermost (last): flatten reasoning list-content so re-sent turns don't 400.
            ReasoningContentSanitizerMiddleware(),
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


# Verdict/control tokens that must never sit in the model's *generation* context: with a low
# temperature the model can latch onto them and copy the literal string into a code field (the
# observed `"translated_schema_code": "REJECTED"` degenerate-output failure). We neutralize them in
# the distilled feedback so the failure detail is preserved without the attractor token.
_CONTROL_TOKEN_RE = re.compile(
    r"\[?\b(?:REJECTED|REJECT|ACCEPTED|ACCEPT|Validation Failed|Structured Output Error)\b\]?",
    re.IGNORECASE,
)


def _quarantine_control_tokens(text: str) -> str:
    """Replace bare verdict/control tokens with a neutral description so they can't be copied."""
    return _CONTROL_TOKEN_RE.sub("(prior verdict)", text)


def _distill_translation_feedback(state: State) -> str:
    """Build a plain-text feedback note for a *regeneration* attempt.

    On the first attempt (`translation_loop_count <= 0`) there is no feedback. On a retry we must
    NOT replay `state.translation_messages` directly: those carry `AIMessage`s with `tool_calls`
    for tools (validators, save_*) that are re-bound on each fresh agent, and replaying orphaned
    tool_calls is rejected by strict sglang/OpenAI-compatible backends. Instead we distill the
    salient failure signal — the evaluator explanation, the most recent tool outputs, and the
    query-equivalence diffs — into a single human-readable note.

    Args:
        state (State): The current graph state.

    Returns:
        str: A feedback note, or "" if this is the first attempt.
    """
    if state.translation_loop_count <= 0:
        return ""

    parts: list[str] = [
        "Your previous translation attempt was rejected. Fix the issues below, then call "
        "save_translation again with every required field filled."
    ]
    if state.explanation_message:
        parts.append(
            f"\nEvaluation / failure detail:\n{_quarantine_control_tokens(state.explanation_message)}"
        )

    # Pull the text content of the last few ToolMessages (compiler/run output) without replaying
    # any AIMessage tool_calls.
    recent_tool_texts: list[str] = []
    for msg in reversed(list(state.translation_messages)):
        if isinstance(msg, ToolMessage) and msg.content:
            recent_tool_texts.append(str(msg.content))
        if len(recent_tool_texts) >= 4:
            break
    if recent_tool_texts:
        parts.append(
            "\nRecent tool output (most recent last):\n"
            + _quarantine_control_tokens("\n---\n".join(reversed(recent_tool_texts)))
        )

    if state.query_equivalence_deep_diffs:
        parts.append(
            "\nQuery equivalence diffs (source vs target must match):\n"
            + orjson.dumps(
                state.query_equivalence_deep_diffs, option=orjson.OPT_INDENT_2
            ).decode("utf-8")
        )
    return "\n".join(parts)


async def generate_translation_node(
    state: State, config: RunnableConfig, runtime: Runtime[Context]
) -> dict[str, Any]:
    """Generate the translation with a tool-using ReAct agent that saves artifacts to state.

    This node is the core "Generation" step of the iterative translation loop. Rather than asking
    the model for one giant strict-JSON structured blob (which the new e-INFRA sglang models do not
    honor), it runs a ReAct agent with *every* tool at its disposal — research (docs/web), database
    inspection (MCP), sandbox execution + validators, and a set of gated `save_*` tools. The agent
    persists each translation artifact individually by calling the corresponding `save_*` tool
    *during* its run; those writes land on `TranslationDraftState` channels (declared by
    `TranslationDraftMiddleware`) and are harvested back into the graph `State` here.

    No structured output is requested. If the agent finishes without saving every required artifact,
    the node surfaces a `[Structured Output Error]`-marked message so `route_post_translation`
    diverts to `human_intervention_node` instead of pushing empty code into validation.

    Args:
        state (State): The current state of the graph.
        config (RunnableConfig): Configuration parameters for the run.
        runtime (Runtime[Context]): The execution runtime containing context.

    Returns:
        dict[str, Any]: State updates with the harvested translation artifacts (or a surfaced
        failure).
    """
    translation_type = state.translation_type or TranslationType.BOTH

    is_schema = translation_type == TranslationType.SCHEMA
    source_fw = state.source_target
    target_fw = state.destination_target
    assert source_fw is not None and target_fw is not None, (
        "source_target/destination_target must be set before translation generation."
    )

    # Entrypoint class names are deterministic (from the snippet mapping), so they are no longer the
    # model's responsibility — we bake them into the save-tool guidance and the assembled output.
    source_entry = (await get_snippet_content(source_fw, is_schema=is_schema))["entry_type_name"]
    target_entry = (await get_snippet_content(target_fw, is_schema=is_schema))["entry_type_name"]

    # Production default is EINFRA_QWEN3_5 with reasoning on; the evaluation harness can swap the
    # generation model (model sweep) and/or force reasoning via Context (set per-invoke, never a
    # global — see Context.translation_model_override). Both this agent's model and the forced-save
    # fallback below honour the same override so an experiment stays internally consistent.
    _override = runtime.context.translation_model_override
    translation_model = (
        AvailableModel(_override) if _override else AvailableModel.EINFRA_QWEN3_5
    )
    _reasoning_override = runtime.context.translation_reasoning_override
    model = await get_model(
        config,
        runtime,
        model_name_override=translation_model,
        reasoning=(_reasoning_override if _reasoning_override is not None else True),
    )

    system_prompt = eval_cache_bust_header(runtime, config) + await build_system_prompt(state)

    message = build_translation_user_message(state)

    save_tool = build_save_translation_tool(translation_type, source_entry, target_entry)

    # Research-only tool surface: documentation (MCP) + web search, plus the single state-writing
    # save tool. Database inspection MCP is deliberately excluded here — the DB schema was already
    # inspected by `schema_inspection` (carried in `state.schema_context`), and re-exposing those
    # tools tempts the agent into long inspection loops that exhaust its step budget before it saves.
    # The validators/sandbox tools are also excluded: validation runs in the proven outer state
    # machine (parallel dotnet+java → gate → equivalence → eval), which avoids double-validation and
    # keeps compiler/run output out of the generation context.
    # Fresh prompt every attempt; on retries append distilled text feedback rather than
    # replaying translation_messages (which carry orphaned tool_calls).
    input_messages: list[BaseMessage] = [HumanMessage(content=message)]
    feedback = _distill_translation_feedback(state)
    if feedback:
        input_messages.append(HumanMessage(content=feedback))

    if state.single_pass:
        # Baseline (evaluation) arm: skip the ReAct research agent and docs MCP entirely. The
        # single-shot generation is the system prompt + human prompt straight into the model with
        # only the save tool — performed by the shared forced-call path below, which an empty
        # response triggers (every required field becomes "missing" → exactly one direct
        # save_translation call). This is the apples-to-apples lower bound for the agentic loop.
        response: dict[str, Any] = {}
    else:
        async with (
            load_docs_mcp_tools() as docs_tools,
        ):
            research_tools = [search, *docs_tools, save_tool]
            agent = create_agent(
                model,
                tools=research_tools,
                system_prompt=system_prompt,
                store=runtime.store,
                middleware=[
                    # Declares TranslationDraftState so the save_translation tool's
                    # Command(update=...) writes are valid and survive into the agent's state.
                    TranslationDraftMiddleware(),
                    SummarizationMiddleware(model, trigger=("fraction", 0.9)),
                    ModelFallbackMiddleware(
                        await get_model(
                            config, runtime, AvailableModel.EINFRA_DEEPSEEK_V4_PRO_THINKING
                        ),
                        await get_model(
                            config, runtime, AvailableModel.OLLAMA_QWEN3_6_27B
                        ),
                    ),
                    ToolRetryMiddleware(),
                    # Innermost (last): flatten reasoning list-content so re-sent turns don't 400.
                    # Critical here — this agent runs the reasoning models (thinker / qwen3.5).
                    ReasoningContentSanitizerMiddleware(),
                ],
            )

            response = await agent.ainvoke(
                {"messages": input_messages}, {"recursion_limit": 60}
            )  # type: ignore

    updates: dict[str, Any] = {
        "translation_loop_count": state.translation_loop_count + 1,
    }

    # Harvest the draft the agent saved via the single save_translation tool.
    required = required_draft_fields(translation_type)
    draft = {f: response.get(f) for f in required if response.get(f)}
    missing = [f for f in required if not draft.get(f)]

    if missing:
        # The research agent ended without a complete save_translation call. With tool_choice="auto"
        # the model may answer in prose and stop instead of calling the finish tool — increasingly
        # likely as the translation grows. Force the issue with one direct call that REQUIRES the
        # save tool. (the model reliably emits a complete, untruncated draft this way; the
        # failure is the agent's optional-tool finish, not the model's output capacity.)
        if state.single_pass:
            logger.info("generate_translation_node: single-pass baseline — one forced save_translation call")
        else:
            logger.warning(
                "generate_translation_node: agent finished without %s; forcing save_translation",
                missing,
            )
        try:
            # Use a FRESH model instance (not the one handed to create_agent, which is bound to the
            # research tools + fallback/summarization middleware) and require the save tool.
            # This reliably returns a complete draft (~38s) on the real prompt.
            # For the single-pass BASELINE this is the primary (and only) generation call, so match
            # the full-loop agent's reasoning mode (line ~1064, reasoning=True) to hold the model
            # config constant across arms — the ablation then isolates the tools+loop, not reasoning.
            # In the full-loop FALLBACK case it stays reasoning=False (a fast forced completion).
            forced_model = await get_model(
                config,
                runtime,
                model_name_override=translation_model,
                temperature=0,
                reasoning=(
                    _reasoning_override
                    if _reasoning_override is not None
                    else state.single_pass
                ),
            )
            forced = forced_model.bind_tools([save_tool], tool_choice="any")
            forced_resp = await forced.ainvoke(
                [SystemMessage(content=system_prompt), *input_messages]
            )
            forced_calls = getattr(forced_resp, "tool_calls", None) or []
            invalid = getattr(forced_resp, "invalid_tool_calls", None) or []
            logger.warning(
                "generate_translation_node: forced call returned %d tool_calls, %d invalid",
                len(forced_calls),
                len(invalid),
            )
            for tc in forced_calls:
                if tc.get("name") == "save_translation":
                    args = tc.get("args") or {}
                    draft = {f: args.get(f) for f in required if args.get(f)}
                    break
        except Exception:
            logger.exception("generate_translation_node: forced save_translation call failed")
        missing = [f for f in required if not draft.get(f)]

    if missing:
        # The agent finished without persisting every required field. Surface the failure as a
        # normal assistant message so it renders in chat and `route_post_translation` diverts to
        # human intervention (it keys on the ERROR_PREFIX marker).
        logger.error(
            "generate_translation_node: missing required draft fields after run: %s",
            missing,
        )
        detail = (
            f"{StructuredOutputRetryMiddleware.ERROR_PREFIX} The translation agent finished without "
            f"providing the required field(s): {', '.join(missing)}. Call save_translation once "
            f"with every required field filled before finishing."
        )
        failure_message = AIMessage(content=detail)
        updates["messages"] = [failure_message]
        updates["translation_messages"] = [failure_message]
        updates["explanation_message"] = detail
        return updates

    # NOTE: generation no longer produces the clean, user-facing translated_schema_code /
    # translated_query_code. Those are derived post-acceptance by `finalize_translation_node` from
    # the VALIDATED harness, so the published answer is always a projection of code that compiled,
    # ran, and passed equivalence (and is stable enough to serve as a CodeBleu baseline).

    # Deterministically assemble the runnable validation code: inject the canonical, byte-stable
    # prelude (imports + serializer + runtime support + template factory) around the model-authored
    # body. Entry-type names come from the snippet mapping, not the model.
    source_code, source_entry_name = await assemble_validation_code(
        source_fw, draft["source_validation_body"], is_schema=is_schema
    )
    target_code, target_entry_name = await assemble_validation_code(
        target_fw, draft["target_validation_body"], is_schema=is_schema
    )
    if is_schema:
        updates["source_validation_schema_code"] = source_code
        updates["target_validation_schema_code"] = target_code
    else:
        updates["source_validation_harness_code"] = source_code
        updates["target_validation_harness_code"] = target_code
    updates["source_validation_entry_type_name"] = source_entry_name
    updates["target_validation_entry_type_name"] = target_entry_name

    saved_summary = {
        "source_validation_entry_type_name": source_entry_name,
        "target_validation_entry_type_name": target_entry_name,
        "source_validation_body_chars": len(draft["source_validation_body"]),
        "target_validation_body_chars": len(draft["target_validation_body"]),
    }
    summary_message = AIMessage(
        content=(
            "Translation generated successfully. Assembled runnable validation harnesses from the "
            "model-authored bodies + canonical prelude. Draft:\n```json\n"
            + orjson.dumps(
                {k: v for k, v in saved_summary.items() if v is not None},
                option=orjson.OPT_INDENT_2,
            ).decode("utf-8")
            + "\n```"
        )
    )
    updates["messages"] = [summary_message]
    updates["translation_messages"] = [summary_message]

    return updates


def _truncate(value: Any, limit: int = 2000) -> Any:
    """Truncate long string values for inclusion in a chat summary message."""
    if isinstance(value, str) and len(value) > limit:
        return value[:limit] + " …[truncated]"
    return value


class HumanInterventionResponse(BaseModel):
    """Pydantic model representing the feedback and decision from a human-in-the-loop intervention.

    Attributes:
        decision: The logical decision, either "accept" to commit the translation or "reject" to loop back with feedback.
        feedback: Text description or critique describing necessary adjustments.
    """

    decision: Literal["accept", "reject"]
    feedback: str


async def human_intervention_node(
    state: State,
) -> Command[Literal["generate_translation_node", "finalize_translation_node"]]:
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
    # The clean translated_*_code is only produced post-acceptance by finalize_translation_node, so
    # at this (pre-finalize) point it is still None. Surface what actually exists for review: the
    # validated/assembled harness + schema code and the evaluation explanation.
    response = interrupt(
        {
            "instruction": "Review the current state, generated translation and validation results. Decide if the translation is correct or if another translation attempt is needed and provide feedback on what needs to be improved in the next attempt.",
            "state": {
                "source_validation_schema_code": state.source_validation_schema_code,
                "target_validation_schema_code": state.target_validation_schema_code,
                "source_validation_harness_code": state.source_validation_harness_code,
                "target_validation_harness_code": state.target_validation_harness_code,
                "explanation_message": state.explanation_message,
                "query_equivalence_deep_diffs": state.query_equivalence_deep_diffs,
            },
        }
    )
    output = HumanInterventionResponse.model_validate(response)

    # Both branches route explicitly via Command(goto=...). There is no static outgoing edge for this
    # node (see graph wiring) — a static edge would co-fire with these Commands and, on accept, wrongly
    # re-run generation alongside finalize.
    if output.decision == "reject":
        if output.feedback:
            feedback_message = HumanMessage(
                content=f"User rejected the translation with feedback:\n{output.feedback}"
            )
        else:
            feedback_message = HumanMessage(
                content="User rejected the translation without providing feedback."
            )
        return Command(
            update={
                "messages": feedback_message,
                "translation_messages": feedback_message,
            },
            goto="generate_translation_node",
        )
    else:
        feedback_message = HumanMessage(content="Translation was accepted.")
        return Command(
            update={
                "messages": feedback_message,
                "translation_messages": feedback_message,
            },
            goto="finalize_translation_node",
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
    if state.source_target in DotnetFramework:
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
    elif state.source_target in JavaFramework:
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
    if state.destination_target in DotnetFramework:
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
    elif state.destination_target in JavaFramework:
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
    model = await get_model(config, runtime, AvailableModel.EINFRA_KIMI_K2_7)

    last_msgs = [str(msg) for msg in state.translation_messages[-4:]]

    prompt = eval_cache_bust_header(runtime, config) + f"""Evaluate the following validation results for a schema/query translation.
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
                await get_model(config, runtime, AvailableModel.EINFRA_DEEPSEEK_V4_PRO_THINKING),
                await get_model(config, runtime, AvailableModel.OLLAMA_QWEN3_6_27B),
                await get_model(config, runtime)
            ),
            ToolRetryMiddleware(),
            # Innermost (last): flatten reasoning list-content so re-sent turns don't 400.
            ReasoningContentSanitizerMiddleware(),
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
        # The clean, user-facing translated code is produced next by `finalize_translation_node`
        # (derived from the now-validated harness). Here we only surface the judge's verdict; the
        # final code markdown is emitted downstream so it is always a projection of validated code.
        messages = messages + [
            AIMessage(content=f"""The translation was accepted by automated evaluation. Finalizing the translated code…

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


# Matches a fenced code block, capturing its body. The opening fence may carry an optional language
# tag (```java / ```csharp / ```cs / bare ```). Used to parse the finalize model's prose output.
_CODE_FENCE_RE = re.compile(r"```[a-zA-Z0-9_+-]*\s*\n(.*?)```", re.DOTALL)


def _extract_code_fences(text: str) -> list[str]:
    """Extract the bodies of fenced code blocks from a markdown/prose string, in order.

    The finalize model emits its answer as fenced code blocks rather than a tool-call/strict-JSON
    object: the e-INFRA sglang models collapse multi-line code in tool-call JSON to its first line
    (an unescaped-newline truncation), whereas fenced prose preserves the full multi-line code. This
    is the proven-reliable transport for getting code-sized output from these models.

    Args:
        text: The model's textual response.

    Returns:
        list[str]: The stripped contents of each fenced code block, in document order.
    """
    return [block.strip() for block in _CODE_FENCE_RE.findall(text) if block.strip()]


async def finalize_translation_node(
    state: State, config: RunnableConfig, runtime: Runtime[Context]
) -> dict[str, Any]:
    """Derive the clean, user-facing translated code from the VALIDATED harness, post-acceptance.

    Generation no longer emits ``translated_schema_code`` / ``translated_query_code``. This node runs
    only after a translation is accepted (LLM-judge ACCEPT for QUERY/BOTH, compile-pass for
    SCHEMA-only, or human accept) and projects the already-validated harness/schema code into clean
    production code. Because the input is frozen-after-validation, this is a constrained extraction
    (not a re-translation): the published answer is always a projection of code that compiled, ran,
    and passed equivalence, and is structurally stable enough to serve as a CodeBleu baseline.

    The result is written to ``translated_schema_code`` / ``translated_query_code`` and rendered as a
    markdown message into BOTH ``messages`` (frontend) and ``translation_messages`` (internal loop).

    Args:
        state (State): The current state of the graph.
        config (RunnableConfig): Configuration parameters for the run.
        runtime (Runtime[Context]): The execution runtime containing context.

    Returns:
        dict[str, Any]: State updates with the finalized production code and a markdown summary.
    """
    translation_type = state.translation_type or TranslationType.BOTH
    assert state.destination_target is not None and state.source_target is not None

    # Source of truth = the validated code. For SCHEMA-only that is the schema-validation code; for
    # QUERY/BOTH it is the full query-execution harness (which carries both entities and queries).
    if translation_type == TranslationType.SCHEMA:
        target_validated = state.target_validation_schema_code or ""
        source_validated = state.source_validation_schema_code or ""
    else:
        target_validated = state.target_validation_harness_code or ""
        source_validated = state.source_validation_harness_code or ""

    markdown_lang = FRAMEWORK_TO_LANGUAGE_TYPE[state.destination_target].value

    if translation_type == TranslationType.SCHEMA:
        type_specific = "Produce ONLY the clean target entity/model classes. There are no queries to finalize."
        fence_instruction = (
            f"Return EXACTLY ONE fenced ```{markdown_lang} code block and nothing else (no prose, no "
            "second block): the clean entity/model class definitions."
        )
        expected_blocks = 1
    elif translation_type == TranslationType.QUERY:
        type_specific = "Produce ONLY the clean target query class. Do not emit entity/model class definitions."
        fence_instruction = (
            f"Return EXACTLY ONE fenced ```{markdown_lang} code block and nothing else (no prose, no "
            "second block): the clean query class with one method per source query."
        )
        expected_blocks = 1
    else:
        type_specific = "Produce BOTH the entity/model classes and the query class."
        fence_instruction = (
            f"Return EXACTLY TWO fenced ```{markdown_lang} code blocks and nothing else (no prose "
            f"between or around them): the FIRST block is the entity/model classes, the SECOND block "
            "is the query class with one method per source query."
        )
        expected_blocks = 2

    # Build the human message by f-string (NOT str.format): the validated code contains many braces
    # that would break format-string substitution.
    human = f"""Finalize the accepted translation from {state.source_target.value} to {state.destination_target.value} (type: {translation_type.value}).
{type_specific}

{fence_instruction}

--- VALIDATED TARGET HARNESS ({state.destination_target.value}) — SOURCE OF TRUTH, copy semantics verbatim ---
{target_validated}

--- ORIGINAL SOURCE CODE (reference for naming/ordering only; do NOT pull semantics from here) ---
{f"<source_schema_code>\n{state.source_schema_code}\n</source_schema_code>" if state.source_schema_code else ""}{f"\n<source_query_code>\n{state.source_query_code}\n</source_query_code>" if state.source_query_code else ""}
"""

    # Pin a SINGLE model (no fallback) for finalization. This node's output is the CodeBleu baseline
    # input — a silent fallback to a different model would emit differently-structured code and
    # confound AST/data-flow comparison across runs (a metric delta could be a model swap, not a
    # translation change).
    #
    # Transport = PROSE with fenced code blocks (parsed below), NOT a tool call / strict-JSON: the
    # e-INFRA sglang models collapse multi-line code in tool-call JSON to its first line (verified
    # live — both fields came back as just `package uom.services;`), whereas fenced prose returns the
    # full multi-line code reliably (verified: complete clean schema+query in ~14s). The socket
    # timeout is raised above the hardcoded 120s default because finalizing a full schema+queries can
    # legitimately stream for longer.
    finalize_model_name = AvailableModel.EINFRA_QWEN3_5
    model = await get_model(
        config,
        runtime,
        model_name_override=finalize_model_name,
        temperature=0,
        reasoning=False,
    )
    try:
        model.request_timeout = 300  # type: ignore[attr-defined]
    except Exception:
        pass

    updates: dict[str, Any] = {}
    schema_code: str | None = None
    query_code: str | None = None
    try:
        response = await model.ainvoke(
            [
                SystemMessage(
                    content=eval_cache_bust_header(runtime, config) + SYSTEM_PROMPT_FINALIZE
                ),
                HumanMessage(content=human),
            ]
        )
        text = response.content if isinstance(response.content, str) else ""
        blocks = _extract_code_fences(text)
        if translation_type == TranslationType.QUERY:
            query_code = blocks[0] if blocks else None
        elif translation_type == TranslationType.SCHEMA:
            schema_code = blocks[0] if blocks else None
        else:
            schema_code = blocks[0] if len(blocks) >= 1 else None
            query_code = blocks[1] if len(blocks) >= 2 else None
        if len(blocks) < expected_blocks:
            logger.warning(
                "finalize_translation_node: expected %d code block(s), parsed %d.",
                expected_blocks,
                len(blocks),
            )
    except Exception:
        logger.exception("finalize_translation_node: finalize call failed")

    logger.info(
        "finalize_translation_node: finalized with model=%s (schema=%s, query=%s)",
        finalize_model_name.value if hasattr(finalize_model_name, "value") else finalize_model_name,
        bool(schema_code),
        bool(query_code),
    )

    # If the model produced none of the expected fields, the translation is still accepted and
    # validated — surface the validated harness so nothing is lost and the user can review. This is
    # an explicit, logged degradation (NOT a silent substitution into the CodeBleu baseline fields).
    if not schema_code and not query_code:
        logger.warning("finalize_translation_node: no finalized code produced; surfacing validated harness.")
        fallback = AIMessage(
            content=(
                "The translation was accepted, but automatic finalization of the clean production "
                "code did not complete. The validated, runnable code is below:\n\n"
                f"```{markdown_lang}\n{target_validated}\n```"
            )
        )
        return {"messages": [fallback], "translation_messages": [fallback]}

    sections = ["The translation is finalized. Here is the final translated code:\n"]
    if schema_code:
        updates["translated_schema_code"] = schema_code
        sections.append(f"Translated schema:\n```{markdown_lang}\n{schema_code}\n```\n")
    if query_code:
        updates["translated_query_code"] = query_code
        sections.append(f"Translated query:\n```{markdown_lang}\n{query_code}\n```\n")

    final_message = AIMessage(content="\n".join(sections))
    updates["messages"] = [final_message]
    updates["translation_messages"] = [final_message]
    return updates


def route_post_evaluation(
    state: State,
) -> Literal["generate_translation_node", "human_intervention_node", "finalize_translation_node", "__end__"]:
    """Determine the next state transition after evaluation.

    If the evaluation was rejected or failed, it routes back to `generate_translation_node`
    to retry. If the maximum translation loop count is reached, it routes to
    `human_intervention_node` instead. If accepted, it routes to `finalize_translation_node`,
    which derives the clean, user-facing translated code from the validated harness before ending.

    Args:
        state (State): The current state of the graph.

    Returns:
        Literal["generate_translation_node", "human_intervention_node", "finalize_translation_node"]:
        The next node.
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
        # Baseline arm: one shot, no self-repair loop and no human hand-off — terminate so the
        # experiment records the single-pass failure (validation results stay in state).
        if state.single_pass:
            return "__end__"
        # We check the translation_loop_count to prevent infinite loops of failing compilation.
        # If [Structured Output Error] occured in this last evaluation stage, we don't want to run expensive translation again, we let the user decide.
        # If it exceeds the maximum (typically 3), we route to 'human_intervention_node' to let the user fix the issue manually.
        if state.translation_loop_count >= MAX_TRANSLATION_LOOPS or "[Structured Output Error]" in last_msg:
            return "human_intervention_node"
        return "generate_translation_node"
    return "finalize_translation_node"


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
) -> Literal[
    "prep_schema_validation", "prep_query_validation", "human_intervention_node", "__end__"
]:
    """Determine the next validation state transition after code generation.

    If generation could not produce a valid structured output (surfaced by
    `generate_translation_node` as a `[Structured Output Error]` message), routes to
    `human_intervention_node` so the failure is reviewed instead of pushing empty/invalid code
    into validation. Otherwise routes to `prep_schema_validation` for SCHEMA translations, or to
    `prep_query_validation` for QUERY/BOTH.

    Args:
        state (State): The current state of the graph.

    Returns:
        Literal["prep_schema_validation", "prep_query_validation", "human_intervention_node", "__end__"]:
        The next node.
    """
    last_msg = (
        str(state.translation_messages[-1].content)
        if state.translation_messages
        else ""
    )
    if StructuredOutputRetryMiddleware.ERROR_PREFIX in last_msg:
        # Baseline arm: a failed single-shot generation terminates rather than interrupting for a
        # human (which would block batch experiment runs).
        return "__end__" if state.single_pass else "human_intervention_node"
    if state.translation_type == TranslationType.SCHEMA:
        return "prep_schema_validation"
    return "prep_query_validation"


def route_post_schema_validation(
    state: State,
) -> Literal[
    "prep_query_validation",
    "generate_translation_node",
    "human_intervention_node",
    "finalize_translation_node",
    "__end__",
]:
    """Determine the next state transition after schema validation.

    If schema compilation failed, it routes back to `generate_translation_node` (or
    `human_intervention_node` if max retries exceeded) without proceeding further.
    If it passed and the translation type is BOTH, it routes to `prep_query_validation`.
    Otherwise (SCHEMA-only success), it routes to `finalize_translation_node` to derive the clean
    translated schema from the validated harness before ending.

    Args:
        state (State): The current state of the graph.

    Returns:
        Literal["prep_query_validation", "generate_translation_node", "human_intervention_node", "finalize_translation_node", "__end__"]: The next node.
    """
    last_msg = (
        state.translation_messages[-1].content if state.translation_messages else ""
    )
    if "Failed]" in last_msg:
        # Baseline arm: no self-repair loop, no human hand-off — terminate on schema compile failure.
        if state.single_pass:
            return "__end__"
        if state.translation_loop_count >= MAX_TRANSLATION_LOOPS:
            return "human_intervention_node"
        return "generate_translation_node"

    if state.translation_type == TranslationType.BOTH:
        return "prep_query_validation"
    return "finalize_translation_node"


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

# Same as `retry_policy` but never re-runs the whole node on a structured-output validation
# failure: `StructuredOutputRetryMiddleware` already retried the model in place and surfaced a
# user-facing error, so a full-node re-run (3x the model/fallback fan-out) would only add cost.
generation_retry_policy = RetryPolicy(
    max_attempts=3,
    retry_on=_retry_on_excluding_structured_output,
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
    retry_policy=generation_retry_policy,
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
builder.add_node(
    finalize_translation_node,  # type: ignore
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
# human_intervention_node routes dynamically via Command(goto=...): generate_translation_node on
# reject, finalize_translation_node on accept. No static edge here — it would co-fire with the
# Command and, on accept, wrongly re-run generation in parallel with finalize.

graph = builder.compile(
    name="Universal Object Mapping Translator",
    # checkpointer=checkpointer,
    cache=node_cache,
    # debug=True if os.getenv("DEVELOPMENT") else False,
)

# logger.info(graph.get_graph().draw_mermaid())
