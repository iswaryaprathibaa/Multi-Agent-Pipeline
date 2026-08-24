"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import type { TraceEntry } from "@/lib/types";

export interface ReportTabsProps {
  researchNotes: string;
  draft: string;
  editedDraft: string;
  isValid: boolean | null;
  validationFeedback: string;
  validationIssues: string[];
  finalReport: string;
  trace: TraceEntry[];
}

const TABS = ["Research Notes", "Draft", "Edited Draft", "Validation", "Final Report", "Trace Log"] as const;
type Tab = (typeof TABS)[number];

export default function ReportTabs(props: ReportTabsProps) {
  const [active, setActive] = useState<Tab>("Research Notes");

  return (
    <div className="tabs-wrap">
      <div className="tabs-header">
        {TABS.map((t) => (
          <button key={t} className={`tab-btn ${active === t ? "tab-btn-active" : ""}`} onClick={() => setActive(t)}>
            {t}
          </button>
        ))}
      </div>
      <div className="tab-panel">
        {active === "Research Notes" && <Markdown text={props.researchNotes} empty="Nothing yet — run the pipeline." />}
        {active === "Draft" && <Markdown text={props.draft} empty="Nothing yet." />}
        {active === "Edited Draft" && <Markdown text={props.editedDraft} empty="Nothing yet." />}
        {active === "Validation" && (
          <div>
            {props.isValid === null ? (
              <p className="muted">Nothing yet.</p>
            ) : (
              <>
                <p>
                  <strong>Verdict:</strong> {props.isValid ? "✅ Passed" : "❌ Needs revision"}
                </p>
                <p>
                  <strong>Feedback:</strong> {props.validationFeedback || <span className="muted">none</span>}
                </p>
                {props.validationIssues.length > 0 && (
                  <>
                    <strong>Issues:</strong>
                    <ul>
                      {props.validationIssues.map((issue, i) => (
                        <li key={i}>{issue}</li>
                      ))}
                    </ul>
                  </>
                )}
              </>
            )}
          </div>
        )}
        {active === "Final Report" && <Markdown text={props.finalReport} empty="The report lands here once the Validator accepts it." />}
        {active === "Trace Log" && (
          <div className="trace-log">
            {props.trace.length === 0 && <p className="muted">Nothing yet.</p>}
            {props.trace.map((t, i) => (
              <div key={i} className="trace-entry">
                <span className="trace-agent">{t.agent}</span>
                <span className="trace-summary">{t.summary}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function Markdown({ text, empty }: { text: string; empty: string }) {
  if (!text) return <p className="muted">{empty}</p>;
  return (
    <div className="markdown-body">
      <ReactMarkdown>{text}</ReactMarkdown>
    </div>
  );
}
