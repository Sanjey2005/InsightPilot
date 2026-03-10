"use client";

import { useState } from "react";
import { Sparkles, X, Info, Settings2 } from "lucide-react";

export default function Navbar() {
    const [modal, setModal] = useState<"about" | "how_it_works" | null>(null);

    return (
        <>
            <div className="fixed top-0 left-0 w-full z-[60] pt-6 px-4 flex justify-center pointer-events-none">
                {/* ── Navbar ────────────────────────────────────────────────────────── */}
            <nav className="pointer-events-auto flex items-center justify-between px-6 py-3 rounded-full bg-white/5 backdrop-blur-xl border border-white/10 shadow-[0_0_40px_rgba(6,182,212,0.15)] transition-all duration-300 hover:border-cyan-400/40 hover:shadow-[0_0_60px_rgba(6,182,212,0.25)] min-w-[340px] md:min-w-[400px]">
                <div className="flex items-center gap-2">
                    <Sparkles className="w-5 h-5 text-cyan-400 drop-shadow-[0_0_10px_rgba(6,182,212,0.6)]" />
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
                            <X className="w-5 h-5" />
                        </button>

                        {modal === "about" && (
                            <div className="relative z-10">
                                <div className="w-14 h-14 rounded-2xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center mb-8 shadow-[0_0_30px_rgba(6,182,212,0.2)]">
                                    <Info className="w-7 h-7 text-cyan-400 drop-shadow-[0_0_8px_rgba(6,182,212,0.8)]" />
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
                                    <Settings2 className="w-7 h-7 text-purple-400 drop-shadow-[0_0_8px_rgba(168,85,247,0.8)]" />
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
