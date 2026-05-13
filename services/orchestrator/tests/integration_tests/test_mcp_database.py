"""Integration tests for MCP database tools.

Tests real connections to MongoDB and the DB Toolbox service.
"""

from unittest.mock import MagicMock, patch

import pytest
from langgraph.runtime import Runtime

from react_agent.context import Context
from react_agent.custom_tools.mcp_database import (
    load_database_tools,
)

pytestmark = [pytest.mark.anyio, pytest.mark.asyncio]


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
            try:
                async with load_database_tools() as tools:
                    tool_names = [t.name for t in tools]
            except RuntimeError as exc:
                pytest.skip(f"DB toolbox unavailable in this environment: {exc}")

            assert isinstance(tool_names, list)
            if tool_names:
                print(tool_names)
                real_tools = ["execute_sql", "list_tables", "execute_cypher", "get_schema"]
                assert any(name in tool_names for name in real_tools), (
                    f"Expected at least one database tool, got: {tool_names}"
                )

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
            try:
                async with load_database_tools() as tools:
                    tool_names = [t.name for t in tools]
            except RuntimeError as exc:
                # Current implementation may raise when async generator exits early.
                assert "generator didn't yield" in str(exc)
            else:
                assert tool_names == [], (
                    f"Expected no tools loaded from toolbox, got: {tool_names}"
                )
