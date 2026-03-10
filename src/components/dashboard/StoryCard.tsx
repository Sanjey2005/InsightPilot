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
import { ThumbsUp, ThumbsDown } from "lucide-react";
import type { InsightResponse } from "@/lib/api";
import { submitFeedback } from "@/lib/api";

interface StoryCardProps {
  insight: InsightResponse;
  index?: number;
}

export default function StoryCard({ insight, index = 0 }: StoryCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const [feedbackSignal, setFeedbackSignal] = useState<"thumbs_up" | "thumbs_down" | null>(null);

  // Simple staggered mount animation — no ScrollTrigger so cards are never
  // left invisible if position measurement misfires after the layout switch.
  useGSAP(() => {
    gsap.fromTo(
      cardRef.current,
      { opacity: 0, y: 24 },
      { opacity: 1, y: 0, duration: 0.55, ease: "power2.out", delay: index * 0.12 }
    );
  }, []);

  const getTypeColor = (type: string) => {
    switch (type) {
      case "anomaly": return "bg-purple-500/20 text-purple-400 border-purple-500/30";
      case "trend":   return "bg-cyan-500/20 text-cyan-400 border-cyan-500/30";
      case "segment": return "bg-emerald-500/20 text-emerald-400 border-emerald-500/30";
      default:        return "bg-gray-500/20 text-gray-400 border-gray-500/30";
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
  const xKey = cfg?.x_key ?? "name";
  const yKey =
    cfg?.y_key ??
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

  // FIX (issue #3): height must be a number, not "100%".
  // ResponsiveContainer with height="100%" reads the parent's computed height via
  // ResizeObserver. In React 19 concurrent mode the observer fires before the
  // browser has committed the Tailwind h-64 class, so height resolves to 0 and
  // Recharts never renders its SVG. Passing height={240} bypasses measurement.
  const chart = renderChart();

  return (
    <div
      ref={cardRef}
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

        <div className="flex items-center gap-3">
          <button
            onClick={() => handleFeedback("thumbs_up")}
            className={`p-2 rounded-full transition-colors ${
              feedbackSignal === "thumbs_up"
                ? "text-cyan-400 bg-cyan-500/10"
                : "text-gray-500 hover:text-cyan-400 hover:bg-white/5"
            }`}
          >
            <ThumbsUp className="w-5 h-5" />
          </button>
          <button
            onClick={() => handleFeedback("thumbs_down")}
            className={`p-2 rounded-full transition-colors ${
              feedbackSignal === "thumbs_down"
                ? "text-red-400 bg-red-500/10"
                : "text-gray-500 hover:text-red-400 hover:bg-white/5"
            }`}
          >
            <ThumbsDown className="w-5 h-5" />
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
