from typing import Any, Literal

from react_agent.constants import (
    DotnetFramework,
    FrameworkEnum,
    JavaFramework,
    SourceFramework,
    TargetFramework,
)

FrameworkType = DotnetFramework | JavaFramework | SourceFramework | TargetFramework | FrameworkEnum

QueryValidationResults = dict[
    Literal["count", "firstSample", "lastSample", "error", "sqlString", "cypher", "mongoQuery", "mongoAggregation"], 
    Any
]

QueryEquivalenceDeepDiff = dict[
    Literal["deepdiff_mapping", "count_diff", "first_sample_diff", "last_sample_diff", "error"],
    Any
]
