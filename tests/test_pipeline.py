"""Structural tests that don't require an OpenAI/LangSmith key -- they only
exercise graph wiring, not actual LLM calls."""
from langgraph.graph import END

from src.graph import build_graph, get_mermaid, route_after_validation


def test_graph_compiles():
    app = build_graph(with_memory=False)
    node_names = set(app.get_graph().nodes.keys())
    for expected in ("researcher", "writer", "editor", "validator"):
        assert expected in node_names


def test_route_after_validation_passes():
    assert route_after_validation({"is_valid": True}) == END


def test_route_after_validation_loops_back_to_writer():
    assert route_after_validation({"is_valid": False}) == "writer"


def test_mermaid_contains_all_agents():
    mermaid = get_mermaid()
    for agent in ("researcher", "writer", "editor", "validator"):
        assert agent in mermaid
