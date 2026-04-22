"""Utilities for deterministic checks on translation outputs and validation states in React Agent."""

import logging
from typing import Any, Literal

from langchain_core.messages import HumanMessage

from react_agent.constants import FrameworkType, TranslationType
from react_agent.state import State
from react_agent.utils import get_message_text

logger = logging.getLogger(__name__)


def _contains_structured_code(code: str | None) -> bool:
    """Return True when a generated code payload looks like code."""
    if code is None:
        return False
    return bool(code.strip()) and "class " in code


def _contains_validation_harness_payload(code: str | None) -> bool:
    """Detect whether query output still contains validation harness artifacts."""
    if code is None:
        return False

    lower_code = code.lower()
    tokens = (
        "validation_harness",
        "queryvalidationharness",
        "validationharness",
    )
    return any(token in lower_code for token in tokens)


def _message_contains_marker(messages: list[Any], marker: str) -> bool:
    """Return whether any message content contains a marker."""
    for message in reversed(messages):
        content = ""
        try:
            content = get_message_text(message)
        except Exception:
            raw_content = getattr(message, "content", "")
            content = str(raw_content)
        if marker in content:
            return True
    return False


def _find_unexpected_tokens(
    source_code: str | None,
    translated_code: str | None,
    tokens: tuple[str, ...],
) -> list[str]:
    """Return tokens introduced by translated code that are not present in source code."""
    if not (source_code or "").strip():
        return []

    source = (source_code or "").lower()
    translated = (translated_code or "").lower()
    return [token for token in tokens if token in translated and token not in source]


def _latest_validation_outcome(
    messages: list[Any],
    passed_marker: str,
    failed_marker: str,
) -> Literal["passed", "failed", "missing"]:
    """Return latest known validation outcome from message history."""
    for message in reversed(messages):
        content = ""
        try:
            content = get_message_text(message)
        except Exception:
            raw_content = getattr(message, "content", "")
            content = str(raw_content)

        if passed_marker in content:
            return "passed"
        if failed_marker in content:
            return "failed"

    return "missing"


def _validate_query_code_structure(
    destination_target: FrameworkType | None,
    translated_query_code: str | None,
    source_query_code: str | None,
) -> list[str]:
    """Apply deterministic structural checks to translated query code."""
    errors: list[str] = []

    if not _contains_structured_code(translated_query_code):
        errors.append(
            "translated_query_code must contain concrete Java/C# class-based code, not prose."
        )
        return errors

    assert translated_query_code is not None
    lower_code = translated_query_code.lower()

    unexpected_sort_tokens = _find_unexpected_tokens(
        source_query_code,
        translated_query_code,
        ("sortbyfield", "sortdirection", "ascending", "descending"),
    )
    if unexpected_sort_tokens:
        errors.append(
            "translated_query_code introduced synthetic ordering/config inputs not present in source query "
            f"({', '.join(unexpected_sort_tokens)}). Keep translated_query_code equivalent to the source query "
            "and place deterministic validation setup in validation_harness_code."
        )

    if destination_target == FrameworkType.JAVA_SPRING_DATA_MONGODB:
        for token in ("mongotemplate", "criteria", "query"):
            if token not in lower_code:
                errors.append(
                    "Spring Data MongoDB query must use MongoTemplate with Query/Criteria API."
                )
                break

    if destination_target == FrameworkType.JAVA_SPRING_DATA_NEO4J:
        if "neo4jtemplate" not in lower_code:
            errors.append("Spring Data Neo4j query must use Neo4jTemplate.")

        uses_cypher_dsl = any(
            token in translated_query_code
            for token in (
                "org.neo4j.cypherdsl.core",
                "Cypher.",
                "Statement",
                "Renderer",
            )
        )
        if not uses_cypher_dsl:
            errors.append(
                "Spring Data Neo4j query must use Cypher-DSL syntax (not raw Cypher string composition)."
            )

    return errors


def _deterministic_translation_issues(
    state: State,
    translated_schema_code: str | None,
    translated_query_code: str | None,
    validation_harness_code: str | None,
    messages: list[Any],
) -> tuple[list[str], bool, bool]:
    """Validate whether current translation state can safely terminate."""
    issues: list[str] = []
    schema_ok = True
    query_ok = True

    if state.translation_type in {TranslationType.SCHEMA, TranslationType.BOTH}:
        if not _contains_structured_code(translated_schema_code):
            schema_ok = False
            issues.append(
                "translated_schema_code is missing or not valid class-based code."
            )

    if state.translation_type in {TranslationType.QUERY, TranslationType.BOTH}:
        if not _contains_structured_code(validation_harness_code):
            query_ok = False
            issues.append(
                "validation_harness_code must contain class-based validation helper code for query metadata checks."
            )

        if _contains_validation_harness_payload(translated_query_code):
            query_ok = False
            issues.append(
                "translated_query_code must exclude validation harness content. Keep harness in validation_harness_code only."
            )

        query_structure_issues = _validate_query_code_structure(
            state.destination_target,
            translated_query_code,
            state.source_query_code,
        )
        if query_structure_issues:
            query_ok = False
            issues.extend(query_structure_issues)

        source_validation = _latest_validation_outcome(
            messages,
            "[Source Query Validation Passed]",
            "[Source Query Validation Failed]",
        )
        if source_validation == "failed":
            query_ok = False
            issues.append(
                "validate_source_query failed. Source query/schema must be fixed before continuing."
            )
        elif source_validation != "passed":
            query_ok = False
            issues.append(
                "validate_source_query must pass before query translation can finish."
            )

        if not _message_contains_marker(messages, "[Target Query Validation Passed]"):
            query_ok = False
            issues.append(
                "validate_target_query must pass before query translation can finish."
            )

        if not _message_contains_marker(messages, "[Query Equivalence Passed]"):
            query_ok = False
            issues.append(
                "check_query_equivalence must pass before query translation can finish."
            )

    return issues, schema_ok, query_ok


def _deterministic_feedback_message(issues: list[str]) -> HumanMessage:
    """Build a deterministic repair instruction for the translation agent."""
    numbered_issues = "\n".join(
        f"{idx + 1}. {issue}" for idx, issue in enumerate(issues)
    )
    feedback = (
        "Your previous translation attempt cannot be accepted yet.\n"
        "Fix all deterministic issues below, then return structured output again:\n"
        f"{numbered_issues}\n"
        "For query translations, keep translated_query_code and validation_harness_code separate.\n"
        "Required tool sequence for query translations:"
        " validate_source_query -> validate_target_query -> check_query_equivalence."
    )
    return HumanMessage(content=feedback)
