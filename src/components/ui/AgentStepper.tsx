"use client";

import { useRef } from "react";
import { useAppStore } from "@/lib/store";
import { useGSAP } from "@gsap/react";
import gsap from "gsap";

// ── Inline SVG icons (no lucide-react) ─────────────────────────────────────
const CheckCircleIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10" />
    <path d="m9 12 2 2 4-4" />
  </svg>
);

const CircleDotIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10" strokeDasharray="4 2" />
    <circle cx="12" cy="12" r="1" fill="currentColor" stroke="none" />
  </svg>
);

const SpinnerIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 12a9 9 0 1 1-6.219-8.56" />
  </svg>
);
// ───────────────────────────────────────────────────────────────────────────

const AGENTS = [
  { key: "schema_agent",  name: "Schema Discovery Agent",  desc: "Inferring schema & detecting KPIs..." },
  { key: "sql_agent",     name: "SQL Generation Agent",    desc: "Structuring queries..." },
  { key: "insight_agent", name: "Insight Discovery Agent", desc: "Hunting for anomalies and trends..." },
  { key: "viz_agent",     name: "Visualization Agent",     desc: "Plotting charts..." },
  { key: "supervisor",    name: "Supervisor Agent",        desc: "Compiling narrative..." },
];

export default function AgentStepper() {
  const containerRef = useRef<HTMLDivElement>(null);
  const rowRefs = useRef<(HTMLDivElement | null)[]>([]);
  const prevCompletedRef = useRef(new Set<string>());

  const agentLogs = useAppStore((s) => s.agentLogs);
  const runStatus = useAppStore((s) => s.runStatus);

  // Build completed set from real log data
  const completedKeys = new Set(
    agentLogs.map((l) => l.agent)
  );
  if (runStatus === "completed") completedKeys.add("supervisor");

  // Fade container in on mount
  useGSAP(() => {
    gsap.fromTo(
      containerRef.current,
      { opacity: 0, y: 30 },
      { opacity: 1, y: 0, duration: 0.8, ease: "power3.out" }
    );
  }, { scope: containerRef });

  // Scale blip only on newly completed agents
  useGSAP(() => {
    AGENTS.forEach((agent, i) => {
      if (completedKeys.has(agent.key) && !prevCompletedRef.current.has(agent.key)) {
        const row = rowRefs.current[i];
        if (row) {
          gsap.fromTo(row, { scale: 1 }, { scale: 1.02, duration: 0.1, yoyo: true, repeat: 1 });
        }
        prevCompletedRef.current.add(agent.key);
      }
    });
  }, { scope: containerRef, dependencies: [completedKeys.size] });

  return (
    <div
      ref={containerRef}
      className="w-full max-w-xl bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl p-8 shadow-[0_0_40px_rgba(168,85,247,0.15)] opacity-0 relative z-20"
    >
      <h2 className="text-2xl font-bold font-space-grotesk text-center text-white mb-8 tracking-wide">
        Agent Orchestration
      </h2>

      <div className="flex flex-col gap-6">
        {AGENTS.map((agent, i) => {
          const isDone = completedKeys.has(agent.key) && (i === 0 || completedKeys.has(AGENTS[i - 1].key));
          const isActive =
            !isDone && (i === 0 || (completedKeys.has(AGENTS[i - 1].key) && (i === 1 || completedKeys.has(AGENTS[i - 2].key))));

          return (
            <div
              key={agent.key}
              ref={(el) => { rowRefs.current[i] = el; }}
              className={`flex items-center gap-4 transition-opacity duration-500 ${
                isDone ? "opacity-100" : "opacity-30"
              }`}
            >
              <div className="w-6 h-6 shrink-0">
                {isDone ? (
                  <CheckCircleIcon className="w-6 h-6 text-cyan-400" />
                ) : isActive ? (
                  <SpinnerIcon className="w-6 h-6 text-purple-400 animate-spin" />
                ) : (
                  <CircleDotIcon className="w-6 h-6 text-gray-500" />
                )}
              </div>

              <div className="flex flex-col">
                <span className="font-space-grotesk font-semibold text-lg text-white">
                  {agent.name}
                </span>
                <span className="font-inter text-sm text-gray-400">
                  {agent.desc}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
