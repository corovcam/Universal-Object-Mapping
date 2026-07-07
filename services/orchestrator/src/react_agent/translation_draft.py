"""Tool-driven translation drafting with deterministic harness assembly.

The new e-INFRA sglang models do not honor a single giant strict-JSON structured output, and they
reliably mis-reproduce the invariant harness boilerplate (imports, serializer, runtime support)
when asked to emit whole files. This module replaces both failure modes:

1. **Per-piece** state-writing save tools collect the genuinely dataset-specific code the model
   authors. ``save_schema_translation`` persists the entity/mapping classes for both sides;
   ``save_query_translation`` persists ONE query's harness fragment for both sides. Small,
   per-query tool calls keep each model output far below the truncation/rumination threshold that
   killed the monolithic-save runs (a single ~40k-char tool call after 200k chars of reasoning),
   and they make selective retries possible: a rejected loop regenerates only the failing queries.
2. :mod:`react_agent.utils.harness_assembler` then injects the canonical, byte-stable prelude
   (imports + serializer + template factory) around those fragments and generates the entrypoint
   ``main`` deterministically, so the results-protocol (per-query try/catch + JSON write) is no
   longer the model's responsibility at all.

The legacy monolithic ``save_translation`` tool is retained for the single-pass baseline arm and
as the forced-call fallback when the agent finishes without saving.

A middleware declares the extra state channels so the tools' ``Command(update=...)`` writes are
valid and survive into the agent's final state, where the node harvests them.
"""

from __future__ import annotations

import logging
import re
from typing import Annotated, Any

from langchain.agents.middleware import AgentMiddleware
from langchain.agents.middleware.types import (
    AgentState,
    ModelRequest,
    ModelResponse,
    hook_config,
)
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import BaseTool, InjectedToolCallId, StructuredTool
from langgraph.runtime import Runtime
from langgraph.types import Command
from pydantic import BaseModel, Field, create_model
from typing_extensions import NotRequired

from react_agent.constants import TranslationType

logger = logging.getLogger(__name__)

# The draft channels the monolithic save tool writes. The two ``*_validation_body`` fields hold the
# model-authored harness body (no prelude); the node assembles them into the full
# ``*_validation_harness_code`` / ``*_validation_schema_code`` the downstream validators read.
#
# Note: the generation step deliberately does NOT produce the clean, user-facing
# ``translated_schema_code`` / ``translated_query_code`` anymore. Those are derived *after*
# acceptance by ``finalize_translation_node`` from the VALIDATED harness (so the published answer is
# always a projection of code that actually compiled, ran, and passed equivalence — and is stable
# enough to use as a CodeBleu baseline). Generation only authors the harness bodies/fragments.
DRAFT_FIELDS: tuple[str, ...] = (
    "source_validation_body",
    "target_validation_body",
)

# Channels used by the per-query (fragment) contract.
FRAGMENT_SCHEMA_FIELDS: tuple[str, ...] = ("draft_source_schema", "draft_target_schema")

# Query ids present in the source input (`Query1`, `Query2`, ...). Drives the per-query save
# contract: the agent must save a fragment for every id found here.
_QUERY_ID_RE = re.compile(r"\bQuery(\d+)\b")


def expected_query_ids_from_source(source_query_code: str | None) -> tuple[int, ...]:
    """Extract the query ids a translation must cover from the source query code."""
    ids = sorted({int(m) for m in _QUERY_ID_RE.findall(source_query_code or "")})
    return tuple(ids) if ids else (1,)


def merge_query_fragments(
    left: dict[str, dict[str, str]] | None,
    right: dict[str, dict[str, str]] | None,
) -> dict[str, dict[str, str]]:
    """Reducer for the ``draft_queries`` channel: merge per-query fragment saves.

    Each ``save_query_translation`` call contributes ``{qid: {"source": ..., "target": ...}}``;
    later saves for the same query id overwrite that query only (retries), never the whole dict.
    """
    merged: dict[str, dict[str, str]] = {k: dict(v) for k, v in (left or {}).items()}
    for qid, sides in (right or {}).items():
        current = dict(merged.get(qid) or {})
        current.update({k: v for k, v in (sides or {}).items() if v})
        merged[qid] = current
    return merged


