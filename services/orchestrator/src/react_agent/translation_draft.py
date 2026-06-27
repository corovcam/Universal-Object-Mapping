"""Tool-driven translation drafting with deterministic harness assembly.

The new e-INFRA sglang models do not honor a single giant strict-JSON structured output, and they
reliably mis-reproduce the invariant harness boilerplate (imports, serializer, runtime support)
when asked to emit whole files. This module replaces both failure modes:

1. **One** state-writing ``save_translation`` tool (not a dozen per-field tools) collects the
   genuinely dataset-specific code the model authors — the translated production schema/queries and
   the *body* of each validation harness (entity classes + query classes + entrypoint ``main``),
   *without* the boilerplate prelude.
2. :mod:`react_agent.utils.harness_assembler` then injects the canonical, byte-stable prelude
   (imports + serializer + template factory) around those bodies in ``generate_translation_node``.

A middleware declares the extra state channels so the tool's ``Command(update=...)`` writes are
valid and survive into the agent's final state, where the node harvests them.
"""

from __future__ import annotations

from typing import Annotated

from langchain.agents.middleware import AgentMiddleware
from langchain.agents.middleware.types import AgentState
from langchain_core.messages import ToolMessage
from langchain_core.tools import BaseTool, InjectedToolCallId, StructuredTool
from langgraph.types import Command
from pydantic import BaseModel, Field, create_model
from typing_extensions import NotRequired

from react_agent.constants import TranslationType

# The draft channels the single save tool writes. The two ``*_validation_body`` fields hold the
# model-authored harness body (no prelude); the node assembles them into the full
# ``*_validation_harness_code`` / ``*_validation_schema_code`` the downstream validators read.
#
# Note: the generation step deliberately does NOT produce the clean, user-facing
# ``translated_schema_code`` / ``translated_query_code`` anymore. Those are derived *after*
# acceptance by ``finalize_translation_node`` from the VALIDATED harness (so the published answer is
# always a projection of code that actually compiled, ran, and passed equivalence — and is stable
# enough to use as a CodeBleu baseline). Generation only authors the two harness bodies.
DRAFT_FIELDS: tuple[str, ...] = (
    "source_validation_body",
    "target_validation_body",
)


class TranslationDraftState(AgentState):
    """Agent state extended with the channels the ``save_translation`` tool writes."""

    source_validation_body: NotRequired[str]
    target_validation_body: NotRequired[str]


class TranslationDraftMiddleware(AgentMiddleware):
    """Registers :class:`TranslationDraftState` so the save tool's writes are valid and surface."""

    state_schema = TranslationDraftState


# Per-field guidance shown to the model as the save tool's argument descriptions.
_FIELD_DESCRIPTIONS: dict[str, str] = {
    "source_validation_body": (
        "The SOURCE-side validation harness BODY: the source entity classes (+ any "
        "context/session/config bootstrap), the source query classes/methods, and the entrypoint "
        "class containing `main`/`Main` that validates each entity and runs each query, writing the "
        "JSON results to the environment path. Start directly at the schema/entity declarations. Do "
        "NOT write any `import`/`using`/`package`/`namespace` lines and do NOT (re)declare the "
        "provided serializer / runtime-support / template-factory classes — those are injected for "
        "you. You MUST declare the entrypoint class named exactly `{source_entry}`."
    ),
    "target_validation_body": (
        "The TARGET-side validation harness BODY: the translated entity classes, the translated "
        "query classes/methods, and the entrypoint class containing `main`/`Main` that validates "
        "each entity and runs each query, writing the JSON results to the environment path. Start "
        "directly at the schema/entity declarations. Do NOT write any "
        "`import`/`using`/`package`/`namespace` lines and do NOT (re)declare the provided serializer "
        "/ runtime-support / template-factory classes — those are injected for you. You MUST declare "
        "the entrypoint class named exactly `{target_entry}`."
    ),
}


def required_draft_fields(translation_type: TranslationType) -> tuple[str, ...]:
    """Return the draft fields the model must provide for the given translation type.

    The generation step always authors exactly the two validation harness bodies regardless of
    translation type — the clean ``translated_*_code`` answer is derived later, post-acceptance, by
    ``finalize_translation_node``. The argument is retained for call-site compatibility.
    """
    return DRAFT_FIELDS


def build_save_translation_tool(
    translation_type: TranslationType,
    source_entry: str,
    target_entry: str,
) -> BaseTool:
    """Build the single ``save_translation`` tool, gated to the required fields for this type.

    Args:
        translation_type: SCHEMA, QUERY, or BOTH — selects which fields are required.
        source_entry: Deterministic source entrypoint class name (baked into the field guidance).
        target_entry: Deterministic target entrypoint class name (baked into the field guidance).

    Returns:
        BaseTool: An async tool that persists the provided draft fields to state via ``Command``.
    """
    fields = required_draft_fields(translation_type)

    schema_fields: dict[str, object] = {}
    for name in fields:
        desc = _FIELD_DESCRIPTIONS[name].format(
            source_entry=source_entry, target_entry=target_entry
        )
        schema_fields[name] = (str, Field(description=desc))
    # tool_call_id is injected by the runtime (not surfaced to the model) so we can build the
    # ToolMessage that closes out the tool call; it must be declared in the args schema with the
    # InjectedToolCallId annotation for LangChain to recognize and supply it.
    schema_fields["tool_call_id"] = (
        Annotated[str, InjectedToolCallId],
        Field(default=""),
    )
    args_model: type[BaseModel] = create_model(  # type: ignore[call-overload]
        "SaveTranslationArgs", **schema_fields
    )

    async def _save(
        source_validation_body: str = "",
        target_validation_body: str = "",
        tool_call_id: str = "",
    ) -> Command:
        values = {
            "source_validation_body": source_validation_body,
            "target_validation_body": target_validation_body,
        }
        update: dict[str, object] = {
            name: values[name] for name in fields if values.get(name)
        }
        saved = ", ".join(f"`{n}`" for n in update) or "(nothing)"
        update["messages"] = [
            ToolMessage(
                content=f"Saved translation draft: {saved}.",
                tool_call_id=tool_call_id,
                name="save_translation",
            )
        ]
        return Command(update=update)

    return StructuredTool.from_function(
        coroutine=_save,
        name="save_translation",
        description=(
            "Persist the completed translation. Call this ONCE, at the end, with every required "
            "field filled. This is how you finish — there is no separate JSON output."
        ),
        args_schema=args_model,
    )


__all__ = [
    "TranslationDraftState",
    "TranslationDraftMiddleware",
    "build_save_translation_tool",
    "required_draft_fields",
    "DRAFT_FIELDS",
]
