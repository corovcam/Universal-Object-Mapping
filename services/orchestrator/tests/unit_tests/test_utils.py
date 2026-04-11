import pytest

from react_agent.context import AvailableModel, Context
from react_agent.utils import load_chat_model


@pytest.mark.asyncio
async def test_load_chat_model(context: Context) -> None:
    model = await load_chat_model(
        AvailableModel.EINFRA_MINI,
        {
            "openai_api_url": context.openai_api_url,
            "openai_api_key": context.openai_api_key,
        },
    )
    assert model is not None
