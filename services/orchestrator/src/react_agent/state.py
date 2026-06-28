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

    This class encapsulates the initial state and structure of incoming data provided
    by the user or extracted from the conversation history. It holds the raw code
    snippets to be translated and the identified source and target frameworks.
    
    Attributes:
        messages: A sequence of messages tracking the conversational state.
        source_schema_code: The raw source schema code string provided by the user.
        source_query_code: The raw source query code string provided by the user.
        translation_type: The scope of the translation (SCHEMA, QUERY, or BOTH).
        source_target: The identified origin framework (e.g., DOTNET_EFCORE).
        source_target_version: The version of the origin framework, if applicable.
        destination_target: The identified target framework (e.g., JAVA_SPRING_DATA_MONGODB).
        destination_target_version: The version of the target framework, if applicable.
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

    single_pass: bool = field(default=False)
    """
    Experiment run-mode flag (the evaluation baseline arm). When True, the pipeline runs as a
    SINGLE-SHOT translator: `generate_translation_node` does one direct model call with just the
    save tool (no ReAct research loop, no docs MCP), and the validation routers do NOT loop back to
    regenerate or hand off to human intervention on failure — they terminate. This isolates the
    value of the agentic self-repair loop (the only difference from the default full-loop run) while
    producing the same deterministic assemble→validate→finalize artifacts for an apples-to-apples
    comparison. Settable at invoke because the conditional-edge routers read it from state.
    """


@dataclass
class OutputState:
    """Defines the output state for the graph, representing a narrower interface to the outside world.

    This class encapsulates the final resulting data that is returned back to the user
    once the translation and evaluation process completes successfully or ends in failure.
    
    Attributes:
        translated_schema_code: The final translated schema code in the target framework.
        translated_query_code: The final translated query code in the target framework.
        source_validation_schema_code: The fully runnable source schema setup for validation.
        source_validation_harness_code: The fully runnable source query execution harness.
        target_validation_schema_code: The fully runnable target schema setup for validation.
        target_validation_harness_code: The fully runnable target query execution harness.
        explanation_message: The final reasoning or evaluation summary provided by the LLM.
        messages: The sequence of messages representing the final conversational state.
    """

    translated_schema_code: str | None = field(default=None)
    translated_query_code: str | None = field(default=None)
    source_validation_schema_code: str | None = field(default=None)
    source_validation_harness_code: str | None = field(default=None)
    target_validation_schema_code: str | None = field(default=None)
    target_validation_harness_code: str | None = field(default=None)
    explanation_message: str | None = field(default=None)
    messages: Annotated[Sequence[AnyMessage], add_messages] = field(
        default_factory=list
    )


@dataclass
class State(InputState, OutputState):
    """Represents the complete internal state of the graph, extending InputState and OutputState.

    This class is used as the core memory object passed around between nodes in the LangGraph
    state machine. It holds intermediate artifacts, tool execution results, retry counters,
    and equivalence testing states throughout the agent's lifecycle.
    
    Attributes:
        is_last_step: A LangGraph managed flag indicating if the recursion limit is about to be hit.
        source_validation_entry_type_name: The entrypoint class name for running source validation.
        target_validation_entry_type_name: The entrypoint class name for running target validation.
        source_query_validation_results: The JSON results generated by the source query execution.
        target_query_validation_results: The JSON results generated by the target query execution.
        query_equivalence_deep_diffs: Dictionary of entity-level equivalence diffs between source and target outputs.
        schema_context: A textual summary of the database schema mapping used by the LLM.
        translation_messages: An isolated message thread specifically for the translation/validation loop.
        extraction_loop_count: Counter for how many times the extraction node has retried.
        translation_loop_count: Counter for how many times the translation node has retried.
    """

    is_last_step: IsLastStep = field(default=False)
    """
    Indicates whether the current step is the last one before the graph raises an error.

    This is a 'managed' variable, controlled by the state machine rather than user code.
    It is set to 'True' when the step count reaches recursion_limit - 1.
    """

    # Core variables
    source_validation_entry_type_name: str | None = field(default=None)
    """
    The entrypoint class name for running source validation, extracted from `source_validation_schema_code`.
    This name is used by the sandbox execution tool to locate the correct class to instantiate and run.
    """
    target_validation_entry_type_name: str | None = field(default=None)
    """
    The entrypoint class name for running target validation, extracted from `target_validation_schema_code`.
    This name is used by the sandbox execution tool to locate the correct class to instantiate and run.
    """
    source_query_validation_results: QueryValidationResults | None = field(default=None)
    """
    The raw JSON results from executing the source framework's query harness in the sandbox.
    Contains entity data and raw outputs.
    """
    target_query_validation_results: QueryValidationResults | None = field(default=None)
    """
    The raw JSON results from executing the target framework's query harness in the sandbox.
    Contains entity data and raw outputs.
    """
    query_equivalence_deep_diffs: dict[str, QueryEquivalenceDeepDiff] | None = field(default=None)
    """
    Stores the differential analysis between source and target query outputs.
    If the graph detects semantic drift, it stores entity-level diffs here to help the LLM debug and subsequent auto/manual evaluation.
    """

    schema_context: str = field(default="")
    """
    Used to hold large schema metadata extracted from the database via MCP tools.
    We store this outside of 'messages' to prevent the main chat history from blowing up context windows.
    """
    
    translation_messages: Annotated[Sequence[AnyMessage], add_messages] = field(
        default_factory=list
    )
    """
    An isolated sub-graph message list. 
    The LangGraph translation cycle can get very noisy with sandbox compile errors and retries.
    By separating this from `messages`, the core reasoning loop doesn't get distracted by iterative trial-and-error logs.
    """
    

    extraction_loop_count: int = field(default=0)
    """
    Track the number of times we've looped through the extraction node 
    to prevent infinite recursion if the LLM fundamentally fails to parse user intent.
    """
    
    translation_loop_count: int = field(default=0)
    """
    Track the number of times we've retried a translation after sandbox failures or deepdiff failures.
    The graph uses this to branch to `human_intervention_node` if it exceeds the limit (e.g., > 3).
    """
    
    ui_messages: Annotated[Sequence[AnyMessage], add_messages] = field(
        default_factory=list,
    )
    """
    A separate message list intended for UI-only display purposes.
    """
