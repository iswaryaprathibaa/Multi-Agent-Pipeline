"""Streamlit dashboard: run the multi-agent pipeline and watch the LangGraph
orchestration live -- which agent is active, when the Validator loops feedback
back to the Writer, and each agent's output as it lands."""
import uuid

import streamlit as st
import streamlit.components.v1 as components

from src import config
from src.graph import build_graph
from src.state import initial_state
from src.vectorstore import collection_count, ingest_directory, ingest_texts

st.set_page_config(page_title="Multi-Agent Research Pipeline", layout="wide", page_icon="\U0001F9ED")

NODE_ORDER = ["researcher", "writer", "editor", "validator"]
NEXT_NODE = {"researcher": "writer", "writer": "editor", "editor": "validator"}

# status -> (fill, stroke, text)
COLORS = {
    "pending": ("#f1f5f9", "#94a3b8", "#64748b"),
    "active": ("#dbeafe", "#2563eb", "#1e3a8a"),
    "done": ("#dcfce7", "#16a34a", "#14532d"),
    "flagged": ("#fef3c7", "#d97706", "#78350f"),
}

NODE_META = {
    "researcher": {"emoji": "\U0001F50E", "title": "Researcher", "subtitle": "RAG retrieval + notes", "x": 96},
    "writer": {"emoji": "✍️", "title": "Writer", "subtitle": "drafts / revises report", "x": 316},
    "editor": {"emoji": "\U0001FA84", "title": "Editor", "subtitle": "polishes clarity & tone", "x": 536},
    "validator": {"emoji": "✅", "title": "Validator", "subtitle": "fact-checks & gates", "x": 756},
}
RECT_W, RECT_H, RECT_Y, CENTER_Y = 170, 90, 95, 140
LOOP_PATH = "M841,95 C841,15 401,15 401,95"
STRAIGHT_EDGES = [
    ("start_researcher", "M64,140 L92,140", "researcher"),
    ("researcher_writer", "M266,140 L312,140", "writer"),
    ("writer_editor", "M486,140 L532,140", "editor"),
    ("editor_validator", "M706,140 L752,140", "validator"),
    ("validator_end", "M926,140 L968,140", "end"),
]

DIAGRAM_STYLE = """
<style>
.diagram-wrap {font-family: -apple-system, "Segoe UI", sans-serif; overflow-x:auto;}
.pulse-blue rect, .pulse-blue circle {animation: pulseBlue 1.1s ease-in-out infinite;}
.pulse-orange rect, .pulse-orange circle {animation: pulseOrange 1.1s ease-in-out infinite;}
@keyframes pulseBlue {0%,100%{stroke-width:2.5; filter:drop-shadow(0 0 2px #2563eb);} 50%{stroke-width:4.5; filter:drop-shadow(0 0 9px #2563eb);}}
@keyframes pulseOrange {0%,100%{stroke-width:2.5; filter:drop-shadow(0 0 2px #d97706);} 50%{stroke-width:4.5; filter:drop-shadow(0 0 9px #d97706);}}
.flow-pending {stroke:#cbd5e1; stroke-width:2; stroke-dasharray:4 5; opacity:.65; fill:none;}
.flow-done {stroke:#16a34a; stroke-width:3; fill:none;}
.flow-active {stroke:#2563eb; stroke-width:3; stroke-dasharray:7 7; fill:none; animation:dashflow .6s linear infinite;}
.loop-idle {stroke:#cbd5e1; stroke-width:2; stroke-dasharray:4 5; opacity:.45; fill:none;}
.loop-active {stroke:#d97706; stroke-width:3; stroke-dasharray:7 7; fill:none; animation:dashflow .6s linear infinite;}
@keyframes dashflow {to {stroke-dashoffset:-28;}}
.legend {display:flex; gap:18px; flex-wrap:wrap; font-size:12.5px; color:#64748b; margin-top:2px;}
.legend span {display:inline-flex; align-items:center; gap:5px;}
.legend i {width:10px; height:10px; border-radius:50%; display:inline-block;}
</style>
"""


def _node_svg(name: str, status: str) -> str:
    meta = NODE_META[name]
    fill, stroke, text = COLORS[status]
    pulse = "pulse-blue" if status == "active" else ("pulse-orange" if status == "flagged" else "")
    cx = meta["x"] + RECT_W / 2
    return (
        f'<g class="{pulse}">'
        f'<rect x="{meta["x"]}" y="{RECT_Y}" width="{RECT_W}" height="{RECT_H}" rx="16" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="2.5"/>'
        f'<text x="{cx}" y="133" text-anchor="middle" font-size="16" font-weight="700" fill="{text}">'
        f'{meta["emoji"]} {meta["title"]}</text>'
        f'<text x="{cx}" y="153" text-anchor="middle" font-size="11" fill="{text}" opacity="0.85">'
        f'{meta["subtitle"]}</text>'
        f"</g>"
    )


