import os

from react_agent.constants import AvailableModel
from react_agent.context import Context


def test_context_init_with_passed_kwargs() -> None:
    context = Context(model=AvailableModel.EINFRA_GPT_OSS_120B)
    assert context.model == AvailableModel.EINFRA_GPT_OSS_120B


def test_context_init_with_env_vars() -> None:
    os.environ["MODEL"] = AvailableModel.EINFRA_GPT_OSS_120B.value
    context = Context()
    assert context.model == AvailableModel.EINFRA_GPT_OSS_120B.value


def test_context_init_with_env_vars_and_passed_values() -> None:
    os.environ["MODEL"] = AvailableModel.EINFRA_GPT_OSS_120B.value
    context = Context(model=AvailableModel.EINFRA_QWEN3_5_122B)
    assert context.model == AvailableModel.EINFRA_QWEN3_5_122B
