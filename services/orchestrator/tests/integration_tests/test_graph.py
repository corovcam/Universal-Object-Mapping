from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime

from react_agent.context import AvailableModel, Context
from react_agent.graph import ExtractionOutput, extract_input, graph
from react_agent.state import FrameworkType, State

pytestmark = pytest.mark.anyio


async def test_uom_graph_compilation() -> None:
    """Graph compiles and registers the expected node names."""
    assert graph.name == "UOM Orchestrator Workflow"
    nodes = list(graph.nodes.keys())
    for expected in [
        "extract_input",
        "council_of_models",
        "translation_agent",
    ]:
        assert expected in nodes, f"Missing node: {expected}"


async def test_uom_graph_has_correct_entry_point() -> None:
    """Graph starts at the extract_input node."""
    # The first edge from __start__ should route to extract_input
    nodes = list(graph.nodes.keys())
    assert nodes[0] == "__start__"
    assert "extract_input" in nodes


@patch("react_agent.graph._get_model")
async def test_extract_input_skips_when_state_populated(
    mock_get_model: MagicMock,
) -> None:
    """When source_code and targets are already set, extract_input returns empty dict."""
    state = State(
        messages=[HumanMessage(content="translate my code")],
        source_code="SELECT * FROM users",
        source_target=FrameworkType.MS_SQL_NATIVE,
        destination_target=FrameworkType.EFCORE_LINQ,
    )

    context = Context(model=AvailableModel.EINFRA_MINI)
    runtime = MagicMock(spec=Runtime)
    runtime.context = context
    config = RunnableConfig()

    result = await extract_input(state, config, runtime)

    assert result == {}
    mock_get_model.assert_not_called()


@patch("react_agent.graph._get_model")
async def test_extract_input_invokes_llm_when_state_empty(
    mock_get_model: MagicMock,
) -> None:
    """When source data is missing, extract_input calls the LLM for extraction."""
    mock_llm = MagicMock()
    mock_get_model.return_value = mock_llm

    mock_structured = AsyncMock()
    mock_llm.with_structured_output.return_value = mock_structured
    mock_structured.ainvoke.return_value = ExtractionOutput(
        source_code="SELECT * FROM users",
        source_target=FrameworkType.MS_SQL_NATIVE,
        destination_target=FrameworkType.EFCORE_LINQ,
    )

    state = State(
        messages=[HumanMessage(content="Convert this SQL to EFCore: SELECT * FROM users")],
        source_code="",
        source_target=FrameworkType.UNKNOWN,
        destination_target=FrameworkType.UNKNOWN,
    )

    context = Context(model=AvailableModel.EINFRA_MINI)
    runtime = MagicMock(spec=Runtime)
    runtime.context = context
    config = RunnableConfig()

    result = await extract_input(state, config, runtime)

    assert result["source_code"] == "SELECT * FROM users"
    assert result["source_target"] == FrameworkType.MS_SQL_NATIVE
    assert result["destination_target"] == FrameworkType.EFCORE_LINQ
    mock_llm.with_structured_output.assert_called_once_with(ExtractionOutput)
    mock_structured.ainvoke.assert_awaited_once()
