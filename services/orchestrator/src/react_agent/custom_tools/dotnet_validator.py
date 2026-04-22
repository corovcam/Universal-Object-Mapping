"""Dotnet compilation and validation tool via dotnet-service REST API."""

import logging
import os
from typing import cast

import httpx
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from react_agent.constants import (
    FRAMEWORK_TO_NORMALIZED_NAME,
    DotnetFramework,
    FrameworkType,
)
from react_agent.utils.utils import get_normalized_framework_name

logger = logging.getLogger(__name__)


class DotnetValidationInput(BaseModel):
    source_code: str = Field(description="The C# schema code to validate.")
    framework: DotnetFramework = Field(description="The target .NET framework.")


def _get_dotnet_service_uri() -> str:
    """Return dotnet-service base URL from environment with local default."""
    return os.environ.get("DOTNET_SERVICE_URI", "http://localhost:5073")


@tool("validate_dotnet_code", args_schema=DotnetValidationInput)
async def validate_dotnet_code(
    source_code: str, framework: DotnetFramework = DotnetFramework.DOTNET_EFCORE
) -> str:
    """Compile and validate C# source code through dotnet-service.

    This tool currently validates schema/source code compilation before query
    validation stages run in the orchestrator workflow.
    """
    if "class " not in source_code and "record " not in source_code:
        return "Compilation Error: No class or record defined in C# source code."

    base_url = _get_dotnet_service_uri()
    url = f"{base_url}/api/compiler/validate-schema"
    payload = {
        "sourceCode": source_code,
        "framework": get_normalized_framework_name(framework),
    }

    logger.debug(
        "Requesting dotnet validation at %s (framework=%s)",
        url,
        framework.value,
    )

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload)
    except httpx.ConnectError:
        return (
            f"[Connection Error] Could not connect to dotnet-service at {base_url}. "
            "Ensure the service is running."
        )
    except httpx.TimeoutException:
        return (
            f"[Timeout] dotnet-service at {base_url} did not respond within 60 seconds."
        )
    except httpx.HTTPError as ex:
        return f"[HTTP Error] Failed to communicate with dotnet-service: {ex}"

    try:
        data = response.json()
    except Exception:
        return (
            f"[Error] dotnet-service returned non-JSON response (status {response.status_code}): "
            f"{response.text[:500]}"
        )

    if response.is_success:
        return f"[Dotnet Validation Passed] Sandbox schema validation successful. Framework targeted: {framework.value}"

    errors = data.get("errors") if isinstance(data, dict) else None
    if isinstance(errors, list) and len(errors) > 0:
        error_message = "\n".join(str(error) for error in errors)
    else:
        error_message = (
            data.get("error") or data.get("message") or "Compilation failed."
        )

    return f"[Dotnet Compilation Failed] {error_message}"
