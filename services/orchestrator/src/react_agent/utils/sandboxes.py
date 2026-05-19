"""Handles creation and management of Daytona sandboxes for code execution."""
import asyncio
import logging
import os

import structlog
from daytona import (
    AsyncDaytona,
    AsyncSandbox,
    CreateSandboxFromSnapshotParams,
    CreateSnapshotParams,
    Image,
    SandboxState,
)
from langchain.tools import ToolRuntime

from react_agent.constants import SandboxType

logger = structlog.stdlib.get_logger()


def process_chunks(chunk, writer, log_buffer: list | None = None):
    writer(chunk)
    if log_buffer is not None:
        log_buffer.append(chunk)

class ValidationSandbox:
    SANDBOXES: dict[SandboxType, AsyncSandbox] = {}
    
    DAYTONA_SANDBOX_IMAGES: dict[SandboxType, Image] = {
        SandboxType.DOTNET_10_SANDBOX: Image
            .base(os.getenv("DOTNET_SANDBOX_IMAGE", "mcr.microsoft.com/dotnet/sdk:10.0")),
            # .workdir("/sandbox")
            # .add_local_file(os.path.join(os.getenv("CONTEXT_ABSOLUTE_PATH", ""), "/snippets/efcore-sandbox.csproj") if os.getenv("CONTEXT_ABSOLUTE_PATH") else os.path.join(os.getcwd(), "src/context/snippets/efcore-sandbox.csproj"), "/app/efcore-sandbox.csproj")
            # .dockerfile(),
        SandboxType.JAVA_25_SANDBOX: Image
            .base(os.getenv("JAVA_SANDBOX_IMAGE", "bellsoft/liberica-openjdk-debian:25-cds"))
            .run_commands("apt-get update && apt-get install -y --no-install-recommends maven && rm -rf /var/lib/apt/lists/*"),
            # .workdir("/sandbox")
            # .add_local_file(os.path.join(os.getenv("CONTEXT_ABSOLUTE_PATH", ""), "/snippets/mongo-pom.xml") if os.getenv("CONTEXT_ABSOLUTE_PATH") else os.path.join(os.getcwd(), "src/context/snippets/mongo-pom.xml"), "mongo-pom.xml")
            # .dockerfile(),
    }
    
    @staticmethod
    async def get_sandbox(daytona: AsyncDaytona, sandbox_type: SandboxType, runtime: ToolRuntime) -> AsyncSandbox:
        await ValidationSandbox.create_snapshot(daytona, sandbox_type, runtime)
        await ValidationSandbox.initialize_validation_sandbox(daytona, sandbox_type, runtime)
        return ValidationSandbox.SANDBOXES[sandbox_type]
    
    @staticmethod
    async def create_snapshot(daytona: AsyncDaytona, sandbox_type: SandboxType, runtime: ToolRuntime) -> None:
        """Create a snapshot for the specified sandbox type."""
        params = CreateSnapshotParams(
            name=f"validation-snapshot-{sandbox_type.value.lower()}",
            image=ValidationSandbox.DAYTONA_SANDBOX_IMAGES[sandbox_type],
        )
        
        chunk_buffer = []
        max_retries = 5
        for attempt in range(max_retries):
            try:
                try:
                    existing_snapshot = await daytona.snapshot.get(params.name)
                    logger.info(f"Snapshot '{params.name}' already exists with ID: {existing_snapshot.id}")
                    return
                except Exception as e:
                    logger.info(f"Snapshot '{params.name}' not found or error retrieving: {e}")
                snapshot = await daytona.snapshot.create(params, on_logs=lambda chunk: process_chunks(chunk, runtime.stream_writer, chunk_buffer))
                logger.info(f"Snapshot created with ID: {snapshot.id}")
                break
            except Exception as e:
                logger.error(f"Failed to create snapshot for sandbox '{sandbox_type.value}': {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise
            finally:
                if chunk_buffer:
                    await logger.adebug("snapshot_creation_logs", sandbox_type=sandbox_type.value, logs="".join(chunk_buffer))
            raise
  
    @staticmethod
    async def initialize_validation_sandbox(daytona: AsyncDaytona, sandbox_type: SandboxType, runtime: ToolRuntime) -> None:
        """Initialize a validation sandbox."""
        params = CreateSandboxFromSnapshotParams(
            snapshot=f"validation-snapshot-{sandbox_type.value.lower()}",
            auto_stop_interval=30, # Sandbox will be stopped after 30 minutes
            name=f"validation-sandbox-{sandbox_type.value.lower()}",
        )
        assert params.name is not None
        
        max_retries = 5
        
        for attempt in range(max_retries):
            try:
                sandbox_instance = None
                try:
                    sandbox_instance = await daytona.get(params.name)
                except Exception as e:
                    logger.info(f"Sandbox '{params.name}' not found or error retrieving: {e}")
                
                if sandbox_instance is None or sandbox_instance.state == SandboxState.DESTROYED:
                    logger.info(f"Creating sandbox '{params.name}'...")
                    sandbox_instance = await daytona.create(params, timeout=180)
                    logger.info(f"Sandbox created with ID: {sandbox_instance.id}")
                
                state = sandbox_instance.state
                logger.info(f"Sandbox '{params.name}' current state: {state}")
                
                if state in (SandboxState.ERROR, SandboxState.BUILD_FAILED, SandboxState.ARCHIVED):
                    logger.warning(f"Sandbox '{params.name}' is in state '{state}'. Deleting and recreating...")
                    try:
                        await daytona.delete(sandbox_instance)
                        await asyncio.sleep(5)
                    except Exception as e:
                        logger.warning(f"Failed to delete sandbox: {e}")
                    # Force recreate in next iteration
                    continue
                    
                if state in (SandboxState.DESTROYING, SandboxState.ARCHIVING):
                    logger.warning(f"Sandbox '{params.name}' is in '{state}' state. Waiting before recreating...")
                    await asyncio.sleep(5)
                    try:
                        if state in (SandboxState.DESTROYED, SandboxState.ARCHIVED):
                            await daytona.delete(sandbox_instance)
                            await asyncio.sleep(5)
                    except Exception:
                        pass
                    continue
                    
                if state in (SandboxState.STOPPED, SandboxState.STOPPING):
                    if state == SandboxState.STOPPING:
                        logger.info(f"Sandbox '{params.name}' is stopping. Waiting...")
                        await sandbox_instance.wait_for_sandbox_stop(timeout=180)
                        sandbox_instance = await daytona.get(params.name)
                    
                    logger.info(f"Starting sandbox '{params.name}'...")
                    await sandbox_instance.start(timeout=60)
                    await sandbox_instance.wait_for_sandbox_start(timeout=180)
                    
                elif state in (SandboxState.CREATING, SandboxState.PENDING_BUILD, SandboxState.BUILDING_SNAPSHOT, SandboxState.STARTING, SandboxState.PULLING_SNAPSHOT, SandboxState.RESTORING, SandboxState.RESIZING, SandboxState.SNAPSHOTTING, SandboxState.FORKING, SandboxState.UNKNOWN):
                    logger.info(f"Sandbox '{params.name}' is in progress state '{state}'. Waiting to start...")
                    await sandbox_instance.wait_for_sandbox_start(timeout=180)
                
                elif state == SandboxState.STARTED:
                    logger.info(f"Sandbox '{params.name}' is already started.")
                    
                # Final check to ensure it's started
                sandbox_instance = await daytona.get(params.name)
                if sandbox_instance.state == SandboxState.STARTED:
                    ValidationSandbox.SANDBOXES[sandbox_type] = sandbox_instance
                    logger.debug("Sandbox details:\n%s", sandbox_instance.model_dump_json(indent=2))
                    return
                else:
                    logger.warning(f"Sandbox '{params.name}' failed to reach STARTED state. Current state: {sandbox_instance.state}")
                    
            except Exception as e:
                logger.error(f"Error handling sandbox '{params.name}' on attempt {attempt + 1}/{max_retries}: {e}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Failed to handle sandbox '{params.name}' after {max_retries} attempts.")
                    logger.warning("Continuing gracefully without the sandbox.")
                    return
        
        logger.warning(f"Exhausted retries for sandbox '{params.name}'. Continuing gracefully.")
    