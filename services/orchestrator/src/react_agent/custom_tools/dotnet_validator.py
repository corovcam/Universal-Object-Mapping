"""Dotnet compilation and validation tool using execute_in_sandbox."""
import base64
import logging
import os
from datetime import datetime
from typing import Literal, cast

from langchain.tools import ToolRuntime
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from react_agent.constants import DotnetFramework, FrameworkEnum, TranslationType
from react_agent.custom_tools.ssh_tools import execute_in_sandbox, scp_from_sandbox
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
        return f"[Error] {e}", None

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
    echo "JSON_PATH=$NEWEST_JSON"
fi
"""

    try:
        output = await execute_in_sandbox.ainvoke(
            {"service_name": "dotnet-service", "command": script}
        )
    except Exception as e:
        logger.error("[Error] Dotnet sandbox execution failed", exc_info=True)
        return f"[Error] Dotnet sandbox execution failed: {e}", None

    if "Build succeeded" in output:
        json_part = None
        json_path_line = [
            line for line in output.splitlines() if line.startswith("JSON_PATH=")
        ]
        if json_path_line:
            remote_path = json_path_line[0].split("=")[1].strip()
            json_content = await scp_from_sandbox.ainvoke(
                {"service_name": "dotnet-service", "remote_path": remote_path}
            )
            if not json_content.startswith("[SCP Error]"):
                json_part = json_content
            else:
                json_part = f"\\n===JSON ERROR===\\nFailed to fetch JSON from {remote_path}."

        return f"[Dotnet Validation Passed] Validation successful. Framework targeted: {framework.value}\\n{output[-1500:]}", json_part
    else:
        return f"[Dotnet Compilation Failed] {output[-2000:]}", None


@tool("validate_dotnet_code", args_schema=DotnetValidationInput)
async def validate_dotnet_code(
    source_code: str,
    framework: DotnetFramework,
    runtime: ToolRuntime,
) -> str:
    """Compile and validate C# source code through dotnet-service CLI."""
    translation_type = cast(TranslationType, runtime.state.get("translation_type"))
    output, json_part = await compile_and_run_dotnet(source_code, framework, translation_type)
    
    if json_part:
        return f"{output}\n\n[JSON Results]\n{json_part}"
    return output
