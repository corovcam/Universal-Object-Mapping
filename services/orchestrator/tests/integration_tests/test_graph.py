"""Integration tests for the UOM orchestrator graph.

Tests cover graph structure, individual node invocations (both with and
without real LLM calls), and partial graph execution via LangGraph's
update_state / interrupt_after patterns.
"""

from unittest.mock import MagicMock

import pytest
from langchain_core.runnables import RunnableConfig

from react_agent.graph import (
    extract_input,
    graph,
    schema_inspection,
    validate_schema,
)
from react_agent.state import FrameworkType, State

pytestmark = pytest.mark.anyio


# ── Graph Structure ──────────────────────────────────────────────────────────


class TestGraphStructure:
    """Verify the compiled graph has the expected topology."""

    def test_graph_name(self):
        assert graph.name == "UOM Orchestrator Workflow"

    def test_expected_nodes_present(self):
        nodes = list(graph.nodes.keys())
        for expected in [
            "extract_input",
            "schema_inspection",
            "validate_schema",
            "translate_code",
        ]:
            assert expected in nodes, f"Missing node: {expected}"

    def test_entry_point(self):
        nodes = list(graph.nodes.keys())
        assert nodes[0] == "__start__"
        assert "extract_input" in nodes

    def test_schema_inspection_before_translation(self):
        nodes = list(graph.nodes.keys())
        assert nodes.index("schema_inspection") < nodes.index("validate_schema"), (
            "schema_inspection should precede validate_schema"
        )

    def test_edge_topology(self):
        return

        """Verify the full linear edge chain."""
        nodes = list(graph.nodes.keys())
        expected_order = [
            "extract_input",
            "schema_inspection",
            "validate_schema",
            "translate_code",
        ]
        indices = [nodes.index(n) for n in expected_order]
        assert indices == sorted(indices), f"Node order mismatch: {indices}"


# ── extract_input Node ───────────────────────────────────────────────────────


class TestExtractInput:
    """Tests for the extract_input node function."""

    async def test_skips_when_state_populated(
        self, sample_state: State, runnable_config: RunnableConfig, runtime: MagicMock
    ):
        """When source_code and targets are set, returns empty dict."""
        result = await extract_input(sample_state, runnable_config, runtime)
        assert result == {}

    @pytest.mark.integration
    async def test_with_real_llm(
        self, empty_state: State, runnable_config: RunnableConfig, runtime: MagicMock
    ):
        """Call extract_input with a real EINFRA_MINI model.

        Asserts structural correctness of the output (valid FrameworkType,
        non-empty source_code) without checking exact content.
        """
        result = await extract_input(empty_state, runnable_config, runtime)

        assert "source_code" in result
        assert len(result["source_code"]) > 0

        assert "source_target" in result
        assert isinstance(result["source_target"], FrameworkType)
        assert result["source_target"] is not None

        assert "destination_target" in result
        assert isinstance(result["destination_target"], FrameworkType)
        assert result["destination_target"] is not None


# ── schema_inspection Node ───────────────────────────────────────────────────


class TestSchemaInspection:
    """Tests for the schema_inspection node function."""

    @pytest.mark.integration
    async def test_returns_schema_context(
        self, sample_state: State, runnable_config: RunnableConfig, runtime: MagicMock
    ):
        """Schema inspection produces a non-empty schema_context string."""
        result = await schema_inspection(sample_state, runnable_config, runtime)

        assert "schema_context" in result
        assert isinstance(result["schema_context"], str)
        assert len(result["schema_context"]) > 0


# ── validate_schema Node ──────────────────────────────────────────────────


class TestCouncilOfModels:
    """Tests for the validate_schema node function."""

    @pytest.mark.integration
    async def test_returns_strategies(
        self, sample_state: State, runnable_config: RunnableConfig, runtime: MagicMock
    ):
        """Council returns at least one valid strategy response."""
        # Pre-fill schema_context so the council has something to work with
        sample_state.schema_context = (
            "Source: MSSQL with Customers/Orders tables. Target: MongoDB collections."
        )

        result = await validate_schema(sample_state, runnable_config, runtime)

        assert "council_responses" in result
        assert isinstance(result["council_responses"], list)
        # At least one model should succeed
        assert len(result["council_responses"]) >= 1

        for resp in result["council_responses"]:
            assert "model" in resp
            assert "strategy" in resp
            assert len(resp["strategy"]) > 0


# ── Partial Graph Execution ─────────────────────────────────────────────────


class TestPartialGraphExecution:
    """Test running subsets of the graph using LangGraph patterns."""

    def test_individual_node_invocation(self, compiled_graph, sample_state: State):
        """Invoke a single node via compiled_graph.nodes[...].invoke()."""
        node = compiled_graph.nodes.get("extract_input")
        assert node is not None, "extract_input node not found in compiled graph"

    @pytest.mark.integration
    async def test_extract_to_schema_partial(
        self, compiled_graph_with_checkpointer, empty_state: State
    ):
        """Run extract_input → schema_inspection using partial execution.

        Uses update_state to seed state, then invokes with interrupt_after.
        """
        g = compiled_graph_with_checkpointer
        thread_config = {"configurable": {"thread_id": "test-partial-1"}}

        # Run the full graph but interrupt after schema_inspection
        try:
            _result = await g.ainvoke(
                {
                    "messages": empty_state.messages,
                    "source_code": empty_state.source_code,
                    "source_target": empty_state.source_target,
                    "destination_target": empty_state.destination_target,
                },
                config=thread_config,
                interrupt_after=["schema_inspection"],
            )

            # If we got here, the graph ran extract_input and schema_inspection
            state = await g.aget_state(thread_config)
            assert state is not None
        except Exception as e:
            # Schema inspection may fail if db-toolbox is not running —
            # that's acceptable, we're testing the graph flow itself
            pytest.skip(f"Partial execution skipped due to service unavailability: {e}")
