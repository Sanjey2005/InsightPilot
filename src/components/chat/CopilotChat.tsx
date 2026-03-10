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
import { Send, Sparkles, User, TerminalSquare, ChevronDown, ChevronUp } from "lucide-react";

interface Message {
  id: string;
  role: "user" | "ai";
  content: string;
  sql?: string;
}

const DEFAULT_SUGGESTIONS = [
  "Which category has highest revenue?",
  "Show me anomalies last month",
  "Which segment is growing fastest?",
];

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
    fetchSuggestions(datasetId).then(setSuggestions).catch(() => {});
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
    setIsLoading(true);
    setTimeout(animateNewMessage, 50);

    try {
      if (!datasetId) throw new Error("no dataset");
      const res = await sendChatQuery(question, datasetId);
      const aiMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "ai",
        content: res.disclaimer ? `${res.answer}\n\n${res.disclaimer}` : res.answer,
        sql: res.sql_used,
      };
      setMessages((prev) => [...prev, aiMsg]);
    } catch {
      const aiMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "ai",
        content: fallbackChatResponse as string,
      };
      setMessages((prev) => [...prev, aiMsg]);
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
      className="fixed inset-y-0 right-0 w-[30%] min-w-[320px] max-w-[400px] bg-black/40 backdrop-blur-2xl border-l border-white/10 flex flex-col z-40 opacity-0 shadow-[-20px_0_40px_rgba(0,0,0,0.5)]"
    >
      {/* Header */}
      <div className="h-16 flex items-center px-6 border-b border-white/10 shrink-0 bg-white/5">
        <Sparkles className="w-5 h-5 text-cyan-400 mr-2" />
        <h2 className="font-space-grotesk font-semibold text-white tracking-wide">InsightPilot Chat</h2>
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
                  <TerminalSquare className="w-4 h-4" />
                </div>
              ) : (
                <div className="w-8 h-8 rounded-full bg-purple-500/20 border border-purple-500/50 flex items-center justify-center text-purple-400">
                  <User className="w-4 h-4" />
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

              {/* SQL Accordion */}
              {msg.sql && (
                <div className="mt-2">
                  <button
                    onClick={() => setExpandedSql(expandedSql === msg.id ? null : msg.id)}
                    className="flex items-center gap-1 text-xs text-gray-500 hover:text-cyan-400 transition-colors"
                  >
                    {expandedSql === msg.id ? (
                      <ChevronUp className="w-3 h-3" />
                    ) : (
                      <ChevronDown className="w-3 h-3" />
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
            <Send className="w-4 h-4" />
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
