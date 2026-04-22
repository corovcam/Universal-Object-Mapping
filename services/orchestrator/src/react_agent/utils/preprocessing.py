"""Mapping preprocessing helpers for MongoDB and Neo4j."""

from typing import Any, Literal, cast

from react_agent.constants import FrameworkType
from react_agent.utils.utils import get_database_mapping_json


def _normalize_text(value: Any) -> str | None:
    """Normalize a text value by stripping surrounding whitespace."""
    if not isinstance(value, str):
        return None

    normalized = value.strip()
    if not normalized:
        return None
    return normalized


def _singularize_name(name: str) -> str:
    """Convert a plural identifier to a simple singular form."""
    if name.endswith("ies") and len(name) > 3:
        return f"{name[:-3]}y"
    if name.endswith("s") and not name.endswith("ss") and len(name) > 1:
        return name[:-1]
    return name


def _format_mongodb_source_schema(table_path_payload: Any) -> str | None:
    """Build a source schema string from MongoDB table path metadata."""
    if not isinstance(table_path_payload, dict):
        return None

    source_database = _normalize_text(table_path_payload.get("database"))
    source_schema = _normalize_text(table_path_payload.get("schema"))

    if source_database and source_schema:
        return f"{source_database}.{source_schema}"
    return source_schema or source_database


def _extract_mongodb_property_mappings(fields_payload: Any) -> list[dict[str, Any]]:
    """Extract MongoDB property mappings in standalone format."""
    if not isinstance(fields_payload, dict):
        return []

    fields_payload_dict = cast(dict[str, Any], fields_payload)

    property_mappings: list[dict[str, Any]] = []
    seen_mappings: set[tuple[str, str]] = set()

    for source_field_key, field_payload in sorted(
        fields_payload_dict.items(),
        key=lambda item: str(item[0]).lower(),
    ):
        if not isinstance(field_payload, dict):
            continue

        field_payload_dict = cast(dict[str, Any], field_payload)

        source = field_payload_dict.get("source")
        target = field_payload_dict.get("target")
        if not isinstance(source, dict) or not isinstance(target, dict):
            continue
        if target.get("included") is False:
            continue

        source_column = _normalize_text(source.get("name")) or _normalize_text(
            source_field_key
        )
        target_property = _normalize_text(target.get("name"))
        sql_data_type = _normalize_text(source.get("databaseSpecificType"))
        mongo_data_type = _normalize_text(target.get("type"))

        if (
            not source_column
            or not target_property
            or not sql_data_type
            or not mongo_data_type
        ):
            continue
        if source_column == "_id" or sql_data_type.upper() == "NONE":
            continue

        mapping_key = (source_column.lower(), target_property.lower())
        if mapping_key in seen_mappings:
            continue
        seen_mappings.add(mapping_key)

        property_mappings.append(
            {
                "sourceColumn": source_column,
                "sqlDataType": sql_data_type.lower(),
                "isPrimaryKey": bool(source.get("isPrimaryKey") is True),
                "targetProperty": target_property,
                "mongoDataType": mongo_data_type.upper(),
            }
        )

    property_mappings.sort(
        key=lambda item: (
            str(item.get("targetProperty", "")).lower(),
            str(item.get("sourceColumn", "")).lower(),
        )
    )
    return property_mappings


