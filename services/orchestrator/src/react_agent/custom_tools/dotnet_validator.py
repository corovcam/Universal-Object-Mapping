"""Dotnet compilation and validation tool using execute_in_sandbox."""
import base64
import logging
import os
from datetime import datetime
from typing import cast

import orjson
from langchain.tools import ToolRuntime
from langchain_core.messages import ToolMessage
from langchain_core.tools import tool
from langgraph.types import Command
from pydantic import BaseModel, Field

from react_agent.constants import (
    DotnetFramework,
    FrameworkEnum,
    SandboxType,
    TranslationType,
)
from react_agent.context import Context
from react_agent.custom_tools.sandbox_tools import (
    download_file_from_sandbox,
    execute_in_sandbox,
)
from react_agent.state import State
from react_agent.utils.utils import get_framework_config_content

logger = logging.getLogger(__name__)


class DotnetValidationInput(BaseModel):
    source_code: str = Field(description="The C# code to validate.")
    framework: DotnetFramework = Field(description="The target .NET framework.")


async def compile_and_run_dotnet(
    source_code: str,
    framework: DotnetFramework,
    translation_type: TranslationType,
) -> tuple[str, str | None]:
    """Helper to compile and run C# source code, returning (output, json_part)."""
    if "class " not in source_code and "record " not in source_code:
        return "Compilation Error: No class or record defined in C# source code.", None

    try:
        csproj_content = await get_framework_config_content(FrameworkEnum(framework.value))
    except ValueError as e:
        raise RuntimeError(f"[Error] {e}") from e

    csproj_b64 = base64.b64encode(csproj_content.encode()).decode()
    cs_b64 = base64.b64encode(source_code.encode()).decode()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    sandbox_dir = f"/sandbox/sandbox-{timestamp}"
    results_dir = f"{sandbox_dir}/results"

    script = f"""
export CONNECTION_STRING="{os.getenv('MSSQL_CONNECTION_STRING', 'Server=mssql_db,1433;Database=WideWorldImporters;User Id=sa;Password=Testingorms123;TrustServerCertificate=True')}"
export EFCORE_RESULTS_PATH="{results_dir}"
export DAPPER_RESULTS_PATH="{results_dir}"
export NHIBERNATE_RESULTS_PATH="{results_dir}"
mkdir -p "{sandbox_dir}"
mkdir -p "{results_dir}"
echo "{csproj_b64}" | base64 -d > "{sandbox_dir}/sandbox.csproj"
echo "{cs_b64}" | base64 -d > "{sandbox_dir}/Program.cs"
cd "{sandbox_dir}"
dotnet build
"""
    if source_code.strip():
        script += "dotnet run\n"
        if translation_type in [TranslationType.QUERY, TranslationType.BOTH]:
            script += f"""
# Output newest json file path
NEWEST_JSON=$(ls -t "{results_dir}"/*.json 2>/dev/null | head -n 1)
if [ -n "$NEWEST_JSON" ]; then
    printf "\nJSON_PATH=%s\n" "$NEWEST_JSON"
fi
"""

    try:
        result = await execute_in_sandbox.ainvoke(
            {"sandbox_type": SandboxType.DOTNET_10_SANDBOX, "command": script}
        )
        output: str = result[0]
        exit_code: int = result[1]
    except Exception as e:
        logger.error("Dotnet sandbox execution failed", exc_info=True)
        raise RuntimeError(f"[Error] Dotnet sandbox execution failed: {e}") from e

    json_path_line = next((line for line in reversed(output.splitlines()) if line.startswith("JSON_PATH=")), None)
    if exit_code == 0:
        if json_path_line is not None:
            remote_path = json_path_line.split("=")[1].strip()
            json_content = await download_file_from_sandbox.ainvoke(
                {"sandbox_type": SandboxType.DOTNET_10_SANDBOX, "remote_path": remote_path}
            )
            json_part = json_content

            return f"[Dotnet Validation Passed] Validation successful. Framework targeted: {framework.value}\n{output}", json_part
        else:
            return f"[Dotnet Validation Failed] No JSON path found in output.\n{output}", None
    else:
        return f"[Dotnet Validation Failed]\n{output}", None


@tool("validate_dotnet_code", args_schema=DotnetValidationInput)
async def validate_dotnet_code(
    source_code: str,
    framework: DotnetFramework,
    runtime: ToolRuntime,
) -> Command | str:
    """Compile and validate C# source code through dotnet-service CLI."""
    runtime: ToolRuntime[Context, State] = runtime  # ty:ignore[invalid-assignment]
    output, json_part = await compile_and_run_dotnet(source_code, framework, cast(TranslationType, runtime.state.translation_type))
    
    if json_part:
        if "===JSON ERROR===" in json_part:
            return f"{output}\n\n[JSON Results]\n{json_part}"
        try:
            parsed = orjson.loads(json_part)
        except orjson.JSONDecodeError:
            return f"[Dotnet Validation Failed] Could not parse JSON output.\n{output}\n{json_part}"
            
        tool_call_id = getattr(runtime, "tool_call_id", None)
        update_dict = {}
        if tool_call_id == "source_query_val":
            update_dict["source_query_validation_results"] = parsed
        elif tool_call_id == "target_query_val":
            update_dict["target_query_validation_results"] = parsed
            
        return Command(
            update={
                **update_dict,
                "translation_messages": [
                    ToolMessage(
                        content=output,
                        tool_call_id=tool_call_id,
                        name=validate_dotnet_code.name
                    )
                ]
            }
        )
    return output
