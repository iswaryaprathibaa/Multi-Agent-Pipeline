# Multi-Agent Research Pipeline

A 4-agent report-generation pipeline orchestrated with **LangGraph**:

```
START → Researcher → Writer → Editor → Validator ──▶ END   (validation passed)
                        ▲                   │
                        └── feedback ───────┘           (validation failed, retry
                                                          up to max_revisions)
```

- **Researcher** — retrieves relevant chunks from a **ChromaDB** knowledge base (RAG) and
  synthesizes cited research notes.
- **Writer** — drafts a structured Markdown report from the research notes; on a revision
  loop, rewrites the report to address the Validator's feedback.
- **Editor** — polishes clarity, grammar, tone and structure without changing facts.
- **Validator** — a 4th agent that fact-checks the edited report against the research notes,
  flags hallucinations/gaps, and either accepts the report or routes it back to the Writer.

All LLM calls go through **OpenAI** (via `langchain_openai`), which means every call is
automatically traced to **LangSmith** once your API key is configured — no extra instrumentation
code required. A **Streamlit** dashboard (`app.py`) visualizes the orchestration live: which
agent is currently active, when the Validator loops feedback back to the Writer, and each
agent's output as it streams in.

## Project layout

```
src/
  config.py          # env/config + LangSmith wiring
  llm.py             # shared ChatOpenAI factory
  state.py           # LangGraph state schema (TypedDict)
  vectorstore.py      # ChromaDB ingestion + retrieval
  graph.py            # LangGraph StateGraph: nodes, edges, revision loop
  pipeline.py          # CLI runner
  agents/
    researcher.py
    writer.py
    editor.py
    validator.py
app.py                 # Streamlit live orchestration dashboard
data/                   # sample docs auto-ingested into ChromaDB
tests/test_pipeline.py  # graph-wiring tests (no API key required)
```

## Setup

1. **Install dependencies** (Python 3.10+ recommended):

   ```bash
   pip install -r requirements.txt
   ```

2. **Configure your keys** — copy the example env file and fill in your own keys:

   ```bash
   cp .env.example .env
   ```

   Edit `.env`:

   ```
   OPENAI_API_KEY=sk-...your key...
   LANGSMITH_API_KEY=lsv2-...your key...
   LANGSMITH_PROJECT=multi-agent-research-pipeline
   ```

   Never commit `.env` — it's already in `.gitignore`.

## Run it

### Option A — Live visual dashboard (recommended)

```bash
streamlit run app.py
```

Open the URL Streamlit prints (usually http://localhost:8501). Enter a topic, click
**Run pipeline**, and watch the graph diagram light up node-by-node as Researcher → Writer →
Editor → Validator execute, with each agent's output appearing in its own tab as soon as it's
ready. If the Validator rejects the report, the diagram highlights the feedback loop back to
the Writer and shows the revision count.

### Option B — Command line

```bash
python -m src.pipeline "The impact of retrieval-augmented generation on enterprise search"
```

This ingests `data/` into ChromaDB on first run, executes the graph, prints each agent's step
as it completes, and writes the final report to `output_<timestamp>.md`.

### Add your own source documents

Drop `.txt`/`.md` files into `data/` (or upload them from the Streamlit sidebar) before running
— the Researcher agent retrieves from whatever is in the ChromaDB collection, so more/better
source documents produce better-grounded reports. If retrieval comes back empty or irrelevant,
the Researcher falls back to general knowledge and marks those points `[General knowledge]` so
the Validator can tell the difference from cited claims.

## Seeing the orchestration

- **Streamlit dashboard** (`app.py`) — the primary "watch it happen" view described above.
- **LangSmith** — every OpenAI call (research synthesis, writing, editing, validation) is traced
  automatically as soon as `LANGSMITH_API_KEY` is set in `.env`. Open
  https://smith.langchain.com and select the `multi-agent-research-pipeline` project (or
  whatever you set `LANGSMITH_PROJECT` to) to see the full call tree, token usage, latency, and
  the exact prompts/outputs for each agent invocation, including every revision loop.
- **Static graph diagram** — `python -c "from src.graph import get_mermaid; print(get_mermaid())"`
  prints the graph as Mermaid syntax you can paste into
  [mermaid.live](https://mermaid.live) or any Mermaid renderer.

## Tests

```bash
pytest
```

These only check graph wiring (nodes exist, the validator routing function branches correctly,
mermaid output includes all agents) — they don't call OpenAI, so they run without any API key.

## Notes on the revision loop

- `max_revisions` (env `MAX_REVISIONS`, default `2`, adjustable per-run in the CLI/dashboard)
  bounds how many times the Validator can send the report back to the Writer.
- If the Validator still finds issues after `max_revisions` attempts, it force-accepts the
  current report as final (rather than looping forever) and records that decision in the trace
  log so it's visible in both the dashboard and LangSmith.
