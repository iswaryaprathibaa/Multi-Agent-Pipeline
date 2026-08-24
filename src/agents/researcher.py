"""Researcher agent: retrieves context from ChromaDB and synthesizes research notes."""
from datetime import datetime, timezone

from langchain_core.messages import HumanMessage, SystemMessage

from src.llm import get_llm
from src.vectorstore import retrieve

SYSTEM_PROMPT = """You are a meticulous Research Agent inside a multi-agent report-writing pipeline.
Given a topic and retrieved reference excerpts, produce structured research notes:
- Key facts and findings, each tagged with the source id that supports it, e.g. [S1].
- A short list of open questions or gaps in the available sources.
Be factual and do not invent sources. If the excerpts are thin or irrelevant, say so explicitly
and you may fall back on general knowledge you are confident about, but mark those points
clearly as [General knowledge] rather than [S#] so the Validator can tell them apart."""


def researcher_node(state):
    topic = state["topic"]
    docs = retrieve(topic, k=6)

    sources = []
    context_parts = []
    for i, d in enumerate(docs, start=1):
        sid = f"S{i}"
        sources.append({"id": sid, "content": d.page_content, "metadata": dict(d.metadata)})
        context_parts.append(f"[{sid}] (source: {d.metadata.get('source', 'unknown')})\n{d.page_content}")

    context = "\n\n".join(context_parts) if context_parts else "(no matching documents were retrieved from the knowledge base)"

    llm = get_llm(temperature=0.2)
    result = llm.invoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"Topic: {topic}\n\nRetrieved excerpts:\n{context}\n\nWrite the research notes now."),
    ])

    return {
        "research_notes": result.content,
        "sources": sources,
        "trace": [{
            "agent": "researcher",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "summary": f"Retrieved {len(sources)} source chunk(s) from ChromaDB and drafted research notes.",
        }],
    }
