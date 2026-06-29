"""Unit tests for the dynamic translation-output model factory in graph.py.

These cover `_create_translation_output_model`, which strips irrelevant fields from
`BaseTranslationOutput` depending on the `translation_type`. Stripped fields default to the
pydantic MISSING sentinel, which previously made the `check_entrypoint_names` after-validator
crash with ``TypeError: argument of type 'Sentinel' is not a container or iterable``.
"""

import json

import pytest
from langchain.agents import create_agent
from langchain.agents.middleware import ModelFallbackMiddleware
from langchain.agents.structured_output import (
    ProviderStrategy,
    StructuredOutputValidationError,
)
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import ValidationError
from pydantic.experimental.missing_sentinel import MISSING

from react_agent.constants import FrameworkEnum, TranslationType
from react_agent.graph import (
    StructuredOutputRetryMiddleware,
    _create_translation_output_model,
    _flatten_message_content,
    _format_structured_output_error,
    _sanitize_request_messages,
)
from react_agent.state import State


def _make_state(translation_type: TranslationType) -> State:
    """Build a minimal State with the frameworks the factory asserts on."""
    return State(
        messages=[HumanMessage(content="translate this")],
        translation_type=translation_type,
        source_target=FrameworkEnum.DOTNET_EFCORE,
        destination_target=FrameworkEnum.JAVA_SPRING_DATA_MONGODB,
    )


# Fields that should be excluded from the generated model per translation_type.
SCHEMA_EXCLUDED = (
    "translated_query_code",
    "source_validation_harness_code",
    "target_validation_harness_code",
)
QUERY_EXCLUDED = (
    "source_validation_schema_code",
    "target_validation_schema_code",
)


@pytest.mark.asyncio
async def test_schema_mode_strips_query_and_harness_fields() -> None:
    model = await _create_translation_output_model(_make_state(TranslationType.SCHEMA))

    for name in SCHEMA_EXCLUDED:
        field = model.model_fields[name]
        assert field.default is MISSING
        assert field.exclude is True

    # Schema validation fields stay required (not excluded).
    for name in ("source_validation_schema_code", "target_validation_schema_code"):
        assert model.model_fields[name].exclude in (None, False)


@pytest.mark.asyncio
async def test_schema_mode_validates_without_sentinel_error() -> None:
    """Regression test for the MISSING-sentinel membership crash.

    A SCHEMA translation leaves the harness/query fields as the MISSING sentinel. The
    after-validator must skip them instead of running ``entry_name not in <MISSING>``.
    """
    model = await _create_translation_output_model(_make_state(TranslationType.SCHEMA))

    instance = model(
        translated_schema_code="public class Order {}",
        source_validation_schema_code="public class EFCoreEntrypoint { }",
        source_validation_entry_type_name="EFCoreEntrypoint",
        target_validation_schema_code="public class MongoEntrypoint { }",
        target_validation_entry_type_name="MongoEntrypoint",
    )

    assert instance.source_validation_entry_type_name == "EFCoreEntrypoint"
    # Excluded fields are not serialized back out.
    dumped = instance.model_dump(exclude_unset=True)
    for name in SCHEMA_EXCLUDED:
        assert name not in dumped


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "translation_type", [TranslationType.QUERY, TranslationType.BOTH]
)
async def test_query_mode_strips_schema_validation_fields(
    translation_type: TranslationType,
) -> None:
    model = await _create_translation_output_model(_make_state(translation_type))

    for name in QUERY_EXCLUDED:
        field = model.model_fields[name]
        assert field.default is MISSING
        assert field.exclude is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "translation_type", [TranslationType.QUERY, TranslationType.BOTH]
)
async def test_query_mode_validates_without_sentinel_error(
    translation_type: TranslationType,
) -> None:
    """The mirror case: schema-validation fields are MISSING and must be skipped."""
    model = await _create_translation_output_model(_make_state(translation_type))

    instance = model(
        translated_schema_code="public class Order {}",
        translated_query_code="orders.find()",
        source_validation_harness_code="public class EFCoreEntrypoint { }",
        source_validation_entry_type_name="EFCoreEntrypoint",
        target_validation_harness_code="public class MongoEntrypoint { }",
        target_validation_entry_type_name="MongoEntrypoint",
    )

    dumped = instance.model_dump(exclude_unset=True)
    for name in QUERY_EXCLUDED:
        assert name not in dumped


@pytest.mark.asyncio
async def test_entrypoint_missing_from_included_code_still_raises() -> None:
    """The entrypoint check must still fire for the fields that ARE present.

    Here the source entrypoint name is absent from its (non-excluded) schema code, so
    `check_entrypoint_names` raises a ValueError, which pydantic surfaces as a ValidationError
    whose message retains the full actionable detail (so it can be fed back to the model).
    """
    model = await _create_translation_output_model(_make_state(TranslationType.SCHEMA))

    with pytest.raises(ValidationError) as exc_info:
        model(
            translated_schema_code="public class Order {}",
            source_validation_schema_code="public class Unrelated { }",
            source_validation_entry_type_name="EFCoreEntrypoint",  # not in the code above
            target_validation_schema_code="public class MongoEntrypoint { }",
            target_validation_entry_type_name="MongoEntrypoint",
        )

    assert (
        "source_validation_entry_type_name must be declared in source_validation_schema_code"
        in str(exc_info.value)
    )


