"""Unit tests for deterministic harness assembly and the single translation save tool.

The assembler's contract is that the *invariant* prelude (imports + byte-stable JSON serializer +
runtime support + DB template factory) is injected verbatim around the model-authored body. The
serializer in particular must be byte-identical to the snippet, because the DeepDiff equivalence
check depends on its exact number/date formatting. These tests assert that invariant by feeding each
snippet's own body back through the assembler and checking the prelude is reproduced exactly and
exactly once.
"""

import re

import pytest

from react_agent.constants import FrameworkEnum, TranslationType
from react_agent.translation_draft import build_save_translation_tool, required_draft_fields
from react_agent.utils import harness_assembler as ha
from react_agent.utils.utils import get_snippet_content

_ALL = list(FrameworkEnum)


@pytest.mark.asyncio
@pytest.mark.parametrize("framework", _ALL)
@pytest.mark.parametrize("is_schema", [False, True])
async def test_assembler_injects_invariant_prelude_byte_identically(framework, is_schema):
    snippet = await get_snippet_content(framework, is_schema=is_schema)
    content = snippet["content"]
    if not content:
        pytest.skip(f"no snippet for {framework.value} schema={is_schema}")

    # The "model body" is exactly the region below the schema seam in the canonical snippet.
    body = (
        content.split(ha.SCHEMA_MARKER, 1)[1]
        if ha.SCHEMA_MARKER in content
        else content
    )
    assembled, entry = await ha.assemble_validation_code(framework, body, is_schema=is_schema)

    # 1. The exact serializer block is present exactly once (byte-identity of the DeepDiff-critical
    #    region).
    serializer = ha._extract_named_block(content, "CustomJsonSerializer")
    assert serializer, "snippet must contain CustomJsonSerializer"
    assert assembled.count(serializer) == 1

    # 2. Every invariant utility class is declared exactly once (no duplicate-type compile error).
    for cls in ha._INVARIANT_CLASSES.get(framework, ()):
        assert len(re.findall(rf"\bclass\s+{cls}\b", assembled)) == 1, cls

    # 3. The deterministic entrypoint type name is present in the assembled code.
    assert entry and entry in assembled

    # 4. No import/package directive sits below the first class declaration (would be a hard error).
    first_class = re.search(r"^[^\n]*\bclass\s+\w", assembled, re.MULTILINE)
    assert first_class
    below = assembled[first_class.start():]
    assert not [ln for ln in below.splitlines() if ha._IMPORT_LINE_RE.match(ln)]


@pytest.mark.asyncio
async def test_assembler_strips_model_emitted_imports_and_redeclarations():
    framework = FrameworkEnum.JAVA_SPRING_DATA_MONGODB
    snippet = await get_snippet_content(framework, is_schema=False)
    serializer = ha._extract_named_block(snippet["content"], "CustomJsonSerializer")

    # A noncompliant model body: it re-emits a package line, an import, and redeclares the serializer.
    bad_body = (
        "package uom.services;\n"
        "import java.util.*;\n"
        f"{serializer}\n"
        "class Order {\n    private Integer orderId;\n}\n"
        "public class MongoQueryEntrypoint {\n    public static void main(String[] a) {}\n}\n"
    )
    assembled, _ = await ha.assemble_validation_code(framework, bad_body, is_schema=False)

    # The serializer is not duplicated, and package appears once (in the injected prelude).
    assert assembled.count(serializer) == 1
    assert len(re.findall(r"^\s*package\s+uom\.services;", assembled, re.MULTILINE)) == 1
    assert "class Order" in assembled  # the genuinely dataset-specific code survives


def test_save_tool_gating_matches_translation_type():
    # The generation step now always authors exactly the two validation harness bodies, regardless
    # of translation type. The clean translated_*_code answer is derived later by
    # finalize_translation_node from the validated harness, so it is no longer a save-tool field.
    expected = ("source_validation_body", "target_validation_body")
    for tt in (TranslationType.SCHEMA, TranslationType.QUERY, TranslationType.BOTH):
        assert required_draft_fields(tt) == expected

    full = build_save_translation_tool(TranslationType.BOTH, "SrcEntry", "TgtEntry")
    assert full.name == "save_translation"
    # tool_call_id is injected, not surfaced to the model.
    assert "tool_call_id" not in full.args
    assert set(full.args) == set(expected)
    # The clean production-code fields must NOT be part of the save tool anymore.
    assert "translated_schema_code" not in full.args
    assert "translated_query_code" not in full.args
    # The deterministic entrypoint names are baked into the argument guidance.
    assert "SrcEntry" in full.args["source_validation_body"]["description"]
    assert "TgtEntry" in full.args["target_validation_body"]["description"]


@pytest.mark.asyncio
async def test_save_tool_writes_command_with_injected_call_id():
    tool = build_save_translation_tool(TranslationType.BOTH, "E1", "E2")
    result = await tool.ainvoke(
        {
            "name": "save_translation",
            "args": {
                "source_validation_body": "SB",
                "target_validation_body": "TB",
            },
            "id": "call_123",
            "type": "tool_call",
        }
    )
    assert result.update["source_validation_body"] == "SB"
    assert result.update["target_validation_body"] == "TB"
    msg = result.update["messages"][0]
    assert msg.tool_call_id == "call_123"
    assert msg.name == "save_translation"
