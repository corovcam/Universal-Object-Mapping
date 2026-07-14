import pytest
from langchain.messages import AIMessage, AIMessageChunk, HumanMessage
from langgraph.graph.state import CompiledStateGraph

from react_agent.constants import AvailableModel
from react_agent.context import Context
from react_agent.utils import (
    get_mongodb_standalone_mapping,
    get_neo4j_standalone_mapping,
    load_chat_model,
)


@pytest.mark.asyncio
async def test_load_chat_model(context: Context) -> None:
    model1 = await load_chat_model(
        AvailableModel.EINFRA_KIMI_K2_7.value,
        {
            "openai_api_url": context.openai_api_url,
            "openai_api_key": context.openai_api_key,
            "reasoning": True,
            "temperature": 0.5,
            "extra_body": {
                "enable_thinking": True,
            },
        },
    )
    assert model1 is not None
    model2 = await load_chat_model(
        AvailableModel.OLLAMA_QWEN3_6_27B.value,
        {
            "temperature": 0.7,
            "reasoning": True,
        },
    )
    assert model2 is not None
    model3 = await load_chat_model(
        AvailableModel.EINFRA_QWEN3_5_122B.value,
        {
            "openai_api_url": context.openai_api_url,
            "openai_api_key": context.openai_api_key,
            "temperature": 0,
        },
    )
    assert model3 is not None


@pytest.mark.asyncio
async def test_load_chat_model_and_execute(context: Context) -> None:
    model1 = await load_chat_model(
        AvailableModel.EINFRA_GPT_OSS_120B.value,
        {
            "openai_api_url": context.openai_api_url,
            "openai_api_key": context.openai_api_key,
            "reasoning": True,
            "temperature": 0.5,
            "extra_body": {
                "enable_thinking": True,
            },
        },
    )
    assert model1 is not None
    res = await model1.ainvoke(
        "Tell me a three sentence bedtime story about a unicorn."
    )
    print(res)
    for chunk in res.content_blocks:
        print(chunk)


@pytest.mark.asyncio
async def test_invoke_agent(sample_agent: CompiledStateGraph) -> None:
    response = await sample_agent.ainvoke(
        {
            "messages": [
                HumanMessage(
                    content="Tell me a three sentence bedtime story about a unicorn."
                )
            ]
        },
        stream_mode="messages",
    )
    print(response)
    assert response is not None
    assert AIMessage in [type(msg) for msg in response.get("messages", [])]
    # assert any(
    #     "reasoning" in block.get("type", "")
    #     for msg in response.get("messages", [])
    #     for block in getattr(msg, "content_blocks", [])
    # )
    for msg in response.get("messages", [{}]):
        print(msg)
        if isinstance(msg, AIMessage):
            for block in msg.content_blocks:
                print("Block: ", block)
                if block.get("type") == "reasoning":
                    print("Reasoning block:", block.get("reasoning"))
                if block.get("type") == "text":
                    print("Text block:", block.get("text"))


@pytest.mark.asyncio
async def test_stream_agent(sample_agent: CompiledStateGraph) -> None:
    async for chunk in sample_agent.astream(
        {
            "messages": [
                HumanMessage(
                    content="Tell me a three sentence bedtime story about a unicorn."
                )
            ]
        },
        stream_mode=["messages", "values"],
    ):
        print(chunk)
        if isinstance(chunk, tuple) and chunk[0] == "messages":
            msg = chunk[1][0]
            if isinstance(msg, AIMessageChunk):
                for block in msg.content_blocks:
                    print("Block: ", block)
                    if block.get("type") == "reasoning":
                        print("Reasoning block:", block.get("reasoning"))
                    if block.get("type") == "text":
                        print("Text block:", block.get("text"))
        


@pytest.mark.asyncio
async def test_load_chat_model_handles_missing_extra_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_kwargs: dict[str, object] = {}

    class DummyChatModel:
        def __init__(self, **kwargs):
            captured_kwargs.update(kwargs)
            self.profile = object()

    monkeypatch.setattr("react_agent.utils.utils.ChatOpenAI", DummyChatModel)

    model = await load_chat_model(
        AvailableModel.EINFRA_GPT_OSS_120B.value,
        {
            "reasoning": True,
        },
    )

    assert model is not None
    assert captured_kwargs["extra_body"] == {
        "chat_template_kwargs": {"enable_thinking": True}
    }


