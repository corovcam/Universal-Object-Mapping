"""Type definitions and aliases used across the UOM orchestrator service.

This module provides centralized type aliases to improve code readability,
ensure type safety across tool boundaries, and standardize the shapes of
complex nested dictionaries passed through the LangGraph state.
"""

from typing import Any, Literal

from react_agent.constants import (
    DotnetFramework,
    FrameworkEnum,
    JavaFramework,
    SourceFramework,
    TargetFramework,
)

FrameworkType = DotnetFramework | JavaFramework | SourceFramework | TargetFramework | FrameworkEnum
"""A Union of all possible framework enumerations (both Source and Target)."""

QueryValidationResults = dict[
    Literal["count", "firstSample", "lastSample", "error", "sqlString", "cypher", "mongoQuery", "mongoAggregation"], 
    Any
]
"""Represents the structured JSON output returned by the execution of a validation sandbox harness.
These dictionaries contain metadata (like result counts and stringified JSON samples) used
strictly for deterministic equivalence checks."""

QueryEquivalenceDeepDiff = dict[
    Literal["deepdiff_mapping", "count_diff", "first_sample_diff", "last_sample_diff", "error"],
    Any
]
"""Represents the results from the DeepDiff library after comparing Source and Target QueryValidationResults.
"deepdiff_mapping" contains metadata regarding which side was marked as old/new."""
