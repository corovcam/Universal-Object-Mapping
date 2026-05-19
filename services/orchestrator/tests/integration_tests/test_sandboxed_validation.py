from pathlib import Path
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain.messages import ToolMessage
from langchain.tools import ToolRuntime
from langchain_core.tools import StructuredTool
from langgraph.types import Command

from react_agent.constants import DotnetFramework, TranslationType
from react_agent.context import Context
from react_agent.custom_tools.dotnet_validator import validate_dotnet_code
from react_agent.state import State


@pytest.mark.asyncio
async def test_dotnet_sandbox_compilation_error(sample_tool_runtime):
    """Provide invalid C# with class declaration and verify compilation failure shape."""
    invalid_code = """
    public class TestHarness {
        public void Main() {
            invalid_syntax_here;
        }
    }
    """
    sample_tool_runtime.state = {"translation_type": TranslationType.QUERY}

    func = validate_dotnet_code
    structured = func if isinstance(func, StructuredTool) else None
    assert structured is not None and structured.coroutine is not None

    with patch(
        "react_agent.custom_tools.dotnet_validator.get_framework_config_content",
        AsyncMock(return_value="<Project Sdk=\"Microsoft.NET.Sdk\"></Project>"),
    ), patch(
        "react_agent.custom_tools.dotnet_validator.execute_in_sandbox",
        new=MagicMock(ainvoke=AsyncMock(return_value="Build FAILED\nerror CS1002: ; expected")),
    ):
        result = await structured.coroutine(
            source_code=invalid_code,
            framework=DotnetFramework.DOTNET_EFCORE,
            runtime=sample_tool_runtime,
        )

    assert isinstance(result, dict)
    assert "output" in result
    assert "[Dotnet Compilation Failed]" in result["output"]


@pytest.mark.asyncio
async def test_dotnet_sandbox_rejects_missing_class_keyword(sample_tool_runtime):
    """Validation should reject source without class or record before sandbox call."""
    invalid_code = "totally_invalid_input_without_type_declarations"
    sample_tool_runtime.state = {"translation_type": TranslationType.QUERY}

    func = validate_dotnet_code
    structured = func if isinstance(func, StructuredTool) else None
    assert structured is not None and structured.coroutine is not None

    result = await structured.coroutine(
        source_code=invalid_code,
        framework=DotnetFramework.DOTNET_EFCORE,
        runtime=sample_tool_runtime,
    )

    assert isinstance(result, dict)
    assert result["output"] == "Compilation Error: No class or record defined in C# source code."


@pytest.mark.asyncio
async def test_dotnet_sandbox(sample_tool_runtime: ToolRuntime[Context, State], config: dict[str, Path]):
    """Validation should reject source without class or record before sandbox call."""
    efcore_query_entrypoint = (config["SNIPPETS_DIR"] / "EFCoreQueryEntrypoint.cs").read_text()

    func = validate_dotnet_code
    structured = func if isinstance(func, StructuredTool) else None
    assert structured is not None and structured.coroutine is not None

    result: Command = await structured.coroutine(
        source_code=efcore_query_entrypoint,
        framework=DotnetFramework.DOTNET_EFCORE,
        runtime=sample_tool_runtime,
    )
    
    update = cast(dict[str, list[ToolMessage]], result.update)
    assert isinstance(update, dict)
    tool_message = update.get("messages", [])[0]
    assert "[Dotnet Validation Passed]" in tool_message.content
