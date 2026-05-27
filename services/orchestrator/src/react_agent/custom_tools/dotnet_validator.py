"""Dotnet compilation and validation tool using execute_in_sandbox."""

import base64
import logging
import os
from datetime import datetime
from urllib.parse import urlparse

import orjson
from langchain.tools import ToolRuntime
from langchain_core.messages import ToolMessage
from langchain_core.tools import tool
from langgraph.types import Command
from pydantic import BaseModel, Field

from react_agent.constants import (
    AGENTS_MD_CONTENT,
    DOTNET_DAPPER_SANDBOX_README,
    DOTNET_EFCORE_SANDBOX_README,
    DOTNET_NHIBERNATE_SANDBOX_README,
    DOTNET_VSCODE_EXTENSIONS,
    FRAMEWORK_TO_NORMALIZED_NAME,
    GENERAL_SANDBOX_README,
    MCP_CONFIG_CONTENT,
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
from react_agent.utils.utils import (
    get_framework_config_content,
    translate_localhost_to_host_gateway,
)

logger = logging.getLogger(__name__)


class DotnetValidationInput(BaseModel):
    source_code: str = Field(description="The C# code to validate.")
    framework: DotnetFramework = Field(description="The target .NET framework.")


async def compile_and_run_dotnet(
    source_code: str,
    framework: DotnetFramework,
    runtime: ToolRuntime[Context, State],
) -> tuple[str, str | None]:
    """Helper to compile and run C# source code, returning (output, json_part)."""
    if "class " not in source_code and "record " not in source_code:
        return "Compilation Error: No class or record defined in C# source code.", None

    framework_type = FrameworkEnum(framework.value)
    try:
        csproj_content = await get_framework_config_content(framework_type)
    except ValueError as e:
        raise RuntimeError(f"[Error] {e}") from e

    csproj_b64 = base64.b64encode(csproj_content.encode()).decode()
    cs_b64 = base64.b64encode(source_code.encode()).decode()

    configurable = runtime.config.get("configurable", {}) if runtime.config else {}

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    normalized_name = FRAMEWORK_TO_NORMALIZED_NAME[framework_type]
    thread_id = (
        runtime.execution_info.thread_id
        if runtime.execution_info
        else configurable.get("thread_id", "unknown_thread")
    )
    sandbox_dir = f"/sandbox/{thread_id}/sandbox-{normalized_name}-{timestamp}"
    results_dir = f"{sandbox_dir}/results"

    connection_string = (
        configurable.get("ms_sql_connection_string")
        or configurable.get("mssql_connection_string")
        or runtime.context.ms_sql_connection_string
    )
    sandbox_execution_timeout = (
        configurable.get("sandbox_execution_timeout")
        or configurable.get("daytona_timeout")
        or runtime.context.sandbox_execution_timeout
    )

    mongodb_uri = configurable.get("mongodb_uri") or runtime.context.mongodb_uri
    neo4j_uri = configurable.get("neo4j_uri") or runtime.context.neo4j_uri

    neo4j_browser_uri = os.environ.get("NEO4J_BROWSER_URI")
    if not neo4j_browser_uri:
        parsed_neo4j_uri = urlparse(neo4j_uri)
        neo4j_browser_uri = f"http://{parsed_neo4j_uri.hostname or 'localhost'}:7474"

    env_vars = {
        "CONNECTION_STRING": translate_localhost_to_host_gateway(connection_string),
        "EFCORE_RESULTS_PATH": results_dir,
        "DAPPER_RESULTS_PATH": results_dir,
        "NHIBERNATE_RESULTS_PATH": results_dir,
    }

    daytona_url = (
        configurable.get("daytona_api_url") or runtime.context.daytona_api_url
    ).replace("/api", "")
    general_readme = GENERAL_SANDBOX_README.format(
        daytona_url=daytona_url,
        ms_sql_connection_string=translate_localhost_to_host_gateway(connection_string),
        mongodb_uri=translate_localhost_to_host_gateway(mongodb_uri),
        neo4j_uri=translate_localhost_to_host_gateway(neo4j_uri),
        neo4j_browser_uri=translate_localhost_to_host_gateway(neo4j_browser_uri),
    )
    general_readme_b64 = base64.b64encode(general_readme.encode()).decode()

    readme_template = {
        FrameworkEnum.DOTNET_EFCORE: DOTNET_EFCORE_SANDBOX_README,
        FrameworkEnum.DOTNET_DAPPER: DOTNET_DAPPER_SANDBOX_README,
        FrameworkEnum.DOTNET_NHIBERNATE: DOTNET_NHIBERNATE_SANDBOX_README,
    }[framework_type]

    specific_readme = readme_template.format(
        thread_id=thread_id,
        timestamp=timestamp,
        framework=framework.value,
        connection_string=translate_localhost_to_host_gateway(connection_string),
    )
    specific_readme_b64 = base64.b64encode(specific_readme.encode()).decode()

    run_sh_content = f"""#!/bin/bash
{"\n".join([f'export {key}="{value}"' for key, value in env_vars.items()])}
dotnet build
"""
    if source_code.strip():
        run_sh_content += "dotnet run\n"
        if runtime.state.translation_type in [
            TranslationType.QUERY,
            TranslationType.BOTH,
        ]:
            run_sh_content += f"""
# Output newest json file path
NEWEST_JSON=$(ls -t "{results_dir}"/*.json 2>/dev/null | head -n 1)
if [ -n "$NEWEST_JSON" ]; then
    printf "\\nJSON_PATH=%s\\n" "$NEWEST_JSON"
fi
"""

    run_sh_b64 = base64.b64encode(run_sh_content.encode()).decode()
    vscode_ext_b64 = base64.b64encode(DOTNET_VSCODE_EXTENSIONS.encode()).decode()
    agents_md_b64 = base64.b64encode(AGENTS_MD_CONTENT.encode()).decode()
    host_gateway_ip = os.getenv("OUTER_HOST_GATEWAY_IP", "host.docker.internal")
    mcp_config_b64 = base64.b64encode(
        MCP_CONFIG_CONTENT.format(host_gateway_ip=host_gateway_ip).encode()
    ).decode()

    script = f"""
mkdir -p "/sandbox/.vscode"
mkdir -p "{sandbox_dir}"
mkdir -p "{results_dir}"
mkdir -p "{sandbox_dir}/.vscode"

echo "{general_readme_b64}" | base64 -d > "/sandbox/README.md"
echo "{agents_md_b64}" | base64 -d > "/sandbox/AGENTS.md"
echo "{vscode_ext_b64}" | base64 -d > "/sandbox/.vscode/extensions.json"
echo "{mcp_config_b64}" | base64 -d > "/sandbox/.vscode/mcp.json"

echo "{specific_readme_b64}" | base64 -d > "{sandbox_dir}/README.md"
echo "{agents_md_b64}" | base64 -d > "{sandbox_dir}/AGENTS.md"
echo "{vscode_ext_b64}" | base64 -d > "{sandbox_dir}/.vscode/extensions.json"
echo "{mcp_config_b64}" | base64 -d > "{sandbox_dir}/.vscode/mcp.json"
echo "{csproj_b64}" | base64 -d > "{sandbox_dir}/sandbox.csproj"
echo "{cs_b64}" | base64 -d > "{sandbox_dir}/Program.cs"
echo "{run_sh_b64}" | base64 -d > "{sandbox_dir}/run.sh"
chmod +x "{sandbox_dir}/run.sh"
cd "{sandbox_dir}"
./run.sh
"""

    try:
        result = await execute_in_sandbox.ainvoke(
            {
                "sandbox_type": SandboxType.DOTNET_10_SANDBOX,
                "command": script,
                "timeout": sandbox_execution_timeout,
                "env_vars": env_vars,
                "runtime": runtime,
            },
            config=runtime.config,
        )
        output: str = result[0]
        exit_code: int = result[1]
    except Exception as e:
        logger.error("Dotnet sandbox execution failed", exc_info=True)
        raise RuntimeError(f"[Error] Dotnet sandbox execution failed: {e}") from e

    json_path_line = next(
        (
            line
            for line in reversed(output.splitlines())
            if line.startswith("JSON_PATH=")
        ),
        None,
    )
    if exit_code == 0:
        if json_path_line is not None:
            remote_path = json_path_line.split("=")[1].strip()
            json_content = await download_file_from_sandbox.ainvoke(
                {
                    "sandbox_type": SandboxType.DOTNET_10_SANDBOX,
                    "remote_path": remote_path,
                    "runtime": runtime,
                },
                config=runtime.config,
            )
            json_part = json_content

            return (
                f"[Dotnet Validation Passed] Validation successful. Framework targeted: {framework.value}\n{output}",
                json_part,
            )
        else:
            return (
                f"[Dotnet Validation Failed] No JSON path found in output.\n{output}",
                None,
            )
    else:
        return f"[Dotnet Validation Failed]\n{output}", None


@tool("validate_dotnet_code", args_schema=DotnetValidationInput)
async def validate_dotnet_code(
    source_code: str,
    framework: DotnetFramework,
    runtime: ToolRuntime[Context, State],
) -> Command | str:
    """Compile and validate C# source code through dotnet-service CLI."""
    output, json_part = await compile_and_run_dotnet(source_code, framework, runtime)

    if json_part:
        if "===JSON ERROR===" in json_part:
            return f"{output}\n\n[JSON Results]\n{json_part}"
        try:
            parsed = orjson.loads(json_part)
        except orjson.JSONDecodeError:
            return f"[Dotnet Validation Failed] Could not parse JSON output.\n{output}\n{json_part}"

        # Determine side (source or target)
        side = None
        if (
            source_code.strip()
            == (runtime.state.source_validation_harness_code or "").strip()
        ):
            side = "source"
        elif (
            source_code.strip()
            == (runtime.state.target_validation_harness_code or "").strip()
        ):
            side = "target"

        tool_call_id = (
            getattr(runtime, "tool_call_id", None)
            or (
                runtime.config.get("metadata", {}).get("langgraph_tool_call_id")
                if runtime.config
                else None
            )
            or (
                runtime.config.get("metadata", {}).get("tool_call_id")
                if runtime.config
                else None
            )
        )
        if not side:
            if tool_call_id == "source_query_val":
                side = "source"
            elif tool_call_id == "target_query_val":
                side = "target"

        update_dict = {}
        if side == "source":
            update_dict["source_query_validation_results"] = parsed
        elif side == "target":
            update_dict["target_query_validation_results"] = parsed

        return Command(
            update={
                **update_dict,
                "messages": [
                    ToolMessage(
                        content=output,
                        tool_call_id=tool_call_id,
                        name=validate_dotnet_code.name,
                    )
                ],
            }
        )
    return output
