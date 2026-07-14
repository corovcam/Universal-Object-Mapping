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
from react_agent.translation_draft import (
    build_save_translation_tool,
    required_draft_fields,
)
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


# ---------------------------------------------------------------- fragment contract (per-query)

_CS_SCHEMA_FRAGMENT = """\
public class OrderLine { public int OrderLineID { get; set; } public int Quantity { get; set; } }
public class SandboxDbContext(DbContextOptions<SandboxDbContext> options) : DbContext(options)
{
    public DbSet<OrderLine> OrderLines => Set<OrderLine>();
}"""

_CS_QUERY_FRAGMENT = """\
public static class Query{qid}
{{
    public static object Harness(SandboxDbContext ctx)
    {{
        return HarnessSupport.RunQuery(() => ctx.OrderLines.Where(ol => ol.Quantity > {qid}), x => x.OrderLineID);
    }}
}}"""

_JAVA_SCHEMA_FRAGMENT = """\
@Document(collection = "orderLines")
class OrderLine { @Id String id; @Field("orderLineId") Integer orderLineId; Integer quantity; }"""

_JAVA_QUERY_FRAGMENT = """\
final class Query{qid} {{
    static Map<String, Object> harness(MongoTemplate template) {{
        return Map.of("count", 0L);
    }}
}}"""


@pytest.mark.asyncio
async def test_fragment_assembly_generates_entrypoint_and_orders_queries():
    fragments = {qid: _CS_QUERY_FRAGMENT.format(qid=qid) for qid in (3, 1, 7)}
    assembled, entry = await ha.assemble_query_harness(
        FrameworkEnum.DOTNET_EFCORE, _CS_SCHEMA_FRAGMENT, fragments
    )
    assert entry == "EFCoreQueryEntrypoint"
    # generated tail present exactly once, with all query ids wired in ascending order
    assert assembled.count("public static class HarnessSupport") == 1
    assert assembled.count(f"public static class {entry}") == 1
    pos = [assembled.find(f"({qid}, () => Query{qid}.Harness(context))") for qid in (1, 3, 7)]
    assert all(p > 0 for p in pos) and pos == sorted(pos)
    # results protocol is the generated one (per-query try/catch + JSON write)
    assert "EFCORE_RESULTS_PATH" in assembled and 'results[$"query{qid}"]' in assembled


@pytest.mark.asyncio
async def test_fragment_assembly_java_and_reserved_class_stripping():
    fragments = {
        1: _JAVA_QUERY_FRAGMENT.format(qid=1),
        # A misbehaving model redeclares the entrypoint — it must be dropped, not duplicated.
        2: _JAVA_QUERY_FRAGMENT.format(qid=2)
        + "\npublic class MongoQueryEntrypoint { public static void main(String[] a) {} }",
    }
    assembled, entry = await ha.assemble_query_harness(
        FrameworkEnum.JAVA_SPRING_DATA_MONGODB, _JAVA_SCHEMA_FRAGMENT, fragments
    )
    assert entry == "MongoQueryEntrypoint"
    assert assembled.count("class MongoQueryEntrypoint") == 1
    assert "new HarnessCase(1, () -> Query1.harness(template))" in assembled
    assert "new HarnessCase(2, () -> Query2.harness(template))" in assembled
    assert "MONGO_RESULTS_PATH" in assembled
    # Regression (2026-07-03 traces): `h.run()` is the record ACCESSOR (returns the Supplier);
    # the tail must EXECUTE it with .get(). Storing the accessor result serialized every query
    # as an empty object, so equivalence saw null counts/samples on the whole Java side.
    assert 'results.put("query" + h.id(), h.run().get());' in assembled
    assert 'results.put("query" + h.id(), h.run());' not in assembled


@pytest.mark.asyncio
async def test_fragment_assembly_neo4j_prelude_has_no_hardcoded_entity_set():
    """Regression (2026-07-03 traces): the invariant Neo4jTemplateFactory prelude hardcoded
    `setInitialEntitySet(Set.of(Order.class, Customer.class, …))` from the snippet's example
    schema, so any batch whose schema fragment didn't define those exact entities failed to
    compile ("cannot find symbol: Customer"). Entities must be registered lazily."""
    schema = '@Node("OrderLine")\nclass OrderLine { @Id Long orderLineId; Integer quantity; }'
    query = (
        "final class Query1 {\n"
        "    static Map<String, Object> harness(Neo4jTemplate template, Neo4jClient client) {\n"
        '        return Map.of("count", 0L);\n'
        "    }\n"
        "}"
    )
    assembled, entry = await ha.assemble_query_harness(
        FrameworkEnum.JAVA_SPRING_DATA_NEO4J, schema, {1: query}
    )
    assert entry == "Neo4jQueryEntrypoint"
    assert "setInitialEntitySet(" not in assembled
    assert "Customer.class" not in assembled


@pytest.mark.asyncio
async def test_fragment_assembly_java_supplier_entity_does_not_shadow_harness_case():
    """Regression (2026-07-02 traces): a model-authored `Supplier` entity in the same file shadowed
    `java.util.function.Supplier` in the generated HarnessCase record, failing every lambda with
    "type uom.services.Supplier does not take parameters". The tail must stay compilable by fully
    qualifying the functional interface."""
    schema = _JAVA_SCHEMA_FRAGMENT + (
        '\n@Document(collection = "suppliers")\nclass Supplier {\n'
        "    @Id String id;\n    @Field Integer supplierId;\n}\n"
    )
    assembled, _entry = await ha.assemble_query_harness(
        FrameworkEnum.JAVA_SPRING_DATA_MONGODB,
        schema,
        {1: _JAVA_QUERY_FRAGMENT.format(qid=1)},
    )
    assert "java.util.function.Supplier<Map<String, Object>>" in assembled
    # the record must never reference the bare (shadowable) name
    assert "record HarnessCase(int id, Supplier<" not in assembled


def test_expected_query_ids_from_source():
    from react_agent.translation_draft import expected_query_ids_from_source

    code = "IQueryable<X> Query1(...) ... Query12(...) ... Query3(...)"
    assert expected_query_ids_from_source(code) == (1, 3, 12)
    assert expected_query_ids_from_source(None) == (1,)
    assert expected_query_ids_from_source("no queries here") == (1,)


def test_merge_query_fragments_reducer():
    from react_agent.translation_draft import merge_query_fragments

    left = {"1": {"source": "a", "target": "b"}}
    right = {"1": {"target": "B2"}, "2": {"source": "c", "target": "d"}}
    merged = merge_query_fragments(left, right)
    assert merged["1"] == {"source": "a", "target": "B2"}
    assert merged["2"] == {"source": "c", "target": "d"}
    # left unchanged (no aliasing)
    assert left["1"]["target"] == "b"
