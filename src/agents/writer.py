"""Writer agent: turns research notes into a structured Markdown report, and
revises that report when the Validator sends it back with feedback."""
from datetime import datetime, timezone

from langchain_core.messages import HumanMessage, SystemMessage

from src.llm import get_llm

SYSTEM_PROMPT = """You are the Writer Agent. Turn research notes into a well-structured Markdown report with:
# Title
## Introduction
## Body sections with descriptive headings
## Conclusion
Preserve citation markers like [S1] from the research notes where relevant. Be clear and concise."""

REVISION_PROMPT = """You are the Writer Agent revising a report based on Validator feedback.
Keep what already works and fix only what is flagged. Return the FULL revised report in Markdown,
not a diff and not a summary of changes."""


def writer_node(state):
    topic = state["topic"]
    notes = state["research_notes"]
    feedback = state.get("validation_feedback")
    previous = state.get("edited_draft") or state.get("draft")

    llm = get_llm(temperature=0.5)

    if feedback and previous:
        result = llm.invoke([
            SystemMessage(content=REVISION_PROMPT),
            HumanMessage(content=(
                f"Topic: {topic}\n\nPrevious report:\n{previous}\n\n"
                f"Validator feedback to address:\n{feedback}\n\n"
                f"Research notes (for reference):\n{notes}"
            )),
        ])
        summary = "Revised the report to address validator feedback."
    else:
        result = llm.invoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=f"Topic: {topic}\n\nResearch notes:\n{notes}\n\nWrite the report now."),
        ])
        summary = "Drafted the initial report from research notes."

    return {
        "draft": result.content,
        "trace": [{"agent": "writer", "timestamp": datetime.now(timezone.utc).isoformat(), "summary": summary}],
    }
