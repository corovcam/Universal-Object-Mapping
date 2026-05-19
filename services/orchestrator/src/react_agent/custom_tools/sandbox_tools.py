"""Provides tools for connecting to sandbox Docker containers."""
import logging
from typing import Annotated

from daytona import AsyncDaytona, DaytonaError
from langchain.tools import InjectedToolArg, ToolRuntime
from langchain_core.tools import tool

from react_agent.constants import SandboxType
from react_agent.utils.sandboxes import ValidationSandbox

logger = logging.getLogger(__name__)


@tool
async def execute_in_sandbox(
    sandbox_type: SandboxType, command: str, runtime: Annotated[ToolRuntime, InjectedToolArg]
) -> tuple[str, int]:
    """Executes a shell command directly inside the target Daytona sandbox container (e.g. 'dotnet-service' or 'java-service').

    This is used as a fallback to interact with the environment or compile code manually when the HTTP API is insufficient.

    Args:
        sandbox_type: The target service name (e.g., 'dotnet-service' or 'java-service').
        command: The shell command to run.

    Returns:
        A tuple containing:
        - The standard output and standard error from the executed command, or an error message if it failed.
        - The exit code from the command.
    """
    try:
        async with AsyncDaytona() as daytona:
            sandbox = await ValidationSandbox.get_sandbox(daytona, sandbox_type)
            logger.info("Executing command in service: %s", sandbox_type)
            result = await sandbox.process.exec(command, timeout=300)
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
            output += f"Process exited with status: {exit_code}"
            logger.info("Process exited with status: %s", exit_code)
            
            if not output:
                return "Command executed successfully with no output.", exit_code
            return output, exit_code
    except DaytonaError as e:
        logger.exception("Daytona error")
        raise e
    except Exception as e:
        logger.exception("Unexpected error during sandbox command execution")
        raise e


@tool
async def download_file_from_sandbox(
    sandbox_type: SandboxType, remote_path: str, runtime: Annotated[ToolRuntime, InjectedToolArg]
) -> str:
    """Retrieve the content of a file from a specified service container using Daytona FS.

    Args:
        sandbox_type: The target service name (e.g., 'dotnet-service' or 'java-service').
        remote_path: The absolute path to the remote file to read.

    Returns:
        The content of the file as a string.
    """
    try:
        async with AsyncDaytona() as daytona:
            sandbox = await ValidationSandbox.get_sandbox(daytona, sandbox_type)
            logger.info("Daytona retrieving file: %s from service: %s", remote_path, sandbox_type)
            content = await sandbox.fs.download_file(remote_path)
        
        return content.decode("utf-8")

    except DaytonaError as e:
        logger.exception("Daytona fs download error")
        raise e
    except Exception as e:
        logger.exception("Unexpected error during file download execution")
        raise e
