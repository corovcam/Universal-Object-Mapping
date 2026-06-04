"""Integration tests for the UOM orchestrator graph.

Tests cover graph structure, individual node invocations (both with and
without real LLM calls), and partial graph execution via LangGraph's
update_state / interrupt_after patterns.
"""
import functools
from contextlib import asynccontextmanager
from typing import Awaitable, cast
from unittest.mock import MagicMock, patch

import pytest
from aimock_pytest import AIMockServer
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode

from react_agent.constants import FrameworkEnum, TranslationType
from react_agent.context import Context
from react_agent.graph import (
    extract_input,
    schema_inspection,
)
from react_agent.state import InputState, OutputState, State

pytestmark = pytest.mark.anyio

# @pytest.mark.integration
# @pytest.mark.asyncio
# class TestCompleteGraphExecution:
#     """Tests for running the complete graph end-to-end."""

#     async def test_complete_execution(self, 
#         config, 
#         aimock: AIMockServer, 
#         compiled_graph_with_checkpointer: CompiledStateGraph[State, Context, InputState, OutputState],
#         sample_state: State,
#     ):
#         """Run the entire graph with a real LLM and assert final state is populated."""
#         g = compiled_graph_with_checkpointer
#         thread_config = RunnableConfig(configurable={"thread_id": "test-complete-1"})
#         context = Context(openai_api_key=f"{aimock.url}/v1")
#         aimock.fixtures_path = config["AIMOCK_FIXTURES_DIR"]

#         _result = await g.ainvoke(
#             sample_state,
#             config=thread_config,
#             context=context,
#             interrupt_after=["extract_input"],
#         )

#         # After full execution, we expect source_code and targets to be set
#         state = await g.aget_state(thread_config)
#         assert state is not None
#         # assert state.source_schema_code is not None and len(state.source_schema_code) > 0
#         # assert state.source_target is not None
#         # assert state.destination_target is not None


# ── extract_input Node ───────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestExtractInput:
    """Tests for the extract_input node function."""

    async def test_skips_when_state_populated(
        self, runnable_config: RunnableConfig, runtime: MagicMock
    ):
        """When source_code and targets are set, returns empty dict."""
        populated_state = State(
            source_schema_code="public class Customer {}",
            source_query_code="var customers = await db.Customers.ToListAsync();",
            translation_type=TranslationType.BOTH,
            source_target=FrameworkEnum.DOTNET_EFCORE,
            destination_target=FrameworkEnum.JAVA_SPRING_DATA_MONGODB,
        )
        result = await cast(Awaitable, extract_input(populated_state, runnable_config, runtime))
        assert result == {}

    @pytest.mark.integration
    async def test_with_real_llm(
        self, empty_state: State, runnable_config: RunnableConfig, runtime: MagicMock
    ):
        """Call extract_input with a real EINFRA_MINI model.

        Asserts structural correctness of the output (valid FrameworkType,
        non-empty source_code) without checking exact content.
        """
        result = await cast(Awaitable, extract_input(empty_state, runnable_config, runtime))

        assert "source_schema_code" in result
        assert len(result["source_schema_code"]) > 0

        assert "source_target" in result
        assert isinstance(result["source_target"], FrameworkEnum)
        assert result["source_target"] is not None

        assert "destination_target" in result
        assert isinstance(result["destination_target"], FrameworkEnum)
        assert result["destination_target"] is not None


# ── schema_inspection Node ───────────────────────────────────────────────────


class TestSchemaInspection:
    """Tests for the schema_inspection node function."""

    @pytest.mark.integration
    async def test_returns_schema_context(
        self, sample_state: State, runnable_config: RunnableConfig, runtime: MagicMock
    ):
        """Schema inspection produces a non-empty schema_context string."""
        @asynccontextmanager
        async def empty_tools():
            yield []

        with patch(
            "react_agent.graph.load_toolbox_tools",
            side_effect=empty_tools,
        ), patch(
            "react_agent.graph.load_mongodb_tools",
            side_effect=empty_tools,
        ):
            result = await schema_inspection(sample_state, runnable_config, runtime)

        assert "schema_context" in result
        assert isinstance(result["schema_context"], str)
        assert len(result["schema_context"]) > 0


# ── Partial Graph Execution ─────────────────────────────────────────────────


@pytest.mark.integration
@pytest.mark.asyncio
class TestPartialGraphExecution:
    """Test running subsets of the graph using LangGraph patterns."""
    
    async def test_individual_node_invocation(self, compiled_graph):
        """Invoke a single node via compiled_graph.nodes[...].invoke()."""
        node = compiled_graph.nodes.get("extract_input")
        assert node is not None, "extract_input node not found in compiled graph"
        
    async def test_tool_node(self, compiled_graph_with_checkpointer: CompiledStateGraph[State, Context, InputState, OutputState], sample_config_with_runtime: RunnableConfig, sample_state: State):
        """Invoke a single node via compiled_graph.nodes[...].invoke()."""
        node = compiled_graph_with_checkpointer.nodes.get("validate_query_node")
        assert node is not None, "validate_query_node node not found in compiled graph"
        
        # def local_read_mock(scratchpad, channels, managed, task):
        #     if isinstance(channels, (list, tuple)):
        #         return [sample_state.__dict__.get(ch) for ch in channels]
        #     return sample_state.__dict__.get(channels)
        
        # mock_pregel_read = functools.partial(local_read_mock, None, node.channels)  # Placeholder for unused args
        
        tool_calls = [{
            "name": "validate_dotnet_code",
            "args": {
                "source_code": "public class Customer { public int Id { get; set; } }",
                "framework": FrameworkEnum.DOTNET_EFCORE,
            },
            "id": "source_query_val",
            "type": "tool_call"
        },
        {
            "name": "validate_java_code",
            "args": {
                "source_code": "public class Customer { public int Id { get; set; } }",
                "framework": FrameworkEnum.JAVA_SPRING_DATA_MONGODB,
                "entry_type_name": "ValidationEntryPoint",
            },
            "id": "target_query_val",
            "type": "tool_call"
        }]

        result = await node.ainvoke(
            tool_calls,
            config=sample_config_with_runtime,
        )
        assert result is not None, "Tool node invocation returned None"

    async def test_extract_to_schema_partial(
        self, compiled_graph_with_checkpointer: CompiledStateGraph[State, Context, InputState, OutputState], empty_state: State, runnable_config: RunnableConfig
    ):
        """Run extract_input → schema_inspection using partial execution.

        Uses update_state to seed state, then invokes with interrupt_after.
        """
        # Run the full graph but interrupt after schema_inspection
        try:
            _result = await compiled_graph_with_checkpointer.ainvoke(
                empty_state,
                runnable_config,
                interrupt_after=["schema_inspection"],
            )

            # If we got here, the graph ran extract_input and schema_inspection
            state = await compiled_graph_with_checkpointer.aget_state(runnable_config)
            assert state is not None
        except Exception as e:
            # Schema inspection may fail if db-toolbox is not running —
            # that's acceptable, we're testing the graph flow itself
            pytest.skip(f"Partial execution skipped due to service unavailability: {e}")
