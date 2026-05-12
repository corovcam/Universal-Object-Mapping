"""Java compilation and validation tool using execute_in_sandbox."""
import base64
import logging
import os
from datetime import datetime
from typing import Literal, cast

from langchain.tools import ToolRuntime
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from react_agent.constants import FrameworkEnum, JavaFramework, TranslationType
from react_agent.custom_tools.ssh_tools import execute_in_sandbox, scp_from_sandbox
from react_agent.utils.utils import get_framework_config_content

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
    translation_type: TranslationType,
) -> tuple[str, str | None]:
    """Helper to compile and run Java source code, returning (output, json_part)."""
    try:
        pom_content = await get_framework_config_content(FrameworkEnum(framework.value))
    except ValueError as e:
        return f"[Error] {e}", None

    pom_b64 = base64.b64encode(pom_content.encode()).decode()
    java_b64 = base64.b64encode(source_code.encode()).decode()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    sandbox_dir = f"/sandbox/sandbox-{timestamp}"
    src_dir = f"{sandbox_dir}/src/main/java/uom/services"
    results_dir = f"{sandbox_dir}/results"

    script = f"""
export MONGODB_URI="{os.getenv('MONGODB_URI', 'mongodb://uom_readonly:uom_readonly@mongodb:27017/uom')}"
export NEO4J_URI="{os.getenv('NEO4J_URI', 'neo4j://neo4j:7687')}"
export NEO4J_USERNAME="{os.getenv('NEO4J_USERNAME', 'neo4j')}"
export NEO4J_PASSWORD="{os.getenv('NEO4J_PASSWORD', 'password')}"
export MONGO_RESULTS_PATH="{results_dir}"
export NEO4J_RESULTS_PATH="{results_dir}"
mkdir -p "{src_dir}"
mkdir -p "{results_dir}"
echo "{pom_b64}" | base64 -d > "{sandbox_dir}/pom.xml"
echo "{java_b64}" | base64 -d > "{src_dir}/{entry_type_name}.java"
cd "{sandbox_dir}"
mvn -B --no-transfer-progress dependency:resolve clean compile
"""
    if source_code.strip():
        script += f"mvn -B --no-transfer-progress exec:java -Dexec.mainClass=\"uom.services.{entry_type_name}\" -Dexec.classpathScope=compile"
        if translation_type in [TranslationType.QUERY, TranslationType.BOTH]:
            script += f"""
NEWEST_JSON=$(ls -t "{results_dir}"/*.json 2>/dev/null | head -n 1)
if [ -n "$NEWEST_JSON" ]; then
    echo "JSON_PATH=$NEWEST_JSON"
fi
"""

    try:
        output = await execute_in_sandbox.ainvoke(
            {"service_name": "java-service", "command": script}
        )
    except Exception as e:
        logger.error("[Error] Java sandbox execution failed", exc_info=True)
        return f"[Error] Java sandbox execution failed: {e}", None

    if "BUILD SUCCESS" in output:
        json_part = None
        json_path_line = [
            line for line in output.splitlines() if line.startswith("JSON_PATH=")
        ]
        if json_path_line:
            remote_path = json_path_line[0].split("=")[1].strip()
            json_content = await scp_from_sandbox.ainvoke(
                {"service_name": "java-service", "remote_path": remote_path}
            )
            if not json_content.startswith("[SCP Error]"):
                json_part = json_content
            else:
                json_part = f"\\n===JSON ERROR===\\nFailed to fetch JSON from {remote_path}."
        
        return f"[Java Validation Passed] Validation successful. Framework targeted: {framework.value}\\n{output[-1500:]}", json_part
    else:
        return f"[Java Compilation Failed] {output[-2000:]}", None


@tool("validate_java_code", args_schema=JavaValidationInput)
async def validate_java_code(
    source_code: str,
    framework: JavaFramework,
    entry_type_name: str,
    runtime: ToolRuntime,
) -> str:
    """Compile and validate Java source code through java-service CLI."""
    translation_type = cast(TranslationType, runtime.state.get("translation_type"))
    output, json_part = await compile_and_run_java(source_code, framework, entry_type_name, translation_type)
    
    if json_part:
        return f"{output}\n\n[JSON Results]\n{json_part}"
    return output
