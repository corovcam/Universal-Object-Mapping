import logging
import re
from typing import cast

import orjson
import pytest
from langchain.tools import ToolRuntime
from langchain_core.tools import StructuredTool
from langgraph.types import Command

from react_agent.context import Context
from react_agent.custom_tools.query_validator import check_query_equivalence
from react_agent.state import State

logger = logging.getLogger(__name__)


def _make_validation_output(prefix: str, payload: dict) -> str:
    """Build a validation output string with inline JSON payload."""
    return f"{prefix}\\n===JSON===\\n{orjson.dumps(payload).decode('utf-8')}"


def _parse_query_equivalence_payload(result) -> dict:
    """Parse the per-query diff results from check_query_equivalence's Command."""
    assert isinstance(result, Command), f"expected Command, got {type(result)}: {result}"
    update = cast(dict, result.update)
    assert update is not None
    diffs = update["query_equivalence_deep_diffs"]
    # The ToolMessage content must carry the same payload (it is what the judge reads).
    content = str(update["messages"][0].content)
    assert content.startswith("[Query Equivalence Results]")
    fence = re.search(r"```json\n(.*?)```", content, re.DOTALL)
    assert fence is not None
    assert orjson.loads(fence.group(1)) == orjson.loads(orjson.dumps(diffs))
    return cast(dict, orjson.loads(orjson.dumps(diffs)))


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

    # Target has samples swapped. The validator explicitly tolerates reversed sort orders
    # (source first == target last and vice versa), so this must count as Equivalent.
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
    assert payload["query1"]["status"] == "Equivalent"


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
    # True per-query statuses. The old "all Equivalent" expectation reflected the late-binding
    # bug (every query echoed query5's diff). The fixture data genuinely differs on q1/q2/q4:
    # Mongo-injected `id` fields, a 1-hour timestamp offset, and different rows on sort ties.
    assert payload["query3"]["status"] == "Equivalent"
    assert payload["query5"]["status"] == "Equivalent"
    for key in ("query1", "query2", "query4"):
        assert payload[key]["status"] == "Differences Found", key


@pytest.mark.asyncio
async def test_deepdiff_per_query_isolation_no_late_binding(sample_tool_runtime):
    """Regression: every query must be compared against ITS OWN payloads.

    The old closure + deferred `asyncio.to_thread` late-binding made every query compare the
    LAST sorted key's data ("query9's diff repeated 15x"). Here the last sorted key (query9)
    is equivalent while query1/query10 are not — each must get its own verdict.
    """
    source_json = {
        "query1": {"count": 3, "firstSample": {"id": 1}, "lastSample": {"id": 3}},
        "query10": {"count": 7, "firstSample": {"id": 10}, "lastSample": {"id": 70}},
        "query9": {"count": 5, "firstSample": {"id": 9}, "lastSample": {"id": 90}},
    }
    target_json = {
        "query1": {"count": 999, "firstSample": {"id": 1}, "lastSample": {"id": 3}},
        "query10": {"count": 7, "firstSample": {"id": -1}, "lastSample": {"id": 70}},
        "query9": {"count": 5, "firstSample": {"id": 9}, "lastSample": {"id": 90}},
    }
    source_output = _make_validation_output("[Source Query Validation Passed]", source_json)
    target_output = _make_validation_output("[Target Query Validation Passed]", target_json)
    sample_tool_runtime.state.source_query_validation_results = source_json
    sample_tool_runtime.state.target_query_validation_results = target_json

    func = cast(StructuredTool, check_query_equivalence)
    assert func.coroutine is not None
    result = await func.coroutine(
        source_validation_output=source_output,
        target_validation_output=target_output,
        runtime=sample_tool_runtime,
    )
    payload = _parse_query_equivalence_payload(result)
    assert payload["query9"]["status"] == "Equivalent"
    assert payload["query1"]["status"] == "Differences Found"
    assert payload["query1"]["diffs"]["countDiff"]
    assert payload["query10"]["status"] == "Differences Found"


