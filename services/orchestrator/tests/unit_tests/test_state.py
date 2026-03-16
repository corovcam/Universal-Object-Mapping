from react_agent.state import State, ORMType


def test_state_initialization() -> None:
    """State initializes properly with unknown types and default counters."""
    state = State(
        messages=[],
        source_code="",
        source_target=ORMType.UNKNOWN,
        destination_target=ORMType.UNKNOWN,
        council_responses=[],
        schema_translated_code="",
        query_translated_code="",
        schema_validation_result="",
        query_validation_result="",
        error_feedback="",
        error_count=0,
        max_retries=3,
    )

    assert state.source_target == ORMType.UNKNOWN
    assert state.destination_target == ORMType.UNKNOWN
    assert state.error_count == 0
    assert state.max_retries == 3
    assert state.source_code == ""


def test_orm_type_values() -> None:
    """ORMType enum values match their human-readable string descriptions."""
    assert ORMType.MS_SQL_NATIVE.value == "MS SQL Native"
    assert ORMType.EFCORE_LINQ.value == "C# EFCore LINQ"
    assert ORMType.DAPPER.value == "C# Dapper"
    assert ORMType.NHIBERNATE_HQL.value == "C# NHibernate HQL"
    assert ORMType.SPRING_DATA_JPA.value == "Java Spring Data JPA"
    assert ORMType.SPRING_DATA_MONGODB.value == "Java Spring Data MongoDB"
    assert ORMType.SPRING_DATA_NEO4J.value == "Java Spring Data Neo4j"
    assert ORMType.UNKNOWN.value == "Unknown"


def test_orm_type_enum_identity() -> None:
    """ORMType is a str Enum and can be compared by identity."""
    assert isinstance(ORMType.EFCORE_LINQ, str)
    assert ORMType.EFCORE_LINQ == "C# EFCore LINQ"
    assert ORMType.UNKNOWN != ORMType.MS_SQL_NATIVE


def test_state_inherits_input_state_defaults() -> None:
    """State defaults come from InputState and can be overridden."""
    state = State()
    assert state.source_code == ""
    assert state.source_target == ORMType.UNKNOWN
    assert state.destination_target == ORMType.UNKNOWN
    assert state.schema_translated_code == ""
    assert state.query_translated_code == ""
    assert state.error_count == 0
