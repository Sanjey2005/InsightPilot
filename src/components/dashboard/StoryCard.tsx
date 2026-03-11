"use client";

import { useRef, useState } from "react";
import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import {
  ResponsiveContainer,
  LineChart, Line,
  BarChart, Bar,
  AreaChart, Area,
  ScatterChart, Scatter,
  XAxis, YAxis, CartesianGrid, Tooltip,
} from "recharts";
import type { InsightResponse } from "@/lib/api";
import { submitFeedback } from "@/lib/api";

// ── Inline SVG icons (no lucide-react) ─────────────────────────────────────
const ThumbUpIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M7 10v12" />
    <path d="M15 5.88 14 10h5.83a2 2 0 0 1 1.92 2.56l-2.33 8A2 2 0 0 1 17.5 22H4a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2h2.76a2 2 0 0 0 1.79-1.11L12 2a3.13 3.13 0 0 1 3 3.88Z" />
  </svg>
);

const ThumbDownIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M17 14V2" />
    <path d="M9 18.12 10 14H4.17a2 2 0 0 1-1.92-2.56l2.33-8A2 2 0 0 1 6.5 2H20a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-2.76a2 2 0 0 0-1.79 1.11L12 22a3.13 3.13 0 0 1-3-3.88Z" />
  </svg>
);
// ───────────────────────────────────────────────────────────────────────────

interface StoryCardProps {
  insight: InsightResponse;
  index?: number;
}

export default function StoryCard({ insight, index = 0 }: StoryCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const [feedbackSignal, setFeedbackSignal] = useState<"thumbs_up" | "thumbs_down" | null>(null);

  useGSAP(() => {
    gsap.fromTo(
      cardRef.current,
      { opacity: 0, y: 24 },
      { opacity: 1, y: 0, duration: 0.55, ease: "power2.out", delay: index * 0.12 }
    );
  }, []);

  const getTypeColor = (type: string) => {
    switch (type) {
      case "anomaly": return "bg-red-500/20 text-red-400 border-red-500/30";
      case "trend": return "bg-cyan-500/20 text-cyan-400 border-cyan-500/30";
      case "segment": return "bg-purple-500/20 text-purple-400 border-purple-500/30";
      case "kpi": return "bg-green-500/20 text-green-400 border-green-500/30";
      default: return "bg-gray-500/20 text-gray-400 border-gray-500/30";
    }
  };

  const handleFeedback = async (signal: "thumbs_up" | "thumbs_down") => {
    setFeedbackSignal(signal);
    try {
      await submitFeedback(insight.id, signal);
    } catch {
      // Optimistic — no rollback
    }
  };

  const chartData = insight.data ?? [];
  const cfg = insight.chart_config;
  const xKey = (cfg as any)?.x ?? cfg?.x_key ?? "name";
  const yKey =
    (cfg as any)?.y ?? cfg?.y_key ??
    (chartData[0]
      ? (Object.keys(chartData[0]).find((k) => k !== xKey) ?? "value")
      : "value");
  const color = cfg?.color ?? "#06b6d4";
  const chartType = cfg?.chart_type ?? (insight.type === "trend" ? "bar" : "line");

  const axisProps = {
    stroke: "#ffffff50",
    tick: { fill: "#ffffff80", fontSize: 12 },
    tickLine: false,
    axisLine: false,
  } as const;

  const tooltipStyle = {
    contentStyle: {
      backgroundColor: "#0a0a0a",
      borderColor: "#ffffff20",
      borderRadius: "8px",
      color: "#fff",
    },
  };

  const renderChart = () => {
    if (!chartData.length) return null;

    switch (chartType) {
      case "bar":
        return (
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#ffffff15" vertical={false} />
            <XAxis dataKey={xKey} {...axisProps} />
            <YAxis {...axisProps} />
            <Tooltip {...tooltipStyle} />
            <Bar dataKey={yKey} fill={color} radius={[4, 4, 0, 0]} />
          </BarChart>
        );
      case "area":
        return (
          <AreaChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#ffffff15" vertical={false} />
            <XAxis dataKey={xKey} {...axisProps} />
            <YAxis {...axisProps} />
            <Tooltip {...tooltipStyle} />
            <Area type="monotone" dataKey={yKey} stroke={color} fill={`${color}33`} strokeWidth={3} />
          </AreaChart>
        );
      case "scatter":
        return (
          <ScatterChart>
            <CartesianGrid strokeDasharray="3 3" stroke="#ffffff15" />
            <XAxis dataKey={xKey} {...axisProps} />
            <YAxis dataKey={yKey} {...axisProps} />
            <Tooltip {...tooltipStyle} />
            <Scatter data={chartData} fill={color} />
          </ScatterChart>
        );
      default: // "line"
        return (
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#ffffff15" vertical={false} />
            <XAxis dataKey={xKey} {...axisProps} />
            <YAxis {...axisProps} />
            <Tooltip {...tooltipStyle} />
            <Line
              type="monotone"
              dataKey={yKey}
              stroke={color}
              strokeWidth={3}
              dot={{ fill: "#000", strokeWidth: 2 }}
              activeDot={{ r: 6, fill: "#fff" }}
            />
          </LineChart>
        );
    }
  };

  const chart = renderChart();

  return (
    <div
      ref={cardRef}
      data-print-card
      className="w-full bg-white/5 backdrop-blur-lg border border-white/10 p-6 rounded-3xl relative overflow-hidden group mb-6 opacity-0"
    >
      <div className="absolute top-0 right-0 w-64 h-64 bg-cyan-500/5 rounded-full blur-3xl rounded-tl-[100px] pointer-events-none" />

      <div className="flex justify-between items-start mb-4 relative z-10">
        <div className="flex flex-col gap-2">
          <span
            className={`inline-flex px-3 py-1 rounded-full border text-xs font-semibold capitalize w-max ${getTypeColor(insight.type)}`}
          >
            {insight.type}
          </span>
          <h2 className="text-2xl font-bold font-space-grotesk text-white">
            {insight.title}
          </h2>
          <p className="text-gray-400 font-inter max-w-lg mb-1">{insight.narrative}</p>
        </div>

        <div className="flex items-center gap-3 print-hide">
          <button
            onClick={() => handleFeedback("thumbs_up")}
            className={`p-2 rounded-full transition-colors ${feedbackSignal === "thumbs_up"
                ? "text-cyan-400 bg-cyan-500/10"
                : "text-gray-500 hover:text-cyan-400 hover:bg-white/5"
              }`}
          >
            <ThumbUpIcon className="w-5 h-5" />
          </button>
          <button
            onClick={() => handleFeedback("thumbs_down")}
            className={`p-2 rounded-full transition-colors ${feedbackSignal === "thumbs_down"
                ? "text-red-400 bg-red-500/10"
                : "text-gray-500 hover:text-red-400 hover:bg-white/5"
              }`}
          >
            <ThumbDownIcon className="w-5 h-5" />
          </button>
        </div>
      </div>

      {chart && (
        <div className="mt-6 relative z-10" style={{ width: "100%", height: 240 }}>
          <ResponsiveContainer width="99%" height={240}>
            {chart}
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
