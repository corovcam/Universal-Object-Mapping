"""Define the state structures for the agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Sequence

from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages
from langgraph.managed import IsLastStep
from typing_extensions import Annotated


class FrameworkType(str, Enum):
    """Supported Object-Relational/Document Mapping targets."""

    MS_SQL_NATIVE = "MS SQL Native"
    EFCORE_LINQ = "C# EFCore LINQ"
    DAPPER = "C# Dapper"
    NHIBERNATE_HQL = "C# NHibernate HQL"
    SPRING_DATA_JPA = "Java Spring Data JPA"
    SPRING_DATA_MONGODB = "Java Spring Data MongoDB"
    SPRING_DATA_NEO4J = "Java Spring Data Neo4j"
    UNKNOWN = "Unknown"


@dataclass
class InputState:
    """Defines the input state for the agent, representing a narrower interface to the outside world.

    This class is used to define the initial state and structure of incoming data.
    """

    messages: Annotated[Sequence[AnyMessage], add_messages] = field(
        default_factory=list
    )
    """
    Messages tracking the primary execution state of the agent.

    Typically accumulates a pattern of:
    1. HumanMessage - user input
    2. AIMessage with .tool_calls - agent picking tool(s) to use to collect information
    3. ToolMessage(s) - the responses (or errors) from the executed tools
    4. AIMessage without .tool_calls - agent responding in unstructured format to the user
    5. HumanMessage - user responds with the next conversational turn

    Steps 2-5 may repeat as needed.

    The `add_messages` annotation ensures that new messages are merged with existing ones,
    updating by ID to maintain an "append-only" state unless a message with the same ID is provided.
    """

    # The original source code snippet the user wants translated
    source_code: str = field(default="")
    source_target: FrameworkType = field(default=FrameworkType.UNKNOWN)
    destination_target: FrameworkType = field(default=FrameworkType.UNKNOWN)


@dataclass
class State(InputState):
    """Represents the complete state of the agent, extending InputState with additional attributes.

    This class can be used to store any information needed throughout the agent's lifecycle.
    """

    is_last_step: IsLastStep = field(default=False)
    """
    Indicates whether the current step is the last one before the graph raises an error.

    This is a 'managed' variable, controlled by the state machine rather than user code.
    It is set to 'True' when the step count reaches recursion_limit - 1.
    """

    # --- UOM Architecture State ---

    # Core loop variables
    schema_translated_code: str = field(default="")
    query_translated_code: str = field(default="")
    council_responses: list[dict] = field(default_factory=list)
    error_feedback: str = field(default="")

    # Validation Results
    schema_validation_result: str = field(default="")
    query_validation_result: str = field(default="")

    # Loop lifecycle
    error_count: int = field(default=0)
    max_retries: int = field(default=3)
    HIL_requested: bool = field(default=False)
