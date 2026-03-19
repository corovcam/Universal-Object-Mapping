import os

from react_agent.context import AvailableModel, Context


def test_context_init_with_passed_kwargs() -> None:
    context = Context(model=AvailableModel.EINFRA_MINI)
    assert context.model == AvailableModel.EINFRA_MINI


def test_context_init_with_env_vars() -> None:
    os.environ["MODEL"] = AvailableModel.EINFRA_MINI.value
    context = Context()
    assert context.model == AvailableModel.EINFRA_MINI.value


def test_context_init_with_env_vars_and_passed_values() -> None:
    os.environ["MODEL"] = AvailableModel.EINFRA_MINI.value
    context = Context(model=AvailableModel.EINFRA_AGENTIC)
    assert context.model == AvailableModel.EINFRA_AGENTIC
