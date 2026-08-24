export type NodeName = "researcher" | "writer" | "editor" | "validator";
export type NodeStatus = "pending" | "active" | "done" | "flagged";

export interface TraceEntry {
  agent: string;
  timestamp: string;
  summary: string;
}

export interface SourceChunk {
  id: string;
  content: string;
  metadata: Record<string, unknown>;
}

export interface NodeUpdatePayload {
  node: NodeName;
  trace?: TraceEntry[];
  research_notes?: string;
  sources?: SourceChunk[];
  draft?: string;
  edited_draft?: string;
  is_valid?: boolean;
  validation_feedback?: string;
  validation_issues?: string[];
  revision_count?: number;
  final_report?: string;
}