def _extract_mongodb_standalone_mapping(
    mapping_payload: Any,
) -> dict[Literal["collections"], dict[str, Any]]:
    """Extract MongoDB mapping into standalone collections/mappings structure."""
    empty_mapping: dict[Literal["collections"], dict[str, Any]] = {
        "collections": {},
    }
    if not isinstance(mapping_payload, dict):
        return empty_mapping

    project_payload = mapping_payload.get("project")
    if not isinstance(project_payload, dict):
        return empty_mapping

    content_payload = project_payload.get("content")
    if not isinstance(content_payload, dict):
        return empty_mapping

    collections_payload = content_payload.get("collections")
    mappings_payload = content_payload.get("mappings")
    tables_payload = content_payload.get("tables")

    if (
        not isinstance(collections_payload, dict)
        or not isinstance(mappings_payload, dict)
        or not isinstance(tables_payload, dict)
    ):
        return empty_mapping

    collections_mapping: dict[str, list[dict[str, Any]]] = {}

    for mapping_entry in mappings_payload.values():
        if not isinstance(mapping_entry, dict):
            continue

        collection_id = _normalize_text(mapping_entry.get("collectionId"))
        table_id = _normalize_text(mapping_entry.get("table"))
        if not collection_id or not table_id:
            continue

        collection_entry = collections_payload.get(collection_id)
        table_entry = tables_payload.get(table_id)
        if not isinstance(collection_entry, dict) or not isinstance(table_entry, dict):
            continue

        collection_name = _normalize_text(collection_entry.get("name"))
        table_path = table_entry.get("path")
        source_schema = _format_mongodb_source_schema(table_path)
        source_table = (
            _normalize_text(table_path.get("table"))
            if isinstance(table_path, dict)
            else None
        )

        if not collection_name or not source_schema or not source_table:
            continue

        settings = mapping_entry.get("settings")
        mapping_type = "NEW_DOCUMENT"
        embedded_path: str | None = None

        if isinstance(settings, dict):
            source_mapping_type = _normalize_text(settings.get("type"))
            if source_mapping_type:
                mapping_type = source_mapping_type.upper()
            embedded_path = _normalize_text(settings.get("embeddedPath"))

        standalone_mapping: dict[str, Any] = {
            "mappingType": mapping_type,
            "sourceSchema": source_schema,
            "sourceTable": source_table,
            "propertyMappings": _extract_mongodb_property_mappings(
                mapping_entry.get("fields")
            ),
        }
        if embedded_path and mapping_type != "NEW_DOCUMENT":
            standalone_mapping["embeddedPath"] = embedded_path

        collections_mapping.setdefault(collection_name, []).append(standalone_mapping)

    sorted_collections: dict[str, dict[str, Any]] = {}
    for collection_name in sorted(collections_mapping):
        sorted_collections[collection_name] = {
            "mappings": sorted(
                collections_mapping[collection_name],
                key=lambda item: (
                    str(item.get("mappingType", "")),
                    str(item.get("sourceSchema", "")),
                    str(item.get("sourceTable", "")),
                    str(item.get("embeddedPath", "")),
                ),
            )
        }

    return {"collections": sorted_collections}


def _extract_column_names_in_order(column_payload: Any) -> list[str]:
    """Extract SQL column names while preserving nested traversal order."""
    if not isinstance(column_payload, dict):
        return []

    extracted_names: list[str] = []
    seen_names: set[str] = set()

    def _walk_column(column: Any) -> None:
        if not isinstance(column, dict):
            return

        column_name = _normalize_text(column.get("name"))
        if column_name and column_name not in seen_names:
            seen_names.add(column_name)
            extracted_names.append(column_name)

        nested_columns = column.get("columns")
        if isinstance(nested_columns, list):
            for nested_column in nested_columns:
                _walk_column(nested_column)

        referenced_column = column.get("referenced-column")
        if isinstance(referenced_column, dict):
            _walk_column(referenced_column)

    _walk_column(column_payload)
    return extracted_names


def _extract_table_name(column_payload: Any) -> str | None:
    """Extract the first available source table name from a column payload."""
    if not isinstance(column_payload, dict):
        return None

    direct_table_name = _normalize_text(column_payload.get("table"))
    if direct_table_name:
        return direct_table_name

    nested_columns = column_payload.get("columns")
    if isinstance(nested_columns, list):
        for nested_column in nested_columns:
            nested_table_name = _extract_table_name(nested_column)
            if nested_table_name:
                return nested_table_name

    referenced_column = column_payload.get("referenced-column")
    if isinstance(referenced_column, dict):
        return _extract_table_name(referenced_column)

    return None


def _extract_source_table(mapping_entries: list[Any]) -> str | None:
    """Extract the source table name from graph object mapping entries."""
    for mapping_entry in mapping_entries:
        if not isinstance(mapping_entry, dict):
            continue

        source_table = _extract_table_name(mapping_entry.get("column"))
        if source_table:
            return source_table

    return None


