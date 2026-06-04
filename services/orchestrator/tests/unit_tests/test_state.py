from react_agent.state import State


def test_state_initialization() -> None:
    """State initializes properly with default values."""
    state = State(
        messages=[],
    )

    assert state.messages == []
    assert state.schema_context == ""
    assert state.translation_messages == []
    assert state.translation_loop_count == 0


def test_state_inherits_input_state_defaults() -> None:
    """State defaults come from InputState and can be overridden."""
    state = State()
    assert state.source_schema_code is None
    assert state.source_query_code is None
    assert state.source_target is None
    assert state.destination_target is None
    assert state.schema_context == ""
    assert state.translated_schema_code is None
    assert state.translated_query_code is None
