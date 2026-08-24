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
code required.

There are two ways to watch the orchestration live:

- A **Streamlit** dashboard (`app.py`) — the original all-in-one local tool. Good for quick
  local runs; can't be deployed to Vercel (Streamlit needs a persistent server process).
- A **FastAPI backend (`server/`) + Next.js frontend (`web/`)** — the same live graph
  visualization, but as a real web app: the backend streams orchestration events over
  Server-Sent Events, and the frontend (deployable to **Vercel**) renders them. This is the
  path to production. See [Deploying to production](#deploying-to-production) below.

Both frontends drive the exact same `src/graph.py` pipeline — nothing about the agents changes
depending on which UI you use.

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
app.py                     # Streamlit live orchestration dashboard (local use)
server/                     # FastAPI backend -- deploy this to Render/Fly/Railway
  main.py                    # /health, /kb/*, and /run (SSE stream of the pipeline)
  requirements.txt
web/                         # Next.js frontend -- deploy this to Vercel
  app/page.tsx                # topic form + live diagram + report tabs
  components/PipelineDiagram.tsx  # animated SVG flowchart of the graph
  components/ReportTabs.tsx
data/                       # sample docs auto-ingested into ChromaDB
tests/
  test_pipeline.py            # graph-wiring tests (no API key required)
  test_server.py              # FastAPI endpoint shape tests (no API key required)
Dockerfile, render.yaml       # backend deployment
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

- **Streamlit dashboard** (`app.py`) — quick local "watch it happen" view.
- **Next.js + FastAPI** (`web/` + `server/`) — the same live view as a deployable web app; see
  [Deploying to production](#deploying-to-production).
- **LangSmith** — every OpenAI call (research synthesis, writing, editing, validation) is traced
  automatically as soon as `LANGSMITH_API_KEY` is set in `.env`. Open
  https://smith.langchain.com and select the `multi-agent-research-pipeline` project (or
  whatever you set `LANGSMITH_PROJECT` to) to see the full call tree, token usage, latency, and
  the exact prompts/outputs for each agent invocation, including every revision loop.
- **Static graph diagram** — `python -c "from src.graph import get_mermaid; print(get_mermaid())"`
  prints the graph as Mermaid syntax you can paste into
  [mermaid.live](https://mermaid.live) or any Mermaid renderer.

## Deploying to production

**Why not just deploy `app.py` to Vercel?** Vercel only runs stateless serverless
functions/static sites — it can't host Streamlit's persistent WebSocket server, and its
serverless filesystem is ephemeral, which would break ChromaDB's local persistence. So the
pipeline moves behind a real API (`server/`), and only the frontend (`web/`) goes on Vercel.

### 1. Backend (`server/`) → Render, Fly.io, or Railway

A `Dockerfile` and `render.yaml` are included.

**Render (easiest — Blueprint deploy):**
1. Push this repo to GitHub (already done if you're reading this from the repo).
2. In Render: New → Blueprint → point at this repo → it reads `render.yaml`.
3. Set the secret env vars it prompts for: `OPENAI_API_KEY`, `LANGSMITH_API_KEY`.
4. After it deploys, update `ALLOWED_ORIGINS` in the Render dashboard to your actual Vercel
   URL (e.g. `https://your-app.vercel.app`) once you know it — wildcard `*` works for testing.
5. Note the backend's public URL (e.g. `https://multi-agent-pipeline-api.onrender.com`).

`render.yaml` deploys on Render's **free tier** with no persistent disk, so the ChromaDB
collection resets on every restart/redeploy — the backend just re-ingests `data/` again on
the next request when it finds the collection empty (see `server/main.py`'s `/run` handler),
which is instant for the bundled sample docs. If you outgrow that (e.g. a large custom
knowledge base you don't want to re-ingest constantly), add a `disk:` block back to
`render.yaml` and move to Render's paid Starter tier, which supports persistent disks.

**Fly.io / Railway / any Docker host:** build the root `Dockerfile` and set the same env vars
from `.env.example` (`OPENAI_API_KEY`, `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT`,
`ALLOWED_ORIGINS`, optionally `SERVER_API_KEY`). Optionally mount a persistent volume at
`CHROMA_PERSIST_DIR` (default `/app/chroma_db`) if you want the knowledge base to survive
redeploys instead of re-ingesting `data/` each time.

**Run it locally** (from the repo root, so `src`/`server` imports resolve):
```bash
uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Frontend (`web/`) → Vercel

1. In Vercel: New Project → import this repo → set **Root Directory** to `web`.
2. Add environment variable `NEXT_PUBLIC_API_URL` = your backend's public URL from step 1.
3. If you set `SERVER_API_KEY` on the backend, also add `NEXT_PUBLIC_API_KEY` with the same
   value (it's sent as a `?api_key=` query param since browsers' `EventSource` can't send
   custom headers).
4. Deploy. Vercel auto-detects Next.js and runs `next build`.

**Run it locally:**
```bash
cd web
cp .env.example .env.local   # NEXT_PUBLIC_API_URL=http://localhost:8000
npm install
npm run dev
```
Open http://localhost:3000 (with the backend from step 1 running) — same live diagram and
report tabs as the Streamlit dashboard, served as a normal web app.

### Security note

The `/run` endpoint burns your OpenAI credits on every call. If exposing this publicly, set
`SERVER_API_KEY` on the backend (and the matching `NEXT_PUBLIC_API_KEY` on the frontend) and/or
put rate limiting in front of it — there's none built in.

## Tests

```bash
pytest
```

`tests/test_pipeline.py` checks graph wiring (nodes exist, the validator routing function
branches correctly, mermaid output includes all agents). `tests/test_server.py` checks the
FastAPI endpoint shapes. Neither calls OpenAI, so both run without any API key — safe for CI.

For the frontend, `cd web && npm run build` is the same type-check + production build Vercel
runs, and will fail the same way a bad deploy would.

## Notes on the revision loop

- `max_revisions` (env `MAX_REVISIONS`, default `2`, adjustable per-run in the CLI/dashboard)
  bounds how many times the Validator can send the report back to the Writer.
- If the Validator still finds issues after `max_revisions` attempts, it force-accepts the
  current report as final (rather than looping forever) and records that decision in the trace
  log so it's visible in both the dashboard and LangSmith.
