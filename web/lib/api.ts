export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || "";

export function buildRunUrl(topic: string, maxRevisions: number): string {
  const params = new URLSearchParams({ topic, max_revisions: String(maxRevisions) });
  if (API_KEY) params.set("api_key", API_KEY);
  return `${API_URL}/run?${params.toString()}`;
}

export interface HealthResponse {
  status: string;
  openai_configured: boolean;
  langsmith_tracing: boolean;
  kb_chunks: number;
}

export async function fetchHealth(): Promise<HealthResponse | null> {
  try {
    const res = await fetch(`${API_URL}/health`, { cache: "no-store" });
    if (!res.ok) return null;
    return (await res.json()) as HealthResponse;
  } catch {
    return null;
  }
}
