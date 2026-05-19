"""Define the state structures for the agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages
from langgraph.managed import IsLastStep
from typing_extensions import Annotated

from react_agent.constants import FrameworkEnum, TranslationType
from react_agent.utils.types import QueryEquivalenceDeepDiff, QueryValidationResults


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
    source_schema_code: str | None = field(default=None)
    source_query_code: str | None = field(default=None)
    translation_type: TranslationType | None = field(default=None)
    source_target: FrameworkEnum | None = field(default=None)
    source_target_version: str | None = field(default=None)
    destination_target: FrameworkEnum | None = field(default=None)
    destination_target_version: str | None = field(default=None)


@dataclass
class OutputState:
    """Defines the output state for the graph, representing a narrower interface to the outside world.

    This class is used to define the final state and structure of outgoing data.
    """

    translated_schema_code: str | None = field(default=None)
    translated_query_code: str | None = field(default=None)
    source_validation_schema_code: str | None = field(default=None)
    source_validation_harness_code: str | None = field(default=None)
    target_validation_schema_code: str | None = field(default=None)
    target_validation_harness_code: str | None = field(default=None)
    explanation_message: str | None = field(default=None)


@dataclass
class State(InputState, OutputState):
    """Represents the complete state of the graph, extending InputState with additional attributes.

    This class can be used to store any information needed throughout the agent's lifecycle.
    """

    is_last_step: IsLastStep = field(default=False)
    """
    Indicates whether the current step is the last one before the graph raises an error.

    This is a 'managed' variable, controlled by the state machine rather than user code.
    It is set to 'True' when the step count reaches recursion_limit - 1.
    """

    # Core variables
    source_validation_entry_type_name: str | None = field(default=None)
    target_validation_entry_type_name: str | None = field(default=None)
    source_query_validation_results: QueryValidationResults | None = field(default=None)
    target_query_validation_results: QueryValidationResults | None = field(default=None)
    query_equivalence_deep_diffs: dict[str, QueryEquivalenceDeepDiff] | None = field(default=None)
    schema_context: str = field(default="")
    translation_messages: Annotated[Sequence[AnyMessage], add_messages] = field(
        default_factory=list
    )
    translation_loop_count: int = field(default=0)
