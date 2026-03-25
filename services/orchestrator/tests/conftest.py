"""Shared pytest fixtures for orchestrator tests.

Provides reusable fixtures for Context, Runtime, State, graph compilation,
and live service connections (MongoDB, DB Toolbox, Ollama).
"""

from unittest.mock import MagicMock

import pytest
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.runtime import Runtime

from react_agent.context import AvailableModel, Context
from react_agent.graph import graph as default_graph
from react_agent.state import FrameworkType, State


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


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
    return default_graph


@pytest.fixture()
def compiled_graph_with_checkpointer():
    """Return a freshly compiled graph with an in-memory checkpointer."""
    from react_agent.graph import builder

    return builder.compile(
        checkpointer=MemorySaver(),
        name="UOM Orchestrator Workflow (test)",
    )


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
        source_code=SAMPLE_EFCORE_CODE,
        source_target=FrameworkType.EFCORE_LINQ,
        destination_target=FrameworkType.SPRING_DATA_MONGODB,
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
        source_code="",
        source_target=FrameworkType.UNKNOWN,
        destination_target=FrameworkType.UNKNOWN,
    )
