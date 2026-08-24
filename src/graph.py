"""LangGraph orchestration: Researcher -> Writer -> Editor -> Validator,
with a conditional feedback loop back to the Writer until the report
passes validation or max_revisions is hit."""
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from src.agents.editor import editor_node
from src.agents.researcher import researcher_node
from src.agents.validator import validator_node
from src.agents.writer import writer_node
from src.state import ResearchState

NODE_ORDER = ["researcher", "writer", "editor", "validator"]


def route_after_validation(state: ResearchState) -> str:
    return END if state.get("is_valid") else "writer"


def build_graph(with_memory: bool = True):
    graph = StateGraph(ResearchState)
    graph.add_node("researcher", researcher_node)
    graph.add_node("writer", writer_node)
    graph.add_node("editor", editor_node)
    graph.add_node("validator", validator_node)

    graph.add_edge(START, "researcher")
    graph.add_edge("researcher", "writer")
    graph.add_edge("writer", "editor")
    graph.add_edge("editor", "validator")
    graph.add_conditional_edges("validator", route_after_validation, {"writer": "writer", END: END})

    checkpointer = MemorySaver() if with_memory else None
    return graph.compile(checkpointer=checkpointer)


def get_mermaid() -> str:
    """Static text-based diagram of the graph (also shown in the README)."""
    app = build_graph(with_memory=False)
    return app.get_graph().draw_mermaid()