def _extract_primary_key_columns(mapping_entries: list[Any]) -> set[str]:
    """Extract normalized primary key source columns for a Neo4j node."""
    primary_key_columns: set[str] = set()

    for mapping_entry in mapping_entries:
        if not isinstance(mapping_entry, dict):
            continue

        field = mapping_entry.get("field")
        if not isinstance(field, dict) or field.get("type") != "Id":
            continue

        for column_name in _extract_column_names_in_order(mapping_entry.get("column")):
            primary_key_columns.add(column_name.lower())

    return primary_key_columns


def _extract_node_id_space(mapping_entries: list[Any]) -> str | None:
    """Extract the id-space identifier from a Neo4j node mapping."""
    for mapping_entry in mapping_entries:
        if not isinstance(mapping_entry, dict):
            continue

        field = mapping_entry.get("field")
        if not isinstance(field, dict) or field.get("type") != "Id":
            continue

        node_id_space = _normalize_text(field.get("id-space"))
        if node_id_space:
            return node_id_space

    return None


def _extract_node_label(
    mapping_entries: list[Any],
    source_table: str | None,
) -> str | None:
    """Extract the target node label from Neo4j node mapping entries."""
    for mapping_entry in mapping_entries:
        if not isinstance(mapping_entry, dict):
            continue

        field = mapping_entry.get("field")
        if not isinstance(field, dict) or field.get("type") != "Label":
            continue

        label_candidates = _extract_column_names_in_order(mapping_entry.get("column"))
        if label_candidates:
            return _singularize_name(label_candidates[0])

    if source_table:
        return _singularize_name(source_table)
    return None


def _collect_node_property_mappings(
    mapping_entries: list[Any],
    primary_key_columns: set[str],
) -> list[dict[str, Any]]:
    """Collect node property mappings in the standalone Neo4j format."""
    property_mappings: list[dict[str, Any]] = []
    seen_mappings: set[tuple[str, str]] = set()

    for mapping_entry in mapping_entries:
        if not isinstance(mapping_entry, dict):
            continue

        field = mapping_entry.get("field")
        if not isinstance(field, dict) or field.get("type") != "Data":
            continue

        source_columns = _extract_column_names_in_order(mapping_entry.get("column"))
        if not source_columns:
            continue

        source_column = source_columns[0]
        target_property = _normalize_text(field.get("name"))
        if not target_property:
            continue

        column = mapping_entry.get("column")
        if not isinstance(column, dict):
            continue

        sql_data_type = _normalize_text(column.get("sql-data-type"))
        neo4j_data_type = _normalize_text(field.get("neo4j-data-type"))
        if not sql_data_type or not neo4j_data_type:
            continue

        mapping_key = (source_column.lower(), target_property.lower())
        if mapping_key in seen_mappings:
            continue
        seen_mappings.add(mapping_key)

        property_mappings.append(
            {
                "sourceColumn": source_column,
                "sqlDataType": sql_data_type,
                "isPrimaryKey": source_column.lower() in primary_key_columns,
                "targetProperty": target_property,
                "neo4jDataType": neo4j_data_type,
            }
        )

    property_mappings.sort(
        key=lambda item: (
            str(item.get("targetProperty", "")).lower(),
            str(item.get("sourceColumn", "")).lower(),
        )
    )
    return property_mappings


def _resolve_entity_from_id_space(
    id_space: Any,
    id_space_to_entity: dict[str, str],
) -> str | None:
    """Resolve id-space to a node label for relationship endpoint mappings."""
    normalized_id_space = _normalize_text(id_space)
    if not normalized_id_space:
        return None

    resolved_entity = id_space_to_entity.get(normalized_id_space.lower())
    if resolved_entity:
        return resolved_entity

    fallback_segment = normalized_id_space.rsplit(".", 1)[-1]
    fallback_entity = _normalize_text(fallback_segment)
    if fallback_entity:
        return _singularize_name(fallback_entity)

    return None


