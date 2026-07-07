"""In-agent draft validation: compile + run + per-query equivalence inside the ReAct loop.

Previously the generation agent had to finish its entire draft, exit, and wait for the outer
validate → equivalence → judge pipeline (tens of minutes) before learning that a single query
misused an API. This tool closes that loop *inside* the agent: it assembles the currently saved
fragments into both runnable harnesses (same deterministic assembler the outer pipeline uses),
executes them in the Daytona sandboxes, and returns a compact per-query compile/run/equivalence
report. The outer pipeline remains the final acceptance gate — this is a fast preflight, not a
replacement.

Invocation is budgeted (default 3 per generation loop): each call costs two sandbox runs, and an
unbudgeted validator would recreate the research-doom-loop failure mode with compile cycles.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Annotated, Any, Callable

import orjson
from langchain.tools import ToolRuntime
from langchain_core.tools import BaseTool, StructuredTool
from pydantic import Field

from react_agent.constants import (
    DotnetFramework,
    FrameworkEnum,
    JavaFramework,
)
from react_agent.custom_tools.dotnet_validator import compile_and_run_dotnet
from react_agent.custom_tools.java_validator import compile_and_run_java
from react_agent.custom_tools.query_validator import compute_equivalence_results
from react_agent.translation_draft import missing_fragment_pieces
from react_agent.utils.harness_assembler import assemble_query_harness

logger = logging.getLogger(__name__)

# Tail size of a failing compile/run log returned to the agent. Full sandbox logs run to tens of
# kilobytes of restore/build noise; the actionable compiler errors sit at the end.
_LOG_TAIL_CHARS = 2500


def _tail(text: str, limit: int = _LOG_TAIL_CHARS) -> str:
    text = text.strip()
    return text if len(text) <= limit else "…[truncated]\n" + text[-limit:]


def build_sandbox_runtime(
    graph_state: Any,
    graph_context: Any,
    graph_config: Any,
    stream_writer: Callable[..., Any] | None = None,
) -> ToolRuntime:
    """A REAL ToolRuntime carrying the OUTER graph's context/state/config for the compile helpers.

    The helpers pass this to ``execute_in_sandbox.ainvoke``/``download_file_from_sandbox.ainvoke``,
    whose args_schema pydantic-validates ``runtime`` as ``dataclass_type`` ToolRuntime — a
    duck-typed shim (the 2026-07-03 traces' ``_GraphToolRuntime``) fails that validation and killed
    every ``validate_draft`` call ("Input should be … an instance of ToolRuntime"). The inner
    agent's own ToolRuntime is equally unusable: its context is None and its state is the agent
    dict, while the helpers read ``runtime.context.<connection strings>`` and
    ``runtime.state.translation_type``.
    """
    return ToolRuntime(
        state=graph_state,
        context=graph_context,
        config=graph_config,
        stream_writer=stream_writer or (lambda *_a, **_k: None),
        tool_call_id=None,
        store=None,
    )


def build_validate_draft_tool(
    source_fw: FrameworkEnum,
    target_fw: FrameworkEnum,
    expected_query_ids: tuple[int, ...],
    *,
    graph_state: Any,
    graph_context: Any,
    graph_config: Any,
    stream_writer: Callable[..., Any] | None = None,
    max_calls: int = 3,
) -> BaseTool | None:
    """Build the budgeted ``validate_draft`` tool for the fragment contract.

    Returns None when the pair is not .NET→Java (the fragment contract, and therefore in-agent
    assembly, only supports that direction today).

    Args:
        graph_state: The OUTER graph ``State`` dataclass (the compile helpers read
            ``translation_type`` from it).
        graph_context: The OUTER graph ``Context`` (connection strings, Daytona URL, timeouts).
        graph_config: The node's RunnableConfig (thread_id fallback + sandbox tool config).
        stream_writer: The graph runtime's stream writer (sandbox stdout/stderr events).
    """
    try:
        dotnet_fw = DotnetFramework(source_fw.value)
        java_fw = JavaFramework(target_fw.value)
    except ValueError:
        return None

    sandbox_runtime = build_sandbox_runtime(
        graph_state, graph_context, graph_config, stream_writer
    )

    calls_used = 0

    # NOTE: the args schema is INFERRED from this signature on purpose. The tool node injects
    # the (inner-agent) ToolRuntime by adding a `runtime` key to the call args; an explicit
    # args_schema without a `runtime` field silently *dropped* that key during pydantic
    # validation, so the tool always saw runtime=None/empty state and answered "No schema
    # fragment saved yet" no matter what was saved (the 2026-07-04 traces' doom loop). With the
    # inferred schema, `runtime: ToolRuntime` is injection-aware and hidden from the model.
    # The annotation metadata must only reference module-level names: `from __future__ import
    # annotations` makes get_type_hints re-evaluate these strings in module globals, where
    # closure variables like max_calls do not exist.
    async def _validate_draft(
        query_ids: Annotated[
            list[int] | None,
            Field(
                description=(
                    "Optional subset of query ids to validate (must already be saved). Omit to "
                    "validate everything saved so far. Prefer ONE batched call over many small "
                    "ones — validation runs are budgeted per task (see tool description)."
                ),
            ),
        ] = None,
        *,
        runtime: ToolRuntime,
    ) -> str:
        nonlocal calls_used
        if calls_used >= max_calls:
            return (
                f"[Draft Validation Budget Exhausted] You have used all {max_calls} validation "
                "runs. Save any remaining fragments and finish; the outer pipeline performs the "
                "final validation."
            )

        state = getattr(runtime, "state", None) or {}

        def _get(name: str) -> Any:
            if isinstance(state, dict):
                return state.get(name)
            return getattr(state, name, None)

        source_schema = _get("draft_source_schema") or ""
        target_schema = _get("draft_target_schema") or ""
        fragments: dict[str, dict[str, str]] = _get("draft_queries") or {}

        if not source_schema or not target_schema:
            return (
                "[Draft Validation Error] No schema fragment saved yet — call "
                "save_schema_translation first."
            )

        saved_ids = sorted(
            int(k)
            for k, sides in fragments.items()
            if (sides or {}).get("source") and (sides or {}).get("target")
        )
        if not saved_ids:
            return (
                "[Draft Validation Error] No query fragments saved yet — call "
                "save_query_translation first."
            )
        ids = sorted(set(query_ids) & set(saved_ids)) if query_ids else saved_ids
        if query_ids and not ids:
            return (
                f"[Draft Validation Error] None of the requested query ids {query_ids} are "
                f"saved yet (saved: {saved_ids})."
            )

        calls_used += 1
        source_code, _source_entry = await assemble_query_harness(
            source_fw, source_schema, {qid: fragments[str(qid)]["source"] for qid in ids}
        )
        target_code, target_entry = await assemble_query_harness(
            target_fw, target_schema, {qid: fragments[str(qid)]["target"] for qid in ids}
        )

        # The compile helpers get the OUTER graph's runtime (context/state/config), never the
        # inner agent's ToolRuntime — see sandbox_runtime above.
        src_out, tgt_out = await asyncio.gather(
            compile_and_run_dotnet(source_code, dotnet_fw, sandbox_runtime),  # type: ignore[arg-type]
            compile_and_run_java(target_code, java_fw, target_entry, sandbox_runtime),  # type: ignore[arg-type]
            return_exceptions=True,
        )

        report: list[str] = [
            f"[Draft Validation Run {calls_used}/{max_calls}] queries: {ids}"
        ]

        sides: dict[str, dict | None] = {}
        for label, res in (("source", src_out), ("target", tgt_out)):
            if isinstance(res, BaseException):
                report.append(f"{label.upper()}: sandbox execution error: {res}")
                sides[label] = None
                continue
            output, json_part = res
            if "Validation Failed" in output or json_part is None:
                report.append(f"{label.upper()}: COMPILE/RUN FAILED\n{_tail(str(output))}")
                sides[label] = None
                continue
            try:
                sides[label] = orjson.loads(json_part)
                report.append(f"{label.upper()}: compiled and ran OK")
            except orjson.JSONDecodeError:
                report.append(f"{label.upper()}: could not parse results JSON")
                sides[label] = None

        source_results, target_results = sides.get("source"), sides.get("target")
        if source_results is not None and target_results is not None:
            diffs = await compute_equivalence_results(
                source_results,
                target_results,
                mapping_labels=(source_fw.value, target_fw.value),
            )
            report.append(
                "PER-QUERY EQUIVALENCE:\n"
                + orjson.dumps(diffs, option=orjson.OPT_INDENT_2).decode("utf-8")
            )

        remaining = missing_fragment_pieces(
            {
                "draft_source_schema": source_schema,
                "draft_target_schema": target_schema,
                "draft_queries": fragments,
            },
            expected_query_ids,
        )
        if remaining:
            report.append(f"STILL UNSAVED: {'; '.join(remaining)}")

        return "\n\n".join(report)

    return StructuredTool.from_function(
        coroutine=_validate_draft,
        name="validate_draft",
        description=(
            "Compile and execute the currently saved draft fragments in real sandboxes (both "
            "sides) and compare per-query results for equivalence. Expensive: budget of "
            f"{max_calls} calls — batch it (ideally once, after saving everything). Fix reported "
            "failures by re-saving the affected fragments, then finish."
        ),
    )


__all__ = ["build_sandbox_runtime", "build_validate_draft_tool"]
