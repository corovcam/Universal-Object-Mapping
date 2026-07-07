"""Unit tests for the per-query draft contract: save tools, merge reducer, convergence guard.

Uses a scripted BaseChatModel whose turn script lives at module level — the agent factory
deep-copies the model when middleware declare a custom state_schema, so instance-held iterators
(e.g. GenericFakeChatModel) arrive exhausted and are unusable here.
"""

import pytest
from langchain.agents import create_agent
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from react_agent.translation_draft import (
    TranslationConvergenceMiddleware,
    TranslationDraftMiddleware,
    build_save_query_tool,
    build_save_schema_tool,
)


class ScriptedModel(BaseChatModel):
    """Replays a module-level script of AIMessages (deepcopy-safe)."""

    script_key: str

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        script = _SCRIPTS[self.script_key]
        idx = min(script["i"], len(script["turns"]) - 1)
        script["i"] += 1
        turn = script["turns"][idx]
        # Fresh copy per call: re-emitting the same instance would carry the id assigned by
        # add_messages on the first append and be treated as an in-place update, not a new turn.
        clone = turn.model_copy(update={"id": None})
        return ChatResult(generations=[ChatGeneration(message=clone)])


_SCRIPTS: dict[str, dict] = {}


def _agent(script_key: str, expected_ids=(1, 2)):
    return create_agent(
        ScriptedModel(script_key=script_key),
        tools=[
            build_save_schema_tool("src hint", "tgt hint"),
            build_save_query_tool(expected_ids, "src sig", "tgt sig"),
        ],
        middleware=[
            TranslationDraftMiddleware(),
            TranslationConvergenceMiddleware(expected_query_ids=expected_ids),
        ],
    )


@pytest.mark.asyncio
async def test_convergence_guard_nudges_then_stops():
    """A model that keeps answering in prose gets exactly max_nudges corrective messages."""
    _SCRIPTS["prose"] = {"i": 0, "turns": [AIMessage(content="thinking, not saving")]}
    agent = _agent("prose")
    res = await agent.ainvoke(
        {"messages": [HumanMessage(content="translate")]}, {"recursion_limit": 40}
    )
    nudges = [
        m for m in res["messages"] if "have not been saved yet" in str(getattr(m, "content", ""))
    ]
    assert len(nudges) == 3
    assert res.get("save_nudge_count") == 3
    # 1 initial + 3 nudged model turns
    assert _SCRIPTS["prose"]["i"] == 4


@pytest.mark.asyncio
async def test_save_tools_accumulate_fragments_in_state():
    """Schema + per-query saves land on the draft channels and merge across calls."""
    _SCRIPTS["saves"] = {
        "i": 0,
        "turns": [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "save_schema_translation",
                        "args": {"source_schema_body": "class A {}", "target_schema_body": "class B {}"},
                        "id": "c1",
                    },
                    {
                        "name": "save_query_translation",
                        "args": {"query_id": 1, "source_query_body": "Q1s", "target_query_body": "Q1t"},
                        "id": "c2",
                    },
                ],
            ),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "save_query_translation",
                        "args": {"query_id": 2, "source_query_body": "Q2s", "target_query_body": "Q2t"},
                        "id": "c3",
                    }
                ],
            ),
            AIMessage(content="All pieces saved. Done."),
        ],
    }
    agent = _agent("saves")
    res = await agent.ainvoke(
        {"messages": [HumanMessage(content="translate")]}, {"recursion_limit": 40}
    )
    assert res.get("draft_source_schema") == "class A {}"
    assert res.get("draft_target_schema") == "class B {}"
    assert res.get("draft_queries") == {
        "1": {"source": "Q1s", "target": "Q1t"},
        "2": {"source": "Q2s", "target": "Q2t"},
    }
    # draft complete -> no nudges
    assert not res.get("save_nudge_count")


class _StubRequest:
    """Duck-typed ModelRequest: awrap_model_call only touches messages/tools/override."""

    def __init__(self, messages, tools):
        self.messages = messages
        self.tools = tools

    def override(self, *, tools):
        return _StubRequest(self.messages, tools)


class _NamedTool:
    def __init__(self, name):
        self.name = name


@pytest.mark.asyncio
async def test_research_budget_ignores_save_and_validate_tool_messages():
    """Regression: 15+ per-query saves must NOT consume the research budget (they used to, which
    stripped validate_draft from the tool surface exactly when the model finished saving)."""
    from langchain_core.messages import ToolMessage

    mw = TranslationConvergenceMiddleware(expected_query_ids=(1, 2), research_budget=3)
    tools = [_NamedTool(n) for n in ("search", "save_query_translation", "validate_draft")]

    async def handler(request):
        return request  # echo back so the test can inspect the tool surface

    # 20 save/validate results + 3 research results -> budget (3) NOT exceeded, surface untouched.
    saves = [ToolMessage(content="ok", tool_call_id=f"s{i}", name="save_query_translation") for i in range(18)]
    saves += [ToolMessage(content="ok", tool_call_id=f"v{i}", name="validate_draft") for i in range(2)]
    research = [ToolMessage(content="r", tool_call_id=f"r{i}", name="search") for i in range(3)]
    out = await mw.awrap_model_call(_StubRequest(saves + research, tools), handler)  # type: ignore[arg-type]
    assert [t.name for t in out.tools] == ["search", "save_query_translation", "validate_draft"]  # type: ignore[attr-defined]

    # One more research result crosses the budget -> research tools stripped, validate_draft KEPT.
    research.append(ToolMessage(content="r", tool_call_id="r99", name="search"))
    out = await mw.awrap_model_call(_StubRequest(saves + research, tools), handler)  # type: ignore[arg-type]
    assert sorted(t.name for t in out.tools) == ["save_query_translation", "validate_draft"]  # type: ignore[attr-defined]


