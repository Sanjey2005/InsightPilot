"use client";

import { useRef } from "react";
import { useAppStore } from "@/lib/store";
import { fallbackKPIs } from "@/lib/api";
import type { KPIResponse } from "@/lib/api";
import { useGSAP } from "@gsap/react";
import gsap from "gsap";

function getFormatting(name: string): { prefix: string; suffix: string } {
  const n = name.toLowerCase();
  if (n.includes("revenue") || n.includes("sales") || n.includes("profit") || n.includes("cost")) {
    return { prefix: "$", suffix: "" };
  }
  if (n.includes("%") || n.includes("rate") || n.includes("pct") || n.includes("percent") || n.includes("growth") || n.includes("conversion")) {
    return { prefix: "", suffix: "%" };
  }
  return { prefix: "", suffix: "" };
}

function formatDelta(delta: number | null): { label: string; isPositive: boolean } {
  if (delta === null) return { label: "—", isPositive: true };
  const sign = delta >= 0 ? "+" : "";
  return { label: `${sign}${delta.toFixed(1)}%`, isPositive: delta >= 0 };
}

export default function KPIBar() {
  const isDashboard = useAppStore((s) => s.isDashboard);
  const storeKpis = useAppStore((s) => s.kpis);
  const isSimulated = useAppStore((s) => s.isSimulated);
  const containerRef = useRef<HTMLDivElement>(null);
  const numsRef = useRef<(HTMLSpanElement | null)[]>([]);

  const kpis: KPIResponse[] = storeKpis;

  useGSAP(() => {
    if (!isDashboard || numsRef.current.length === 0) return;

    gsap.fromTo(
      containerRef.current,
      { opacity: 0, y: -20 },
      { opacity: 1, y: 0, duration: 1, ease: "power3.out" }
    );

    kpis.forEach((kpi, index) => {
      const el = numsRef.current[index];
      if (!el || kpi.value === null) return;
      const { prefix, suffix } = getFormatting(kpi.name);
      const dummy = { val: 0 };
      gsap.to(dummy, {
        val: kpi.value,
        duration: 2,
        ease: "power2.out",
        delay: index * 0.15,
        onUpdate: () => {
          const isFloat = kpi.value! % 1 !== 0;
          const formatted = isFloat
            ? dummy.val.toFixed(1)
            : Math.floor(dummy.val).toLocaleString();
          el.textContent = `${prefix}${formatted}${suffix}`;
        },
      });
    });
  }, [isDashboard]);

  if (!isDashboard) return null;

  return (
    <>
      {/* ── Print-only report header ───────────────────────────── */}
      <div className="hidden print-only-block mb-8 pb-4 border-b border-gray-200" id="print-header">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">InsightPilot Analytics Report</h1>
            <p className="text-gray-500 text-sm mt-1">Generated on {new Date().toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric", hour: "2-digit", minute: "2-digit" })}</p>
          </div>
          <div className="text-right text-xs text-gray-400">
            <p className="font-semibold text-gray-700">InsightPilot</p>
            <p>AI-Powered Analytics Copilot</p>
          </div>
        </div>
        {isSimulated && (
          <div className="mt-4 px-4 py-2 bg-amber-50 border border-amber-300 rounded text-amber-700 text-sm font-medium">
            ⚠ SIMULATED DATA — These figures are illustrative only. Upload a real CSV to generate verified calculations.
          </div>
        )}
      </div>

      {/* ── Simulated data warning (shown on screen, not just in print) */}
      {isSimulated && (
        <div className="w-full mb-4 px-4 py-3 rounded-2xl bg-amber-500/10 border border-amber-500/30 flex items-center gap-3 print-hide">
          <span className="text-amber-400 text-lg">⚠</span>
          <div>
            <p className="font-space-grotesk font-semibold text-amber-300 text-sm">Simulated Data</p>
            <p className="font-inter text-amber-400/80 text-xs">These are illustrative mock values. Upload a CSV to see calculations from your real data.</p>
          </div>
        </div>
      )}

      <div
        ref={containerRef}
        className="w-full grid grid-cols-2 lg:grid-cols-4 gap-3 z-20 relative opacity-0"
      >
        {kpis.map((kpi, index) => {
          const { prefix, suffix } = getFormatting(kpi.name);
          const { label: deltaLabel, isPositive } = formatDelta(kpi.delta_pct);

          return (
            <div
              key={kpi.id}
              data-print-kpi
              className="bg-white/5 backdrop-blur-md border border-white/10 p-4 rounded-2xl flex flex-col gap-2 relative overflow-hidden group min-w-0"
            >
              <div className="absolute -inset-2 bg-gradient-to-r from-cyan-500/0 via-cyan-500/5 to-purple-500/0 opacity-0 group-hover:opacity-100 blur-xl transition-opacity duration-500" />

              <h3 className="font-inter text-gray-400 text-xs font-medium z-10 truncate">{kpi.name}</h3>

              <span
                ref={(el: HTMLSpanElement | null) => { numsRef.current[index] = el; }}
                className="font-space-grotesk text-2xl font-bold text-white tracking-tight z-10"
              >
                {prefix}0{suffix}
              </span>

              <span
                className={`font-inter text-xs font-semibold px-2 py-1 rounded-md w-fit z-10 ${isPositive
                    ? "bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 shadow-[0_0_10px_rgba(6,182,212,0.1)]"
                    : "bg-red-500/10 text-red-400 border border-red-500/20"
                  }`}
              >
                {deltaLabel}
              </span>
            </div>
          );
        })}
      </div>
    </>
  );
}
