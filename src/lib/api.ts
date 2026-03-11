// ---------------------------------------------------------------------------
// Types — mirror the FastAPI response schemas exactly
// ---------------------------------------------------------------------------

export interface ColumnProfile {
  name: string;
  inferred_type: string;
  null_percentage: number;
  sample_values: unknown[];
}

export interface SchemaPreview {
  table_name: string;
  row_count: number;
  columns: ColumnProfile[];
}

export interface DatasetUploadResponse {
  id: string;
  user_id: string;
  name: string;
  source_type: string;
  table_name: string;
  row_count: number;
  schema_preview: SchemaPreview;
  created_at: string;
}

export interface AgentLog {
  agent: string;
  status: string; // "completed" | "failed" | "partial"
  started_at: string;
  duration_ms: number;
  error: string | null;
  details?: Record<string, unknown>;
}

export interface KPIResponse {
  id: string;
  name: string;
  value: number | null;
  delta_pct: number | null;
  period_label: string | null;
}

export interface ChartConfig {
  chart_type: string; // "line" | "bar" | "area" | "scatter"
  x_key: string;
  y_key: string;
  x_label: string;
  y_label: string;
  color: string;
  title: string;
}

export interface InsightResponse {
  id: string;
  type: string; // "trend" | "anomaly" | "segment" | "kpi"
  title: string;
  narrative: string;
  sql_used: string | null;
  chart_config: ChartConfig | null;
  data: Record<string, unknown>[] | null;
  kpi_column: string | null;
  severity: string; // "low" | "medium" | "high"
  created_at: string;
}

export interface RunResponse {
  id: string;
  dataset_id: string;
  user_id: string;
  status: string; // "queued" | "running" | "completed" | "failed"
  insights_count: number;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  agent_logs: AgentLog[] | null;
}

export interface RunDetailResponse extends RunResponse {
  kpis: KPIResponse[];
  insights: InsightResponse[];
}

export interface ChatQueryResponse {
  question: string;
  answer: string;
  sql_used: string;
  chart_config: ChartConfig;
  row_count: number;
  disclaimer: string;
}

// ---------------------------------------------------------------------------
// Client
// ---------------------------------------------------------------------------

const BASE_URL = (
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
).replace(/\/$/, ""); // strip trailing slash to avoid double-slash URLs

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, init);
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`API ${res.status} ${path}: ${body}`);
  }
  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

export async function uploadDataset(
  file: File
): Promise<DatasetUploadResponse> {
  const form = new FormData();
  form.append("file", file);
  return apiFetch<DatasetUploadResponse>("/datasets/upload", {
    method: "POST",
    body: form,
  });
}

export async function triggerRun(datasetId: string): Promise<RunResponse> {
  return apiFetch<RunResponse>("/runs/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ dataset_id: datasetId }),
  });
}

export async function pollRun(runId: string): Promise<RunDetailResponse> {
  return apiFetch<RunDetailResponse>(`/runs/${runId}`);
}

export async function sendChatQuery(
  question: string,
  datasetId: string
): Promise<ChatQueryResponse> {
  return apiFetch<ChatQueryResponse>("/chat/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, dataset_id: datasetId }),
  });
}

export async function fetchSuggestions(datasetId: string): Promise<string[]> {
  const res = await apiFetch<{ suggestions: string[] }>(
    `/chat/suggestions?dataset_id=${encodeURIComponent(datasetId)}`
  );
  return res.suggestions;
}

export async function submitFeedback(
  insightId: string,
  signal: "thumbs_up" | "thumbs_down" | "saved"
): Promise<void> {
  await apiFetch(`/insights/${insightId}/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ signal }),
  });
}

// ---------------------------------------------------------------------------
// Fallbacks — mockData shaped into InsightResponse / KPIResponse so every
// consumer has a consistent type regardless of whether the API is reachable.
// ---------------------------------------------------------------------------

import {
  mockInsights,
  mockKPIs,
  mockChatResponse,
} from "@/lib/mockData";

export const fallbackInsights: InsightResponse[] = mockInsights.map((m) => {
  const firstDataKey =
    m.chartData.length > 0
      ? (Object.keys(m.chartData[0]).find((k) => k !== "name") ?? "value")
      : "value";
  return {
    id: m.id,
    type: m.type,
    title: m.title,
    narrative: m.narrative,
    sql_used: null,
    chart_config: {
      chart_type: m.type === "trend" ? "bar" : "line",
      x_key: "name",
      y_key: firstDataKey,
      x_label: "Period",
      y_label: firstDataKey,
      color: m.type === "anomaly" ? "#a855f7" : "#06b6d4",
      title: m.title,
    },
    data: m.chartData as Record<string, unknown>[],
    kpi_column: null,
    severity: "medium",
    created_at: new Date().toISOString(),
  };
});

export const fallbackKPIs: KPIResponse[] = mockKPIs.map((k) => ({
  id: k.id,
  name: k.title,
  value: k.value,
  delta_pct: parseFloat(k.delta),
  period_label: null,
}));

export { mockChatResponse as fallbackChatResponse };