class TranslationDraftState(AgentState):
    """Agent state extended with the channels the save tools write."""

    # Monolithic contract (baseline arm + forced fallback).
    source_validation_body: NotRequired[str]
    target_validation_body: NotRequired[str]
    # Fragment contract (agent path): schema bodies + per-query fragments.
    draft_source_schema: NotRequired[str]
    draft_target_schema: NotRequired[str]
    draft_queries: NotRequired[
        Annotated[dict[str, dict[str, str]], merge_query_fragments]
    ]
    # Bookkeeping for the convergence guard (private-ish; harmless if surfaced).
    save_nudge_count: NotRequired[int]


class TranslationDraftMiddleware(AgentMiddleware):
    """Registers :class:`TranslationDraftState` so the save tools' writes are valid and surface."""

    state_schema = TranslationDraftState


# --------------------------------------------------------------------------- monolithic contract

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
    """Build the single monolithic ``save_translation`` tool (baseline arm / forced fallback).

    Args:
        translation_type: SCHEMA, QUERY, or BOTH — selects which fields are required.
        source_entry: Deterministic source entrypoint class name (baked into the field guidance).
        target_entry: Deterministic target entrypoint class name (baked into the field guidance).

    Returns:
        BaseTool: An async tool that persists the provided draft fields to state via ``Command``.
    """
    fields = required_draft_fields(translation_type)

    schema_fields: dict[str, Any] = {}
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


# ---------------------------------------------------------------------------- fragment contract


def build_save_schema_tool(source_hint: str, target_hint: str) -> BaseTool:
    """Build ``save_schema_translation``: persists both sides' schema/entity fragment.

    Args:
        source_hint: Framework-specific guidance for the source schema fragment (what classes /
            bootstrap types must be declared, e.g. ``SandboxDbContext`` for EF Core).
        target_hint: Framework-specific guidance for the target schema fragment.
    """

    class SaveSchemaArgs(BaseModel):
        source_schema_body: str = Field(
            min_length=1,
            description=(
                "SOURCE-side schema fragment: the entity classes plus any mapping/bootstrap "
                "types, exactly as they should appear below the injected prelude. No "
                "imports/usings/namespace/package lines, no serializer/runtime-support classes, "
                "no entrypoint class and no Main/main method. " + source_hint
            ),
        )
        target_schema_body: str = Field(
            min_length=1,
            description=(
                "TARGET-side schema fragment: the translated entity classes plus any "
                "mapping/bootstrap types. No imports/usings/namespace/package lines, no "
                "serializer/runtime-support classes, no entrypoint class and no Main/main "
                "method. " + target_hint
            ),
        )
        tool_call_id: Annotated[str, InjectedToolCallId] = Field(default="")

    async def _save_schema(
        source_schema_body: str,
        target_schema_body: str,
        tool_call_id: str = "",
    ) -> Command:
        return Command(
            update={
                "draft_source_schema": source_schema_body,
                "draft_target_schema": target_schema_body,
                "messages": [
                    ToolMessage(
                        content="Saved schema fragment for both sides.",
                        tool_call_id=tool_call_id,
                        name="save_schema_translation",
                    )
                ],
            }
        )

    return StructuredTool.from_function(
        coroutine=_save_schema,
        name="save_schema_translation",
        description=(
            "Persist the schema/entity classes for BOTH sides (source and target). Call this "
            "once before (or alongside) the per-query saves; call it again to overwrite if you "
            "need to revise the schema."
        ),
        args_schema=SaveSchemaArgs,
    )