def _extract_endpoint_mapping(
    mapping_entries: list[Any],
    endpoint_type: str,
    id_space_to_entity: dict[str, str],
) -> dict[Literal["sourceColumn", "targetEntity"], str] | None:
    """Extract relationship endpoint mapping for StartId/EndId fields."""
    for mapping_entry in mapping_entries:
        if not isinstance(mapping_entry, dict):
            continue

        field = mapping_entry.get("field")
        if not isinstance(field, dict) or field.get("type") != endpoint_type:
            continue

        source_columns = _extract_column_names_in_order(mapping_entry.get("column"))
        target_entity = _resolve_entity_from_id_space(
            field.get("id-space"),
            id_space_to_entity,
        )

        if source_columns and target_entity:
            return {
                "sourceColumn": source_columns[0],
                "targetEntity": target_entity,
            }

    return None


def _extract_relationship_type(mapping_entries: list[Any]) -> str | None:
    """Extract Neo4j relationship type from mapping entries."""
    for mapping_entry in mapping_entries:
        if not isinstance(mapping_entry, dict):
            continue

        field = mapping_entry.get("field")
        if not isinstance(field, dict) or field.get("type") != "RelationshipType":
            continue

        relationship_columns = _extract_column_names_in_order(
            mapping_entry.get("column")
        )
        if relationship_columns:
            return relationship_columns[0].upper()

    return None


def _collect_relationship_property_mappings(
    mapping_entries: list[Any],
) -> list[dict[str, str]]:
    """Collect relationship properties in the standalone Neo4j format."""
    property_mappings: list[dict[str, str]] = []
    seen_mappings: set[tuple[str, str]] = set()

    for mapping_entry in mapping_entries:
        if not isinstance(mapping_entry, dict):
            continue

        field = mapping_entry.get("field")
        if not isinstance(field, dict) or field.get("type") != "Data":
            continue

        source_columns = _extract_column_names_in_order(mapping_entry.get("column"))
        if not source_columns:
            continue

        source_column = source_columns[0]
        target_property = _normalize_text(field.get("name"))
        if not target_property:
            continue

        column = mapping_entry.get("column")
        if not isinstance(column, dict):
            continue

        sql_data_type = _normalize_text(column.get("sql-data-type"))
        neo4j_data_type = _normalize_text(field.get("neo4j-data-type"))
        if not sql_data_type or not neo4j_data_type:
            continue

        mapping_key = (source_column.lower(), target_property.lower())
        if mapping_key in seen_mappings:
            continue
        seen_mappings.add(mapping_key)

        property_mappings.append(
            {
                "sourceColumn": source_column,
                "sqlDataType": sql_data_type,
                "targetProperty": target_property,
                "neo4jDataType": neo4j_data_type,
            }
        )

    property_mappings.sort(
        key=lambda item: (
            str(item.get("targetProperty", "")).lower(),
            str(item.get("sourceColumn", "")).lower(),
        )
    )
    return property_mappings


