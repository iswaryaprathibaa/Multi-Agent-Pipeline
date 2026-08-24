"use client";

import { useEffect, useRef, useState } from "react";
import PipelineDiagram, { NEXT_NODE } from "@/components/PipelineDiagram";
import ReportTabs from "@/components/ReportTabs";
import { API_URL, buildRunUrl, fetchHealth, type HealthResponse } from "@/lib/api";
import type { NodeName, NodeStatus, NodeUpdatePayload, TraceEntry } from "@/lib/types";

const DEFAULT_TOPIC = "The impact of retrieval-augmented generation on enterprise search";

function idleStatuses(): Record<NodeName, NodeStatus> {
  return { researcher: "pending", writer: "pending", editor: "pending", validator: "pending" };
}

export default function Home() {
  const [topic, setTopic] = useState(DEFAULT_TOPIC);
  const [maxRevisions, setMaxRevisions] = useState(2);
  const [running, setRunning] = useState(false);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [statusLine, setStatusLine] = useState<string | null>(null);

  const [statuses, setStatuses] = useState<Record<NodeName, NodeStatus>>(idleStatuses());
  const [revisionCount, setRevisionCount] = useState(0);
  const [looping, setLooping] = useState(false);
  const [finished, setFinished] = useState(false);

  const [trace, setTrace] = useState<TraceEntry[]>([]);
  const [researchNotes, setResearchNotes] = useState("");
  const [draft, setDraft] = useState("");
  const [editedDraft, setEditedDraft] = useState("");
  const [isValid, setIsValid] = useState<boolean | null>(null);
  const [validationFeedback, setValidationFeedback] = useState("");
  const [validationIssues, setValidationIssues] = useState<string[]>([]);
  const [finalReport, setFinalReport] = useState("");

  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    fetchHealth().then(setHealth);
    return () => {
      esRef.current?.close();
    };
  }, []);

  function resetRunState() {
    setStatuses(idleStatuses());
    setRevisionCount(0);
    setLooping(false);
    setFinished(false);
    setTrace([]);
    setResearchNotes("");
    setDraft("");
    setEditedDraft("");
    setIsValid(null);
    setValidationFeedback("");
    setValidationIssues([]);
    setFinalReport("");
    setErrorMsg(null);
    setStatusLine(null);
  }

  function startRun() {
    if (!topic.trim() || running) return;
    resetRunState();
    setRunning(true);
    setStatuses((prev) => ({ ...prev, researcher: "active" }));

    const es = new EventSource(buildRunUrl(topic.trim(), maxRevisions));
    esRef.current = es;

    es.addEventListener("log", (evt) => {
      try {
        const data = JSON.parse((evt as MessageEvent).data);
        setStatusLine(data.message);
      } catch {
        /* ignore malformed log event */
      }
    });

    es.addEventListener("node_update", (evt) => {
      const payload: NodeUpdatePayload = JSON.parse((evt as MessageEvent).data);
      const node = payload.node;

      if (typeof payload.revision_count === "number") setRevisionCount(payload.revision_count);

      let nowLooping = false;
      setStatuses((prev) => {
        const next = { ...prev };
        if (node === "validator") {
          if (payload.is_valid) {
            next.validator = "done";
            setFinished(true);
          } else {
            next.validator = "flagged";
            next.writer = "active";
            next.editor = "pending";
            nowLooping = true;
          }
        } else {
          next[node] = "done";
          const nxt = NEXT_NODE[node];
          if (nxt) next[nxt] = "active";
        }
        return next;
      });
      setLooping(nowLooping);

      if (payload.trace?.length) {
        setTrace((prev) => [...prev, ...payload.trace!]);
        setStatusLine(`${payload.trace[payload.trace.length - 1].agent} — ${payload.trace[payload.trace.length - 1].summary}`);
      }
      if (payload.research_notes !== undefined) setResearchNotes(payload.research_notes);
      if (payload.draft !== undefined) setDraft(payload.draft);
      if (payload.edited_draft !== undefined) setEditedDraft(payload.edited_draft);
      if (payload.is_valid !== undefined) setIsValid(payload.is_valid);
      if (payload.validation_feedback !== undefined) setValidationFeedback(payload.validation_feedback);
      if (payload.validation_issues !== undefined) setValidationIssues(payload.validation_issues);
      if (payload.final_report !== undefined) setFinalReport(payload.final_report);
    });

    es.addEventListener("done", () => {
      setStatuses({ researcher: "done", writer: "done", editor: "done", validator: "done" });
      setFinished(true);
      setRunning(false);
      es.close();
    });

    // Native connection errors and our custom `event: error` SSE frames both
    // surface here as an "error" event -- data is only present for the latter.
    es.addEventListener("error", (evt) => {
      const data = (evt as MessageEvent).data;
      if (data) {
        try {
          setErrorMsg(JSON.parse(data).message || "Pipeline failed.");
        } catch {
          setErrorMsg("Pipeline failed.");
        }
      } else if (running) {
        setErrorMsg("Lost connection to the backend.");
      }
      setRunning(false);
      es.close();
    });
  }

  return (
    <div className="page">
      <h1>🧭 Multi-Agent Research Pipeline</h1>
      <p className="caption">
        Researcher → Writer → Editor → Validator, orchestrated with <strong>LangGraph</strong> · RAG via <strong>ChromaDB</strong> · LLM calls via{" "}
        <strong>OpenAI</strong> · traced in <strong>LangSmith</strong>
      </p>

      <div className="layout">
        <aside className="sidebar">
          <h3>Backend</h3>
          {health ? (
            <>
              <p>
                <span className={`status-pill ${health.openai_configured ? "ok" : "err"}`}>{health.openai_configured ? "OpenAI ✓" : "OpenAI missing"}</span>{" "}
                <span className={`status-pill ${health.langsmith_tracing ? "ok" : "warn"}`}>{health.langsmith_tracing ? "LangSmith ON" : "LangSmith OFF"}</span>
              </p>
              <p className="muted" style={{ fontSize: "0.82rem" }}>
                KB chunks: {health.kb_chunks}
              </p>
            </>
          ) : (
            <p className="muted" style={{ fontSize: "0.85rem" }}>
              Can&apos;t reach API at <code>{API_URL}</code>
            </p>
          )}

          <hr className="divider" />
          <h3>Run</h3>
          <div className="field">
            <label htmlFor="topic">Research topic</label>
            <input id="topic" type="text" value={topic} onChange={(e) => setTopic(e.target.value)} disabled={running} />
          </div>
          <div className="field">
            <label htmlFor="revisions">
              Max revision loops: <strong>{maxRevisions}</strong>
            </label>
            <input
              id="revisions"
              type="range"
              min={1}
              max={4}
              value={maxRevisions}
              onChange={(e) => setMaxRevisions(Number(e.target.value))}
              disabled={running}
            />
          </div>
          <button className="run-btn" onClick={startRun} disabled={running || !topic.trim()}>
            {running ? "Running…" : "▶ Run pipeline"}
          </button>
        </aside>

        <main>
          {errorMsg && <div className="error-banner">⚠ {errorMsg}</div>}
          <PipelineDiagram statuses={statuses} revisionCount={revisionCount} looping={looping} finished={finished} />
          {statusLine && <div className="status-line">{statusLine}</div>}

          <ReportTabs
            researchNotes={researchNotes}
            draft={draft}
            editedDraft={editedDraft}
            isValid={isValid}
            validationFeedback={validationFeedback}
            validationIssues={validationIssues}
            finalReport={finalReport}
            trace={trace}
          />
        </main>
      </div>
    </div>
  );
}