def build_save_query_tool(
    expected_query_ids: tuple[int, ...],
    source_signature: str,
    target_signature: str,
) -> BaseTool:
    """Build ``save_query_translation``: persists ONE query's fragment for both sides.

    Args:
        expected_query_ids: The query ids present in the source input (e.g. ``(1, ..., 15)``).
            Saves for unknown ids are rejected with an instructive error.
        source_signature: The exact fragment shape required on the source side, e.g.
            ``public static class Query{N} {{ public static object Harness(SandboxDbContext ctx) }}``.
        target_signature: The exact fragment shape required on the target side.
    """
    expected = set(expected_query_ids)
    id_list = ", ".join(str(i) for i in expected_query_ids)

    class SaveQueryArgs(BaseModel):
        query_id: int = Field(
            description=f"The query number this fragment translates. One of: {id_list}."
        )
        source_query_body: str = Field(
            min_length=1,
            description=(
                "SOURCE-side fragment for this single query. Required shape: "
                f"{source_signature}. No imports/usings, no entity classes, no entrypoint/Main."
            ),
        )
        target_query_body: str = Field(
            min_length=1,
            description=(
                "TARGET-side fragment for this single query. Required shape: "
                f"{target_signature}. No imports/package lines, no entity classes, no "
                "entrypoint/main."
            ),
        )
        tool_call_id: Annotated[str, InjectedToolCallId] = Field(default="")

    async def _save_query(
        query_id: int,
        source_query_body: str,
        target_query_body: str,
        tool_call_id: str = "",
    ) -> Command | str:
        if query_id not in expected:
            return (
                f"Error: query_id {query_id} is not part of this task. "
                f"Valid ids: {id_list}. Nothing was saved."
            )
        return Command(
            update={
                "draft_queries": {
                    str(query_id): {
                        "source": source_query_body,
                        "target": target_query_body,
                    }
                },
                "messages": [
                    ToolMessage(
                        content=f"Saved fragment for query {query_id}.",
                        tool_call_id=tool_call_id,
                        name="save_query_translation",
                    )
                ],
            }
        )

    return StructuredTool.from_function(
        coroutine=_save_query,
        name="save_query_translation",
        description=(
            "Persist the translation of ONE query (both sides) by its number. Call once per "
            "query, in any order; re-call with the same query_id to overwrite. You can and "
            "SHOULD emit several save_query_translation calls in a single turn (parallel tool "
            "calls) once multiple queries are ready — do not spend one whole turn per query. "
            "You finish by having saved the schema fragment plus a fragment for every required "
            f"query id ({id_list})."
        ),
        args_schema=SaveQueryArgs,
    )


# ------------------------------------------------------------------------- convergence guard


def missing_fragment_pieces(
    state: dict[str, Any] | Any,
    expected_query_ids: tuple[int, ...],
) -> list[str]:
    """List the draft pieces still missing from an agent state using the fragment contract."""

    def _get(name: str) -> Any:
        if isinstance(state, dict):
            return state.get(name)
        return getattr(state, name, None)

    missing: list[str] = []
    if not _get("draft_source_schema") or not _get("draft_target_schema"):
        missing.append("schema (save_schema_translation)")
    fragments = _get("draft_queries") or {}
    absent = [
        str(qid)
        for qid in expected_query_ids
        if not (fragments.get(str(qid)) or {}).get("source")
        or not (fragments.get(str(qid)) or {}).get("target")
    ]
    if absent:
        missing.append(f"queries {', '.join(absent)} (save_query_translation)")
    return missing


