"""Query validation and equivalence tools for source and target query execution metadata."""

from __future__ import annotations

import asyncio
import json
import logging
from collections import OrderedDict
from typing import Awaitable, cast

import orjson
from deepdiff import DeepDiff
from langchain.tools import ToolRuntime
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from langgraph.types import Command
from langchain_core.messages import ToolMessage

from react_agent.constants import (
    SourceFramework,
    TargetFramework,
)
from react_agent.context import Context
from react_agent.state import State
from react_agent.utils.types import QueryEquivalenceDeepDiff

logger = logging.getLogger(__name__)


class SourceQueryInput(BaseModel):
    """Input payload for validating source-side schema/queries."""

    validation_schema_code: str = Field(
        min_length=1,
        description="Source schema validation code. This should include imports, serialization, runtime config, context/session/config/bootstrap setup, and any other code needed to run the query, but should keep "
        "the Schema and Related Settings logic equivalent to the original source_schema_code (without JSON serialization related annotations). Should be fully valid and runnable code with entrypoint. Include simple one-entity fetch queries to validate each entity (see examples). Do not include source query related code here."
    )
    validation_harness_code: str = Field(
        min_length=1,
        description="Source query validation harness code. Must include the query method(s) and a main entrypoint method that executes the queries, extracts `count`, `firstSample`, `lastSample`, potentially additional query information or errors, and writes the output as JSON to the path defined in the environment variable.",
    )
    source_framework: SourceFramework = Field(
        description="Source framework for translation"
    )
    entry_type_name: str = Field(
        min_length=1,
        description="Entrypoint type name declared in validation_schema_code/validation_harness_code",
    )
    entry_method_name: str = Field(
        min_length=1,
        description="Entrypoint method name declared in validation_schema_code/validation_harness_code",
    )


class TargetQueryInput(BaseModel):
    """Input payload for validating target-side schema/queries."""

    validation_schema_code: str = Field(
        min_length=1,
        description="Target schema validation code. This should include imports, serialization, runtime config, context/session/config/bootstrap setup, and any other code needed to run the query, but should keep "
        "the Schema and Related Settings logic equivalent to the original translated_schema_code (without JSON serialization related annotations). Should be fully valid and runnable code with entrypoint. Include simple one-entity fetch queries to validate each entity (see examples). Do not include target query related code here.",
    )
    validation_harness_code: str = Field(
        min_length=1,
        description="Target query validation harness code. Must include the query method(s) and a main entrypoint method that executes the queries, extracts `count`, `firstSample`, `lastSample`, potentially additional query information or errors, and writes the output as JSON to the path defined in the environment variable.",
    )
    target_framework: TargetFramework = Field(description="Target framework for translation")
    entry_type_name: str = Field(
        min_length=1,
        description="Entrypoint type name declared in validation_schema_code/validation_harness_code",
    )
    entry_method_name: str = Field(
        min_length=1,
        description="Entrypoint method name declared in validation_schema_code/validation_harness_code",
    )


class QueryEquivalenceInput(BaseModel):
    """Input payload for source/target query equivalence checks."""

    source_validation_output: str = Field(
        min_length=1,
        description=(
            "Output of validate_source_query. Preferred format: full tool output string that starts with "
            "[Source Query Validation Passed] followed by JSON summary."
        ),
    )
    target_validation_output: str = Field(
        min_length=1,
        description=(
            "Output of validate_target_query. Preferred format: full tool output string that starts with "
            "[Target Query Validation Passed] followed by JSON summary."
        ),
    )


def _check_validation_markers(
    validation_output: str,
    passed_marker: str,
    failed_marker: str,
) -> str | None:
    text = validation_output.strip()
    if not text:
        return "validation output is empty"
    if failed_marker in text:
        return f"found failure marker {failed_marker}"
    if passed_marker not in text:
        logger.warning("Validation output does not contain expected markers. Output: %s", validation_output)