@pytest.mark.asyncio
async def test_list_code_fields_are_joined() -> None:
    """List inputs (one string per line) are joined into a single string on validation."""
    model = await _create_translation_output_model(_make_state(TranslationType.SCHEMA))

    instance = model(
        translated_schema_code=["public class Order {", "}"],
        source_validation_schema_code=["public class EFCoreEntrypoint {", "}"],
        source_validation_entry_type_name="EFCoreEntrypoint",
        target_validation_schema_code=["public class MongoEntrypoint {", "}"],
        target_validation_entry_type_name="MongoEntrypoint",
    )

    assert instance.translated_schema_code == "public class Order {\n}"
    assert instance.source_validation_schema_code == "public class EFCoreEntrypoint {\n}"


# ---------------------------------------------------------------------------
# StructuredOutputRetryMiddleware
# ---------------------------------------------------------------------------


class BindableFakeChatModel(FakeMessagesListChatModel):
    """Fake chat model that supports `bind_tools` (required by the agent's ProviderStrategy path).

    Records the messages passed on every model call in `seen_messages` so tests can assert that
    validation feedback is actually injected into the prompt on retry.
    """

    seen_messages: list = []

    def bind_tools(self, tools, **kwargs):  # noqa: ANN001, ANN002, ANN003
        # The agent calls bind_tools(..., strict=True, response_format=...) for ProviderStrategy;
        # the fake model ignores tools but must accept (and drop) the strict kwarg.
        return self.bind(**{k: v for k, v in kwargs.items() if k != "strict"})

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):  # noqa: ANN001, ANN002, ANN003
        type(self).seen_messages.append(list(messages))
        return super()._generate(messages, stop=stop, run_manager=run_manager, **kwargs)


def _valid_schema_payload() -> str:
    return json.dumps(
        {
            "translated_schema_code": "public class Order {}",
            "source_validation_schema_code": "public class EFCoreEntrypoint {}",
            "source_validation_entry_type_name": "EFCoreEntrypoint",
            "target_validation_schema_code": "public class MongoEntrypoint {}",
            "target_validation_entry_type_name": "MongoEntrypoint",
        }
    )


def _invalid_schema_payload() -> str:
    # Entry type name absent from the schema code -> @model_validator fails.
    return json.dumps(
        {
            "translated_schema_code": "public class Order {}",
            "source_validation_schema_code": "public class Unrelated {}",
            "source_validation_entry_type_name": "EFCoreEntrypoint",
            "target_validation_schema_code": "public class MongoEntrypoint {}",
            "target_validation_entry_type_name": "MongoEntrypoint",
        }
    )


async def _make_agent(responses, *, max_retries, fallback_responses=None):
    """Build an agent over a fake model using the production middleware ordering."""
    model = await _create_translation_output_model(_make_state(TranslationType.SCHEMA))
    BindableFakeChatModel.seen_messages = []
    primary = BindableFakeChatModel(responses=list(responses))
    middleware = []
    if fallback_responses is not None:
        middleware.append(
            ModelFallbackMiddleware(
                BindableFakeChatModel(responses=list(fallback_responses))
            )
        )
    middleware.append(StructuredOutputRetryMiddleware(max_retries=max_retries))
    return create_agent(
        primary,
        response_format=ProviderStrategy(model, strict=True),
        middleware=middleware,
    )


@pytest.mark.asyncio
async def test_retry_middleware_self_corrects_and_feeds_back_error() -> None:
    """An invalid first response is retried, with the validation error injected as feedback."""
    agent = await _make_agent(
        [AIMessage(content=_invalid_schema_payload()), AIMessage(content=_valid_schema_payload())],
        max_retries=3,
    )

    result = await agent.ainvoke({"messages": [HumanMessage(content="translate")]})

    assert result.get("structured_response") is not None

    # The model was called twice; the second call received an extra feedback HumanMessage
    # containing the actionable validator error.
    calls = BindableFakeChatModel.seen_messages
    assert len(calls) == 2
    assert len(calls[1]) == len(calls[0]) + 1
    feedback = str(calls[1][-1].content)
    assert "failed structured output validation" in feedback
    assert (
        "source_validation_entry_type_name must be declared in source_validation_schema_code"
        in feedback
    )


@pytest.mark.asyncio
async def test_retry_middleware_succeeds_first_try_without_feedback() -> None:
    """A valid first response is returned immediately with no extra model calls."""
    agent = await _make_agent([AIMessage(content=_valid_schema_payload())], max_retries=3)

    result = await agent.ainvoke({"messages": [HumanMessage(content="translate")]})

    assert result.get("structured_response") is not None
    assert len(BindableFakeChatModel.seen_messages) == 1


