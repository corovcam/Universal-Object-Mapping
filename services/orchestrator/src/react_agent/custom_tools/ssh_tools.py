"""Provides SSH tool for connecting to sandbox Docker containers."""

import logging
from typing import Literal

import asyncssh
from langchain_core.tools import tool

from react_agent.utils import get_ssh_host_and_port

logger = logging.getLogger(__name__)


@tool
async def execute_in_sandbox(
    service_name: Literal["dotnet-service", "java-service"], command: str
) -> str:
    """Executes a shell command via SSH directly inside the target sandbox container (e.g. 'dotnet-service' or 'java-service').

    This is used as a fallback to interact with the environment or compile code manually when the HTTP API is insufficient.

    Args:
        service_name: The target docker service name (e.g., 'dotnet-service' or 'java-service').
        command: The shell command to run.

    Returns:
        The standard output and standard error from the executed command, or an error message if it failed.
    """
    try:
        if service_name not in ["dotnet-service", "java-service"]:
            return "Error: Invalid service name. Supported services are 'dotnet-service' and 'java-service'."

        # Connect using the configured user password inside the Dockerfile
        # By default in docker compose, the container hostname matches the service name.
        host, port = get_ssh_host_and_port(service_name)
        async with asyncssh.connect(
            host=host,
            port=port,
            username="sandbox",
            password="sandbox",
            known_hosts=None,
        ) as conn:
            logger.info("Executing command: %s in service: %s", command, service_name)
            result = await conn.run(command)
            output = ""
            if result.stdout:
                output += f"STDOUT:\n{result.stdout}\n"
                logger.info("STDOUT: %s", result.stdout)
            if result.stderr:
                output += f"STDERR:\n{result.stderr}\n"
                logger.info("STDERR: %s", result.stderr)
            if result.exit_status != 0:
                output += f"Process exited with status: {result.exit_status}"
                logger.info("Process exited with status: %s", result.exit_status)
            return output if output else "Command executed successfully with no output."
    except Exception as e:
        return f"Error executing SSH command: {e}"


@tool
async def scp_from_sandbox(
    service_name: Literal["dotnet-service", "java-service"], remote_path: str
) -> str:
    """Retrieve the content of a file from a specified service container using SCP/SFTP.

    Args:
        service_name: The target docker service name (e.g., 'dotnet-service' or 'java-service').
        remote_path: The absolute path to the remote file to read.

    Returns:
        The content of the file as a string.
    """
    try:
        if service_name not in ["dotnet-service", "java-service"]:
            return "Error: Invalid service name. Supported services are 'dotnet-service' and 'java-service'."

        host, port = get_ssh_host_and_port(service_name)
        async with asyncssh.connect(
            host=host,
            port=port,
            username="sandbox",
            password="sandbox",
            known_hosts=None,
        ) as conn:
            logger.info(
                "SCP retrieving file: %s from service: %s", remote_path, service_name
            )
            async with conn.start_sftp_client() as sftp:
                try:
                    async with sftp.open(remote_path, "r") as f:
                        content = await f.read()
                        if isinstance(content, bytes):
                            return content.decode("utf-8")
                        return content
                except asyncssh.SFTPError as e:
                    logger.exception("SFTP error while retrieving file")
                    return f"[SCP Error] File not found or inaccessible: {e}"

    except asyncssh.Error as e:
        logger.exception("SSH SCP error")
        return f"SSH connection failed: {e}"
    except Exception as e:
        logger.exception("Unexpected error during SCP execution")
        return f"Unexpected error: {e}"
