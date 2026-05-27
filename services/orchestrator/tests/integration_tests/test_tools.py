"""Integration tests for orchestrator tools (validators, docs search).

Validator tools are tested directly (no external services required).
Documentation tools are tested with real HTTP endpoints.
"""

import os
from typing import cast

import pytest
from langchain_core.messages import ToolMessage
from langchain_core.tools import StructuredTool
from langgraph.types import Command

from react_agent.constants import JavaFramework, TranslationType
from react_agent.custom_tools.docs_search import fetch_web_docs, load_docs_mcp_tools
from react_agent.custom_tools.java_validator import validate_java_code

pytestmark = [pytest.mark.anyio, pytest.mark.asyncio]

# ── Java Validator ───────────────────────────────────────────────────────────


SAMPLE_JAVA = """import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;
import org.springframework.data.mongodb.core.mapping.Field;

@Document(collection = "orders")
class Order {
    @Id
    private String id;
    @Field("orderId")
    private Integer orderId;
    @Field("customerId")
    private Integer customerId;
    @Field("orderDate")
    private LocalDateTime orderDate;
    private Customer customer;
    public Order() {}
    public String getId() { return id; }
}

class Customer {
    private Integer customerId;
    private String customerName;
    private BigDecimal creditLimit;
    private List<CustomerTransaction> customerTransactions = new ArrayList<>();
    public Customer() {}
}

class CustomerTransaction {
    private Integer customerTransactionId;
    private BigDecimal transactionAmount;
    public CustomerTransaction() {}
}

@Document(collection = "orderLines")
class OrderLine {
    @Id
    private String id;
    @Field("orderLineId")
    private Integer orderLineId;
    private Integer quantity;
    private BigDecimal unitPrice;
    private StockItem stockItem;
    public OrderLine() {}
}

class StockItem {
    private Integer stockItemId;
    private String stockItemName;
    public StockItem() {}
}"""


class TestJavaValidator:
    """Tests for validate_java_code tool."""

    async def test_valid_java_code(self, sample_tool_runtime):
        sample_tool_runtime.tool_call_id = "test_id"
        sample_tool_runtime.state.translation_type = TranslationType.SCHEMA
        func = cast(StructuredTool, validate_java_code)

        assert func.coroutine is not None
        result = await func.coroutine(
            source_code=SAMPLE_JAVA,
            framework=JavaFramework.JAVA_SPRING_DATA_MONGODB,
            entry_type_name="Order",
            runtime=sample_tool_runtime,
        )

        assert isinstance(result, Command)
        update = cast(dict[str, list[ToolMessage]], result.update)
        assert "[Java Validation Passed]" in update["messages"][0].content

    async def test_invalid_java_no_class(self, sample_tool_runtime):
        sample_tool_runtime.state.translation_type = TranslationType.SCHEMA
        func = cast(StructuredTool, validate_java_code)

        assert func.coroutine is not None
        result = await func.coroutine(
            source_code="System.out.println('hello');",
            framework=JavaFramework.JAVA_SPRING_DATA_MONGODB,
            entry_type_name="ValidationEntryPoint",
            runtime=sample_tool_runtime,
        )

        assert isinstance(result, str)
        assert "[Java Validation Failed]" in result

    async def test_maven_fallback(self, sample_tool_runtime):
        sample_tool_runtime.state.translation_type = TranslationType.QUERY
        func = cast(StructuredTool, validate_java_code)

        assert func.coroutine is not None
        result = await func.coroutine(
            source_code=SAMPLE_JAVA,
            framework=JavaFramework.JAVA_SPRING_DATA_MONGODB,
            entry_type_name="Order",
            runtime=sample_tool_runtime,
        )

        assert isinstance(result, str)
        assert "[Java Validation Failed]" in result


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
        async with load_docs_mcp_tools() as tools:
            assert len(tools) >= 1
            tool_names = [t.name for t in tools]
        expected_names = {
            "fetch_web_docs",
            "microsoft_docs_search",
            "microsoft_code_sample_search",
            "microsoft_docs_fetch",
        }
        assert any(name in expected_names for name in tool_names)