def test_build_sandbox_runtime_is_a_real_toolruntime():
    """Regression (2026-07-03 traces): the compile helpers hand this runtime to
    `execute_in_sandbox.ainvoke`, whose args_schema pydantic-validates `runtime` as a ToolRuntime
    dataclass instance. The previous duck-typed shim failed that validation and killed every
    validate_draft call. The exact contract: the built runtime must pass the tool's own schema."""
    from react_agent.constants import SandboxType, TranslationType
    from react_agent.context import Context
    from react_agent.custom_tools.draft_validator import build_sandbox_runtime
    from react_agent.custom_tools.sandbox_tools import execute_in_sandbox
    from react_agent.state import State

    rt = build_sandbox_runtime(
        State(translation_type=TranslationType.BOTH), Context(), {"configurable": {}}
    )
    validated = execute_in_sandbox.args_schema.model_validate(
        {
            "sandbox_type": SandboxType.JAVA_25_SANDBOX,
            "command": "echo hi",
            "timeout": 5,
            "env_vars": None,
            "runtime": rt,
        }
    )
    assert validated.runtime is not None
    # The helpers read these through the runtime — they must survive construction.
    assert rt.state.translation_type == TranslationType.BOTH
    assert rt.context is not None and rt.config == {"configurable": {}}


def test_build_validate_draft_tool_pair_gating_and_outer_runtime():
    from react_agent.constants import FrameworkEnum
    from react_agent.custom_tools.draft_validator import build_validate_draft_tool

    tool_ = build_validate_draft_tool(
        FrameworkEnum.DOTNET_EFCORE,
        FrameworkEnum.JAVA_SPRING_DATA_MONGODB,
        (1, 2),
        graph_state=object(),
        graph_context=object(),
        graph_config={},
    )
    assert tool_ is not None and tool_.name == "validate_draft"
    # non-.NET→Java pair -> no tool
    assert (
        build_validate_draft_tool(
            FrameworkEnum.JAVA_SPRING_DATA_MONGODB,
            FrameworkEnum.DOTNET_EFCORE,
            (1,),
            graph_state=object(),
            graph_context=object(),
            graph_config={},
        )
        is None
    )


@pytest.mark.asyncio
async def test_save_query_rejects_unknown_id():
    """Saving a query id outside the task is rejected with an instructive tool error."""
    _SCRIPTS["badid"] = {
        "i": 0,
        "turns": [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "save_query_translation",
                        "args": {"query_id": 99, "source_query_body": "x", "target_query_body": "y"},
                        "id": "c1",
                    }
                ],
            ),
            AIMessage(content="ok stopping"),
        ],
    }
    agent = _agent("badid")
    res = await agent.ainvoke(
        {"messages": [HumanMessage(content="translate")]}, {"recursion_limit": 40}
    )
    tool_msgs = [m for m in res["messages"] if getattr(m, "type", "") == "tool"]
    assert any("not part of this task" in str(m.content) for m in tool_msgs)
    assert not res.get("draft_queries")


@pytest.mark.asyncio
async def test_validate_draft_receives_injected_inner_runtime_through_tool_node():
    """Regression (2026-07-04 traces): the tool declared `runtime: ToolRuntime` on its coroutine
    but pinned an explicit args_schema WITHOUT a `runtime` field. The tool node injected the
    inner-agent runtime into the call args, pydantic validation silently dropped the unknown key,
    and the tool ran with runtime=None — so it answered "No schema fragment saved yet" no matter
    what was saved, doom-looping every generation run that touched it. The args schema is now
    inferred from the signature: the model sees only `query_ids`, and the injected runtime must
    reach the coroutine (proven here by the tool reading draft channels out of the INNER state)."""
    from langgraph.prebuilt.tool_node import ToolNode
    from langgraph.runtime import Runtime

    from react_agent.constants import FrameworkEnum, TranslationType
    from react_agent.context import Context
    from react_agent.custom_tools.draft_validator import build_validate_draft_tool
    from react_agent.state import State

    tool_ = build_validate_draft_tool(
        FrameworkEnum.DOTNET_EFCORE,
        FrameworkEnum.JAVA_SPRING_DATA_MONGODB,
        (1, 2),
        graph_state=State(translation_type=TranslationType.BOTH),
        graph_context=Context(),
        graph_config={"configurable": {}},
    )
    assert tool_ is not None
    # The model-visible schema must not leak the injected parameter.
    assert set(tool_.args) == {"query_ids"}

    node = ToolNode([tool_])
    call = {"name": "validate_draft", "args": {}, "id": "c1", "type": "tool_call"}
    inner_state = {
        "messages": [AIMessage(content="", tool_calls=[call])],
        # Schema saved, queries not: the tool must get PAST the schema check (it can only do
        # that by reading the injected inner-agent state) and stop at the query check — which
        # keeps the test off the network/sandboxes.
        "draft_source_schema": "public class X {}",
        "draft_target_schema": "@Document class X {}",
        "draft_queries": {},
    }
    config = {
        "configurable": {
            "__pregel_runtime": Runtime(
                context=None,
                store=None,
                stream_writer=lambda *_a, **_k: None,
                previous=None,
            )
        }
    }
    res = await node.ainvoke(inner_state, config)
    content = str(res["messages"][-1].content)
    assert "No query fragments saved yet" in content
    assert "No schema fragment saved yet" not in content
