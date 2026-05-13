"""Shared pytest fixtures for orchestrator tests.

Provides reusable fixtures for Context, Runtime, State, graph compilation,
and live service connections (MongoDB, DB Toolbox, Ollama).
"""
import os
from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

import orjson
import pytest
from langchain.tools import ToolRuntime
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.runtime import Runtime

from react_agent.constants import AvailableModel, FrameworkEnum, TranslationType
from react_agent.context import Context
from react_agent.graph import graph
from react_agent.state import State

FIXTURES_DIR = Path(__file__).parent / "fixtures"

#  ---------------------------------------------------------------------------
#  Pytest Fixtures
#  ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session")
def vcr_config():
    return {
        "filter_headers": ["authorization"],
        "ignore_localhost": True,
        "record_mode": "once",
    }


@pytest.fixture(scope="module")
def check_api_keys():
    if not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")

# ---------------------------------------------------------------------------
# Context & Runtime
# ---------------------------------------------------------------------------


@pytest.fixture()
def context() -> Context:
    """Create a Context wired to real endpoints (reads from env / defaults)."""
    return Context(model=AvailableModel.EINFRA_MINI)


@pytest.fixture()
def runtime(context: Context) -> MagicMock:
    """A mock Runtime whose `.context` points to the real Context."""
    rt = MagicMock(spec=Runtime)
    rt.context = context
    return rt


@pytest.fixture()
def runnable_config() -> RunnableConfig:
    """A minimal RunnableConfig for node invocations."""
    return RunnableConfig()


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------


@pytest.fixture()
def compiled_graph():
    """Return the default compiled graph (no checkpointer)."""
    try:
        return graph
    except Exception as exc:
        pytest.skip(f"Graph build unavailable for integration tests: {exc}")


@pytest.fixture()
def compiled_graph_with_checkpointer():
    """Return a freshly compiled graph with an in-memory checkpointer."""
    try:
        return graph.builder.compile(
            checkpointer=MemorySaver(),
            name="UOM Orchestrator Workflow (test)",
        )
    except Exception as exc:
        pytest.skip(f"Graph build with checkpointer unavailable: {exc}")


# ---------------------------------------------------------------------------
# Sample States
# ---------------------------------------------------------------------------

SAMPLE_EFCORE_CODE = """\
public class Customer
{
    public int Id { get; set; }
    public string Name { get; set; }
    public ICollection<Order> Orders { get; set; }
}

public class Order
{
    public int Id { get; set; }
    public DateTime OrderDate { get; set; }
    public int CustomerId { get; set; }
    public Customer Customer { get; set; }
}

// Query
var customers = await dbContext.Customers
    .Include(c => c.Orders)
    .Where(c => c.Orders.Any(o => o.OrderDate > DateTime.UtcNow.AddDays(-30)))
    .ToListAsync();
"""


@pytest.fixture()
def sample_state() -> State:
    """A pre-populated State for EFCore → Spring Data MongoDB translation."""
    return State(
        messages=[
            HumanMessage(
                content=(
                    "Translate this EFCore code to Spring Data MongoDB:\n"
                    + SAMPLE_EFCORE_CODE
                )
            )
        ],
        translation_type=TranslationType.BOTH,
        source_target=FrameworkEnum.DOTNET_EFCORE,
        destination_target=FrameworkEnum.JAVA_SPRING_DATA_MONGODB,
    )


@pytest.fixture()
def empty_state() -> State:
    """A State with no source data — forces extract_input to call the LLM."""
    return State(
        messages=[
            HumanMessage(
                content=(
                    "Convert this EFCore LINQ code to Spring Data MongoDB:\n"
                    + SAMPLE_EFCORE_CODE
                )
            )
        ],
    )


@pytest.fixture()
def sample_tool_runtime(runtime, runnable_config, sample_state) -> ToolRuntime[Context, State]:
    # Create the ToolRuntime
    tool_runtime = ToolRuntime(
        state=sample_state,
        config=runnable_config,
        context=runtime.context,
        store=runtime.store,
        stream_writer=runtime.stream_writer,
        tools=[],
        tool_call_id=f"mocked_call_{uuid4()}",
    )
    return tool_runtime


@pytest.fixture()
def sample_config_with_runtime(runtime: Runtime, sample_tool_runtime: ToolRuntime) -> RunnableConfig:
    # Mock the internal Pregel Runtime
    mock_pregel_runtime = runtime
    return {
        "configurable": {
            "__pregel_runtime": mock_pregel_runtime,
            "__tool_runtime__": sample_tool_runtime,
        }
    }


@pytest.fixture()
def sample_efcore_results() -> dict:
    """Sample EFCore results for testing."""
    return orjson.loads((FIXTURES_DIR / "efcore_results.json").read_bytes())


@pytest.fixture()
def sample_mongo_results() -> dict:
    """Sample MongoDB results for testing."""
    return orjson.loads((FIXTURES_DIR / "mongo_results.json").read_bytes())