class TranslationConvergenceMiddleware(AgentMiddleware):
    """Keeps the translation agent converging on the save tools instead of wandering off.

    Two observed failure modes from the 2026-07-01 traces:

    1. **No-tool-call finish** — the model ruminates (200k+ chars of reasoning) and ends its turn
       with no tool call while the draft is incomplete; ``create_agent`` treats that as final.
       ``after_model`` intercepts it: while draft pieces are missing, inject a corrective user
       message and jump back to the model (bounded by ``max_nudges``).
    2. **Research doom-loop** — 15+ consecutive web-search calls without ever saving.
       ``wrap_model_call`` counts prior tool calls; past ``research_budget`` it strips every tool
       except the save tools, forcing convergence.
    """

    state_schema = TranslationDraftState

    def __init__(
        self,
        *,
        expected_query_ids: tuple[int, ...] = (),
        monolithic: bool = False,
        research_budget: int = 14,
        max_nudges: int = 3,
    ) -> None:
        super().__init__()
        self.expected_query_ids = expected_query_ids
        self.monolithic = monolithic
        self.research_budget = research_budget
        self.max_nudges = max_nudges
        self.tools = []

    _SAVE_TOOL_NAMES = frozenset(
        {"save_translation", "save_schema_translation", "save_query_translation"}
    )
    # Tools that remain available after the research budget is spent. validate_draft is part of
    # the save/validate convergence loop, NOT research — stripping it exactly when the model
    # finished saving (as the 2026-07-02 runs did) made the preflight unreachable.
    _CONVERGENCE_TOOL_NAMES = _SAVE_TOOL_NAMES | {"validate_draft"}

    def _missing(self, state: dict[str, Any] | Any) -> list[str]:
        def _get(name: str) -> Any:
            if isinstance(state, dict):
                return state.get(name)
            return getattr(state, name, None)

        if self.monolithic:
            return [f for f in DRAFT_FIELDS if not _get(f)]
        return missing_fragment_pieces(state, self.expected_query_ids)

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler,
    ) -> ModelResponse:
        """Enforce the research budget by shrinking the tool surface once it is spent.

        Only RESEARCH tool results count against the budget. Save/validate calls are the
        convergence work itself — with 15+ per-query saves each producing a ToolMessage, counting
        them burned the whole budget on saving and stripped validate_draft before it could run.
        """
        n_research_msgs = sum(
            1
            for m in request.messages
            if isinstance(m, ToolMessage)
            and (m.name or "") not in self._CONVERGENCE_TOOL_NAMES
        )
        if n_research_msgs > self.research_budget:
            convergence_only = [
                t
                for t in (request.tools or [])
                if (getattr(t, "name", None) or getattr(t, "__name__", ""))
                in self._CONVERGENCE_TOOL_NAMES
            ]
            if convergence_only and len(convergence_only) != len(request.tools or []):
                logger.warning(
                    "TranslationConvergenceMiddleware: research budget spent (%d research tool "
                    "msgs); restricting tool surface to save/validate tools only",
                    n_research_msgs,
                )
                request = request.override(tools=convergence_only)
        return await handler(request)

    @hook_config(can_jump_to=["model"])
    async def aafter_model(
        self, state: AgentState, runtime: Runtime
    ) -> dict[str, Any] | None:
        """Nudge the model back to the save tools when it stops without a complete draft."""
        messages = state.get("messages") or []
        last = messages[-1] if messages else None
        if not isinstance(last, AIMessage) or last.tool_calls:
            return None
        missing = self._missing(state)
        if not missing:
            return None
        nudges = int(state.get("save_nudge_count") or 0)
        if nudges >= self.max_nudges:
            logger.error(
                "TranslationConvergenceMiddleware: draft still missing %s after %d nudges; "
                "letting the agent end (node-level fallback takes over)",
                missing,
                nudges,
            )
            return None
        logger.warning(
            "TranslationConvergenceMiddleware: model stopped without tool calls but draft "
            "is missing %s — nudging (attempt %d/%d)",
            missing,
            nudges + 1,
            self.max_nudges,
        )
        return {
            "save_nudge_count": nudges + 1,
            "messages": [
                HumanMessage(
                    content=(
                        "You are not done: the following draft pieces have not been saved yet: "
                        f"{'; '.join(missing)}. Do not answer in prose. Call the save tool(s) "
                        "now with the completed code — you may emit multiple "
                        "save_query_translation calls in this one turn. Keep any analysis brief."
                    )
                )
            ],
            "jump_to": "model",
        }


__all__ = [
    "TranslationDraftState",
    "TranslationDraftMiddleware",
    "TranslationConvergenceMiddleware",
    "build_save_translation_tool",
    "build_save_schema_tool",
    "build_save_query_tool",
    "merge_query_fragments",
    "missing_fragment_pieces",
    "required_draft_fields",
    "DRAFT_FIELDS",
]