@pytest.mark.asyncio
async def test_deepdiff_error_payloads_never_equivalent(sample_tool_runtime):
    """Regression: a harness-side {"error": ...} payload must surface as an execution error.

    Previously two failed queries (count/samples all None) compared None-vs-None and were
    reported "Equivalent". Also guards result alignment when error keys are skipped before
    the DeepDiff scheduling loop.
    """
    source_json = {
        "query1": {"count": 2, "firstSample": {"id": 1}, "lastSample": {"id": 2}},
        "query2": {"count": 0, "firstSample": None, "lastSample": None},
        "query3": {"error": "ObjectNotFoundException: no row"},
    }
    target_json = {
        "query1": {"count": 2, "firstSample": {"id": 1}, "lastSample": {"id": 2}},
        "query2": {"error": "IllegalArgumentException: Expected unique result"},
        "query3": {"error": "IllegalArgumentException: Expected unique result"},
    }
    source_output = _make_validation_output("[Source Query Validation Passed]", source_json)
    target_output = _make_validation_output("[Target Query Validation Passed]", target_json)
    sample_tool_runtime.state.source_query_validation_results = source_json
    sample_tool_runtime.state.target_query_validation_results = target_json

    func = cast(StructuredTool, check_query_equivalence)
    assert func.coroutine is not None
    result = await func.coroutine(
        source_validation_output=source_output,
        target_validation_output=target_output,
        runtime=sample_tool_runtime,
    )
    payload = _parse_query_equivalence_payload(result)
    # query1 is genuinely fine — and must stay aligned despite query2/query3 being skipped
    assert payload["query1"]["status"] == "Equivalent"
    assert payload["query2"]["status"] == "Execution Error"
    assert payload["query2"]["executionErrors"] == {
        "target": "IllegalArgumentException: Expected unique result"
    }
    assert payload["query3"]["status"] == "Execution Error"
    assert set(payload["query3"]["executionErrors"]) == {"source", "target"}


@pytest.mark.asyncio
async def test_deepdiff_datetime_format_mismatch_is_equivalent(sample_tool_runtime):
    """Regression (2026-07-03 traces): the .NET serializer formats temporals as
    `yyyy-MM-dd'T'HH:mm:ss.SSS'Z'`, but stores that keep the value as a plain string (WWI
    datetime2 columns imported into Neo4j) return e.g. "2014-05-14 11:00:00.0000000" verbatim —
    the byte-level DeepDiff rejected every sample containing a date. Both sides must be
    canonicalized before diffing; genuinely different instants must still be rejected.
    """
    source_json = {
        "query1": {
            "count": 1,
            "firstSample": {"id": 1, "when": "2014-05-14T11:00:00.000Z"},
            "lastSample": {"id": 1, "when": "2014-05-14T11:00:00.000Z"},
        },
        "query2": {
            "count": 1,
            "firstSample": {"id": 1, "when": "2014-05-14T11:00:00.000Z"},
            "lastSample": {"id": 1, "when": "2014-05-14T11:00:00.000Z"},
        },
    }
    target_json = {
        "query1": {
            "count": 1,
            "firstSample": {"id": 1, "when": "2014-05-14 11:00:00.0000000"},
            "lastSample": {"id": 1, "when": "2014-05-14 11:00:00.0000000"},
        },
        "query2": {
            "count": 1,
            # a genuinely different instant — must still fail
            "firstSample": {"id": 1, "when": "2014-05-15 11:00:00.0000000"},
            "lastSample": {"id": 1, "when": "2014-05-15 11:00:00.0000000"},
        },
    }
    source_output = _make_validation_output("[Source Query Validation Passed]", source_json)
    target_output = _make_validation_output("[Target Query Validation Passed]", target_json)
    sample_tool_runtime.state.source_query_validation_results = source_json
    sample_tool_runtime.state.target_query_validation_results = target_json

    func = cast(StructuredTool, check_query_equivalence)
    assert func.coroutine is not None
    result = await func.coroutine(
        source_validation_output=source_output,
        target_validation_output=target_output,
        runtime=sample_tool_runtime,
    )
    payload = _parse_query_equivalence_payload(result)
    assert payload["query1"]["status"] == "Equivalent"
    assert payload["query2"]["status"] == "Differences Found"


def test_canonicalize_temporals_shapes():
    from react_agent.custom_tools.query_validator import canonicalize_temporals

    assert canonicalize_temporals("2014-05-14 11:00:00.0000000") == "2014-05-14T11:00:00.000Z"
    assert canonicalize_temporals("2014-05-14T11:00:00.000Z") == "2014-05-14T11:00:00.000Z"
    assert canonicalize_temporals("2014-05-14") == "2014-05-14T00:00:00.000Z"
    # tz-aware forms collapse to the same UTC instant
    assert canonicalize_temporals("2014-05-14T13:00:00+02:00") == "2014-05-14T11:00:00.000Z"
    # non-temporal strings and scalars pass through untouched
    assert canonicalize_temporals("Furry animal socks (Pink) XL") == "Furry animal socks (Pink) XL"
    assert canonicalize_temporals("2014-0") == "2014-0"
    assert canonicalize_temporals(15.0) == 15.0
    assert canonicalize_temporals(None) is None
    assert canonicalize_temporals({"a": ["2014-05-14 11:00:00.0000000", 1]}) == {
        "a": ["2014-05-14T11:00:00.000Z", 1]
    }
