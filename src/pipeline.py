"""CLI entry point: run the full pipeline for a topic and write the final report.

Usage:
    python -m src.pipeline "Your research topic here"
    python -m src.pipeline "Your topic" --max-revisions 3 --out report.md
"""
import argparse
import uuid
from datetime import datetime, timezone

from src import config
from src.graph import build_graph
from src.state import initial_state
from src.vectorstore import collection_count, ingest_directory


def run(topic: str, max_revisions: int = None, ingest: bool = True, verbose: bool = True) -> dict:
    if ingest and collection_count() == 0:
        n = ingest_directory("data")
        if verbose:
            print(f"[setup] Ingested {n} chunk(s) into ChromaDB knowledge base ('{config.CHROMA_COLLECTION}').")

    app = build_graph(with_memory=True)
    state = initial_state(topic, max_revisions if max_revisions is not None else config.MAX_REVISIONS)
    thread_id = str(uuid.uuid4())

    final_state = None
    for update in app.stream(state, config={"configurable": {"thread_id": thread_id}}, stream_mode="values"):
        final_state = update
        if verbose and update.get("trace"):
            last = update["trace"][-1]
            print(f"[{last['agent']}] {last['summary']}")
    return final_state


def main():
    parser = argparse.ArgumentParser(description="Run the multi-agent research pipeline.")
    parser.add_argument("topic", help="Research topic / question for the report.")
    parser.add_argument("--max-revisions", type=int, default=None)
    parser.add_argument("--no-ingest", action="store_true", help="Skip auto-ingesting data/ into ChromaDB.")
    parser.add_argument("--out", default=None, help="Output file path for the final report markdown.")
    args = parser.parse_args()

    final_state = run(args.topic, max_revisions=args.max_revisions, ingest=not args.no_ingest)

    report = final_state.get("final_report") or final_state.get("edited_draft") or ""
    out_path = args.out or f"output_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.md"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\nRevisions used: {final_state.get('revision_count', 0)}")
    print(f"Final report written to {out_path}")
    if config.LANGSMITH_API_KEY:
        print(f"Trace available in LangSmith project '{config.LANGSMITH_PROJECT}' at https://smith.langchain.com")


if __name__ == "__main__":
    main()