@pytest.mark.asyncio
async def test_retry_middleware_caps_attempts_then_raises() -> None:
    """After max_retries + 1 failed attempts the error propagates (escalates past the loop)."""
    agent = await _make_agent([AIMessage(content=_invalid_schema_payload())] * 6, max_retries=2)

    with pytest.raises(StructuredOutputValidationError):
        await agent.ainvoke({"messages": [HumanMessage(content="translate")]})

    # Initial attempt + 2 retries = 3 model calls (no fallback configured).
    assert len(BindableFakeChatModel.seen_messages) == 3


@pytest.mark.asyncio
async def test_retry_middleware_escalates_to_fallback_after_exhaustion() -> None:
    """When the primary exhausts its feedback retries, the fallback model is tried."""
    agent = await _make_agent(
        [AIMessage(content=_invalid_schema_payload())] * 4,
        max_retries=1,
        fallback_responses=[AIMessage(content=_valid_schema_payload())],
    )

    result = await agent.ainvoke({"messages": [HumanMessage(content="translate")]})

    assert result.get("structured_response") is not None
    # 2 primary attempts (initial + 1 retry) before the fallback resolved it.
    assert len(BindableFakeChatModel.seen_messages) >= 3


def test_format_structured_output_error_extracts_validation_detail() -> None:
    """The formatter surfaces the pydantic validator message and omits the bulky input echo."""
    from pydantic import BaseModel, model_validator

    class _Model(BaseModel):
        x: int

        @model_validator(mode="after")
        def _check(self):
            raise ValueError("entry name must be declared in schema code")

    try:
        _Model(x=1)
    except ValidationError as validation_error:
        # Mimic the wrapping done by ProviderStrategyBinding.parse -> _parse_with_schema.
        source = ValueError(f"Failed to parse data to _Model: {validation_error}")
        source.__cause__ = validation_error
        exc = StructuredOutputValidationError("_Model", source, AIMessage(content="{}"))

    formatted = _format_structured_output_error(exc)
    assert "entry name must be declared in schema code" in formatted
    # The model's (potentially huge / truncated) input must NOT be echoed back.
    assert "input_value" not in formatted


# ---------------------------------------------------------------------------
# ReasoningContentSanitizerMiddleware / _flatten_message_content
#
# Reasoning models (qwen3.5 / the EINFRA thinker) stream an AIMessage whose content is a list of
# bare text deltas + {"type": "thinking"} blocks. Re-sent verbatim, litellm strips the thinking
# blocks and leaves content as a list of bare strings, which sglang/vLLM reject with a 400. The
# helper must flatten such AIMessages to a single string while leaving everything else untouched.
# ---------------------------------------------------------------------------


def test_flatten_reasoning_aimessage_to_plain_string() -> None:
    """A reasoning turn (bare strings + thinking blocks) flattens to a single string."""
    msg = AIMessage(
        content=[
            "",
            {"type": "thinking", "thinking": "Let me analyze"},
            {"type": "thinking", "thinking": " the schema."},
            "I'll inspect the schemas.",
            "\n\n",
        ]
    )
    out = _flatten_message_content(msg)
    assert isinstance(out.content, str)
    assert out.content == "I'll inspect the schemas.\n\n"
    # No thinking text leaks back to the provider.
    assert "analyze" not in out.content


def test_flatten_preserves_tool_calls_when_content_empties() -> None:
    """An AIMessage that is only reasoning + tool calls keeps its tool_calls after flattening."""
    msg = AIMessage(
        content=["", {"type": "thinking", "thinking": "deciding"}, "\n\n\n\n"],
        tool_calls=[{"name": "search", "args": {"q": "x"}, "id": "call_1"}],
    )
    out = _flatten_message_content(msg)
    assert isinstance(out.content, str)
    assert out.content == "\n\n\n\n"
    assert out.tool_calls == msg.tool_calls


def test_flatten_leaves_plain_and_non_ai_messages_untouched() -> None:
    """String-content AIMessages, HumanMessages, and tool-style list content are not rewritten."""
    plain_ai = AIMessage(content="already a string")
    human = HumanMessage(content="hello")
    # A valid OpenAI content-part list (all dicts, no bare strings) must be preserved as-is.
    tool_like = AIMessage(content=[{"type": "text", "text": "part"}])
    assert _flatten_message_content(plain_ai) is plain_ai
    assert _flatten_message_content(human) is human
    flattened_tool_like = _flatten_message_content(tool_like)
    # All-dict text parts still flatten (harmless), and crucially produce a valid string.
    assert flattened_tool_like.content == "part"


def test_sanitize_request_messages_removes_all_bare_string_lists() -> None:
    """After sanitizing, no message content is a list containing a bare string (the 400 trigger)."""
    messages = [
        HumanMessage(content="translate this"),
        AIMessage(
            content=["", {"type": "thinking", "thinking": "t"}, "answer"],
            tool_calls=[{"name": "save", "args": {}, "id": "c1"}],
        ),
    ]
    out = _sanitize_request_messages(messages)
    for m in out:
        if isinstance(m.content, list):
            assert not any(isinstance(b, str) for b in m.content)
    assert isinstance(out[1].content, str) and out[1].content == "answer"
    assert out[1].tool_calls == messages[1].tool_calls
