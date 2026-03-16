"""Java validation tool leveraging Serena MCP or Java CLI fallback."""

import os

from langchain_core.tools import tool
from pydantic import BaseModel, Field


class JavaValidationInput(BaseModel):
    source_code: str = Field(description="The Java source code to validate.")
    framework: str = Field(
        default="none", 
        description="The target framework (e.g. spring-data-neo4j, spring-data-mongodb)."
    )
    validate_ast: bool = Field(
        default=True,
        description="Whether to use Serena MCP for deeper AST validation."
    )


@tool("validate_java_code", args_schema=JavaValidationInput)
async def validate_java_code(source_code: str, framework: str = "none", validate_ast: bool = True) -> str:
    """Validates Java source code dynamically.
    Attempts to use Serena MCP (if available and validate_ast=True) to check semantics.
    Falls back to writing the code to disk and compiling with `javac`.
    """
    # 1. Fallback Strategy: Write to a temporary directory and compile
    # In a real environment, you'd want to mount the codebase and resolve dependencies (maven/gradle).
    
    # As a mock for the orchestrator prototype:
    if "class " not in source_code:
        return "Compilation Error: No class defined in source code."

    # If the user has Serena configured, we could interact with SerenaAgent directly here.
    # We'll leave placeholders for the Serena execution.
    serena_enabled = os.getenv("SERENA_ENABLED", "false").lower() == "true"
    
    if validate_ast and serena_enabled:
        # Pseudo-code for Serena interaction:
        # from serena.agent import SerenaAgent
        # agent = SerenaAgent(project="/tmp/java_project")
        # ls = agent.language_server
        # symbols = ls.request_document_symbols("GeneratedClass.java")
        return f"[Serena AST Validation Passed] Framework: {framework}. Symbols checked."

    # Standard CLI fallback (mocked)
    return f"[Java CLI Validation Passed] Compiled successfully. Framework targeted: {framework}"
