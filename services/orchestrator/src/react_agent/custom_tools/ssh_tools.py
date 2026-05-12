"""Provides tools for connecting to sandbox Docker containers."""

import logging
from typing import Literal

from daytona import AsyncDaytona, AsyncSandbox, DaytonaNotFoundError
from langchain_core.tools import tool

from react_agent.constants import SandboxType
from react_agent.context import ValidationSandbox

logger = logging.getLogger(__name__)


async def _get_sandbox(daytona: AsyncDaytona, service_name: str) -> AsyncSandbox | None:
    if service_name == "dotnet-service":
        sandbox_type = SandboxType.DOTNET_10_SANDBOX
    elif service_name == "java-service":
        sandbox_type = SandboxType.JAVA_25_SANDBOX
    else:
        raise ValueError(f"Unknown service name: {service_name}")
    await ValidationSandbox.initialize_validation_sandbox(daytona, sandbox_type)
    return ValidationSandbox.SANDBOXES[sandbox_type]


@tool
async def execute_in_sandbox(
    service_name: Literal["dotnet-service", "java-service"], command: str
) -> str:
    """Executes a shell command directly inside the target Daytona sandbox container (e.g. 'dotnet-service' or 'java-service').

    This is used as a fallback to interact with the environment or compile code manually when the HTTP API is insufficient.

    Args:
        service_name: The target service name (e.g., 'dotnet-service' or 'java-service').
        command: The shell command to run.

    Returns:
        The standard output and standard error from the executed command, or an error message if it failed.
    """
    if service_name not in ["dotnet-service", "java-service"]:
        return "Error: Invalid service name. Supported services are 'dotnet-service' and 'java-service'."
    
    try:
        async with AsyncDaytona() as daytona:
            sandbox = await _get_sandbox(daytona, service_name)
            if not sandbox:
                return f"Error: Daytona Sandbox for {service_name} not found."
            
            logger.info("Executing command in service: %s", service_name)
            result = await sandbox.process.exec(command)
            output = ""
            
            stdout = getattr(result, "result", None)
            if stdout:
                output += f"STDOUT:\n{stdout}\n"
                logger.info("STDOUT: %s", stdout)
                
            stderr = getattr(result, "error", getattr(result, "stderr", None))
            if stderr:
                output += f"STDERR:\n{stderr}\n"
                logger.info("STDERR: %s", stderr)
                
            exit_code = getattr(result, "exit_code", getattr(result, "exitCode", 0))
            if exit_code != 0:
                output += f"Process exited with status: {exit_code}"
                logger.info("Process exited with status: %s", exit_code)
                
            return output if output else "Command executed successfully with no output."
    except DaytonaNotFoundError as e:
        logger.exception("Daytona error")
        return f"[Daytona Error] {e}"   
    except Exception as e:
        logger.exception("Unexpected error during sandbox command execution")
        return f"Error executing sandbox command: {e}"


@tool
async def scp_from_sandbox(
    service_name: Literal["dotnet-service", "java-service"], remote_path: str
) -> str:
    """Retrieve the content of a file from a specified service container using Daytona FS.

    Args:
        service_name: The target service name (e.g., 'dotnet-service' or 'java-service').
        remote_path: The absolute path to the remote file to read.

    Returns:
        The content of the file as a string.
    """
    if service_name not in ["dotnet-service", "java-service"]:
        return "Error: Invalid service name. Supported services are 'dotnet-service' and 'java-service'."

    try:
        async with AsyncDaytona() as daytona:
            sandbox = await _get_sandbox(daytona, service_name)
            if not sandbox:
                return f"Error: Daytona Sandbox for {service_name} not found."
            logger.info("Daytona retrieving file: %s from service: %s", remote_path, service_name)
            content = await sandbox.fs.download_file(remote_path)
        
        if isinstance(content, bytes):
            return content.decode("utf-8")

    except DaytonaNotFoundError as e:
        logger.exception("Daytona fs download error: file not found")
        return f"[SCP Error] File not found: {e}"
    except Exception as e:
        logger.exception("Unexpected error during file download execution")
        return f"Unexpected error: {e}"
