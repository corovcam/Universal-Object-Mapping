import pytest
from langgraph_sdk.client import LangGraphClient

from react_agent.context import Context


@pytest.mark.asyncio
async def test_graph_events(client: LangGraphClient, context: Context, efcore_mongodb_unstructured_input: str):
    # Create assistant using langgraph-sdk
    assistant = await client.assistants.create(
        graph_id="universal-object-mapping-translator",
        context=context,
        if_exists="do_nothing",
        name="UOM Translator Test Assistant"
    )
    print(f"Assistant created: {assistant}")
    
    # Create thread using langgraph-sdk
    thread = await client.threads.create()
    print(f"Thread created: {thread}")
    
    # Act
    input = {"messages": [{"role": "human", "content": efcore_mongodb_unstructured_input}]}
    run_stream = client.runs.stream(thread_id=thread.get("thread_id"), assistant_id=assistant.get("assistant_id"), input=input, stream_mode=["debug"], multitask_strategy="reject", on_disconnect="cancel")
    
    # Stream
    async for event in run_stream:
        print(event)

    await client.aclose()
    