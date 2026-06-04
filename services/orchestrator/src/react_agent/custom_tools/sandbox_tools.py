"""Provides tools for connecting to sandbox Docker containers."""
import asyncio
import logging
from typing import Annotated, Any
from uuid import uuid4

import structlog
from daytona import (
    AsyncDaytona,
    DaytonaError,
    SessionExecuteRequest,
    SessionExecuteResponse,
)
from langchain.tools import InjectedToolArg, ToolRuntime
from langchain_core.tools import tool

from react_agent.constants import LanggraphCustomEventKeys, SandboxType
from react_agent.utils.sandboxes import ValidationSandbox
from react_agent.utils.utils import process_streaming_chunks

logger = structlog.stdlib.get_logger()


@tool
async def execute_in_sandbox(
    sandbox_type: SandboxType, command: str, timeout: int, env_vars: dict[str, Any] | None, runtime: Annotated[ToolRuntime, InjectedToolArg]
) -> tuple[str, int]:
    """Execute a shell command directly inside the target Daytona sandbox container asynchronously.

    This tool interfaces with the Daytona process manager to run arbitrary commands (like Maven
    or Dotnet CLI) within an isolated workspace. It seamlessly pipes stdout and stderr via
    `runtime.stream_writer` back to the LangGraph execution environment so the user can observe
    real-time compiler output via `LanggraphCustomEventKeys`.

    Args:
        sandbox_type (SandboxType): The target service architecture enum (e.g., DOTNET_10_SANDBOX).
        command (str): The raw shell command or script to run.
        timeout (int): The execution timeout in seconds.
        env_vars (dict[str, Any] | None): Dictionary of environment variables to inject.
        runtime (Annotated[ToolRuntime, InjectedToolArg]): Injected tool runtime context.

    Returns:
        tuple[str, int]: A tuple of the combined output (stdout/stderr) and the exit code.

    Raises:
        DaytonaError: If communicating with the Daytona daemon fails.
    """
    # This callback intercepts chunked streams coming from Daytona's stdout/stderr buffers
    # and re-broadcasts them onto the LangGraph event stream using proprietary event keys.
    # The frontend client listens for these keys to render a real-time console log UI.
    def custom_event_stream_writer(chunk, channel):
        if sandbox_type == SandboxType.JAVA_25_SANDBOX:
            if channel == "stdout":
                runtime.stream_writer({"type": LanggraphCustomEventKeys.JAVA_SANDBOX_COMMAND_EXECUTION_STDOUT, "data": chunk})
            else:
                runtime.stream_writer({"type": LanggraphCustomEventKeys.JAVA_SANDBOX_COMMAND_EXECUTION_STDERR, "data": chunk})
        elif sandbox_type == SandboxType.DOTNET_10_SANDBOX:
            if channel == "stdout":
                runtime.stream_writer({"type": LanggraphCustomEventKeys.DOTNET_SANDBOX_COMMAND_EXECUTION_STDOUT, "data": chunk})
            else:
                runtime.stream_writer({"type": LanggraphCustomEventKeys.DOTNET_SANDBOX_COMMAND_EXECUTION_STDERR, "data": chunk})
    
    try:
        async with AsyncDaytona() as daytona:
            sandbox = await ValidationSandbox.get_sandbox(daytona, sandbox_type, runtime.stream_writer, env_vars)
            
            session_id = f"{sandbox.name}-{uuid4()}"
            await sandbox.process.create_session(session_id)

            logger.info("Executing command in service: %s", sandbox_type)
            # result = await sandbox.process.exec(daytona_cmd, timeout=480) # TODO: Make this configurable by user
            exec_response = await sandbox.process.execute_session_command(
                session_id,
                SessionExecuteRequest(
                    command=command,
                    run_async=True,
                ),
                timeout=timeout, # TODO: Make this configurable by user or by env
            )
            # Stream logs with separate callbacks running concurrently in a background task.
            # This ensures we don't drop logs if the execution is producing them rapidly.
            logs_task = asyncio.create_task(
                sandbox.process.get_session_command_logs_async(
                    session_id,
                    exec_response.cmd_id,
                    lambda stdout: process_streaming_chunks(stdout, lambda chunk: custom_event_stream_writer(chunk, "stdout")),
                    lambda stderr: process_streaming_chunks(stderr, lambda chunk: custom_event_stream_writer(chunk, "stderr")),
                )
            )
            # Wait for the logs to complete
            await logs_task
            session_cmd = await sandbox.process.get_session_command(session_id, exec_response.cmd_id)
            logs = await sandbox.process.get_session_command_logs(session_id, exec_response.cmd_id)
            
            output = ""
            stdout = getattr(logs, "stdout", None)
            if stdout:
                output += f"STDOUT:\n{stdout}\n"
                logger.info("STDOUT: %s", stdout)
 
            stderr = getattr(logs, "stderr", None)
            if stderr:
                output += f"STDERR:\n{stderr}\n"
                logger.info("STDERR: %s", stderr)

            exit_code = getattr(session_cmd, "exit_code", 0)
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
    """Retrieve the contents of a file from a specified service container using the Daytona FS API.

    Used primarily to extract the generated JSON execution results after a query validation
    harness finishes running in the sandbox.

    Args:
        sandbox_type (SandboxType): The target service architecture enum.
        remote_path (str): The absolute path to the file on the remote container's filesystem.
        runtime (Annotated[ToolRuntime, InjectedToolArg]): Injected tool runtime context.

    Returns:
        str: The UTF-8 decoded string content of the requested file.

    Raises:
        DaytonaError: If the file does not exist or Daytona communication fails.
    """
    try:
        async with AsyncDaytona() as daytona:
            sandbox = await ValidationSandbox.get_sandbox(daytona, sandbox_type, runtime.stream_writer)
            logger.info("Daytona retrieving file: %s from service: %s", remote_path, sandbox_type)
            content = await sandbox.fs.download_file(remote_path)
        
        return content.decode("utf-8")

    except DaytonaError as e:
        logger.exception("Daytona fs download error")
        raise e
    except Exception as e:
        logger.exception("Unexpected error during file download execution")
        raise e
