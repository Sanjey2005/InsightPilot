"use client";

import { useRef, useEffect, useCallback, useState } from "react";
import { useAppStore } from "@/lib/store";
import AgentStepper from "@/components/ui/AgentStepper";
import KPIBar from "@/components/dashboard/KPIBar";
import StoryCard from "@/components/dashboard/StoryCard";
import CopilotChat from "@/components/chat/CopilotChat";
import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import {
  uploadDataset,
  triggerRun,
  pollRun,
  fallbackInsights,
  fallbackKPIs,
} from "@/lib/api";

export default function Home() {
  const {
    isProcessing,
    isDashboard,
    datasetId,
    insights,
    schemaPreview,
    setIsProcessing,
    setIsDashboard,
    setDatasetId,
    setRunId,
    setRunStatus,
    setAgentLogs,
    setInsights,
    setKPIs,
    setSchemaPreview,
    setIsSimulated,
  } = useAppStore();

  const heroRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [errorToast, setErrorToast] = useState<string | null>(null);
  const pollFailures = useRef(0);

  // ── Cleanup poll on unmount ──────────────────────────────────────────
  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  // ── GSAP exit animation (hero → stepper) ────────────────────────────
  const { contextSafe } = useGSAP({ scope: heroRef });
  const animateHeroOut = contextSafe(() => {
    setIsProcessing(true);
    gsap.to(heroRef.current, {
      opacity: 0,
      y: -50,
      scale: 0.95,
      duration: 0.8,
      ease: "power3.inOut",
      onComplete: () => {
        if (heroRef.current) heroRef.current.style.display = "none";
      },
    });
  });

  // ── Fallback simulation (API unreachable) ────────────────────────────
  const startFallbackSimulation = useCallback(() => {
    setIsSimulated(true);
    const FAKE_AGENTS = [
      "schema_agent",
      "sql_agent",
      "insight_agent",
      "viz_agent",
    ];
    FAKE_AGENTS.forEach((agent, i) => {
      setTimeout(() => {
        setAgentLogs(
          FAKE_AGENTS.slice(0, i + 1).map((a) => ({
            agent: a,
            status: "completed",
            started_at: new Date().toISOString(),
            duration_ms: 800 + Math.random() * 400,
            error: null,
          }))
        );
      }, (i + 1) * 2_200);
    });
    // Supervisor completes last → load mock data → show dashboard
    setTimeout(() => {
      setRunStatus("completed");
      setInsights(fallbackInsights);
      setKPIs(fallbackKPIs);
      setTimeout(() => setIsDashboard(true), 1_200);
    }, FAKE_AGENTS.length * 2_200 + 800);
  }, [setAgentLogs, setRunStatus, setInsights, setKPIs, setIsDashboard]);

  // ── Live polling ─────────────────────────────────────────────────────  
  const startPolling = useCallback(
    (runId: string) => {
      pollFailures.current = 0;
      if (pollRef.current) clearInterval(pollRef.current);
      pollRef.current = setInterval(async () => {
        try {
          const run = await pollRun(runId);
          pollFailures.current = 0;  // reset on success
          setAgentLogs(run.agent_logs ?? []);
          setRunStatus(run.status);

          if (run.status === "completed") {
            clearInterval(pollRef.current!);
            setInsights(run.insights ?? []);
            setKPIs(run.kpis ?? []);
            setTimeout(() => setIsDashboard(true), 1_200);
          } else if (run.status === "failed") {
            clearInterval(pollRef.current!);
            setErrorToast("The analysis pipeline encountered an error. Check the agent logs above for details.");
            setIsProcessing(false);
          }
        } catch (err) {
          pollFailures.current += 1;
          if (pollFailures.current >= 3) {
            // Backend unreachable after 3 retries → show error
            clearInterval(pollRef.current!);
            setErrorToast(err instanceof Error ? err.message : "Lost connection to the analysis server.");
            setIsProcessing(false);
          }
        }
      }, 3_000);
    },
    [setAgentLogs, setRunStatus, setInsights, setKPIs, setIsDashboard, setIsProcessing]
  );

  // ── File selected from input ─────────────────────────────────────────
  const handleFileChange = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;
      try {
        const result = await uploadDataset(file);
        setDatasetId(result.id);
        setSchemaPreview(result.schema_preview);
      } catch (err) {
        setErrorToast(
          err instanceof Error ? err.message : "Upload failed — is the backend running on port 8000?"
        );
      }
    },
    [setDatasetId, setSchemaPreview]
  );

  // ── Drop zone drag-and-drop ──────────────────────────────────────────
  const handleDrop = useCallback(
    async (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      const file = e.dataTransfer.files?.[0];
      if (!file || !file.name.endsWith(".csv")) return;
      try {
        const result = await uploadDataset(file);
        setDatasetId(result.id);
        setSchemaPreview(result.schema_preview);
      } catch (err) {
        setErrorToast(
          err instanceof Error ? err.message : "Upload failed — is the backend running on port 8000?"
        );
      }
    },
    [setDatasetId, setSchemaPreview]
  );

  // ── Main CTA: trigger run (or simulate if no API) ────────────────────
  const handleAnalyze = useCallback(async () => {
    animateHeroOut();

    if (!datasetId) {
      // No file uploaded or API was unreachable — use full mock simulation
      startFallbackSimulation();
      return;
    }

    try {
      const run = await triggerRun(datasetId);
      setRunId(run.id);
      setRunStatus(run.status);
      setIsSimulated(false);
      startPolling(run.id);
    } catch (err) {
      // Backend unreachable after upload
      setErrorToast(err instanceof Error ? err.message : "Failed to trigger analysis run.");
      setIsProcessing(false);
    }
  }, [
    animateHeroOut,
    datasetId,
    startFallbackSimulation,
    startPolling,
    setRunId,
    setRunStatus,
    setIsSimulated,
  ]);

  // ── Global Error Toast ───────────────────────────────────────────────
  const renderErrorToast = () => {
    if (!errorToast) return null;
    return (
      <div className="fixed top-10 left-1/2 -translate-x-1/2 bg-white/5 backdrop-blur-md border border-red-500/20 px-6 py-3 rounded-2xl z-50 shadow-2xl flex items-center gap-4">
        <p className="text-red-400 font-inter text-sm whitespace-pre-line text-center">{errorToast}</p>
        <button onClick={() => setErrorToast(null)} className="text-gray-400 hover:text-white transition-colors">✕</button>
      </div>
    );
  };

  // ── Dashboard view ───────────────────────────────────────────────────
  if (isDashboard) {
    return (
      <div
        className="min-h-[calc(100vh-1rem)] w-full flex flex-col relative z-20 pt-8 max-w-[1400px] mx-auto px-4 lg:pr-[35%]"
        data-print-content
      >
        {renderErrorToast()}

        {/* Dashboard header with Download Report button */}
        <div className="flex items-center justify-between mb-6 print-hide">
          <h1 className="text-2xl font-bold font-space-grotesk text-white drop-shadow-[0_0_10px_rgba(6,182,212,0.3)]">
            InsightPilot Dashboard
          </h1>
          <button
            onClick={() => {
              const original = document.title;
              const datasetName = schemaPreview?.table_name ?? "InsightPilot";
              const date = new Date().toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" });
              document.title = `InsightPilot Report — ${datasetName} — ${date}`;
              window.print();
              setTimeout(() => { document.title = original; }, 1000);
            }}
            className="flex items-center gap-2 px-5 py-2 rounded-2xl font-space-grotesk font-semibold text-sm text-cyan-500 bg-white/5 backdrop-blur-lg border border-white/10 hover:bg-white/10 hover:border-cyan-400/40 hover:shadow-[0_0_20px_rgba(6,182,212,0.35)] transition-all print-hide"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="7 10 12 15 17 10" />
              <line x1="12" y1="15" x2="12" y2="3" />
            </svg>
            Download Report
          </button>
        </div>

        <KPIBar />
        <div className="w-full mt-10 pb-32">
          <h2 className="text-xl font-space-grotesk text-white mb-6 font-semibold drop-shadow-[0_0_10px_rgba(255,255,255,0.2)]">
            Active Insights
          </h2>
          {insights.length === 0 ? (
            <div className="w-full bg-white/5 backdrop-blur-md border border-white/10 p-8 rounded-3xl flex flex-col items-center justify-center text-center">
              <h3 className="text-xl font-space-grotesk font-semibold text-white mb-2">No Insights Found</h3>
              <p className="text-gray-400 font-inter text-sm max-w-md">
                No insights generated yet. Try uploading a larger dataset.
              </p>
            </div>
          ) : (
            insights.map((insight, i) => (
              <StoryCard key={insight.id} insight={insight} index={i} />
            ))
          )}
        </div>
        <div data-print-hide>
          <CopilotChat />
        </div>
      </div>
    );
  }

  // ── Upload / hero view ───────────────────────────────────────────────
  const ctaLabel = datasetId ? "Analyze Dataset" : "Simulate Analysis";
  const hasSchema = schemaPreview !== null;


  return (
    <div className="flex min-h-[calc(100vh-1rem)] flex-col items-center justify-center px-4 relative overflow-hidden">
      
      {/* ── Dynamic Particle Background ── */}
      <div className="absolute inset-0 z-0 pointer-events-none overflow-hidden">
        {/* Deep background glow */}
        <div className="absolute top-1/4 left-1/4 w-[500px] h-[500px] bg-cyan-500/10 rounded-full blur-[120px] mix-blend-screen animate-pulse duration-[8000ms]" />
        <div className="absolute bottom-1/4 right-1/4 w-[600px] h-[600px] bg-purple-500/10 rounded-full blur-[150px] mix-blend-screen animate-pulse duration-[10000ms]" />
        
        {/* Floating Stars / Particles */}
        <div className="absolute top-[15%] left-[10%] w-1.5 h-1.5 bg-cyan-400 rounded-full shadow-[0_0_15px_#22d3ee] animate-[ping_3s_ease-in-out_infinite]" />
        <div className="absolute top-[45%] right-[20%] w-1 h-1 bg-purple-400 rounded-full shadow-[0_0_10px_#a855f7] animate-[ping_4s_ease-in-out_infinite_1s]" />
        <div className="absolute bottom-[25%] left-[30%] w-2 h-2 bg-blue-400 rounded-full shadow-[0_0_20px_#60a5fa] animate-[ping_5s_ease-in-out_infinite_2s]" />
        <div className="absolute top-[60%] left-[80%] w-1.5 h-1.5 bg-cyan-300 rounded-full shadow-[0_0_15px_#67e8f9] animate-[ping_3.5s_ease-in-out_infinite_0.5s]" />
      </div>

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".csv"
        className="hidden"
        onChange={handleFileChange}
      />

      {/* Hero Dropzone */}
      <div
        ref={heroRef}
        className={`flex flex-col items-center justify-center w-full max-w-4xl transition-opacity ${isProcessing ? "pointer-events-none" : ""
          }`}
      >
        <h1 className="text-5xl md:text-6xl lg:text-7xl font-bold mb-6 text-center text-white drop-shadow-[0_0_20px_rgba(6,182,212,0.4)] tracking-tight font-space-grotesk">
          Upload Dataset.
          <br />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-purple-500">
            Awaken InsightPilot.
          </span>
        </h1>

        {/* Drop zone */}
        <div
          onClick={() => fileInputRef.current?.click()}
          onDrop={handleDrop}
          onDragOver={(e) => e.preventDefault()}
          className="w-full max-w-2xl bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl p-16 mt-8 text-center cursor-pointer transition-all duration-500 hover:bg-white/10 hover:border-cyan-400/60 hover:shadow-[0_0_40px_rgba(6,182,212,0.25)] group relative overflow-hidden"
        >
          <div className="absolute inset-0 bg-gradient-to-r from-cyan-500/10 to-purple-500/10 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />

          {hasSchema ? (
            <div className="relative z-10 flex flex-col items-center gap-2">
              <p className="font-space-grotesk text-cyan-400 text-lg font-semibold">
                ✓ {schemaPreview!.columns.length} columns ·{" "}
                {schemaPreview!.row_count.toLocaleString()} rows
              </p>
              <p className="font-inter text-sm text-gray-400">
                {schemaPreview!.table_name}
              </p>
              <p className="font-inter text-xs text-gray-600 mt-1">
                Click to replace file
              </p>
            </div>
          ) : (
            <p className="font-space-grotesk text-gray-300 text-xl font-medium relative z-10 group-hover:text-white transition-colors">
              Drop your CSV file here
              <br />
              <span className="text-sm text-gray-500 mt-2 block font-inter group-hover:text-cyan-300/80">
                or click to browse
              </span>
            </p>
          )}
        </div>


        {/* CTA Button */}
        <button
          onClick={handleAnalyze}
          className="mt-6 px-10 py-3 rounded-2xl font-space-grotesk font-semibold text-base text-cyan-500 bg-white/5 backdrop-blur-lg border border-white/10 transition-all duration-300 hover:bg-white/10 hover:border-cyan-400/40 hover:shadow-[0_0_24px_rgba(6,182,212,0.4)]"
        >
          {ctaLabel}
        </button>
      </div>

      {/* Agent Stepper */}
      {isProcessing && !isDashboard && (
        <div className="absolute inset-0 flex items-center justify-center w-full z-20">
          <AgentStepper />
        </div>
      )}
    </div>
  );
}
