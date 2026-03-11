"use client";

import { useState } from "react";

// ── Inline SVG icons (no lucide-react) ─────────────────────────────────────
const SparklesIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <path d="M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z" />
    <path d="M20 3v4M22 5h-4M4 17v2M5 18H3" />
  </svg>
);

const XIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M18 6 6 18M6 6l12 12" />
  </svg>
);

const InfoIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10" />
    <path d="M12 16v-4M12 8h.01" />
  </svg>
);

const SettingsIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
    <circle cx="12" cy="12" r="3" />
  </svg>
);
// ───────────────────────────────────────────────────────────────────────────

export default function Navbar() {
    const [modal, setModal] = useState<"about" | "how_it_works" | null>(null);

    return (
        <>
            <div className="fixed top-0 left-0 w-full z-[60] pt-6 px-4 flex justify-center pointer-events-none">
                {/* ── Navbar ────────────────────────────────────────────────────────── */}
            <nav className="pointer-events-auto flex items-center justify-between px-6 py-3 rounded-full bg-white/5 backdrop-blur-xl border border-white/10 shadow-[0_0_40px_rgba(6,182,212,0.15)] transition-all duration-300 hover:border-cyan-400/40 hover:shadow-[0_0_60px_rgba(6,182,212,0.25)] min-w-[340px] md:min-w-[400px]">
                <div className="flex items-center gap-2">
                    <SparklesIcon className="w-5 h-5 text-cyan-400 drop-shadow-[0_0_10px_rgba(6,182,212,0.6)]" />
                    <span className="font-space-grotesk font-bold text-white tracking-wide text-lg drop-shadow-[0_2px_10px_rgba(255,255,255,0.2)]">
                        InsightPilot
                    </span>
                </div>
                <div className="flex items-center gap-6">
                    <button
                        onClick={() => setModal("about")}
                        className="text-sm font-inter font-semibold text-gray-400 hover:text-cyan-300 transition-colors drop-shadow-sm"
                    >
                        About
                    </button>
                    <button
                        onClick={() => setModal("how_it_works")}
                        className="text-sm font-inter font-semibold text-gray-400 hover:text-cyan-300 transition-colors drop-shadow-sm"
                    >
                        How It Works
                    </button>
                </div>
            </nav>
        </div>

            {/* ── Modals ──────────────────────────────────────────────────────── */}
            {modal && (
                <div className="fixed inset-0 z-[70] flex items-center justify-center p-4">
                    <div
                        className="absolute inset-0 bg-black/80 backdrop-blur-md transition-opacity duration-300 animate-in fade-in"
                        onClick={() => setModal(null)}
                    />
                    <div className="bg-[#050508]/90 backdrop-blur-2xl border border-white/10 p-10 rounded-3xl max-w-lg w-full relative z-10 shadow-[0_0_80px_rgba(6,182,212,0.15)] ring-1 ring-white/5 transform animate-in fade-in zoom-in-95 duration-300 ease-out overflow-hidden">
                        
                        {/* Subtle Background Glows */}
                        <div className="absolute top-0 left-1/4 w-1/2 h-1 bg-gradient-to-r from-transparent via-cyan-500 to-transparent blur-sm opacity-50" />
                        <div className="absolute -top-24 -left-24 w-48 h-48 bg-cyan-500/20 rounded-full blur-3xl pointer-events-none" />
                        <div className="absolute -bottom-24 -right-24 w-48 h-48 bg-purple-500/20 rounded-full blur-3xl pointer-events-none" />

                        <button
                            onClick={() => setModal(null)}
                            className="absolute top-6 right-6 text-gray-500 hover:text-white hover:bg-white/10 p-2 rounded-full transition-all duration-200 z-20"
                        >
                            <XIcon className="w-5 h-5" />
                        </button>

                        {modal === "about" && (
                            <div className="relative z-10">
                                <div className="w-14 h-14 rounded-2xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center mb-8 shadow-[0_0_30px_rgba(6,182,212,0.2)]">
                                    <InfoIcon className="w-7 h-7 text-cyan-400 drop-shadow-[0_0_8px_rgba(6,182,212,0.8)]" />
                                </div>
                                <h2 className="text-3xl font-space-grotesk font-bold text-white mb-6 tracking-tight drop-shadow-md">
                                    About InsightPilot
                                </h2>
                                <div className="space-y-5 text-gray-300 font-inter text-sm leading-relaxed">
                                    <p className="border-l-2 border-cyan-500/50 pl-4 py-1 bg-gradient-to-r from-cyan-500/5 to-transparent rounded-r-lg">
                                        <strong className="text-white font-semibold">InsightPilot</strong> is an AI-powered analytics copilot designed to instantly surface the most important stories hidden in your raw data.
                                    </p>
                                    <p>
                                        Simply upload a CSV, and our multi-agent architecture autonomously discovers schemas, writes SQL, uncovers trends, detects anomalies, and generates visual dashboards.
                                    </p>
                                    <p>
                                        It eliminates the need for manual data wrangling, allowing you to ask natural language questions and get immediate, verifiable answers backed by your own data.
                                    </p>
                                </div>
                            </div>
                        )}

                        {modal === "how_it_works" && (
                            <div className="relative z-10">
                                <div className="w-14 h-14 rounded-2xl bg-purple-500/10 border border-purple-500/30 flex items-center justify-center mb-8 shadow-[0_0_30px_rgba(168,85,247,0.2)]">
                                    <SettingsIcon className="w-7 h-7 text-purple-400 drop-shadow-[0_0_8px_rgba(168,85,247,0.8)]" />
                                </div>
                                <h2 className="text-3xl font-space-grotesk font-bold text-white mb-8 tracking-tight drop-shadow-md">
                                    How It Works
                                </h2>
                                <div className="space-y-6">
                                    <div className="flex gap-5 group">
                                        <div className="w-10 h-10 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center text-sm font-bold text-cyan-400 shrink-0 group-hover:bg-cyan-500/10 group-hover:border-cyan-500/40 group-hover:shadow-[0_0_15px_rgba(6,182,212,0.3)] transition-all duration-300">1</div>
                                        <div>
                                            <h4 className="text-white font-semibold text-sm mb-1 group-hover:text-cyan-300 transition-colors">Schema Discovery</h4>
                                            <p className="text-gray-400 text-xs leading-relaxed">An agent infers data types, detects primary metrics, and formulates targeted analytical hypotheses.</p>
                                        </div>
                                    </div>
                                    <div className="flex gap-5 group">
                                        <div className="w-10 h-10 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center text-sm font-bold text-cyan-400 shrink-0 group-hover:bg-cyan-500/10 group-hover:border-cyan-500/40 group-hover:shadow-[0_0_15px_rgba(6,182,212,0.3)] transition-all duration-300">2</div>
                                        <div>
                                            <h4 className="text-white font-semibold text-sm mb-1 group-hover:text-cyan-300 transition-colors">SQL Generation</h4>
                                            <p className="text-gray-400 text-xs leading-relaxed">A specialized text-to-SQL agent translates the hypotheses into optimized queries run against your data.</p>
                                        </div>
                                    </div>
                                    <div className="flex gap-5 group">
                                        <div className="w-10 h-10 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center text-sm font-bold text-cyan-400 shrink-0 group-hover:bg-cyan-500/10 group-hover:border-cyan-500/40 group-hover:shadow-[0_0_15px_rgba(6,182,212,0.3)] transition-all duration-300">3</div>
                                        <div>
                                            <h4 className="text-white font-semibold text-sm mb-1 group-hover:text-cyan-300 transition-colors">Insight Extraction</h4>
                                            <p className="text-gray-400 text-xs leading-relaxed">An analyst agent reviews the query results, finding trends, segments, and anomalies to build narratives.</p>
                                        </div>
                                    </div>
                                    <div className="flex gap-5 group">
                                        <div className="w-10 h-10 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center text-sm font-bold text-cyan-400 shrink-0 group-hover:bg-cyan-500/10 group-hover:border-cyan-500/40 group-hover:shadow-[0_0_15px_rgba(6,182,212,0.3)] transition-all duration-300">4</div>
                                        <div>
                                            <h4 className="text-white font-semibold text-sm mb-1 group-hover:text-cyan-300 transition-colors">Visualization Prep</h4>
                                            <p className="text-gray-400 text-xs leading-relaxed">A design agent selects the perfect chart type and axis configuration to visually represent each insight.</p>
                                        </div>
                                    </div>
                                    <div className="flex gap-5 group">
                                        <div className="w-10 h-10 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center text-sm font-bold text-cyan-400 shrink-0 group-hover:bg-cyan-500/10 group-hover:border-cyan-500/40 group-hover:shadow-[0_0_15px_rgba(6,182,212,0.3)] transition-all duration-300">5</div>
                                        <div>
                                            <h4 className="text-white font-semibold text-sm mb-1 group-hover:text-cyan-300 transition-colors">Copilot Chat</h4>
                                            <p className="text-gray-400 text-xs leading-relaxed">You can now chat directly with your dataset, using the same agentic pipeline to answer ad-hoc questions.</p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            )}
        </>
    );
}
