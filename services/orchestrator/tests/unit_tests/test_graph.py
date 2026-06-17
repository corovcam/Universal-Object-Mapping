"""Unit tests for the dynamic translation-output model factory in graph.py.

These cover `_create_translation_output_model`, which strips irrelevant fields from
`BaseTranslationOutput` depending on the `translation_type`. Stripped fields default to the
pydantic MISSING sentinel, which previously made the `check_entrypoint_names` after-validator
crash with ``TypeError: argument of type 'Sentinel' is not a container or iterable``.
"""

import pytest
from langchain_core.messages import HumanMessage
from pydantic.experimental.missing_sentinel import MISSING

from react_agent.constants import FrameworkEnum, TranslationType
from react_agent.graph import _create_translation_output_model
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
    `check_entrypoint_names` collects a ValueError and raises it as an ExceptionGroup.
    """
    model = await _create_translation_output_model(_make_state(TranslationType.SCHEMA))

    with pytest.raises(ExceptionGroup) as exc_info:
        model(
            translated_schema_code="public class Order {}",
            source_validation_schema_code="public class Unrelated { }",
            source_validation_entry_type_name="EFCoreEntrypoint",  # not in the code above
            target_validation_schema_code="public class MongoEntrypoint { }",
            target_validation_entry_type_name="MongoEntrypoint",
        )

    messages = [str(e) for e in exc_info.value.exceptions]
    assert any(
        "source_validation_entry_type_name must be declared in source_validation_schema_code"
        in m
        for m in messages
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
