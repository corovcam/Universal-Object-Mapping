from react_agent.graph import graph
from tests.unit_tests.test_graph import BindableFakeChatModel
from uom_deep_agent.uom_agent import build_deep_agent

if __name__ == "__main__":
    from langchain_core.runnables.graph import CurveStyle
    
    with open("uom_translator_graph_diagram.mermaid", "w") as f:
        f.write(graph.get_graph(xray=True).draw_mermaid(curve_style=CurveStyle.BASIS))
    with open("uom_deep_agent_graph_diagram.mermaid", "w") as f:
        f.write(build_deep_agent(model=BindableFakeChatModel(responses=[]), dotnet_sandbox=None, java_sandbox=None).get_graph(xray=True).draw_mermaid(curve_style=CurveStyle.BASIS)) # type: ignore
