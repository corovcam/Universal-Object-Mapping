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


@tool("validate_java_code", args_schema=JavaValidationInput)
async def validate_java_code(
    source_code: str,
    framework: JavaFramework,
    entry_type_name: str,
    runtime: ToolRuntime
) -> dict[Literal["output", "json"], str]:
    """Compile and validate Java Spring Data source code against live databases via SSH sandbox."""
    try:
        pom_content = await get_framework_config_content(FrameworkEnum(framework.value))
    except ValueError as e:
        return {"output": f"[Error] {e}"}

    pom_b64 = base64.b64encode(pom_content.encode()).decode()
    java_b64 = base64.b64encode(source_code.encode()).decode()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    sandbox_dir = f"/sandbox/sandbox-{timestamp}"
    results_dir = f"{sandbox_dir}/results"

    translation_type = cast(TranslationType, runtime.state.get("translation_type"))
    script = f"""
export MONGODB_URI="mongodb://uom_readonly:uom_readonly@mongodb:27017/uom"
export NEO4J_URI="bolt://neo4j:7687"
export NEO4J_USERNAME="neo4j"
export NEO4J_PASSWORD="password"
export MONGO_RESULTS_PATH="{results_dir}"
export NEO4J_RESULTS_PATH="{results_dir}"
mkdir -p "{sandbox_dir}/src/main/java/uom/services"
mkdir -p "{results_dir}"
echo "{pom_b64}" | base64 -d > "{sandbox_dir}/pom.xml"
echo "{java_b64}" | base64 -d > "{sandbox_dir}/src/main/java/uom/services/{entry_type_name}.java"
cd "{sandbox_dir}"
mvn clean compile
"""
    if source_code.strip():
        script += f"mvn exec:java -Dexec.mainClass=\"uom.services.{entry_type_name}\" -Dexec.classpathScope=compile"
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
        return {"output": f"[Error] SSH sandbox execution failed: {e}"}

    if "BUILD SUCCESS" in output:
        if "Error occurred" not in output and "Exception" not in output:
            json_part = ""
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
                    json_part = f"\\n===JSON ERROR===\\nFailed to fetch JSON from {remote_path}: {json_content}"

            return {
                "output": f"[Java Validation Passed] Successfully compiled and executed.\\nMaven Output:\\n{output[:500]}...",
                "json": json_part
            }
        else:
            return {"output": f"[Java Validation Failed] Execution failed.\\nMaven Output:\\n{output[-1000:]}"}
    else:
        return {"output": f"[Java Compilation Failed] Maven Output:\\n{output[-2000:]}"}
