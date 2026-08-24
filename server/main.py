"""FastAPI backend for the multi-agent research pipeline.

Wraps the existing LangGraph pipeline (src/graph.py) as an HTTP service so a
separately-hosted frontend (e.g. a Next.js app on Vercel) can drive it.

Run from the repo root (imports depend on it):
    uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload
"""
import json
import os
import uuid

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src import config
from src.graph import build_graph
from src.state import initial_state
from src.vectorstore import collection_count, ingest_directory, ingest_texts

app = FastAPI(title="Multi-Agent Research Pipeline API", version="1.0.0")

_allowed_origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

_SERVER_API_KEY = os.getenv("SERVER_API_KEY", "")


def require_api_key(x_api_key: str = None):
    if _SERVER_API_KEY and x_api_key != _SERVER_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key header.")
    return True


class IngestTextRequest(BaseModel):
    texts: list[str]
    sources: list[str] | None = None


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@app.get("/health")
def health():
    return {
        "status": "ok",
        "openai_configured": bool(config.OPENAI_API_KEY),
        "langsmith_tracing": os.environ.get("LANGCHAIN_TRACING_V2") == "true",
        "kb_chunks": collection_count(),
    }


@app.get("/kb/count")
def kb_count():
    return {"count": collection_count()}


@app.post("/kb/ingest-directory")
def kb_ingest_directory(directory: str = "data", _auth: bool = Depends(require_api_key)):
    n = ingest_directory(directory)
    return {"ingested_chunks": n, "total_chunks": collection_count()}


@app.post("/kb/ingest-text")
def kb_ingest_text(req: IngestTextRequest, _auth: bool = Depends(require_api_key)):
    sources = req.sources or [f"upload-{i}" for i in range(len(req.texts))]
    metas = [{"source": s} for s in sources]
    n = ingest_texts(req.texts, metas)
    return {"ingested_chunks": n, "total_chunks": collection_count()}


@app.get("/run")
def run_pipeline(
    topic: str = Query(..., min_length=1),
    max_revisions: int = Query(default=None, ge=1, le=6),
    x_api_key: str = Query(default=None, alias="api_key"),
):
    # Browsers' native EventSource only supports GET, so auth (when enabled)
    # is passed as a query param here rather than a header.
    if _SERVER_API_KEY and x_api_key != _SERVER_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing api_key query param.")

    if not config.OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not configured on the server.")

    resolved_max_revisions = max_revisions if max_revisions is not None else config.MAX_REVISIONS

    def event_stream():
        try:
            if collection_count() == 0:
                n = ingest_directory("data")
                yield _sse("log", {"message": f"Ingested {n} chunk(s) into ChromaDB knowledge base."})

            graph = build_graph(with_memory=True)
            state = initial_state(topic, resolved_max_revisions)
            thread_id = str(uuid.uuid4())
            revision_count = 0

            for update in graph.stream(state, config={"configurable": {"thread_id": thread_id}}, stream_mode="updates"):
                for node_name, partial in update.items():
                    if node_name not in ("researcher", "writer", "editor", "validator"):
                        continue
                    revision_count = partial.get("revision_count", revision_count)
                    payload = {"node": node_name, **partial}
                    yield _sse("node_update", payload)

            yield _sse("done", {"ok": True, "revision_count": revision_count})
        except Exception as exc:  # surfaced to the client instead of a bare 500 mid-stream
            yield _sse("error", {"message": str(exc)})

    headers = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"}
    return StreamingResponse(event_stream(), media_type="text/event-stream", headers=headers)
