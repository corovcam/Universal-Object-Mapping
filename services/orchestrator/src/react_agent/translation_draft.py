"""Incremental, tool-driven translation drafting (no final structured output).

The new e-INFRA sglang models do not honor strict JSON structured output for a single giant
zero-shot blob (the old `ProviderStrategy(BaseTranslationOutput)` path). They are tuned for long
agentic sessions with many small tool calls. This module replaces the one-shot structured response
with **state-writing save tools**: the ReAct agent persists each translation artifact individually
*during* its execution by calling a dedicated `save_*` tool, and a middleware declares the extra
state channels so those `Command(update=...)` writes are valid and survive in the agent's final
state. `generate_translation_node` then harvests those channels back into the graph `State`.

The fields mirror `BaseTranslationOutput`; the per-`TranslationType` gating mirrors
`_create_translation_output_model` so the model is only asked for the artifacts it actually needs.
"""

from __future__ import annotations

from typing import Annotated

from langchain.agents.middleware import AgentMiddleware
from langchain.agents.middleware.types import AgentState
from langchain_core.messages import ToolMessage
from langchain_core.tools import BaseTool, InjectedToolCallId, tool
from langgraph.types import Command
from typing_extensions import NotRequired

from react_agent.constants import TranslationType
from react_agent.utils.types import QueryEquivalenceDeepDiff, QueryValidationResults


class TranslationDraftState(AgentState):
    """Agent state extended with every channel the translation ReAct agent writes.

    Two groups of keys are declared here so the agent's tools can issue `Command(update=...)`
    against them without LangGraph rejecting an unknown channel:

    1. The translation artifacts, written by the `save_*` tools in this module (mirrors the
       `BaseTranslationOutput` fields).
    2. The validation results, written by the *real* validators (`validate_dotnet_code`,
       `validate_java_code`, `check_query_equivalence`) when the agent runs them inline. These
       targets exist on the graph `State` but not on the default `AgentState`, so they must be
       declared here too or an inline validator call would crash the node.
    """

    # --- Translation artifacts (written by save_* tools) ---
    translated_schema_code: NotRequired[str]
    translated_query_code: NotRequired[str]
    source_validation_schema_code: NotRequired[str]
    source_validation_harness_code: NotRequired[str]
    target_validation_schema_code: NotRequired[str]
    target_validation_harness_code: NotRequired[str]
    source_validation_entry_type_name: NotRequired[str]
    target_validation_entry_type_name: NotRequired[str]

    # --- Validation results (written by the inline validator tools) ---
    source_query_validation_results: NotRequired[QueryValidationResults]
    target_query_validation_results: NotRequired[QueryValidationResults]
    query_equivalence_deep_diffs: NotRequired[dict[str, QueryEquivalenceDeepDiff]]


class TranslationDraftMiddleware(AgentMiddleware):
    """Middleware whose sole job is to register `TranslationDraftState` on the agent.

    Declaring the extended schema here (rather than via `create_agent(state_schema=...)`) keeps the
    save-tool writes and the inline-validator `Command` updates valid, and makes the harvested keys
    appear in the dict returned by `agent.ainvoke(...)`.
    """

    state_schema = TranslationDraftState


def _save_tool(field_name: str, description: str) -> BaseTool:
    """Build a single state-writing save tool for one translation artifact field.

    Args:
        field_name: The `TranslationDraftState` / graph `State` key to write.
        description: The tool description shown to the model (reused from
            `BaseTranslationOutput`).

    Returns:
        BaseTool: An async tool returning a `Command` that persists the value into state.
    """

    async def _save(
        content: str, tool_call_id: Annotated[str, InjectedToolCallId]
    ) -> Command:
        return Command(
            update={
                field_name: content,
                "messages": [
                    ToolMessage(
                        content=f"Saved `{field_name}` ({len(content)} chars).",
                        tool_call_id=tool_call_id,
                        name=f"save_{field_name}",
                    )
                ],
            }
        )

    return tool(f"save_{field_name}", description=description)(_save)