def _circle_svg(cx: int, label: str, status: str) -> str:
    fill, stroke, text = COLORS[status]
    return (
        f'<circle cx="{cx}" cy="{CENTER_Y}" r="24" fill="{fill}" stroke="{stroke}" stroke-width="3"/>'
        f'<text x="{cx}" y="145" text-anchor="middle" font-size="11" font-weight="700" fill="{text}">{label}</text>'
    )


def render_diagram(statuses: dict, revision_count: int, looping: bool, finished: bool) -> str:
    def status_of(name: str) -> str:
        if name == "start":
            return "pending" if statuses.get("researcher", "pending") == "pending" else "done"
        if name == "end":
            return "done" if finished else "pending"
        # while looping, the writer box glows but its ORIGINAL incoming edge
        # (researcher->writer) should stay "done" -- only the loop arc animates.
        if name == "writer" and looping:
            return "done"
        return statuses.get(name, "pending")

    def edge_cls_marker(target: str):
        s = status_of(target)
        if s == "active":
            return "flow-active", "url(#arrow-blue)"
        if s in ("done", "flagged"):
            return "flow-done", "url(#arrow-green)"
        return "flow-pending", "url(#arrow-gray)"

    nodes_svg = "".join(_node_svg(n, statuses.get(n, "pending")) for n in NODE_ORDER)
    nodes_svg += _circle_svg(40, "START", status_of("start"))
    nodes_svg += _circle_svg(996, "END", status_of("end"))

    edges_svg = []
    dots_svg = []
    for key, path_d, target in STRAIGHT_EDGES:
        cls, marker = edge_cls_marker(target)
        edges_svg.append(f'<path d="{path_d}" class="{cls}" marker-end="{marker}"/>')
        if cls == "flow-active":
            dots_svg.append(f'<circle r="5" fill="#2563eb"><animateMotion dur="0.9s" repeatCount="indefinite" path="{path_d}"/></circle>')

    loop_cls, loop_marker = ("loop-active", "url(#arrow-orange)") if looping else ("loop-idle", "url(#arrow-gray)")
    edges_svg.append(f'<path d="{LOOP_PATH}" class="{loop_cls}" marker-end="{loop_marker}" />')
    if looping:
        dots_svg.append(f'<circle r="5" fill="#d97706"><animateMotion dur="1.4s" repeatCount="indefinite" path="{LOOP_PATH}"/></circle>')

    loop_label_color = "#d97706" if looping else "#94a3b8"
    loop_label_weight = "700" if looping else "500"
    loop_label = "feedback loop" + (f" — revision #{revision_count}" if revision_count else "")

    svg = f"""
    <svg viewBox="0 0 1040 190" width="100%" style="min-width:760px" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <marker id="arrow-gray" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#cbd5e1"/></marker>
        <marker id="arrow-blue" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#2563eb"/></marker>
        <marker id="arrow-green" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#16a34a"/></marker>
        <marker id="arrow-orange" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#d97706"/></marker>
      </defs>
      {''.join(edges_svg)}
      {''.join(dots_svg)}
      {nodes_svg}
      <text x="621" y="30" text-anchor="middle" font-size="12" font-weight="{loop_label_weight}" fill="{loop_label_color}">{loop_label}</text>
    </svg>
    """

    legend = (
        '<div class="legend">'
        '<span><i style="background:#94a3b8"></i>pending</span>'
        '<span><i style="background:#2563eb"></i>active</span>'
        '<span><i style="background:#16a34a"></i>done</span>'
        '<span><i style="background:#d97706"></i>needs revision</span>'
        "</div>"
    )
    return DIAGRAM_STYLE + f'<div class="diagram-wrap">{svg}{legend}</div>'


if "trace" not in st.session_state:
    st.session_state.trace = []
if "running" not in st.session_state:
    st.session_state.running = False

st.title("\U0001F9ED Multi-Agent Research Pipeline")
st.caption(
    "Researcher → Writer → Editor → Validator, orchestrated with **LangGraph** · "
    "RAG via **ChromaDB** · LLM calls via **OpenAI** · traced in **LangSmith**"
)

