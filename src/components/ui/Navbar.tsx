"use client";

import { useState } from "react";
import { Sparkles, X, Info, Settings2 } from "lucide-react";

export default function Navbar() {
    const [modal, setModal] = useState<"about" | "how_it_works" | null>(null);

    return (
        <>
            {/* ── Navbar ────────────────────────────────────────────────────────── */}
            <nav className="fixed top-0 left-0 w-full h-16 bg-white/5 backdrop-blur-lg border-b border-white/10 z-[60] flex items-center justify-between px-6">
                <div className="flex items-center gap-2">
                    <Sparkles className="w-5 h-5 text-cyan-400" />
                    <span className="font-space-grotesk font-bold text-white tracking-wide text-lg">
                        InsightPilot
                    </span>
                </div>
                <div className="flex items-center gap-6">
                    <button
                        onClick={() => setModal("about")}
                        className="text-sm font-inter font-medium text-gray-300 hover:text-cyan-400 transition-colors"
                    >
                        About
                    </button>
                    <button
                        onClick={() => setModal("how_it_works")}
                        className="text-sm font-inter font-medium text-gray-300 hover:text-cyan-400 transition-colors"
                    >
                        How It Works
                    </button>
                </div>
            </nav>

            {/* ── Modals ──────────────────────────────────────────────────────── */}
            {modal && (
                <div className="fixed inset-0 z-[70] flex items-center justify-center p-4">
                    <div
                        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
                        onClick={() => setModal(null)}
                    />
                    <div className="bg-[#0f1115]/80 backdrop-blur-xl border border-white/10 p-8 rounded-3xl max-w-lg w-full relative z-10 shadow-[0_0_50px_rgba(0,0,0,0.5)] transform animate-in fade-in zoom-in duration-200">
                        <button
                            onClick={() => setModal(null)}
                            className="absolute top-6 right-6 text-gray-500 hover:text-white transition-colors"
                        >
                            <X className="w-5 h-5" />
                        </button>

                        {modal === "about" && (
                            <>
                                <div className="w-12 h-12 rounded-full bg-cyan-500/20 flex items-center justify-center mb-6">
                                    <Info className="w-6 h-6 text-cyan-400" />
                                </div>
                                <h2 className="text-2xl font-space-grotesk font-bold text-white mb-4">
                                    About InsightPilot
                                </h2>
                                <div className="space-y-4 text-gray-300 font-inter text-sm leading-relaxed">
                                    <p>
                                        InsightPilot is an AI-powered analytics copilot designed to instantly surface the most important stories hidden in your raw data.
                                    </p>
                                    <p>
                                        Simply upload a CSV, and our multi-agent architecture autonomously discovers schemas, writes SQL, uncovers trends, detects anomalies, and generates visual dashboards.
                                    </p>
                                    <p>
                                        It eliminates the need for manual data wrangling, allowing you to ask natural language questions and get immediate, verifiable answers backed by your own data.
                                    </p>
                                </div>
                            </>
                        )}

                        {modal === "how_it_works" && (
                            <>
                                <div className="w-12 h-12 rounded-full bg-purple-500/20 flex items-center justify-center mb-6">
                                    <Settings2 className="w-6 h-6 text-purple-400" />
                                </div>
                                <h2 className="text-2xl font-space-grotesk font-bold text-white mb-6">
                                    How It Works
                                </h2>
                                <div className="space-y-6">
                                    <div className="flex gap-4">
                                        <div className="w-8 h-8 rounded-full bg-white/5 border border-white/10 flex items-center justify-center text-xs font-bold text-cyan-400 shrink-0">1</div>
                                        <div>
                                            <h4 className="text-white font-semibold text-sm mb-1">Schema Discovery</h4>
                                            <p className="text-gray-400 text-xs leading-relaxed">An agent infers data types, detects primary metrics, and formulates targeted analytical hypotheses.</p>
                                        </div>
                                    </div>
                                    <div className="flex gap-4">
                                        <div className="w-8 h-8 rounded-full bg-white/5 border border-white/10 flex items-center justify-center text-xs font-bold text-cyan-400 shrink-0">2</div>
                                        <div>
                                            <h4 className="text-white font-semibold text-sm mb-1">SQL Generation</h4>
                                            <p className="text-gray-400 text-xs leading-relaxed">A specialized text-to-SQL agent translates the hypotheses into optimized queries run against your data.</p>
                                        </div>
                                    </div>
                                    <div className="flex gap-4">
                                        <div className="w-8 h-8 rounded-full bg-white/5 border border-white/10 flex items-center justify-center text-xs font-bold text-cyan-400 shrink-0">3</div>
                                        <div>
                                            <h4 className="text-white font-semibold text-sm mb-1">Insight Extraction</h4>
                                            <p className="text-gray-400 text-xs leading-relaxed">An analyst agent reviews the query results, finding trends, segments, and anomalies to build narratives.</p>
                                        </div>
                                    </div>
                                    <div className="flex gap-4">
                                        <div className="w-8 h-8 rounded-full bg-white/5 border border-white/10 flex items-center justify-center text-xs font-bold text-cyan-400 shrink-0">4</div>
                                        <div>
                                            <h4 className="text-white font-semibold text-sm mb-1">Visualization Prep</h4>
                                            <p className="text-gray-400 text-xs leading-relaxed">A design agent selects the perfect chart type and axis configuration to visually represent each insight.</p>
                                        </div>
                                    </div>
                                    <div className="flex gap-4">
                                        <div className="w-8 h-8 rounded-full bg-white/5 border border-white/10 flex items-center justify-center text-xs font-bold text-cyan-400 shrink-0">5</div>
                                        <div>
                                            <h4 className="text-white font-semibold text-sm mb-1">Copilot Chat</h4>
                                            <p className="text-gray-400 text-xs leading-relaxed">You can now chat directly with your dataset, using the same agentic pipeline to answer ad-hoc questions.</p>
                                        </div>
                                    </div>
                                </div>
                            </>
                        )}
                    </div>
                </div>
            )}
        </>
    );
}
