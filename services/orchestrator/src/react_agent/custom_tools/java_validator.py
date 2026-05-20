"""Java compilation and validation tool using execute_in_sandbox."""
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
    FrameworkEnum,
    JavaFramework,
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
    translate_localhost_to_host_docker_internal,
)

logger = logging.getLogger(__name__)


class JavaValidationInput(BaseModel):
    source_code: str = Field(
        min_length=1,
        description="The Java source code to compile and validate."
    )
    framework: JavaFramework = Field(
        description="The Java framework.",
    )
    entry_type_name: str = Field(
        min_length=1,
        description="Entrypoint type class name declared in the Java source code.",
    )


async def compile_and_run_java(
    source_code: str,
    framework: JavaFramework,
    entry_type_name: str,
    runtime: ToolRuntime[Context, State],
) -> tuple[str, str | None]:
    """Helper to compile and run Java source code, returning (output, json_part)."""
    try:
        pom_content = await get_framework_config_content(FrameworkEnum(framework.value))
    except ValueError as e:
        raise RuntimeError(f"[Error] {e}") from e

    pom_b64 = base64.b64encode(pom_content.encode()).decode()
    java_b64 = base64.b64encode(source_code.encode()).decode()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    sandbox_dir = f"/sandbox/sandbox-{timestamp}"
    src_dir = f"{sandbox_dir}/src/main/java/uom/services"
    results_dir = f"{sandbox_dir}/results"
    env_vars = {
        "MONGODB_URI": translate_localhost_to_host_docker_internal(runtime.context.mongodb_uri),
        "NEO4J_URI": translate_localhost_to_host_docker_internal(runtime.context.neo4j_uri),
        "NEO4J_USERNAME": runtime.context.neo4j_username,
        "NEO4J_PASSWORD": runtime.context.neo4j_password,
        "MONGO_RESULTS_PATH": results_dir,
        "NEO4J_RESULTS_PATH": results_dir,
    }

    script = f"""
{"\n".join([f"export {key}=\"{value}\"" for key, value in env_vars.items()])}
mkdir -p "{src_dir}"
mkdir -p "{results_dir}"
echo "{pom_b64}" | base64 -d > "{sandbox_dir}/pom.xml"
echo "{java_b64}" | base64 -d > "{src_dir}/{entry_type_name}.java"
cd "{sandbox_dir}"
mvn -q -B --no-transfer-progress dependency:resolve clean compile
"""
    if source_code.strip():
        script += f"mvn -q -B --no-transfer-progress exec:java -Dexec.mainClass=\"uom.services.{entry_type_name}\" -Dexec.classpathScope=compile"
        if runtime.state.translation_type in [TranslationType.QUERY, TranslationType.BOTH]:
            script += f"""
NEWEST_JSON=$(ls -t "{results_dir}"/*.json 2>/dev/null | head -n 1)
if [ -n "$NEWEST_JSON" ]; then
    printf "\nJSON_PATH=%s\n" "$NEWEST_JSON"
fi
"""

    try:
        result = await execute_in_sandbox.ainvoke(
            {"sandbox_type": SandboxType.JAVA_25_SANDBOX, "command": script, "timeout": runtime.context.sandbox_execution_timeout, "env_vars": env_vars, "runtime": runtime},
            config=runtime.config,
        )
        output: str = result[0]
        exit_code: int = result[1]
    except Exception as e:
        logger.error("Java sandbox execution failed", exc_info=True)
        raise RuntimeError(f"[Error] Java sandbox execution failed: {e}") from e

    json_path_line = next((line for line in reversed(output.splitlines()) if line.startswith("JSON_PATH=")), None)
    if exit_code == 0:
        if json_path_line is not None:
            remote_path = json_path_line.split("=")[1].strip()
            json_content = await download_file_from_sandbox.ainvoke(
                {"sandbox_type": SandboxType.JAVA_25_SANDBOX, "remote_path": remote_path, "runtime": runtime},
                config=runtime.config,
            )
            json_part = json_content

            return f"[Java Validation Passed] Validation successful. Framework targeted: {framework.value}\n{output}", json_part
        else:
            return f"[Java Validation Failed] No JSON path found in output.\n{output}", None
    else:
        return f"[Java Validation Failed]\n{output}", None


@tool("validate_java_code", args_schema=JavaValidationInput)
async def validate_java_code(
    source_code: str,
    framework: JavaFramework,
    entry_type_name: str,
    runtime: ToolRuntime[Context, State],
) -> Command | str:
    """Compile and validate Java source code through java-service CLI."""
    output, json_part = await compile_and_run_java(source_code, framework, entry_type_name, runtime)
    
    if json_part:
        if "===JSON ERROR===" in json_part:
            return f"{output}\n\n[JSON Results]\n{json_part}"
        try:
            parsed = orjson.loads(json_part)
        except orjson.JSONDecodeError:
            return f"[Java Validation Failed] Could not parse JSON output.\n{output}\n{json_part}"
            
        tool_call_id = getattr(runtime, "tool_call_id", None)
        update_dict = {}
        if tool_call_id == "source_query_val":
            update_dict["source_query_validation_results"] = parsed
        elif tool_call_id == "target_query_val":
            update_dict["target_query_validation_results"] = parsed
            
        return Command(
            update={
                **update_dict,
                "messages": [
                    ToolMessage(
                        content=output,
                        tool_call_id=tool_call_id,
                        name=validate_java_code.name
                    )
                ]
            }
        )
    return output