@pytest.mark.asyncio
async def test_get_mongodb_standalone_mapping() -> None:
    mapping = await get_mongodb_standalone_mapping()

    assert mapping is not None
    assert "collections" in mapping

    orders_collection = mapping["collections"].get("orders")
    assert isinstance(orders_collection, dict)

    orders_mappings = orders_collection.get("mappings")
    assert isinstance(orders_mappings, list)

    assert any(
        item.get("mappingType") == "NEW_DOCUMENT"
        and item.get("sourceSchema") == "WideWorldImporters.Sales"
        and item.get("sourceTable") == "Orders"
        and any(
            property_mapping.get("sourceColumn") == "OrderID"
            and property_mapping.get("targetProperty") == "orderId"
            and property_mapping.get("isPrimaryKey") is True
            for property_mapping in item.get("propertyMappings", [])
        )
        for item in orders_mappings
    )

    assert any(
        item.get("mappingType") == "EMBEDDED_DOCUMENT"
        and item.get("embeddedPath") == "customer"
        and item.get("sourceTable") == "Customers"
        for item in orders_mappings
    )


@pytest.mark.asyncio
async def test_get_neo4j_standalone_mapping() -> None:
    mapping = await get_neo4j_standalone_mapping()

    assert mapping is not None
    assert "nodes" in mapping
    assert "relationships" in mapping

    stock_item_node = mapping["nodes"].get("StockItem")
    assert isinstance(stock_item_node, dict)

    stock_item_mappings = stock_item_node.get("propertyMappings")
    assert isinstance(stock_item_mappings, list)
    assert any(
        item.get("sourceColumn") == "StockItemID"
        and item.get("targetProperty") == "stockItemId"
        and item.get("isPrimaryKey") is True
        for item in stock_item_mappings
    )

    people_relationships = mapping["relationships"].get("PEOPLE")
    assert isinstance(people_relationships, list)
    assert any(item.get("sourceTable") == "Orders" for item in people_relationships)


def test_bind_tools_with_empty_list_omits_tools_field():
    """Regression (2026-07-04 traces): `create_agent` with a ProviderStrategy response format
    calls `model.bind_tools(final_tools, strict=True, **kwargs)` even when the agent has no tools
    (the LLM-judge evaluate node). The stock classes then put a literal `tools: []` in the
    payload, which vLLM/e-INFRA rejects with 400 "`tools` must not be an empty array" — every
    deepseek-v4 judge call failed onto weaker fallbacks. The Safe* subclasses must bind the
    remaining kwargs and omit `tools` (plus the tools-only kwargs) entirely; non-empty tool
    lists must bind exactly as before."""
    from react_agent.utils.utils import SafeChatLiteLLM, SafeChatOpenAI

    def dummy_tool(x: int) -> str:
        """Do nothing."""
        return str(x)

    response_format = {
        "type": "json_schema",
        "json_schema": {
            "name": "Out",
            "schema": {
                "type": "object",
                "properties": {"decision": {"type": "string"}},
                "required": ["decision"],
                "title": "Out",
            },
        },
    }

    openai_model = SafeChatOpenAI(model="m", api_key="x", base_url="http://localhost:1")
    litellm_model = SafeChatLiteLLM(
        model="openai/m", api_key="x", openai_api_key="x", api_base="http://localhost:1"
    )
    for model in (openai_model, litellm_model):
        empty = model.bind_tools([], strict=True, response_format=response_format)
        assert "tools" not in empty.kwargs
        assert "strict" not in empty.kwargs
        assert "tool_choice" not in empty.kwargs
        assert empty.kwargs.get("response_format") is not None

        full = model.bind_tools([dummy_tool], response_format=response_format)
        assert full.kwargs.get("tools"), "non-empty tools must still be bound"


def test_compact_build_log_strips_noise_and_caps():
    """Restore/download progress noise is dropped and oversized logs are head+tail capped —
    a raw validation log once inflated a single evaluation prompt to 1.5 MB (nhib-neo4j,
    run 20260708-234928)."""
    from react_agent.utils import compact_build_log

    noise = "\n".join(f"  Restored /sandbox/x/sandbox.csproj (in {i} ms)." for i in range(2000))
    log = (
        "Determining projects to restore...\n" + noise +
        "\nerror CS1002: ; expected\nwarning CS0168: unused\nBuild FAILED.\n"
    )
    out = compact_build_log(log)
    assert "Restored /sandbox" not in out
    assert "build/restore progress lines omitted" in out
    assert "error CS1002" in out and "warning CS0168" in out and "Build FAILED." in out

    # Cap: huge non-noise content keeps head and tail with an omission marker.
    big = "HEAD-MARKER\n" + ("x" * 100_000) + "\nTAIL-MARKER"
    capped = compact_build_log(big, cap=10_000)
    assert len(capped) < 12_000
    assert capped.startswith("HEAD-MARKER") and capped.rstrip().endswith("TAIL-MARKER")
    assert "chars omitted" in capped

    # Small clean logs pass through untouched.
    assert compact_build_log("BUILD SUCCESS") == "BUILD SUCCESS"
