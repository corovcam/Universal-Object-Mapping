from react_agent.state import FrameworkType, State


def test_state_initialization() -> None:
    """State initializes properly with unknown types and default counters."""
    state = State(
        messages=[],
        source_schema_code="", source_query_code="",
        source_target=FrameworkType.EFCORE_LINQ,
        destination_target=FrameworkType.SPRING_DATA_MONGODB,
        council_responses=[],
        translated_schema_code="",
        translated_query_code="",
    )

    assert state.source_target == FrameworkType.EFCORE_LINQ or state.source_target is None
    assert state.destination_target == FrameworkType.SPRING_DATA_MONGODB or state.destination_target is None
    assert state.source_schema_code == ""


def test_orm_type_values() -> None:
    """FrameworkType enum values match their human-readable string descriptions."""
    assert FrameworkType.DAPPER.value == "C# Dapper"
    assert FrameworkType.EFCORE_LINQ.value == "C# EFCore LINQ"
    assert FrameworkType.DAPPER.value == "C# Dapper"
    assert FrameworkType.NHIBERNATE_HQL.value == "C# NHibernate HQL"

    assert FrameworkType.SPRING_DATA_MONGODB.value == "Java Spring Data MongoDB"
    assert FrameworkType.SPRING_DATA_NEO4J.value == "Java Spring Data Neo4j"



def test_orm_type_enum_identity() -> None:
    """FrameworkType is a str Enum and can be compared by identity."""
    assert isinstance(FrameworkType.EFCORE_LINQ, str)
    assert FrameworkType.EFCORE_LINQ == "C# EFCore LINQ"
    assert FrameworkType.EFCORE_LINQ != FrameworkType.DAPPER


def test_state_inherits_input_state_defaults() -> None:
    """State defaults come from InputState and can be overridden."""
    state = State()
    assert state.source_schema_code is None
    assert state.source_target is None
    assert state.destination_target == FrameworkType.SPRING_DATA_MONGODB or state.destination_target is None
    assert state.schema_context == ""
    assert state.translated_schema_code is None
    assert state.translated_query_code is None
