"""Query validation and equivalence tools for source and target query execution metadata."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from enum import Enum
from typing import Any

import httpx
from langchain.tools import ToolRuntime
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from react_agent.constants import FrameworkType, SourceFramework, TargetFramework
from react_agent.context import Context
from react_agent.utils.utils import get_normalized_framework_name


class SourceQueryInput(BaseModel):
    """Input payload for validating source-side query metadata."""

    validation_schema_code: str = Field(
        min_length=1,
        description="C# schema/entity code. This may include DbContext/session/config/bootstrap setup, but should keep "
        "the core source schema mapping equivalent to the original source_schema_code. Should be fully valid C# code. Do not include query-related code here."
        + """
<example orm=\"EfCore\">
using System;
using Microsoft.EntityFrameworkCore;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace Sandbox;

[Table(\"OrderLines\", Schema = \"Sales\")]
public class OrderLine
{
    [Key]
    public int OrderLineID { get; set; }

    public DateTime? PickingCompletedWhen { get; set; }

    public string Description { get; set; } = string.Empty;
}

public class WideWorldImportersContext : DbContext
{
    public WideWorldImportersContext(DbContextOptions<WideWorldImportersContext> options)
        : base(options)
    {
    }

    public DbSet<OrderLine> OrderLines => Set<OrderLine>();
}
</example>""",
    )
    validation_harness_code: str = Field(
        min_length=1,
        description="C# query validation harness code only. Should keep the core source query logic equivalent to the original source query method."
        + """
<example orm=\"EfCore\">
using System;
using Microsoft.EntityFrameworkCore;

namespace Sandbox;

public static class QueryEntrypoint
{
    public static IQueryable<OrderLine> Build(WideWorldImportersContext context, bool ascending)
    {
        var from = new DateTime(2014, 12, 20);
        var to = new DateTime(2014, 12, 31);

        var query = context.OrderLines
            .Where(ol => ol.PickingCompletedWhen >= from && ol.PickingCompletedWhen <= to);

        var sorted = ascending ? query.OrderBy(ol => ol.OrderLineID) : query.OrderByDescending(ol => ol.OrderLineID);

        return sorted;
    }
}
</example>""",
    )
    source_framework: SourceFramework = Field(
        description="Source framework for query execution"
    )
    sort_by_field: str = Field(
        min_length=1,
        description="Deterministic sort field (preferably unique ID, or any relevant property) for first/last sample extraction",
    )
    entry_type_name: str = Field(
        min_length=1,
        description="Entrypoint type name declared in validation_harness_code",
    )
    entry_method_name: str = Field(
        min_length=1,
        description="Entrypoint method name declared in validation_harness_code",
    )


class TargetQueryInput(BaseModel):
    """Input payload for validating target-side query metadata."""

    validation_schema_code: str = Field(
        min_length=1,
        description="Java schema code only with .",
    )
    validation_harness_code: str = Field(
        min_length=1,
        description=(
            "Java query validation harness code only. Place validator-only setup/wiring here (template/bootstrap/count) while "
            "keeping translated_query_code focused on the production query method."
        ),
    )
    framework: TargetFramework = Field(description="Target query framework")
    sort_by_field: str = Field(
        min_length=1,
        description="Deterministic sort field for first/last sample extraction. Should be the same field as source query sort_by_field or its mapped equivalent.",
    )
    entry_type_name: str = Field(
        min_length=1,
        description="Entrypoint type name declared in validation_harness_code",
    )
    entry_method_name: str = Field(
        min_length=1,
        description="Entrypoint method name declared in validation_harness_code",
    )


class QueryEquivalenceInput(BaseModel):
    """Input payload for source/target query equivalence checks."""

    source_validation_output: str = Field(
        min_length=1,
        description=(
            "Output of validate_source_query. Preferred format: full tool output string that starts with "
            "[Source Query Validation Passed] followed by JSON summary."
        ),
    )
    target_validation_output: str = Field(
        min_length=1,
        description=(
            "Output of validate_target_query. Preferred format: full tool output string that starts with "
            "[Target Query Validation Passed] followed by JSON summary."
        ),
    )
    mapping_json: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Mapping in JSON format. Example: "
            '{"nodes":{"Customer":{"propertyMappings":[{"sourceColumn":"CustomerID","targetProperty":"customerId"}]}},'
            '"relationships":{"PEOPLE":[{"propertyMappings":[{"sourceColumn":"LastEditedBy","targetProperty":"lastEditedBy"}]}]}}'
        ),
    )


def _extract_type_names(code: str) -> set[str]:
    return {
        match.group(2).lower()
        for match in re.finditer(
            r"\b(class|record|interface|enum)\s+([A-Za-z_][A-Za-z0-9_]*)",
            code,
        )
    }


def _detect_duplicate_type_names(schema_code: str, harness_code: str) -> list[str]:
    return sorted(
        _extract_type_names(schema_code).intersection(_extract_type_names(harness_code))
    )


@tool("validate_source_query", args_schema=SourceQueryInput)
async def validate_source_query(
    validation_schema_code: str,
    validation_harness_code: str,
    framework: SourceFramework,
    sort_by_field: str,
    entry_type_name: str,
    entry_method_name: str,
    runtime: ToolRuntime[Context],
) -> str:
    """Validate source query execution metadata via dotnet-service."""
    normalized_schema = validation_schema_code.strip()
    normalized_harness = validation_harness_code.strip()

    duplicate_types = _detect_duplicate_type_names(
        normalized_schema, normalized_harness
    )
    if duplicate_types:
        return "[Source Query Validation Failed]\n" + json.dumps(
            {
                "errors": [
                    "validation_harness_code duplicates schema types. Keep schema and harness separate."
                ],
                "duplicateTypes": duplicate_types,
            },
            default=str,
        )

    payload = {
        "sourceCode": normalized_harness,
        "schemaCode": normalized_schema,
        "framework": get_normalized_framework_name(framework),
        "sortByField": sort_by_field,
        "entryTypeName": entry_type_name,
        "entryMethodName": entry_method_name,
    }

    dotnet_service_uri = runtime.context.dotnet_service_uri
    url = f"{dotnet_service_uri}/api/compiler/query-info"
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, json=payload)
    except httpx.ConnectError:
        return (
            f"[Source Query Validation Failed] Could not connect to dotnet-service at "
            f"{dotnet_service_uri}."
        )
    except httpx.TimeoutException:
        return "[Source Query Validation Failed] dotnet-service query-info request timed out."
    except httpx.HTTPError as ex:
        return f"[Source Query Validation Failed] HTTP error while calling dotnet-service: {ex}"

    try:
        result = response.json()
    except Exception:
        return (
            "[Source Query Validation Failed] dotnet-service returned non-JSON payload: "
            f"{response.text[:600]}"
        )

    if response.is_success and result.get("success", False):
        summary = {
            "estimatedRowCount": result.get("estimatedRowCount"),
            "errors": result.get(
                "errors", []
            ),  # TODO: just return the whole error stream from dotnet/java services, dont't try to parse it in the services, it is too error prone.
            "payload": result,
        }
        return "[Source Query Validation Passed]\n" + json.dumps(summary, default=str)

    errors = result.get("errors") if isinstance(result, dict) else None
    if not isinstance(errors, list):
        errors = [result]

    return "[Source Query Validation Failed]\n" + json.dumps(
        {
            "errors": errors,
            "payload": result,
        },
        default=str,
    )


@tool("validate_target_query", args_schema=TargetQueryInput)
async def validate_target_query(
    validation_schema_code: str,
    validation_harness_code: str,
    framework: TargetFramework,
    sort_by_field: str,
    entry_type_name: str,
    entry_method_name: str,
    runtime: ToolRuntime[Context],
) -> str:
    """Validate target query execution metadata via java-services."""
    normalized_schema = validation_schema_code.strip()
    normalized_harness = validation_harness_code.strip()

    duplicate_types = _detect_duplicate_type_names(
        normalized_schema, normalized_harness
    )
    if duplicate_types:
        return "[Target Query Validation Failed]\n" + json.dumps(
            {
                "errors": [
                    "validation_harness_code duplicates schema types. Keep schema and harness separate."
                ],
                "duplicateTypes": duplicate_types,
            },
            default=str,
        )

    payload = {
        "sourceCode": normalized_harness,
        "schemaCode": normalized_schema,
        "framework": get_normalized_framework_name(framework),
        "sortByField": sort_by_field,
        "entryTypeName": entry_type_name,
        "entryMethodName": entry_method_name,
    }

    java_service_uri = runtime.context.java_service_uri
    url = f"{java_service_uri}/api/query/info"
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, json=payload)
    except httpx.ConnectError:
        return (
            f"[Target Query Validation Failed] Could not connect to java-services at "
            f"{java_service_uri}."
        )
    except httpx.TimeoutException:
        return "[Target Query Validation Failed] java-services query-info request timed out."
    except httpx.HTTPError as ex:
        return f"[Target Query Validation Failed] HTTP error while calling java-services: {ex}"

    try:
        result = response.json()
    except Exception:
        return (
            "[Target Query Validation Failed] java-services returned non-JSON payload: "
            f"{response.text[:600]}"
        )

    if response.is_success and result.get("success", False):
        summary = {
            "estimatedResultCount": result.get("estimatedResultCount"),
            "errors": result.get(
                "errors", []
            ),  # TODO: just return the whole error stream from dotnet/java services, dont't try to parse it in the services, it is too error prone.
            "payload": result,
        }
        return "[Target Query Validation Passed]\n" + json.dumps(summary, default=str)

    errors = result.get("errors") if isinstance(result, dict) else None
    if not isinstance(errors, list):
        errors = [result]

    return "[Target Query Validation Failed]\n" + json.dumps(
        {
            "errors": errors,
            "payload": result,
        },
        default=str,
    )


def _parse_validation_payload(
    validation_output: str,
    passed_marker: str,
    failed_marker: str,
) -> tuple[dict[str, Any] | None, str | None]:
    text = validation_output.strip()
    if not text:
        return None, "validation output is empty"

    if failed_marker in text:
        return None, f"found failure marker {failed_marker}"

    parsed: dict[str, Any] | None = None
    try:
        as_json = json.loads(text)
        if isinstance(as_json, dict):
            parsed = as_json
    except json.JSONDecodeError:
        parsed = None

    if parsed is None and passed_marker in text:
        _, _, json_part = text.partition("\n")
        if json_part.strip():
            try:
                as_json = json.loads(json_part)
                if isinstance(as_json, dict):
                    parsed = as_json
            except json.JSONDecodeError:
                parsed = None

    if parsed is None:
        return None, "could not parse JSON payload from validator output"

    payload = parsed.get("payload")
    if isinstance(payload, dict):
        return payload, None

    return parsed, None


@tool("check_query_equivalence", args_schema=QueryEquivalenceInput)
async def check_query_equivalence(
    source_validation_output: str,
    target_validation_output: str,
    mapping_json: dict[str, Any],
) -> str:
    """Compare source and target query metadata for logical equivalence."""
    source_info, source_error = _parse_validation_payload(
        source_validation_output,
        "[Source Query Validation Passed]",
        "[Source Query Validation Failed]",
    )
    if source_error is not None:
        return f"[Query Equivalence Failed] Invalid source validation payload: {source_error}"

    target_info, target_error = _parse_validation_payload(
        target_validation_output,
        "[Target Query Validation Passed]",
        "[Target Query Validation Failed]",
    )
    if target_error is not None:
        return f"[Query Equivalence Failed] Invalid target validation payload: {target_error}"

    assert source_info is not None
    assert target_info is not None

    mapping = _extract_field_mapping(mapping_json)
    # TODO: add edit distance (Levenshtein distance) maybe for string comparisons
    # TODO: add tolerance threshold for sample comparison, not just pass/fail
    # TODO: we don't need to compare query output schemas, we just need to compare samples
    # and count, we just need easy-to-compare JSON representations of samples from services
    count_match, count_details = _compare_count(source_info, target_info)
    sample_match, sample_details = _compare_samples(source_info, target_info, mapping)

    overall = count_match and sample_match
    status = "Passed" if overall else "Failed"
    return "\n".join(
        [
            f"[Query Equivalence {status}]",
            f"count_match={count_match}; details={count_details}",
            f"sample_match={sample_match}; details={sample_details}",
        ]
    )


def _extract_field_mapping(mapping_payload: Any) -> dict[str, list[str]]:
    """Extract source-to-target field mapping from standalone mapping payloads."""
    mapping: dict[str, list[str]] = {}

    if not isinstance(mapping_payload, dict):
        return mapping

    collections = mapping_payload.get("collections")
    if isinstance(collections, dict):
        for collection_payload in collections.values():
            if not isinstance(collection_payload, dict):
                continue

            collection_mappings = collection_payload.get("mappings")
            if not isinstance(collection_mappings, list):
                continue

            for collection_mapping in collection_mappings:
                if not isinstance(collection_mapping, dict):
                    continue
                _merge_property_mappings(
                    collection_mapping.get("propertyMappings"),
                    mapping,
                )

    nodes = mapping_payload.get("nodes")
    if isinstance(nodes, dict):
        for node_payload in nodes.values():
            if not isinstance(node_payload, dict):
                continue
            _merge_property_mappings(node_payload.get("propertyMappings"), mapping)

    relationships = mapping_payload.get("relationships")
    if isinstance(relationships, dict):
        for relationship_entries in relationships.values():
            if not isinstance(relationship_entries, list):
                continue
            for relationship_payload in relationship_entries:
                if not isinstance(relationship_payload, dict):
                    continue
                _merge_property_mappings(
                    relationship_payload.get("propertyMappings"),
                    mapping,
                )

    for source_column in mapping:
        mapping[source_column] = sorted(mapping[source_column])

    return dict(sorted(mapping.items()))


def _merge_property_mappings(
    property_mappings_payload: Any,
    mapping: dict[str, list[str]],
) -> None:
    """Merge source column to target property entries into an index."""
    if not isinstance(property_mappings_payload, list):
        return

    for property_mapping in property_mappings_payload:
        if not isinstance(property_mapping, dict):
            continue

        source_column = property_mapping.get("sourceColumn")
        target_property = property_mapping.get("targetProperty")

        if not isinstance(source_column, str) or not isinstance(target_property, str):
            continue

        normalized_source = source_column.strip().lower()
        normalized_target = target_property.strip().lower()
        if not normalized_source or not normalized_target:
            continue

        mapping.setdefault(normalized_source, [])
        if normalized_target not in mapping[normalized_source]:
            mapping[normalized_source].append(normalized_target)


def _compare_count(
    source_info: dict[str, Any],
    target_info: dict[str, Any],
) -> tuple[bool, str]:
    source_count = source_info.get("estimatedRowCount")
    if source_count is None:
        source_count = source_info.get("estimatedResultCount")

    target_count = target_info.get("estimatedResultCount")
    if target_count is None:
        target_count = target_info.get("estimatedRowCount")

    if source_count is None or target_count is None:
        return False, "count missing in source or target payload"

    try:
        normalized_source_count = int(source_count)
        normalized_target_count = int(target_count)
    except (TypeError, ValueError):
        return (
            False,
            (
                "non-numeric count values "
                f"(source={source_count}, target={target_count})"
            ),
        )

    if normalized_source_count == normalized_target_count:
        return True, f"exact match ({normalized_source_count})"

    return (
        False,
        (
            "exact mismatch "
            f"(source={normalized_source_count}, target={normalized_target_count})"
        ),
    )


def _compare_samples(
    source_info: dict[str, Any],
    target_info: dict[str, Any],
    mapping: dict[str, list[str]],
) -> tuple[bool, str]:
    source_first = source_info.get("firstSample")
    source_last = source_info.get("lastSample")
    target_first = target_info.get("firstSample")
    target_last = target_info.get("lastSample")

    first_ok, first_detail = _compare_sample_pair(source_first, target_first, mapping)
    last_ok, last_detail = _compare_sample_pair(source_last, target_last, mapping)

    if first_ok and last_ok:
        return True, "first and last sample pairs matched"

    return False, json.dumps({"first": first_detail, "last": last_detail})


# TODO: normalization should also be handled in dotnet-service and java-service when serializing into JSON somehow so that we simplify this part
def _compare_sample_pair(
    source: Any, target: Any, mapping: dict[str, list[str]]
) -> tuple[bool, Any]:
    if source is None and target is None:
        return True, "both samples are null"
    if source is None or target is None:
        return False, "one sample is null"

    if not isinstance(source, dict) or not isinstance(target, dict):
        normalized_source = _normalize_value(source)
        normalized_target = _normalize_value(target)
        return normalized_source == normalized_target, {
            "source": normalized_source,
            "target": normalized_target,
        }

    target_normalized = {
        key.lower(): _normalize_value(value) for key, value in target.items()
    }
    mismatches = []

    for source_key, source_value in source.items():
        source_key_normalized = source_key.lower()
        expected_target_keys = mapping.get(
            source_key_normalized, [source_key_normalized]
        )
        normalized_source_value = _normalize_value(source_value)

        if not any(
            expected_key in target_normalized
            and target_normalized[expected_key] == normalized_source_value
            for expected_key in expected_target_keys
        ):
            mismatches.append(
                {
                    "sourceKey": source_key,
                    "sourceValue": normalized_source_value,
                    "expectedTargetKeys": expected_target_keys,
                }
            )
    # TODO: should use tolerance threshold, or e.g. levenshtein distance
    return len(mismatches) == 0, {"mismatches": mismatches}


def _normalize_value(value: Any) -> Any:
    if value is None:
        return None

    if isinstance(value, bool):
        return value

    if isinstance(value, int | float):
        if isinstance(value, float) and value.is_integer():
            return int(value)
        return value

    if isinstance(value, str):
        candidate = value.strip()
        try:
            parsed = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
            return parsed.isoformat()
        except ValueError:
            return candidate

    if isinstance(value, list):
        return [_normalize_value(item) for item in value]

    if isinstance(value, dict):
        return {
            str(key).lower(): _normalize_value(inner) for key, inner in value.items()
        }

    return str(value)
