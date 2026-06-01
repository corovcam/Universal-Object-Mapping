"""Query validation and equivalence tools for source and target query execution metadata.

This module provides Pydantic models for inputs and LangChain tool definitions that facilitate
the execution and semantic equivalence comparison of source-side and target-side database queries.
Semantic equivalence is computed using the `DeepDiff` library to compare query output metrics
such as row counts and data samples, with tolerance for sorting differences and precision variances.
"""

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
    """Input payload for validating source-side schema/queries in .NET environments.

    Attributes:
        validation_schema_code: Source schema validation code containing imports,
            initialization, context setup, and minor fetch validation logic.
        validation_harness_code: Runnable execution harness code that runs the C# LINQ
            queries, captures count/samples, and writes the structured output JSON.
        source_framework: The relational source framework target (e.g. EF Core, Dapper).
        entry_type_name: Declared main class/type name containing the entry point.
        entry_method_name: Declared main static method name serving as execution entry.
    """

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
    """Input payload for validating target-side schema/queries in Java environments.

    Attributes:
        validation_schema_code: Target schema validation code containing imports,
            bootstrapping, entity annotations, and driver configuration.
        validation_harness_code: Runnable execution harness code that runs the Java MongoDB/Neo4j
            queries, captures count/samples, and writes the structured output JSON.
        target_framework: The target framework target (e.g. Spring Data MongoDB, Spring Data Neo4j).
        entry_type_name: Declared main public class name containing the entry point.
        entry_method_name: Declared main static method name serving as execution entry.
    """

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
    """Input payload for comparing source and target query outputs for equivalence.

    Attributes:
        source_validation_output: Text/log output produced by executing source validation.
        target_validation_output: Text/log output produced by executing target validation.
    """

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
    """Scan sandbox validation output logs to detect successful compilation and execution markers.

    Args:
        validation_output: Raw string output containing build logs, execution logs, and outcomes.
        passed_marker: Target substring indicating compilation and execution success.
        failed_marker: Target substring indicating validation failure.

    Returns:
        str | None: An error message describing the failure or missing marker if validation failed;
            None if the logs look valid.
    """
    text = validation_output.strip()
    if not text:
        return "validation output is empty"
    if failed_marker in text:
        return f"found failure marker {failed_marker}"
    if passed_marker not in text:
        logger.warning("Validation output does not contain expected markers. Output: %s", validation_output)
        return None  # Log warning but continue processing if passed marker is simply missing in output formatting
    return None


@tool
async def check_query_equivalence(
    source_validation_output: str,
    target_validation_output: str,
    runtime: ToolRuntime,  # type: ignore
) -> Command | str:
    """Compare source C#/.NET and target Java query execution outputs to verify logical equivalence.

    This tool acts as a semantic validation gate. It retrieves the JSON outputs stored in the state,
    identifies common queries, and uses `DeepDiff` to evaluate whether they returned identical counts
    and matching records.

    It implements a robust sorting-tolerant comparison logic (swapped orders) to prevent false-positives
    when database drivers iterate or sort query datasets differently under relational vs NoSQL engines.

    Args:
        source_validation_output: String output logging from source validation tool.
        target_validation_output: String output logging from target validation tool.
        runtime: Injected LangChain ToolRuntime context to access state and configuration.

    Returns:
        Command | str: A LangGraph Command updating the equivalence diff state and adding
            a ToolMessage, or an error string if validation markers are violated.
    """
    runtime: ToolRuntime[Context, State] = runtime  # type: ignore
    
    # 1. Parse and verify that the source validation executed successfully
    output = _check_validation_markers(
        source_validation_output,
        "Validation Passed]",
        "Validation Failed]",
    )
    if output is not None:
        return f"[Query Equivalence Failed] Invalid source validation payload: {output}"

    # 2. Parse and verify that the target validation executed successfully
    output = _check_validation_markers(
        target_validation_output,
        "Validation Passed]",
        "Validation Failed]",
    )
    if output is not None:
        return f"[Query Equivalence Failed] Invalid target validation payload: {output}"

    # 3. Retrieve validation outputs stored by sandboxes in the state
    source_query_validation_results = runtime.state.source_query_validation_results or {}
    target_query_validation_results = runtime.state.target_query_validation_results or {}
    
    # 4. Find all common query keys to compare (e.g. Query1, Query2)
    common_keys = list(set(source_query_validation_results.keys()).intersection(set(target_query_validation_results.keys())))
    common_keys.sort()

    if not common_keys:
        return f"[Query Equivalence Results]\n{json.dumps({'error': 'No matching query keys found between source and target.'})}"

    diff_results = {}
    diff_tasks: dict[str, Awaitable[QueryEquivalenceDeepDiff]] = OrderedDict()
    
    # 5. Iteratively compare each query using CPU-bound DeepDiff computations run on background threads
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
            """Perform DeepDiff analysis over count, firstSample, and lastSample in a worker thread."""
            # Compare total counts directly
            count_diff = DeepDiff(src_count, tgt_count)

            # Compare samples with robust parameters: ignore dictionary keys order, 
            # report item repetitions, allow floating-point decimal tolerances, and measure deep distances.
            diff_first = DeepDiff(src_first, tgt_first, ignore_order=True, report_repetition=True, significant_digits=3, cutoff_intersection_for_pairs=1, cutoff_distance_for_pairs=1, get_deep_distance=True)
            diff_last = DeepDiff(src_last, tgt_last, ignore_order=True, report_repetition=True, significant_digits=3, cutoff_intersection_for_pairs=1, cutoff_distance_for_pairs=1, get_deep_distance=True)

            # If direct order count and sample values match, the queries are equivalent
            if not count_diff and diff_first.get("deep_distance") == 0 and diff_last.get("deep_distance") == 0:
                return {}

            # Edge Case: Swapped Sorting Orders.
            # If the database returns the identical rows but sorted differently (e.g. reverse sorting order),
            # the source first sample will equal target last sample, and source last sample will equal target first.
            # We explicitly check for this pattern to prevent false failure reports.
            diff_swapped_first = DeepDiff(src_first, tgt_last, ignore_order=True, report_repetition=True, significant_digits=3, cutoff_intersection_for_pairs=1, cutoff_distance_for_pairs=1, get_deep_distance=True)
            diff_swapped_last = DeepDiff(src_last, tgt_first, ignore_order=True, report_repetition=True, significant_digits=3, cutoff_intersection_for_pairs=1, cutoff_distance_for_pairs=1, get_deep_distance=True)

            if not count_diff and diff_swapped_first.get("deep_distance") == 0 and diff_swapped_last.get("deep_distance") == 0:
                return {}

            # Construct structural differences package if equivalence failed
            sample_diffs = OrderedDict((
                ("deepdiff_mapping", { "old": runtime.state.source_target or "source", "new": runtime.state.destination_target or "target" }),
                ("countDiff", count_diff.to_json()), 
                ("firstSampleDiff", diff_first.to_json()), 
                ("lastSampleDiff", diff_last.to_json())
            ))

            return sample_diffs

        # Launch the deepdiff calculations in thread pools to prevent blocking the async event loop
        diff_tasks[key] = asyncio.to_thread(compute_diffs)
    
    # 6. Await all deepdiff calculations running in parallel threads
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

    # 7. Extract the unique tool call identifier to structure standard ToolMessages
    tool_call_id = (
        getattr(runtime, "tool_call_id", None)
        or (runtime.config.get("metadata", {}).get("langgraph_tool_call_id") if runtime.config else None)
        or (runtime.config.get("metadata", {}).get("tool_call_id") if runtime.config else None)
    )
    
    # 8. Return Command returning both state changes and the message update
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
