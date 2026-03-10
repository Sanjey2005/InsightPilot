// SELECTOR RULE (fixes issue #6):
// Always use one useAppStore call per value:
//   const foo = useAppStore((s) => s.foo);
// Never use an inline object selector — (s) => ({ a: s.a, b: s.b }) creates a
// new reference every render and triggers an infinite loop via useSyncExternalStore.
import { create } from "zustand";
import type {
  AgentLog,
  InsightResponse,
  KPIResponse,
  SchemaPreview,
} from "@/lib/api";

interface AppState {
  // ── Phase flags ────────────────────────────────────────────────────
  isProcessing: boolean;
  isDashboard: boolean;
  isSimulated: boolean; // true when fallback mock data is shown

  // ── Upload / run IDs ───────────────────────────────────────────────
  datasetId: string | null;
  runId: string | null;
  runStatus: string; // "idle" | "queued" | "running" | "completed" | "failed"

  // ── Agent pipeline data ────────────────────────────────────────────
  agentLogs: AgentLog[];
  schemaPreview: SchemaPreview | null;

  // ── Dashboard data ─────────────────────────────────────────────────
  insights: InsightResponse[];
  kpis: KPIResponse[];

  // ── Chat ───────────────────────────────────────────────────────────
  suggestions: string[];

  // ── Setters ────────────────────────────────────────────────────────
  setIsProcessing: (val: boolean) => void;
  setIsDashboard: (val: boolean) => void;
  setDatasetId: (val: string | null) => void;
  setRunId: (val: string | null) => void;
  setRunStatus: (val: string) => void;
  setAgentLogs: (logs: AgentLog[]) => void;
  setSchemaPreview: (preview: SchemaPreview | null) => void;
  setInsights: (insights: InsightResponse[]) => void;
  setKPIs: (kpis: KPIResponse[]) => void;
  setSuggestions: (suggestions: string[]) => void;
  setIsSimulated: (val: boolean) => void;
  setUploadError: (val: string | null) => void;
  setRunError: (val: string | null) => void;
}

export const useAppStore = create<AppState>((set) => ({
  isProcessing: false,
  isDashboard: false,
  isSimulated: false,
  datasetId: null,
  runId: null,
  runStatus: "idle",
  agentLogs: [],
  schemaPreview: null,
  insights: [],
  kpis: [],
  suggestions: [],

  setIsProcessing: (isProcessing) => set({ isProcessing }),
  setIsDashboard: (isDashboard) => set({ isDashboard }),
  setDatasetId: (datasetId) => set({ datasetId }),
  setRunId: (runId) => set({ runId }),
  setRunStatus: (runStatus) => set({ runStatus }),
  setAgentLogs: (agentLogs) => set({ agentLogs }),
  setSchemaPreview: (schemaPreview) => set({ schemaPreview }),
  setInsights: (insights) => set({ insights }),
  setKPIs: (kpis) => set({ kpis }),
  setSuggestions: (suggestions) => set({ suggestions }),
  setIsSimulated: (isSimulated) => set({ isSimulated }),
  setUploadError: () => { }, // No longer used in state, kept for compat
  setRunError: () => { }, // No longer used in state, kept for compat
}));
