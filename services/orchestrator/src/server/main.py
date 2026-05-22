"""Main application entry point for the API server."""

from enum import StrEnum
from typing import Dict

from daytona import AsyncDaytona
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from react_agent.constants import SandboxType

app = FastAPI()


class NormalizedFramework(StrEnum):
    DOTNET_EFCORE = "dotnet_efcore"
    DOTNET_DAPPER = "dotnet_dapper"
    DOTNET_NHIBERNATE = "dotnet_nhibernate"
    JAVA_SPRING_DATA_MONGODB = "java_spring_data_mongodb"
    JAVA_SPRING_DATA_NEO4J = "java_spring_data_neo4j"


class SshAccessResponse(BaseModel):
    sandbox_id: str
    token: str
    ssh_command: str


class SandboxDTO(BaseModel):
    """Data transfer object for Daytona sandbox information."""

    id: str
    name: str
    state: str
    target: str | None = None
    labels: Dict[str, str] | None = None
    created_at: str | None = None


@app.get("/sandboxes", response_model=list[SandboxDTO])
async def list_sandboxes():
    """List all available sandboxes from the Daytona API server."""
    try:
        async with AsyncDaytona() as daytona:
            # list() returns AsyncPaginatedSandboxes which has an .items property
            sandboxes_response = await daytona.list()

            # Map Daytona DTOs to our response model
            return [
                SandboxDTO(
                    id=s.id,
                    name=s.name,
                    state=str(s.state),
                    target=str(s.target) if s.target else None,
                    labels=s.labels,
                    created_at=str(s.created_at) if s.created_at else None,
                )
                for s in sandboxes_response.items
            ]
    except Exception as e:
        raise HTTPException(
            status_code=getattr(e, "status_code", 500) or 500,
            detail="Failed to list sandboxes: " + str(e),
        )


@app.get("/sandboxes/framework/{framework}", response_model=SandboxDTO)
async def get_sandbox_for_framework(framework: NormalizedFramework):
    """Get the specific sandbox for a given framework by hitting the Daytona API."""
    if framework in (
        NormalizedFramework.DOTNET_EFCORE,
        NormalizedFramework.DOTNET_DAPPER,
        NormalizedFramework.DOTNET_NHIBERNATE,
    ):
        target_name = SandboxType.DOTNET_10_SANDBOX.value
    elif framework in (
        NormalizedFramework.JAVA_SPRING_DATA_MONGODB,
        NormalizedFramework.JAVA_SPRING_DATA_NEO4J,
    ):
        target_name = SandboxType.JAVA_25_SANDBOX.value
    else:
        raise HTTPException(status_code=400, detail=f"Unknown framework: {framework}")

    try:
        async with AsyncDaytona() as daytona:
            sandbox = await daytona.get(f"validation-sandbox-{target_name.lower()}")

            return SandboxDTO(
                id=sandbox.id,
                name=sandbox.name,
                state=str(sandbox.state),
                target=str(sandbox.target) if sandbox.target else None,
                labels=sandbox.labels,
                created_at=str(sandbox.created_at) if sandbox.created_at else None,
            )
    except Exception as e:
        raise HTTPException(
            status_code=getattr(e, "status_code", 500) or 500,
            detail=f"Failed to retrieve sandbox for framework '{framework}': " + str(e),
        )


@app.post("/sandbox/{sandbox_id}/ssh-token", response_model=SshAccessResponse)
async def create_ssh_token(sandbox_id: str):
    """Create an SSH access token for a given Daytona sandbox.

    The access token is valid indefinitely.
    """
    try:
        async with AsyncDaytona() as daytona:
            # Get the sandbox by id or name
            sandbox = await daytona.get(sandbox_id)

            # Create an SSH access token that never expires
            ssh_access = await sandbox.create_ssh_access(expires_in_minutes=0)

            return SshAccessResponse(
                sandbox_id=sandbox_id,
                token=ssh_access.token,
                ssh_command=ssh_access.ssh_command,
            )
    except Exception as e:
        raise HTTPException(
            status_code=getattr(e, "status_code", 500) or 500,
            detail=f"Failed to create SSH token for sandbox '{sandbox_id}': " + str(e),
        )
