"""Editor agent: polishes clarity, grammar, tone, and structure without touching facts."""
from datetime import datetime, timezone

from langchain_core.messages import HumanMessage, SystemMessage

from src.llm import get_llm

SYSTEM_PROMPT = """You are the Editor Agent. Improve clarity, flow, grammar, tone and structure of the
draft report WITHOUT changing its factual content or citation markers (e.g. [S1]). Return the
full edited report in Markdown."""


def editor_node(state):
    draft = state["draft"]
    llm = get_llm(temperature=0.3)
    result = llm.invoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"Draft report:\n\n{draft}\n\nReturn the polished version."),
    ])
    return {
        "edited_draft": result.content,
        "trace": [{
            "agent": "editor",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "summary": "Edited draft for clarity, grammar, tone and structure.",
        }],
    }