# Per-field descriptions, mirrored from `BaseTranslationOutput` so the model gets the same guidance
# it had when these were structured-output fields.
_DESCRIPTIONS: dict[str, str] = {
    "translated_schema_code": (
        "Save the precise translated schema definitions (entities/models) and "
        "context/session/config/bootstrap setup with runtime configs. Plain code only. Do not "
        "include usage queries. Corresponds to the example code below the "
        "`--- Schema and Related Settings ---` comment."
    ),
    "translated_query_code": (
        "Save the precise translated production queries only. Keep query semantics and method "
        "shape equivalent to the source query code. Plain code only. Do not include schema "
        "definitions, validation harness helpers, or synthetic validator-only parameters unless "
        "they already exist in the source query code. Corresponds to the `QueryX`/`queryX` methods."
    ),
    "source_validation_schema_code": (
        "Save the SOURCE schema validation code: imports, serialization, runtime config, "
        "context/session/config/bootstrap setup, and everything needed to run, keeping the Schema "
        "and Related Settings logic equivalent to the original source schema (without JSON "
        "serialization annotations). Fully valid and runnable with an entrypoint. Include simple "
        "one-entity fetch queries to validate each entity. No source query code here."
    ),
    "source_validation_harness_code": (
        "Save the full execution harness code for the SOURCE queries: source schema, query "
        "methods, any necessary helper classes/records, and the main entry point that executes the "
        "source queries and writes the resulting JSON to the environment path."
    ),
    "target_validation_schema_code": (
        "Save the TARGET schema validation code: imports, serialization, runtime config, "
        "context/session/config/bootstrap setup, and everything needed to run, keeping the Schema "
        "and Related Settings logic equivalent to the translated schema (without JSON "
        "serialization annotations). Fully valid and runnable with an entrypoint. Include simple "
        "one-entity fetch queries to validate each entity. No target query code here."
    ),
    "target_validation_harness_code": (
        "Save the full execution harness code for the translated TARGET queries: translated query "
        "methods, any necessary helper classes/records, and the main entry point that executes the "
        "target queries and writes the resulting JSON to the environment path."
    ),
    "source_validation_entry_type_name": (
        "Save the name of the main entry point type (class) in the source validation code. Just "
        "the class/type name, without namespace or module prefix. Examples: `EFCoreQueryEntrypoint`, "
        "`NHibernateQueryEntrypoint`, `DapperQueryEntrypoint`. It must be declared in the source "
        "validation code you saved."
    ),
    "target_validation_entry_type_name": (
        "Save the name of the main entry point type (class) in the target validation code. Just "
        "the class/type name, without namespace or module prefix. Examples: `MongoQueryEntrypoint`, "
        "`Neo4jQueryEntrypoint`. It must be declared in the target validation code you saved."
    ),
}

# Which artifact fields are required per translation type — mirrors `_create_translation_output_model`.
_FIELDS_BY_TYPE: dict[TranslationType, tuple[str, ...]] = {
    TranslationType.SCHEMA: (
        "translated_schema_code",
        "source_validation_schema_code",
        "source_validation_entry_type_name",
        "target_validation_schema_code",
        "target_validation_entry_type_name",
    ),
    TranslationType.QUERY: (
        "translated_schema_code",
        "translated_query_code",
        "source_validation_harness_code",
        "source_validation_entry_type_name",
        "target_validation_harness_code",
        "target_validation_entry_type_name",
    ),
    TranslationType.BOTH: (
        "translated_schema_code",
        "translated_query_code",
        "source_validation_harness_code",
        "source_validation_entry_type_name",
        "target_validation_harness_code",
        "target_validation_entry_type_name",
    ),
}


# Every artifact channel the save_* tools may write (harvested back into the graph State).
ARTIFACT_FIELDS: tuple[str, ...] = (
    "translated_schema_code",
    "translated_query_code",
    "source_validation_schema_code",
    "source_validation_harness_code",
    "target_validation_schema_code",
    "target_validation_harness_code",
    "source_validation_entry_type_name",
    "target_validation_entry_type_name",
)

# Validation result channels the inline validator tools may write (also harvested back).
VALIDATION_RESULT_FIELDS: tuple[str, ...] = (
    "source_query_validation_results",
    "target_query_validation_results",
    "query_equivalence_deep_diffs",
)


def required_draft_fields(translation_type: TranslationType) -> tuple[str, ...]:
    """Return the artifact fields the agent must save for the given translation type."""
    return _FIELDS_BY_TYPE.get(translation_type, ())


def build_translation_save_tools(translation_type: TranslationType) -> list[BaseTool]:
    """Build the gated set of `save_*` tools for the given translation type.

    Args:
        translation_type: SCHEMA, QUERY, or BOTH — selects which artifact fields are exposed.

    Returns:
        list[BaseTool]: One save tool per required artifact field.
    """
    fields = required_draft_fields(translation_type)
    return [_save_tool(field, _DESCRIPTIONS[field]) for field in fields]


__all__ = [
    "TranslationDraftState",
    "TranslationDraftMiddleware",
    "build_translation_save_tools",
    "required_draft_fields",
    "ARTIFACT_FIELDS",
    "VALIDATION_RESULT_FIELDS",
]
