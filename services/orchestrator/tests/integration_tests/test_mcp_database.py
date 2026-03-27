"""Integration tests for MCP database tools.

Tests real connections to MongoDB and the DB Toolbox service.
"""

from unittest.mock import MagicMock, patch

import pytest
from langgraph.runtime import Runtime

from react_agent.context import Context
from react_agent.custom_tools.mcp_database import (
    list_mongodb_collections,
    load_database_tools,
)

pytestmark = pytest.mark.anyio


# ── list_mongodb_collections ─────────────────────────────────────────────────


class TestListMongoDBCollections:
    """Tests for the list_mongodb_collections tool."""

    @pytest.mark.integration
    async def test_real_connection(self, runtime: MagicMock):
        """Connect to the real MongoDB and list collections."""
        with patch(
            "react_agent.custom_tools.mcp_database.get_runtime",
            return_value=runtime,
        ):
            result = await list_mongodb_collections.ainvoke({})

        # The real DB should have collections OR return "No collections"
        assert isinstance(result, str)
        assert "Collections in" in result or "No collections found" in result, (
            f"Unexpected result: {result}"
        )

    async def test_error_on_invalid_uri(self):
        """Verify graceful error handling with an invalid MongoDB URI."""
        bad_context = Context()
        bad_context.mongodb_uri = "mongodb://nonexistent:99999"
        bad_context.mongodb_database = "bad_db"
        bad_runtime = MagicMock(spec=Runtime)
        bad_runtime.context = bad_context

        with patch(
            "react_agent.custom_tools.mcp_database.get_runtime",
            return_value=bad_runtime,
        ):
            result = await list_mongodb_collections.ainvoke({})

        assert isinstance(result, str)
        assert "Error listing collections" in result


# ── load_database_toolbox_tools ──────────────────────────────────────────────


class TestLoadDatabaseToolboxTools:
    """Tests for loading tools from the DB Toolbox server."""

    @pytest.mark.integration
    async def test_loads_tools_from_real_server(self, runtime: MagicMock):
        """Connect to the real db-toolbox and load tools."""
        with patch(
            "react_agent.custom_tools.mcp_database.get_runtime",
            return_value=runtime,
        ):
            tools = await load_database_tools()

        # Should always include list_mongodb_collections at minimum
        assert len(tools) >= 1
        tool_names = [t.name for t in tools]
        assert "list_mongodb_collections" in tool_names

    async def test_fallback_on_invalid_uri(self):
        """When toolbox is unreachable, still returns native tools."""
        bad_context = Context()
        bad_context.db_toolbox_uri = "http://nonexistent:9999"
        bad_runtime = MagicMock(spec=Runtime)
        bad_runtime.context = bad_context

        with patch(
            "react_agent.custom_tools.mcp_database.get_runtime",
            return_value=bad_runtime,
        ):
            tools = await load_database_tools()

        # Fallback: only native tools
        assert len(tools) >= 1
        tool_names = [t.name for t in tools]
        assert "list_mongodb_collections" in tool_names
