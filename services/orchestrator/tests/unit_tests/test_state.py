from react_agent.state import State, FrameworkType


def test_state_initialization() -> None:
    """State initializes properly with unknown types and default counters."""
    state = State(
        messages=[],
        source_code="",
        source_target=FrameworkType.UNKNOWN,
        destination_target=FrameworkType.UNKNOWN,
        council_responses=[],
        schema_translated_code="",
        query_translated_code="",
    )

    assert state.source_target == FrameworkType.UNKNOWN
    assert state.destination_target == FrameworkType.UNKNOWN
    assert state.source_code == ""
    assert state.error_count == 0
    assert state.max_retries == 3


def test_orm_type_values() -> None:
    """FrameworkType enum values match their human-readable string descriptions."""
    assert FrameworkType.MS_SQL_NATIVE.value == "MS SQL Native"
    assert FrameworkType.EFCORE_LINQ.value == "C# EFCore LINQ"
    assert FrameworkType.DAPPER.value == "C# Dapper"
    assert FrameworkType.NHIBERNATE_HQL.value == "C# NHibernate HQL"
    assert FrameworkType.SPRING_DATA_JPA.value == "Java Spring Data JPA"
    assert FrameworkType.SPRING_DATA_MONGODB.value == "Java Spring Data MongoDB"
    assert FrameworkType.SPRING_DATA_NEO4J.value == "Java Spring Data Neo4j"
    assert FrameworkType.UNKNOWN.value == "Unknown"


def test_orm_type_enum_identity() -> None:
    """FrameworkType is a str Enum and can be compared by identity."""
    assert isinstance(FrameworkType.EFCORE_LINQ, str)
    assert FrameworkType.EFCORE_LINQ == "C# EFCore LINQ"
    assert FrameworkType.UNKNOWN != FrameworkType.MS_SQL_NATIVE


def test_state_inherits_input_state_defaults() -> None:
    """State defaults come from InputState and can be overridden."""
    state = State()
    assert state.source_code == ""
    assert state.source_target == FrameworkType.UNKNOWN
    assert state.destination_target == FrameworkType.UNKNOWN
    assert state.schema_translated_code == ""
    assert state.query_translated_code == ""