# @tool("check_query_equivalence", args_schema=QueryEquivalenceInput)
@tool
async def check_query_equivalence(
    source_validation_output: str,
    target_validation_output: str,
    runtime: ToolRuntime, # type: ignore
) -> Command | str:
    """Compare source and target query metadata for logical equivalence."""
    runtime: ToolRuntime[Context, State] = runtime  # type: ignore
    output = _check_validation_markers(
        source_validation_output,
        "Validation Passed]",
        "Validation Failed]",
    )
    if output is not None:
        return f"[Query Equivalence Failed] Invalid source validation payload: {output}"

    output = _check_validation_markers(
        target_validation_output,
        "Validation Passed]",
        "Validation Failed]",
    )
    if output is not None:
        return f"[Query Equivalence Failed] Invalid target validation payload: {output}"

    source_query_validation_results = runtime.state.source_query_validation_results or {}
    target_query_validation_results = runtime.state.target_query_validation_results or {}
    common_keys = list(set(source_query_validation_results.keys()).intersection(set(target_query_validation_results.keys())))
    common_keys.sort()

    if not common_keys:
        return f"[Query Equivalence Results]\n{json.dumps({'error': 'No matching query keys found between source and target.'})}"

    diff_results = {}
    diff_tasks: dict[str, Awaitable[QueryEquivalenceDeepDiff]] = OrderedDict()
    for key in common_keys:
        source_q = source_query_validation_results[key]
        target_q = target_query_validation_results[key]

        if not isinstance(source_q, dict) or not isinstance(target_q, dict):
            diff_results[key] = {"error": "Query payload is not an object."}
            continue

        src_count = source_q.get("count")
        tgt_count = target_q.get("count")

        src_first = source_q.get("firstSample")
        tgt_first = target_q.get("firstSample")
        src_last = source_q.get("lastSample")
        tgt_last = target_q.get("lastSample")

        def compute_diffs():
            count_diff = DeepDiff(src_count, tgt_count)

            diff_first = DeepDiff(src_first, tgt_first, ignore_order=True, report_repetition=True, significant_digits=3, cutoff_intersection_for_pairs=1, cutoff_distance_for_pairs=1, get_deep_distance=True)
            diff_last = DeepDiff(src_last, tgt_last, ignore_order=True, report_repetition=True, significant_digits=3, cutoff_intersection_for_pairs=1, cutoff_distance_for_pairs=1, get_deep_distance=True)

            if not count_diff and diff_first.get("deep_distance") == 0 and diff_last.get("deep_distance") == 0:
                return {}

            diff_swapped_first = DeepDiff(src_first, tgt_last, ignore_order=True, report_repetition=True, significant_digits=3, cutoff_intersection_for_pairs=1, cutoff_distance_for_pairs=1, get_deep_distance=True)
            diff_swapped_last = DeepDiff(src_last, tgt_first, ignore_order=True, report_repetition=True, significant_digits=3, cutoff_intersection_for_pairs=1, cutoff_distance_for_pairs=1, get_deep_distance=True)

            if not count_diff and diff_swapped_first.get("deep_distance") == 0 and diff_swapped_last.get("deep_distance") == 0:
                return {}

            sample_diffs = OrderedDict((
                ("deepdiff_mapping", { "old": runtime.state.source_target or "source", "new": runtime.state.destination_target or "target" }),
                ("countDiff", count_diff.to_json()), 
                ("firstSampleDiff", diff_first.to_json()), 
                ("lastSampleDiff", diff_last.to_json())
            ))

            return sample_diffs

        diff_tasks[key] = asyncio.to_thread(compute_diffs)
    
    awaited_tasks = await asyncio.gather(*diff_tasks.values(), return_exceptions=True)
    for i, key in enumerate(common_keys):
        if isinstance(awaited_tasks[i], Exception):
            diff_results[key] = {"error": f"Error computing diffs: {awaited_tasks[i]}"}
        elif cast(QueryEquivalenceDeepDiff, awaited_tasks[i]).get("error") is not None:
            diff_results[key] = {"error": cast(QueryEquivalenceDeepDiff, awaited_tasks[i])["error"]}
        elif not awaited_tasks[i]:
            diff_results[key] = {"status": "Equivalent"}
        else:
            diff_results[key] = OrderedDict((("status", "Differences Found"), ("diffs", awaited_tasks[i])))

    tool_call_id = (
        getattr(runtime, "tool_call_id", None)
        or (runtime.config.get("metadata", {}).get("langgraph_tool_call_id") if runtime.config else None)
        or (runtime.config.get("metadata", {}).get("tool_call_id") if runtime.config else None)
    )
    return Command(
        update={
            "query_equivalence_deep_diffs": diff_results,
            "messages": [
                ToolMessage(
                    content=f"[Query Equivalence Results]\n{orjson.dumps(diff_results).decode('utf-8')}",
                    tool_call_id=tool_call_id,
                    name=check_query_equivalence.name
                )
            ]
        }
    )
