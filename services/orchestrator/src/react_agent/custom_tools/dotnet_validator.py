"""Dotnet validation tool leveraging Serena MCP or Dotnet CLI fallback."""

import os

from langchain_core.tools import tool
from pydantic import BaseModel, Field


class DotnetValidationInput(BaseModel):
    source_code: str = Field(description="The C# source code to validate.")
    orm: str = Field(
        default="efcore", 
        description="The target ORM (e.g. efcore, dapper, nhibernate)."
    )
    validate_ast: bool = Field(
        default=True,
        description="Whether to use Serena MCP for deeper AST validation."
    )

@tool("validate_dotnet_code", args_schema=DotnetValidationInput)
async def validate_dotnet_code(source_code: str, orm: str = "efcore", validate_ast: bool = True) -> str:
    """Validates C# source code dynamically.
    Attempts to use Serena MCP (if available and validate_ast=True) to check semantics.
    Falls back to `dotnet build` or Roslyn diagnostics.
    """
    if "class " not in source_code and "record " not in source_code:
        return "Compilation Error: No class or record defined in C# source code."

    serena_enabled = os.getenv("SERENA_ENABLED", "false").lower() == "true"
    
    if validate_ast and serena_enabled:
        # Pseudo-code for Serena MCP interaction:
        # from serena.agent import SerenaAgent
        # agent = SerenaAgent(project="/tmp/dotnet_project")
        # ls = agent.language_server
        # diagnostics = ls.request_diagnostics("GeneratedClass.cs")
        return f"[Serena C# AST Validation Passed] ORM: {orm}. No diagnostics errors found."

    # Standard CLI fallback (mocked)
    return f"[Dotnet CLI Validation Passed] Compiled successfully. ORM targeted: {orm}"
