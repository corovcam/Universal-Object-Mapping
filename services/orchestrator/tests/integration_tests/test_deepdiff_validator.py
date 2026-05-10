import logging
from typing import cast

import orjson
import pytest
from langchain.tools import ToolRuntime
from langchain_core.tools import StructuredTool

from react_agent.context import Context
from react_agent.custom_tools.query_validator import check_query_equivalence
from react_agent.state import State

logger = logging.getLogger(__name__)


def _make_validation_output(prefix: str, payload: dict) -> str:
    """Build a validation output string with inline JSON payload."""
    return f"{prefix}\\n===JSON===\\n{orjson.dumps(payload).decode('utf-8')}"


def _parse_query_equivalence_payload(result: str) -> dict:
    """Parse the JSON payload from check_query_equivalence output."""
    prefix = "[Query Equivalence Results]\\n"
    assert result.startswith(prefix)
    return cast(dict, orjson.loads(result[len(prefix) :]))


@pytest.mark.asyncio
async def test_deepdiff_equivalence_exact_match(sample_tool_runtime):
    source_json = {
        "query1": {
            "count": 1,
            "firstSample": {"id": 1, "name": "Test"},
            "lastSample": {"id": 1, "name": "Test"},
        }
    }
    target_json = {
        "query1": {
            "count": 1,
            "firstSample": {"id": 1, "name": "Test"},
            "lastSample": {"id": 1, "name": "Test"},
        }
    }

    source_output = _make_validation_output("[Source Query Validation Passed]", source_json)
    target_output = _make_validation_output("[Target Query Validation Passed]", target_json)

    sample_tool_runtime.state.source_query_validation_results = source_json
    sample_tool_runtime.state.target_query_validation_results = target_json

    func = cast(StructuredTool, check_query_equivalence)
    assert func is not None, "check_query_equivalence tool not found"
    assert func.coroutine is not None, "check_query_equivalence does not have a coroutine method"
    result = await func.coroutine(
        source_validation_output=source_output,
        target_validation_output=target_output,
        runtime=sample_tool_runtime,
    )
    logger.debug(f"`test_deepdiff_equivalence_exact_match` result: {result}")

    payload = _parse_query_equivalence_payload(result)
    assert payload["query1"]["status"] == "Equivalent"


@pytest.mark.asyncio
async def test_deepdiff_equivalence_swapped_samples(sample_tool_runtime):
    source_json = {
        "query1": {
            "count": 2,
            "firstSample": {"id": 1, "name": "A"},
            "lastSample": {"id": 2, "name": "B"},
        }
    }

    # Target has samples swapped. Current validator compares first/last directly.
    target_json = {
        "query1": {
            "count": 2,
            "firstSample": {"id": 2, "name": "B"},
            "lastSample": {"id": 1, "name": "A"},
        }
    }

    source_output = _make_validation_output("[Source Query Validation Passed]", source_json)
    target_output = _make_validation_output("[Target Query Validation Passed]", target_json)

    sample_tool_runtime.state.source_query_validation_results = source_json
    sample_tool_runtime.state.target_query_validation_results = target_json

    func = cast(StructuredTool, check_query_equivalence)
    assert func is not None, "check_query_equivalence tool not found"
    assert func.coroutine is not None, "check_query_equivalence does not have a coroutine method"
    
    result = await func.coroutine(
        source_validation_output=source_output,
        target_validation_output=target_output,
        runtime=sample_tool_runtime,
    )

    logger.debug(f"`test_deepdiff_equivalence_swapped_samples` result: {result}")
    payload = _parse_query_equivalence_payload(result)
    assert payload["query1"]["status"] == "Differences Found"
    assert "firstSampleDiff" in payload["query1"]["diffs"]
    assert "lastSampleDiff" in payload["query1"]["diffs"]


@pytest.mark.asyncio
async def test_deepdiff_equivalence_difference_found(sample_tool_runtime):
    source_json = {
        "query1": {
            "count": 1,
            "firstSample": {"id": 1, "name": "Test"},
        }
    }
    target_json = {
        "query1": {
            "count": 2,
            "firstSample": {"id": 1, "name": "Test"},
        }
    }

    source_output = _make_validation_output("[Source Query Validation Passed]", source_json)
    target_output = _make_validation_output("[Target Query Validation Passed]", target_json)

    sample_tool_runtime.state.source_query_validation_results = source_json
    sample_tool_runtime.state.target_query_validation_results = target_json

    func = cast(StructuredTool, check_query_equivalence)
    assert func is not None, "check_query_equivalence tool not found"
    assert func.coroutine is not None, "check_query_equivalence does not have a coroutine method"
    result = await func.coroutine(
        source_validation_output=source_output,
        target_validation_output=target_output,
        runtime=sample_tool_runtime,
    )

    logger.debug(f"`test_deepdiff_equivalence_difference_found` result: {result}")
    payload = _parse_query_equivalence_payload(result)
    assert payload["query1"]["status"] == "Differences Found"
    assert payload["query1"]["diffs"]["countDiff"]


@pytest.mark.asyncio
async def test_deepdiff_equivalence_real_fixture_data(
    sample_tool_runtime: ToolRuntime[Context, State],
    sample_efcore_results: dict,
    sample_mongo_results: dict,
):
    """Compare real fixture outputs captured from EF Core and MongoDB validations."""
    # source_real_subset = {"query5": sample_efcore_results["query5"]}
    # target_real_subset = {"query5": sample_mongo_results["query5"]}

    source_output = _make_validation_output(
        "[Source Query Validation Passed]",
        sample_efcore_results,
    )
    target_output = _make_validation_output(
        "[Target Query Validation Passed]",
        sample_mongo_results,
    )

    sample_tool_runtime.state.source_query_validation_results = sample_efcore_results
    sample_tool_runtime.state.target_query_validation_results = sample_mongo_results

    func = cast(StructuredTool, check_query_equivalence)
    assert func is not None, "check_query_equivalence tool not found"
    assert func.coroutine is not None, "check_query_equivalence does not have a coroutine method"
    
    result = await func.coroutine(
        source_validation_output=source_output,
        target_validation_output=target_output,
        runtime=sample_tool_runtime,
    )

    payload = _parse_query_equivalence_payload(result)
    assert set(payload.keys()) == {"query1", "query2", "query3", "query4", "query5"}
    statuses = {entry.get("status") for entry in payload.values() if isinstance(entry, dict)}
    assert statuses == {"Equivalent"}
    assert payload["query5"]["status"] == "Equivalent"
