"use client";

import { useState, useRef, useEffect } from "react";
import { useAppStore } from "@/lib/store";
import {
  sendChatQuery,
  fetchSuggestions,
  fallbackChatResponse,
} from "@/lib/api";
import { useGSAP } from "@gsap/react";
import gsap from "gsap";
// ── Inline SVG icons (no lucide-react) ─────────────────────────────────────
const SendIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M14.536 21.686a.5.5 0 0 0 .937-.024l6.5-19a.496.496 0 0 0-.635-.635l-19 6.5a.5.5 0 0 0-.024.937l7.93 3.18a2 2 0 0 1 1.112 1.11z" />
    <path d="m21.854 2.147-10.94 10.939" />
  </svg>
);
const SparklesIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <path d="M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z" />
    <path d="M20 3v4M22 5h-4M4 17v2M5 18H3" />
  </svg>
);
const UserIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="8" r="5" />
    <path d="M20 21a8 8 0 1 0-16 0" />
  </svg>
);
const TerminalIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="4 17 10 11 4 5" />
    <line x1="12" x2="20" y1="19" y2="19" />
  </svg>
);
const ChevronDownIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="m6 9 6 6 6-6" />
  </svg>
);
const ChevronUpIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="m18 15-6-6-6 6" />
  </svg>
);
// ───────────────────────────────────────────────────────────────────────────

import {
  ResponsiveContainer,
  LineChart, Line,
  BarChart, Bar,
  AreaChart, Area,
  ScatterChart, Scatter,
  XAxis, YAxis, CartesianGrid, Tooltip,
} from "recharts";
import type { ChartConfig } from "@/lib/api";

interface Message {
  id: string;
  role: "user" | "ai";
  content: string;
  sql?: string;
  chart_config?: ChartConfig;
  chart_data?: Record<string, unknown>[];
}

const DEFAULT_SUGGESTIONS = [
  "Which category has highest revenue?",
  "Show me anomalies last month",
  "Which segment is growing fastest?",
];

