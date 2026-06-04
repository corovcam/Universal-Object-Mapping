import pytest

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
        AvailableModel.EINFRA_KIMI_K2_6.value,
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
        AvailableModel.EINFRA_QWEN3_CODER_NEXT.value,
        {
            "openai_api_url": context.openai_api_url,
            "openai_api_key": context.openai_api_key,
            "temperature": 0,
        },
    )
    assert model3 is not None


@pytest.mark.asyncio
async def test_load_chat_model_handles_missing_extra_body(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_kwargs: dict[str, object] = {}

    class DummyChatModel:
        def __init__(self, **kwargs):
            captured_kwargs.update(kwargs)
            self.profile = object()

    monkeypatch.setattr("react_agent.utils.utils.ChatOpenAI", DummyChatModel)

    model = await load_chat_model(
        AvailableModel.EINFRA_MINI.value,
        {
            "reasoning": True,
        },
    )

    assert model is not None
    assert captured_kwargs["extra_body"] == {"chat_template_kwargs": {"enable_thinking": True}}


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
