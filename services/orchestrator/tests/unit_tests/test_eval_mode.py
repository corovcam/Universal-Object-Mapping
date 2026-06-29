"""Tests for the evaluation-only Context knobs + cache-bust header.

The load-bearing invariant: when eval mode is OFF (production), everything is a no-op — the cache-bust
header is empty and the override fields are None — so the production graph behaves byte-for-byte as
before. These changes exist purely to let the offline eval harness vary per-run behaviour.
"""
from __future__ import annotations

import os
from types import SimpleNamespace
from unittest import mock

import pytest

from react_agent.context import Context
from react_agent.prompts import eval_cache_bust_header


def _runtime(eval_mode: bool):
    """A duck-typed Runtime stand-in (eval_cache_bust_header only reads runtime.context.eval_mode)."""
    return SimpleNamespace(context=SimpleNamespace(eval_mode=eval_mode))


# --------------------------------------------------------------------------- cache-bust header
def test_header_is_empty_in_production():
    # No runtime, eval_mode off, and an explicit non-eval context all yield the empty no-op.
    assert eval_cache_bust_header(None, None) == ""
    assert eval_cache_bust_header(_runtime(False), {"run_id": "x"}) == ""


def test_header_is_nonempty_and_unique_in_eval_mode():
    rt = _runtime(True)
    h1 = eval_cache_bust_header(rt, {"run_id": "abc"})
    h2 = eval_cache_bust_header(rt, {"run_id": "abc"})
    assert h1.startswith("<!-- eval-run-nonce")
    assert "run_id=abc" in h1
    assert h1 != h2  # the uuid makes every header unique even for the same run_id + second


def test_header_reads_run_id_from_thread_id_fallback():
    h = eval_cache_bust_header(_runtime(True), {"configurable": {"thread_id": "t-123"}})
    assert "run_id=t-123" in h


# ------------------------------------------------------------------------------- Context knobs
def test_eval_knobs_default_off():
    with mock.patch.dict(os.environ, {}, clear=False):
        for var in ("EVAL_MODE", "TRANSLATION_MODEL_OVERRIDE", "TRANSLATION_REASONING_OVERRIDE"):
            os.environ.pop(var, None)
        ctx = Context()
    assert ctx.eval_mode is False
    assert ctx.translation_model_override is None
    assert ctx.translation_reasoning_override is None


@pytest.mark.parametrize("raw,expected", [("1", True), ("true", True), ("on", True),
                                          ("0", False), ("false", False), ("", False)])
def test_eval_mode_env_coercion(raw, expected):
    with mock.patch.dict(os.environ, {"EVAL_MODE": raw}, clear=False):
        assert Context().eval_mode is expected


@pytest.mark.parametrize("raw,expected", [("true", True), ("false", False), ("", None),
                                          ("garbage", None)])
def test_reasoning_override_env_coercion(raw, expected):
    with mock.patch.dict(os.environ, {"TRANSLATION_REASONING_OVERRIDE": raw}, clear=False):
        assert Context().translation_reasoning_override is expected


def test_nondefault_explicit_kwargs_win_over_env():
    # The runner always sets these to NON-default values per-invoke (eval_mode=True, a concrete model
    # override), which the __post_init__ reflection leaves untouched (env is only consulted when a
    # field still equals its class default). This is the path the eval harness actually uses.
    with mock.patch.dict(os.environ, {"EVAL_MODE": "0", "TRANSLATION_MODEL_OVERRIDE": "einfra/glm-5.2"}):
        ctx = Context(eval_mode=True, translation_model_override="einfra/kimi-k2.7")
    assert ctx.eval_mode is True
    assert ctx.translation_model_override == "einfra/kimi-k2.7"
