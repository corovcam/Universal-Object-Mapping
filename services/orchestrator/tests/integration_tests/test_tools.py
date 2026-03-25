"""Integration tests for orchestrator tools (validators, docs search).

Validator tools are tested directly (no external services required).
Documentation tools are tested with real HTTP endpoints.
"""

import os

import pytest

from react_agent.custom_tools.docs_search import fetch_web_docs, load_docs_mcp_tools
from react_agent.custom_tools.dotnet_validator import validate_dotnet_code
from react_agent.custom_tools.java_validator import validate_java_code

pytestmark = pytest.mark.anyio


# ── .NET Validator ───────────────────────────────────────────────────────────


SAMPLE_CSHARP = """\
public class Customer
{
    public int Id { get; set; }
    public string Name { get; set; }
}
"""


@pytest.mark.skip
class TestDotnetValidator:
    """Tests for validate_dotnet_code tool."""

    async def test_valid_csharp_code(self):
        result = await validate_dotnet_code.ainvoke(
            {"source_code": SAMPLE_CSHARP, "orm": "efcore"}
        )
        assert isinstance(result, str)
        assert "Validation Passed" in result or "Compiled successfully" in result

    async def test_invalid_csharp_no_class(self):
        result = await validate_dotnet_code.ainvoke(
            {"source_code": "int x = 42;", "orm": "efcore"}
        )
        assert "Compilation Error" in result

    async def test_orm_parameter_reflected(self):
        result = await validate_dotnet_code.ainvoke(
            {"source_code": SAMPLE_CSHARP, "orm": "dapper"}
        )
        assert "dapper" in result.lower()


# ── Java Validator ───────────────────────────────────────────────────────────


SAMPLE_JAVA = """\
public class Customer {
    private int id;
    private String name;
}
"""


@pytest.mark.skip
class TestJavaValidator:
    """Tests for validate_java_code tool."""

    async def test_valid_java_code(self):
        result = await validate_java_code.ainvoke(
            {"source_code": SAMPLE_JAVA, "framework": "spring-data-mongodb"}
        )
        assert isinstance(result, str)
        assert "Validation Passed" in result or "Compiled successfully" in result

    async def test_invalid_java_no_class(self):
        result = await validate_java_code.ainvoke(
            {"source_code": "System.out.println('hello');", "framework": "none"}
        )
        assert "Compilation Error" in result

    async def test_framework_parameter_reflected(self):
        result = await validate_java_code.ainvoke(
            {"source_code": SAMPLE_JAVA, "framework": "spring-data-neo4j"}
        )
        assert "spring-data-neo4j" in result.lower()


# ── Documentation Search ────────────────────────────────────────────────────


class TestFetchWebDocs:
    """Tests for fetch_web_docs tool (HTTP fallback, no Tavily key needed)."""

    @pytest.mark.integration
    async def test_http_fallback_efcore(self):
        """Fetch docs for EF Core via HTTP fallback (no Tavily key)."""
        # Ensure Tavily is not used
        original = os.environ.pop("TAVILY_API_KEY", None)
        try:
            result = await fetch_web_docs.ainvoke(
                {
                    "query": "Entity Framework Core DbContext",
                    "framework_version": "EF Core 9",
                }
            )
            assert isinstance(result, str)
            assert len(result) > 100, "Expected substantial documentation content"
        finally:
            if original is not None:
                os.environ["TAVILY_API_KEY"] = original

    @pytest.mark.integration
    async def test_http_fallback_spring(self):
        """Fetch docs for Spring Data via HTTP fallback."""
        original = os.environ.pop("TAVILY_API_KEY", None)
        try:
            result = await fetch_web_docs.ainvoke(
                {"query": "Spring Data MongoDB repository", "framework_version": ""}
            )
            assert isinstance(result, str)
            # May get "No documentation found" if the URLs don't resolve,
            # but should not raise an exception
        finally:
            if original is not None:
                os.environ["TAVILY_API_KEY"] = original


class TestLoadDocsMcpTools:
    """Tests for loading MCP documentation tools."""

    @pytest.mark.integration
    async def test_loads_at_least_fallback(self):
        """Always loads at least the fetch_web_docs fallback tool."""
        tools = await load_docs_mcp_tools()
        assert len(tools) >= 1
        tool_names = [t.name for t in tools]
        assert "fetch_web_docs" in tool_names