with st.sidebar:
    st.header("Knowledge base (ChromaDB)")
    st.write(f"Chunks stored: **{collection_count()}**")
    uploaded = st.file_uploader("Add source documents", type=["txt", "md"], accept_multiple_files=True)
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("Ingest data/ folder"):
            n = ingest_directory("data")
            st.success(f"Ingested {n} chunks.")
    with col_b:
        if st.button("Ingest uploads") and uploaded:
            texts = [f.read().decode("utf-8", errors="ignore") for f in uploaded]
            metas = [{"source": f.name} for f in uploaded]
            n = ingest_texts(texts, metas)
            st.success(f"Ingested {n} chunks.")

    st.divider()
    st.header("Run")
    topic = st.text_input(
        "Research topic",
        value="The impact of retrieval-augmented generation on enterprise search",
    )
    max_revisions = st.slider("Max revision loops", 1, 4, config.MAX_REVISIONS)
    run_clicked = st.button("▶ Run pipeline", type="primary", disabled=st.session_state.running)

    st.divider()
    if config.LANGSMITH_API_KEY:
        st.success(f"LangSmith tracing: ON\n\nProject: `{config.LANGSMITH_PROJECT}`")
        st.markdown("[Open LangSmith ↗](https://smith.langchain.com)")
    else:
        st.warning("LangSmith tracing: OFF\n\nSet LANGSMITH_API_KEY in .env to enable it.")
    if not config.OPENAI_API_KEY:
        st.error("OPENAI_API_KEY is not set. Add it to .env before running.")

def draw(slot, statuses, revision_count, looping, finished):
    # components.html renders in an isolated iframe (raw HTML/SVG parsing) --
    # unlike st.markdown, it never mistakes the indented SVG source for a
    # Markdown code block, so tags render instead of printing as text.
    with slot:
        components.html(render_diagram(statuses, revision_count, looping, finished), height=250, scrolling=True)


diagram_slot = st.empty()
status_line = st.empty()
draw(diagram_slot, {n: "pending" for n in NODE_ORDER}, 0, False, False)

tab_notes, tab_draft, tab_edit, tab_validate, tab_final, tab_trace = st.tabs(
    ["Research Notes", "Draft", "Edited Draft", "Validation", "Final Report", "Trace Log"]
)
notes_slot, draft_slot, edit_slot, validate_slot, final_slot, trace_slot = (
    tab_notes.empty(), tab_draft.empty(), tab_edit.empty(),
    tab_validate.empty(), tab_final.empty(), tab_trace.empty(),
)

if run_clicked and not topic.strip():
    st.warning("Enter a research topic first.")
elif run_clicked:
    st.session_state.running = True
    st.session_state.trace = []

    statuses = {n: "pending" for n in NODE_ORDER}
    statuses["researcher"] = "active"
    finished = False
    draw(diagram_slot, statuses, 0, False, finished)

    try:
        app = build_graph(with_memory=True)
        state = initial_state(topic, max_revisions)
        thread_id = str(uuid.uuid4())
        revision_count = 0

        for update in app.stream(state, config={"configurable": {"thread_id": thread_id}}, stream_mode="updates"):
            for node_name, partial in update.items():
                if node_name not in NODE_ORDER:
                    continue

                revision_count = partial.get("revision_count", revision_count)
                looping = False

                if node_name == "validator":
                    if partial.get("is_valid"):
                        statuses["validator"] = "done"
                        finished = True
                    else:
                        statuses["validator"] = "flagged"
                        statuses["writer"] = "active"
                        statuses["editor"] = "pending"
                        looping = True
                else:
                    statuses[node_name] = "done"
                    nxt = NEXT_NODE.get(node_name)
                    if nxt:
                        statuses[nxt] = "active"

                draw(diagram_slot, statuses, revision_count, looping, finished)

                for t in partial.get("trace", []):
                    st.session_state.trace.append(t)
                    status_line.info(f"**{t['agent']}** — {t['summary']}")

                if "research_notes" in partial:
                    notes_slot.markdown(partial["research_notes"])
                if "draft" in partial:
                    draft_slot.markdown(partial["draft"])
                if "edited_draft" in partial:
                    edit_slot.markdown(partial["edited_draft"])
                if "validation_feedback" in partial:
                    verdict = "✅ Passed" if partial.get("is_valid") else "❌ Needs revision"
                    issues = partial.get("validation_issues", [])
                    issues_md = ("\n\n**Issues:**\n" + "\n".join(f"- {i}" for i in issues)) if issues else ""
                    validate_slot.markdown(
                        f"**Verdict:** {verdict}\n\n**Feedback:** {partial.get('validation_feedback') or '_none_'}"
                        + issues_md
                    )
                if "final_report" in partial:
                    final_slot.markdown(partial["final_report"])

                trace_slot.json(st.session_state.trace)

        for n in NODE_ORDER:
            statuses[n] = "done"
        finished = True
        draw(diagram_slot, statuses, revision_count, False, finished)
        st.success(f"Pipeline finished after {revision_count} revision loop(s).")
    finally:
        st.session_state.running = False
