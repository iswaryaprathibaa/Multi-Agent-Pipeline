"""Shared state schema passed between every node in the LangGraph pipeline."""
import operator
from typing import Annotated, Any, Dict, List, TypedDict


class Source(TypedDict):
    id: str
    content: str
    metadata: Dict[str, Any]


class ResearchState(TypedDict):
    topic: str
    max_revisions: int
    revision_count: int

    research_notes: str
    sources: List[Source]

    draft: str
    edited_draft: str

    is_valid: bool
    validation_feedback: str
    validation_issues: List[str]

    final_report: str

    # Annotated with operator.add so every node APPENDS to the trace instead
    # of overwriting it -- this is what powers the live orchestration view.
    trace: Annotated[List[Dict[str, Any]], operator.add]


def initial_state(topic: str, max_revisions: int) -> "ResearchState":
    return {
        "topic": topic,
        "max_revisions": max_revisions,
        "revision_count": 0,
        "research_notes": "",
        "sources": [],
        "draft": "",
        "edited_draft": "",
        "is_valid": False,
        "validation_feedback": "",
        "validation_issues": [],
        "final_report": "",
        "trace": [],
    }