def _extract_neo4j_standalone_mapping(
    mapping_payload: Any,
) -> dict[Literal["nodes", "relationships"], dict[str, Any]]:
    """Extract Neo4j mapping into standalone nodes/relationships structure."""
    empty_mapping: dict[Literal["nodes", "relationships"], dict[str, Any]] = {
        "nodes": {},
        "relationships": {},
    }
    if not isinstance(mapping_payload, list):
        return empty_mapping

    nodes: dict[str, dict[str, Any]] = {}
    id_space_to_entity: dict[str, str] = {}

    for graph_object in mapping_payload:
        if not isinstance(graph_object, dict):
            continue
        if graph_object.get("graph-object-type") != "Node":
            continue

        mapping_entries = graph_object.get("mappings")
        if not isinstance(mapping_entries, list):
            continue

        source_schema = _normalize_text(graph_object.get("schema"))
        source_table = _extract_source_table(mapping_entries)
        node_label = _extract_node_label(mapping_entries, source_table)

        if not source_schema or not source_table or not node_label:
            continue

        primary_key_columns = _extract_primary_key_columns(mapping_entries)
        property_mappings = _collect_node_property_mappings(
            mapping_entries,
            primary_key_columns,
        )

        existing_node_mapping = nodes.get(node_label)
        if existing_node_mapping is None:
            nodes[node_label] = {
                "sourceSchema": source_schema,
                "sourceTable": source_table,
                "propertyMappings": property_mappings,
            }
        else:
            merged_property_mappings = [
                *existing_node_mapping.get("propertyMappings", []),
                *property_mappings,
            ]
            deduped: dict[tuple[str, str], dict[str, Any]] = {}
            for property_mapping in merged_property_mappings:
                source_column = _normalize_text(property_mapping.get("sourceColumn"))
                target_property = _normalize_text(
                    property_mapping.get("targetProperty")
                )
                if not source_column or not target_property:
                    continue
                deduped[(source_column.lower(), target_property.lower())] = (
                    property_mapping
                )

            existing_node_mapping["propertyMappings"] = sorted(
                deduped.values(),
                key=lambda item: (
                    str(item.get("targetProperty", "")).lower(),
                    str(item.get("sourceColumn", "")).lower(),
                ),
            )

        node_id_space = _extract_node_id_space(mapping_entries)
        if node_id_space:
            id_space_to_entity[node_id_space.lower()] = node_label

    relationships: dict[str, list[dict[str, Any]]] = {}

    for graph_object in mapping_payload:
        if not isinstance(graph_object, dict):
            continue
        if graph_object.get("graph-object-type") != "Relationship":
            continue

        mapping_entries = graph_object.get("mappings")
        if not isinstance(mapping_entries, list):
            continue

        relationship_type = _extract_relationship_type(mapping_entries)
        source_schema = _normalize_text(graph_object.get("schema"))
        source_table = _extract_source_table(mapping_entries)
        start_node_mapping = _extract_endpoint_mapping(
            mapping_entries,
            "StartId",
            id_space_to_entity,
        )
        end_node_mapping = _extract_endpoint_mapping(
            mapping_entries,
            "EndId",
            id_space_to_entity,
        )

        if (
            not relationship_type
            or not source_schema
            or not source_table
            or not start_node_mapping
            or not end_node_mapping
        ):
            continue

        relationships.setdefault(relationship_type, []).append(
            {
                "sourceSchema": source_schema,
                "sourceTable": source_table,
                "startNodeMapping": start_node_mapping,
                "endNodeMapping": end_node_mapping,
                "propertyMappings": _collect_relationship_property_mappings(
                    mapping_entries
                ),
            }
        )

    sorted_nodes = {node_name: nodes[node_name] for node_name in sorted(nodes)}

    sorted_relationships: dict[str, list[dict[str, Any]]] = {}
    for relationship_type in sorted(relationships):
        sorted_relationships[relationship_type] = sorted(
            relationships[relationship_type],
            key=lambda item: (
                str(item.get("sourceSchema", "")),
                str(item.get("sourceTable", "")),
                str(item.get("startNodeMapping", {}).get("sourceColumn", "")),
                str(item.get("endNodeMapping", {}).get("sourceColumn", "")),
            ),
        )

    return {
        "nodes": sorted_nodes,
        "relationships": sorted_relationships,
    }


async def get_neo4j_standalone_mapping() -> (
    dict[Literal["nodes", "relationships"], dict[str, Any]] | None
):
    """Load standalone SQL-to-Neo4j mapping grouped into nodes and relationships."""
    raw_database_mapping = await get_database_mapping_json(
        FrameworkType.JAVA_SPRING_DATA_NEO4J
    )
    database_mapping = _extract_neo4j_standalone_mapping(
        raw_database_mapping.get("mapping") if raw_database_mapping else None
    )
    if not database_mapping:
        return None

    nodes = database_mapping.get("nodes")
    relationships = database_mapping.get("relationships")
    if not isinstance(nodes, dict) or not isinstance(relationships, dict):
        return None

    return {
        "nodes": nodes,
        "relationships": relationships,
    }


async def get_mongodb_standalone_mapping() -> (
    dict[Literal["collections"], dict[str, Any]] | None
):
    """Load standalone SQL-to-MongoDB mapping grouped into collections."""
    raw_database_mapping = await get_database_mapping_json(
        FrameworkType.JAVA_SPRING_DATA_MONGODB
    )
    database_mapping = _extract_mongodb_standalone_mapping(
        raw_database_mapping.get("mapping") if raw_database_mapping else None
    )
    if not database_mapping:
        return None

    collections = database_mapping.get("collections")
    if not isinstance(collections, dict):
        return None

    return {
        "collections": collections,
    }
