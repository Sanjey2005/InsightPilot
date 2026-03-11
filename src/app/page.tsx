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
    isChatCollapsed,
    chatWidth,
  } = useAppStore();

  const heroRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [errorToast, setErrorToast] = useState<string | null>(null);
  const pollFailures = useRef(0);
  
  // Phase 4 States
  const [activeFilter, setActiveFilter] = useState("All");
  const [isLoadingDashboard, setIsLoadingDashboard] = useState(false);

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
      setIsLoadingDashboard(true);
      setTimeout(() => {
        setIsDashboard(true);
        setIsLoadingDashboard(false);
      }, 1500);
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
            setIsLoadingDashboard(true);
            setTimeout(() => {
              setIsDashboard(true);
              setIsLoadingDashboard(false);
            }, 1000);
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
      }, 6_000);
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
  const handleAnalyze = useCallback(async (overrideDatasetId?: string) => {
    animateHeroOut();

    const activeId = overrideDatasetId || datasetId;

    if (!activeId) {
      // No file uploaded or API was unreachable — use full mock simulation
      startFallbackSimulation();
      return;
    }

    try {
      const run = await triggerRun(activeId);
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

  // ── Load Sample Data ─────────────────────────────────────────────────
  const handleTrySampleData = useCallback(async () => {
    try {
      const res = await fetch("/samples/sample_ecommerce.csv");
      if (!res.ok) throw new Error("Sample file not available.");
      const blob = await res.blob();
      const file = new File([blob], "sample_ecommerce.csv", { type: "text/csv" });
      const result = await uploadDataset(file);
      setDatasetId(result.id);
      setSchemaPreview(result.schema_preview);
      handleAnalyze(result.id);
    } catch (err) {
      setErrorToast("Failed to load sample dataset. Please manually upload a CSV.");
    }
  }, [setDatasetId, setSchemaPreview, handleAnalyze]);

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
        className="min-h-[calc(100vh-1rem)] w-full flex flex-col relative z-20 pt-8 max-w-[1400px] mx-auto px-4 transition-all duration-300"
        style={{ paddingRight: isChatCollapsed ? '1rem' : `${chatWidth + 32}px` }}
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
          <div className="flex flex-col md:flex-row md:items-center justify-between mb-6 gap-4">
            <h2 className="text-xl font-space-grotesk text-white font-semibold drop-shadow-[0_0_10px_rgba(255,255,255,0.2)]">
              Active Insights
            </h2>
            
            {/* Filter Pills */}
            <div className="flex flex-wrap items-center gap-3">
              {["All", "Trends", "Anomalies", "Segments"].map((filter) => (
                <button
                  key={filter}
                  onClick={() => setActiveFilter(filter)}
                  className={`px-6 py-2 rounded-full text-sm font-space-grotesk font-semibold transition-all duration-300 border backdrop-blur-md ${
                    activeFilter === filter
                      ? "bg-cyan-500/30 border-cyan-400 text-white shadow-[0_0_20px_rgba(6,182,212,0.4)]"
                      : "bg-white/10 border-white/20 text-gray-300 hover:text-white hover:bg-white/20 hover:border-white/30"
                  }`}
                >
                  {filter}
                </button>
              ))}
            </div>
          </div>

          {insights.filter(i => {
             if (activeFilter === "All") return true;
             if (activeFilter === "Anomalies") return i.type === "anomaly";
             if (activeFilter === "Segments") return i.type === "segment";
             return i.type === activeFilter.toLowerCase().replace(/s$/, '');
          }).length === 0 ? (
            <div className="w-full bg-white/5 backdrop-blur-md border border-white/10 p-12 rounded-3xl flex flex-col items-center justify-center text-center group transition-all hover:bg-white/10">
              <div className="w-20 h-20 mb-6 rounded-full bg-white/5 border border-white/10 flex items-center justify-center text-gray-500 group-hover:text-cyan-400 group-hover:border-cyan-500/30 transition-colors">
                <svg className="w-10 h-10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="11" cy="11" r="8" />
                  <path d="m21 21-4.3-4.3" />
                  <path d="M11 8v6" />
                  <path d="M8 11h6" />
                </svg>
              </div>
              <h3 className="text-xl font-space-grotesk font-semibold text-white mb-2">No Insights Available</h3>
              <p className="text-gray-400 font-inter text-sm max-w-md">
                We couldn't find any actionable data matching your current filters. Try adjusting your view or upload a more detailed dataset.
              </p>
            </div>
          ) : (
            insights
              .filter(i => {
                if (activeFilter === "All") return true;
                if (activeFilter === "Anomalies") return i.type === "anomaly";
                if (activeFilter === "Segments") return i.type === "segment";
                return i.type === activeFilter.toLowerCase().replace(/s$/, '');
              })
              .map((insight, i) => (
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
    <div className="flex min-h-[calc(100vh-1rem)] flex-col items-center justify-center px-4 pt-32 pb-16 relative overflow-hidden">
      
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
        {/* Text Area with Blur Backdrop for Contrast */}
        <div className="relative text-center w-full z-10 flex flex-col items-center">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[120%] h-[150%] bg-[radial-gradient(ellipse_at_center,rgba(0,0,0,0.6)_0%,rgba(0,0,0,0)_60%)] -z-10 blur-xl pointer-events-none" />
          
          <h1 className="text-5xl md:text-6xl lg:text-7xl font-bold mb-4 text-center text-white drop-shadow-[0_0_30px_rgba(255,255,255,0.4)] tracking-tight font-space-grotesk">
            Upload Dataset.
            <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-300 to-purple-400 drop-shadow-[0_0_30px_rgba(6,182,212,0.6)]">
              Awaken InsightPilot.
            </span>
          </h1>

          {/* Animated tagline */}
          <p className="font-inter text-gray-200 text-sm md:text-base text-center max-w-lg mb-2 leading-relaxed drop-shadow-md">
            Drop your CSV
            <span className="text-cyan-400 font-medium"> →</span> get{" "}
            <span className="text-white font-medium">trends, anomalies &amp; KPIs</span> surfaced by AI in seconds.
          </p>
        </div>

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
        
        {/* Format hint */}
        <p className="font-inter text-xs text-gray-300 mt-4 text-center drop-shadow-sm">
          CSV files · up to 50 MB · UTF-8 encoding
        </p>


        {/* CTA Button */}
        <button
          onClick={() => handleAnalyze()}
          disabled={!datasetId && isProcessing}
          className="mt-6 px-10 py-3 rounded-2xl font-space-grotesk font-semibold text-base text-cyan-500 bg-white/5 backdrop-blur-lg border border-white/10 transition-all duration-300 hover:bg-white/10 hover:border-cyan-400/40 hover:shadow-[0_0_24px_rgba(6,182,212,0.4)] disabled:opacity-50"
        >
          {ctaLabel}
        </button>

        {/* Try Sample Data */}
        {!datasetId && !isProcessing && (
          <button
            onClick={handleTrySampleData}
            className="mt-4 text-xs font-inter text-gray-400 hover:text-cyan-300 transition-colors underline underline-offset-4 decoration-white/20 hover:decoration-cyan-500/50"
          >
            Don't have a CSV? Try Sample Data
          </button>
        )}

        {/* Feature mini-cards */}
        {!isProcessing && (
          <div className="grid grid-cols-3 gap-3 mt-10 mb-8 w-full max-w-xl">
            {[
              { emoji: "📊", title: "Auto KPIs", desc: "Key metrics surfaced automatically" },
              { emoji: "🔍", title: "Anomaly Detection", desc: "Outliers flagged and explained" },
              { emoji: "💬", title: "Chat with Data", desc: "Ask questions in plain English" },
            ].map(({ emoji, title, desc }) => (
              <div
                key={title}
                className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-2xl p-4 flex flex-col items-start gap-1.5 hover:bg-white/10 hover:border-cyan-500/30 transition-colors"
              >
                <span className="text-xl">{emoji}</span>
                <p className="font-space-grotesk text-white text-xs font-semibold">{title}</p>
                <p className="font-inter text-gray-500 text-[10px] leading-snug">{desc}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Agent Stepper & Skeleton Dashboard Loading */}
      {isProcessing && !isDashboard && (
        <div className="absolute inset-0 flex items-center justify-center w-full z-20">
          {!isLoadingDashboard ? (
            <AgentStepper />
          ) : (
            <div className="w-full max-w-[1400px] px-4 lg:pr-[35%] flex flex-col gap-6 animate-pulse mt-32 h-full items-start justify-start">
              {/* Fake KPI row */}
              <div className="w-full grid grid-cols-2 lg:grid-cols-4 gap-4">
                {[1, 2, 3, 4].map(k => <div key={k} className="h-32 rounded-2xl bg-white/5 border border-white/10" />)}
              </div>
              {/* Fake Story Cards */}
              <div className="h-10 w-48 bg-white/5 rounded-xl mt-8" />
              {[1, 2].map(k => <div key={k} className="w-full h-80 rounded-3xl bg-white/5 border border-white/10 mt-4" />)}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