// ─── Out-of-scope guard ────────────────────────────────────────────────────
// Patterns that clearly indicate a non-data question
const OUT_OF_SCOPE_PATTERNS = [
  /^(hi|hello|hey|yo|sup|hiya|howdy|greetings)[!\s.?]*$/i,
  /^(how are you|what's up|what is up|how do you do)[?!.]*$/i,
  /^(who are you|what are you)[?!.]*$/i,
  /^(what('s| is) (the )?(weather|time|date|news|capital|president|meaning of life))/i,
  /^(tell me a joke|say something|can you dance|do you have feelings)/i,
  /^(write (me )?(a |an )?(poem|story|essay|song|code))/i,
  /^(translate|explain|summarize|define)\s+(?!my|the\s+data|this\s+data)/i,
];

const OUT_OF_SCOPE_REPLY =
  "I'm InsightPilot — a data analysis assistant that only works with your uploaded dataset. 📊\n\nTry asking something like:\n• \"What is the total revenue by region?\"\n• \"Which product category performs best?\"\n• \"Show me the monthly trend for sales.\"\n\nI can only answer questions about the data you've uploaded!";

function isOutOfScope(question: string): boolean {
  const q = question.trim();
  return OUT_OF_SCOPE_PATTERNS.some((re) => re.test(q));
}
// ──────────────────────────────────────────────────────────────────────────

const MIN_WIDTH = 300;
const MAX_WIDTH = 700;

export default function CopilotChat() {
  const isDashboard = useAppStore((s) => s.isDashboard);
  const datasetId = useAppStore((s) => s.datasetId);
  const suggestions = useAppStore((s) => s.suggestions);
  const setSuggestions = useAppStore((s) => s.setSuggestions);

  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "ai",
      content: "Hello! InsightPilot is online. What would you like to explore in the dataset?",
    },
  ]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [expandedSql, setExpandedSql] = useState<string | null>(null);
  const [errorToast, setErrorToast] = useState<string | null>(null);

  // ── Resize state ──────────────────────────────────────────────────────
  const [panelWidth, setPanelWidth] = useState(380);
  const isResizing = useRef(false);
  const startX = useRef(0);
  const startWidth = useRef(380);

  const onMouseDownResize = (e: React.MouseEvent) => {
    e.preventDefault();
    isResizing.current = true;
    startX.current = e.clientX;
    startWidth.current = panelWidth;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  };

  useEffect(() => {
    const onMouseMove = (e: MouseEvent) => {
      if (!isResizing.current) return;
      const delta = startX.current - e.clientX; // drag left = wider
      const newWidth = Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, startWidth.current + delta));
      setPanelWidth(newWidth);
    };
    const onMouseUp = () => {
      if (!isResizing.current) return;
      isResizing.current = false;
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };
    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);
    return () => {
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
    };
  }, []);
  // ─────────────────────────────────────────────────────────────────────

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const { contextSafe } = useGSAP({ scope: containerRef });

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  // Fetch suggestions once datasetId is available
  useEffect(() => {
    if (!datasetId || suggestions.length > 0) return;
    fetchSuggestions(datasetId).then(setSuggestions).catch(() => { });
  }, [datasetId, suggestions.length, setSuggestions]);

  // Entrance animation
  useGSAP(() => {
    if (isDashboard) {
      gsap.fromTo(
        containerRef.current,
        { x: 100, opacity: 0 },
        { x: 0, opacity: 1, duration: 0.8, ease: "power3.out" }
      );
    }
  }, [isDashboard]);

  const animateNewMessage = contextSafe(() => {
    gsap.fromTo(
      ".chat-message:last-child",
      { opacity: 0, scale: 0.95, y: 10 },
      { opacity: 1, scale: 1, y: 0, duration: 0.4, ease: "power2.out" }
    );
  });

  const handleSubmit = contextSafe(async (e?: React.FormEvent) => {
    e?.preventDefault();
    const question = inputValue.trim();
    if (!question || isLoading) return;

    const userMsg: Message = { id: Date.now().toString(), role: "user", content: question };
    setMessages((prev) => [...prev, userMsg]);
    setInputValue("");
    setTimeout(animateNewMessage, 50);

    // ── Out-of-scope guard ─────────────────────────────────────────────
    if (isOutOfScope(question)) {
      setTimeout(() => {
        const scopeMsg: Message = {
          id: (Date.now() + 1).toString(),
          role: "ai",
          content: OUT_OF_SCOPE_REPLY,
        };
        setMessages((prev) => [...prev, scopeMsg]);
        setTimeout(animateNewMessage, 50);
      }, 400);
      return;
    }
    // ──────────────────────────────────────────────────────────────────

    setIsLoading(true);

    try {
      if (!datasetId) throw new Error("No dataset selected for analysis.");
      const res = await sendChatQuery(question, datasetId);
      const aiMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "ai",
        content: res.disclaimer ? `${res.answer}\n\n${res.disclaimer}` : res.answer,
        sql: res.sql_used,
        chart_config: res.chart_config,
        // @ts-expect-error - The backend returns data but it's not currently strictly typed on the frontend
        chart_data: res.data ?? [],
      };
      setMessages((prev) => [...prev, aiMsg]);
    } catch (err) {
      setErrorToast(err instanceof Error ? err.message : "Failed to connect to InsightPilot server.");
    } finally {
      setIsLoading(false);
      setTimeout(animateNewMessage, 50);
    }
  });

  const displayedSuggestions = suggestions.length > 0 ? suggestions : DEFAULT_SUGGESTIONS;

  if (!isDashboard) return null;

  return (
    <div
      ref={containerRef}
      style={{ width: panelWidth }}
      className="fixed inset-y-0 right-0 bg-black/40 backdrop-blur-2xl border-l border-white/10 flex flex-col z-40 opacity-0 shadow-[-20px_0_40px_rgba(0,0,0,0.5)]"
    >
      {/* ── Resize handle ─────────────────────────────────────────────── */}
      <div
        onMouseDown={onMouseDownResize}
        title="Drag to resize"
        className="absolute left-0 top-0 bottom-0 w-3 cursor-col-resize z-50 group flex items-center justify-center"
      >
        {/* Visible grip dots */}
        <div className="flex flex-col gap-1 items-center opacity-30 group-hover:opacity-100 transition-opacity duration-200">
          {[0, 1, 2, 3, 4].map((i) => (
            <div key={i} className="w-1 h-1 rounded-full bg-cyan-400" />
          ))}
        </div>
        {/* Wider invisible hit area */}
        <div className="absolute inset-y-0 -left-1 -right-1" />
      </div>
      {/* ──────────────────────────────────────────────────────────────── */}

      {errorToast && (
        <div className="absolute top-20 left-1/2 -translate-x-1/2 w-[90%] bg-white/5 backdrop-blur-md border border-red-500/20 px-4 py-3 rounded-2xl z-50 shadow-2xl flex items-start gap-3">
          <p className="text-red-400 font-inter text-xs leading-relaxed flex-1">{errorToast}</p>
          <button onClick={() => setErrorToast(null)} className="text-gray-400 hover:text-white shrink-0">✕</button>
        </div>
      )}

      {/* Header */}
      <div className="h-16 flex items-center px-6 border-b border-white/10 shrink-0 bg-white/5">
        <SparklesIcon className="w-5 h-5 text-cyan-400 mr-2" />
        <h2 className="font-space-grotesk font-semibold text-white tracking-wide">InsightPilot Chat</h2>
        <span className="ml-auto text-[10px] text-gray-600 font-inter select-none">⟵ drag edge to resize</span>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 flex flex-col gap-6 custom-scrollbar">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`chat-message flex items-start gap-4 ${msg.role === "ai" ? "ai-message" : ""}`}
          >
            <div className="shrink-0 mt-1">
              {msg.role === "ai" ? (
                <div className="w-8 h-8 rounded-full bg-cyan-500/20 border border-cyan-500/50 flex items-center justify-center text-cyan-400">
                  <TerminalIcon className="w-4 h-4" />
                </div>
              ) : (
                <div className="w-8 h-8 rounded-full bg-purple-500/20 border border-purple-500/50 flex items-center justify-center text-purple-400">
                  <UserIcon className="w-4 h-4" />
                </div>
              )}
            </div>

            <div className="flex-1 min-w-0">
              <div className="font-inter text-xs text-gray-500 mb-1 font-medium">
                {msg.role === "ai" ? "InsightPilot" : "You"}
              </div>
              <div
                className={`font-inter text-sm leading-relaxed whitespace-pre-line ${
                  msg.role === "ai" ? "text-gray-300" : "text-white"
                }`}
              >
                {msg.content}
              </div>

              {/* Inline Chart */}
              {msg.chart_data && msg.chart_data.length > 0 && msg.chart_config && (
                <div className="mt-4 w-full bg-black/30 border border-white/10 rounded-xl p-4">
                  <h4 className="text-xs font-semibold text-gray-300 mb-4 font-inter text-center">
                    {msg.chart_config.title}
                  </h4>
                  <div style={{ width: "100%", height: 180 }}>
                    <ResponsiveContainer width="99%" height={180}>
                      {(() => {
                        const data = msg.chart_data;
                        const cfg = msg.chart_config;
                        const xKey = (cfg as any).x ?? cfg.x_key ?? "name";
                        let yKey = (cfg as any).y ?? cfg.y_key;
                        if (!yKey && data[0]) {
                          yKey = Object.keys(data[0]).find((k) => k !== xKey) ?? "value";
                        }
                        const color = cfg.color ?? "#06b6d4";

                        const axisProps = {
                          stroke: "#ffffff50",
                          tick: { fill: "#ffffff80", fontSize: 10 },
                          tickLine: false,
                          axisLine: false,
                        };
                        const tooltipStyle = {
                          contentStyle: {
                            backgroundColor: "#0a0a0a",
                            borderColor: "#ffffff20",
                            borderRadius: "8px",
                            color: "#fff",
                            fontSize: "12px",
                          },
                        };

                        const cType = cfg.chart_type ?? "line";
                        if (cType === "bar") {
                          return (
                            <BarChart data={data}>
                              <CartesianGrid strokeDasharray="3 3" stroke="#ffffff15" vertical={false} />
                              <XAxis dataKey={xKey} {...axisProps} />
                              <YAxis {...axisProps} width={40} />
                              <Tooltip {...tooltipStyle} />
                              <Bar dataKey={yKey} fill={color} radius={[2, 2, 0, 0]} />
                            </BarChart>
                          );
                        } else if (cType === "area") {
                          return (
                            <AreaChart data={data}>
                              <CartesianGrid strokeDasharray="3 3" stroke="#ffffff15" vertical={false} />
                              <XAxis dataKey={xKey} {...axisProps} />
                              <YAxis {...axisProps} width={40} />
                              <Tooltip {...tooltipStyle} />
                              <Area
                                type="monotone"
                                dataKey={yKey}
                                stroke={color}
                                fill={`${color}33`}
                                strokeWidth={2}
                              />
                            </AreaChart>
                          );
                        } else if (cType === "scatter") {
                          return (
                            <ScatterChart>
                              <CartesianGrid strokeDasharray="3 3" stroke="#ffffff15" />
                              <XAxis dataKey={xKey} {...axisProps} />
                              <YAxis dataKey={yKey} {...axisProps} width={40} />
                              <Tooltip {...tooltipStyle} />
                              <Scatter data={data} fill={color} />
                            </ScatterChart>
                          );
                        }
                        return (
                          <LineChart data={data}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#ffffff15" vertical={false} />
                            <XAxis dataKey={xKey} {...axisProps} />
                            <YAxis {...axisProps} width={40} />
                            <Tooltip {...tooltipStyle} />
                            <Line
                              type="monotone"
                              dataKey={yKey}
                              stroke={color}
                              strokeWidth={2}
                              dot={{ r: 3, fill: "#000", strokeWidth: 2 }}
                              activeDot={{ r: 5, fill: "#fff" }}
                            />
                          </LineChart>
                        );
                      })()}
                    </ResponsiveContainer>
                  </div>
                </div>
              )}

              {/* SQL Accordion */}
              {msg.sql && (
                <div className="mt-2">
                  <button
                    onClick={() => setExpandedSql(expandedSql === msg.id ? null : msg.id)}
                    className="flex items-center gap-1 text-xs text-gray-500 hover:text-cyan-400 transition-colors"
                  >
                    {expandedSql === msg.id ? (
                      <ChevronUpIcon className="w-3 h-3" />
                    ) : (
                      <ChevronDownIcon className="w-3 h-3" />
                    )}
                    View SQL
                  </button>
                  {expandedSql === msg.id && (
                    <pre className="mt-2 p-3 bg-black/50 border border-white/10 rounded-lg text-xs text-cyan-300 font-mono overflow-x-auto">
                      {msg.sql}
                    </pre>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}

        {/* Loading indicator */}
        {isLoading && (
          <div className="chat-message flex items-start gap-4 ai-message">
            <div className="shrink-0 mt-1">
              <div className="w-8 h-8 rounded-full bg-cyan-500/20 border border-cyan-500/50 flex items-center justify-center text-cyan-400">
                <TerminalSquare className="w-4 h-4" />
              </div>
            </div>
            <div className="flex-1 min-w-0">
              <div className="font-inter text-xs text-gray-500 mb-2 font-medium">InsightPilot</div>
              <div className="flex gap-1 items-center">
                <span className="w-2 h-2 rounded-full bg-cyan-400/60 animate-bounce" style={{ animationDelay: "0ms" }} />
                <span className="w-2 h-2 rounded-full bg-cyan-400/60 animate-bounce" style={{ animationDelay: "150ms" }} />
                <span className="w-2 h-2 rounded-full bg-cyan-400/60 animate-bounce" style={{ animationDelay: "300ms" }} />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 shrink-0 bg-white/5 border-t border-white/10 backdrop-blur-md">
        <div className="flex flex-wrap gap-2 mb-3">
          {displayedSuggestions.map((q, i) => (
            <button
              key={i}
              onClick={() => setInputValue(q)}
              className="text-xs font-inter font-medium px-3 py-1.5 rounded-full bg-white/5 border border-white/10 text-gray-400 hover:text-cyan-300 hover:border-cyan-500/30 hover:bg-cyan-500/10 transition-colors truncate max-w-full text-left"
            >
              {q}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="relative flex items-center">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Ask anything about the data..."
            className="w-full bg-black/50 border border-white/20 rounded-xl py-3 pl-4 pr-12 text-white font-inter text-sm placeholder:text-gray-600 focus:outline-none focus:border-cyan-400/50 focus:ring-1 focus:ring-cyan-400/50 transition-all"
          />
          <button
            type="submit"
            disabled={!inputValue.trim() || isLoading}
            className="absolute right-2 p-2 rounded-lg text-cyan-500 hover:text-white hover:bg-cyan-500 disabled:opacity-50 disabled:hover:bg-transparent disabled:hover:text-cyan-500 transition-colors"
          >
            <SendIcon className="w-4 h-4" />
          </button>
        </form>
      </div>

      <style jsx global>{`
        .custom-scrollbar::-webkit-scrollbar { width: 6px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 10px; }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.2); }
      `}</style>
    </div>
  );
}
