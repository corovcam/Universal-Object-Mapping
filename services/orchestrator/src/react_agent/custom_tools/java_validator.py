"""Java compilation and validation tool using the Java Spring Boot service REST API."""

import logging
import os

import httpx
from langchain_core.tools import tool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class JavaValidationInput(BaseModel):
    source_code: str = Field(
        description="The Java source code to compile and validate."
    )
    framework: str = Field(
        default="none",
        description=(
            "The target Spring Data framework: "
            "'spring-data-neo4j' or 'spring-data-mongodb'."
        ),
    )
    validate_schema: bool = Field(
        default=True,
        description=(
            "If true, also validate entity mapping against the live database "
            "after successful compilation."
        ),
    )
    use_maven: bool = Field(
        default=False,
        description=(
            "If true, use Maven compilation (slower, ~10-20s) instead of javac (~1-2s). "
            "Maven catches dependency resolution issues that javac might miss. "
            "Use as a fallback if javac compilation succeeds but runtime validation fails."
        ),
    )


def _get_java_service_uri() -> str:
    """Returns the Java service base URI from the environment."""
    return os.environ.get("JAVA_SERVICE_URI", "http://localhost:8090")


def _format_errors(result: dict) -> str:
    """Formats compilation/validation errors into a readable string for the LLM agent."""
    lines = []
    for error in result.get("errors", []):
        line_num = error.get("lineNumber", -1)
        col_num = error.get("columnNumber", -1)
        message = error.get("message", "Unknown error")
        source = error.get("sourceFile", "")
        code = error.get("code", "")

        location = ""
        if line_num > 0:
            location = f"Line {line_num}"
            if col_num > 0:
                location += f", Col {col_num}"
            location += ": "

        source_prefix = f"[{source}] " if source else ""
        code_suffix = f" ({code})" if code else ""

        lines.append(f"  - {source_prefix}{location}{message}{code_suffix}")

    return "\n".join(lines)


@tool("validate_java_code", args_schema=JavaValidationInput)
async def validate_java_code(
    source_code: str,
    framework: str = "none",
    validate_schema: bool = True,
    use_maven: bool = False,
) -> str:
    """Compile and validate Java Spring Data source code against live databases.

    Sends source code (which may contain multiple entity classes in one file)
    to the java-service which:
    1. Compiles it using javax.tools.JavaCompiler (or Maven if use_maven=True)
       with the full Spring Data classpath (MongoDB, Neo4j)
    2. If validate_schema=True, loads the compiled entities dynamically and
       runs sample queries against the live database to verify the mapping works

    Returns compilation errors with line numbers, or validation success/failure.
    Use use_maven=True as a fallback if standard javac compilation produces
    unexpected results.
    """
    base_url = _get_java_service_uri()
    endpoint = "/api/compiler/maven-compile" if use_maven else "/api/compiler/compile"
    url = f"{base_url}{endpoint}"

    payload = {
        "sourceCode": source_code,
        "framework": framework,
        "validate": validate_schema,
    }

    logger.debug(
        f"Requesting Java validation at {url} (framework: {framework}, validate: {validate_schema})"
    )

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload)
    except httpx.ConnectError:
        logger.error(
            f"Connection Error: Could not connect to Java service at {base_url}"
        )
        return (
            f"[Connection Error] Could not connect to Java service at {base_url}. "
            "Ensure the java-service container is running."
        )
    except httpx.TimeoutException:
        logger.error(
            f"Timeout: Java service at {base_url} did not respond within 60 seconds"
        )
        return (
            f"[Timeout] Java service at {base_url} did not respond within 60 seconds. "
            "The compilation may be too complex or the service is overloaded."
        )
    except httpx.HTTPError as e:
        logger.error(f"HTTP Error failed to communicate with Java service: {e}")
        return f"[HTTP Error] Failed to communicate with Java service: {e}"

    try:
        result = response.json()
        logger.debug(f"Java validation response: {result}")
    except Exception as e:
        logger.error(
            f"Non-JSON response from Java service: {e} - Status {response.status_code}"
        )
        return (
            f"[Error] Java service returned non-JSON response "
            f"(status {response.status_code}): {response.text[:500]}"
        )

    success = result.get("success", False)
    message = result.get("message", "")
    warnings = result.get("warnings", [])
    errors = result.get("errors", [])

    if success:
        logger.info(f"Java validation passed. Message: {message}")
        # Build success response
        parts = [f"[Java Validation Passed] {message}"]
        if warnings:
            parts.append("Warnings:")
            for w in warnings:
                parts.append(f"  - {w}")
        return "\n".join(parts)
    else:
        logger.warning(
            f"Java validation failed. Message: {message}. Errors: {len(errors)}"
        )
        # Build failure response with structured errors
        mode = "Maven" if use_maven else "JavaCompiler"
        parts = [f"[Java Compilation/Validation Failed ({mode})] {message}"]
        if errors:
            parts.append("Errors:")
            parts.append(_format_errors(result))
        if warnings:
            parts.append("Warnings:")
            for w in warnings:
                parts.append(f"  - {w}")
        return "\n".join(parts)
