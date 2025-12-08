"use client";

import { Search } from "lucide-react";
import { useState } from "react";

export default function Home() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const handleSearch = async () => {
    if (!query) return;
    setLoading(true);
    setResult(null);

    try {
      // Mock Context for now - In RAG Phase 3 this will come from Retrieval
      const context = "Agni is the first god of the Rigveda. He is the priest, the fire, and the messenger between humans and gods.";

      // Use relative path - Next.js will proxy to http://127.0.0.1:8000 via next.config.mjs
      const res = await fetch("/api/insight", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, context }),
      });

      const data = await res.json();
      setResult(data);
    } catch (err) {
      console.error(err);
      setResult({ output: "Error communicating with the Intellect." });
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="h-screen w-full flex flex-col items-center justify-center relative overflow-hidden selection:bg-truth-white selection:text-truth-black p-6">

      {/* Top Bar */}
      <div className="absolute top-0 w-full p-6 flex justify-between opacity-40 text-xs font-mono tracking-tight uppercase border-b border-truth-white/10 z-10">
        <span>v0.1 // Local Kernel</span>
        <span>Bias: 0.00%</span>
      </div>

      <div className="w-full max-w-3xl flex flex-col gap-8 text-left z-10">

        {/* Polyglot Header */}
        <div className="flex items-center mb-6 opacity-90 hover:opacity-100 transition-opacity cursor-default group">
          <h1 className="text-4xl text-truth-white tracking-widest font-light flex items-baseline">
            <span className="font-sans-sanskrit">धी</span>
            <span className="script-sep">/</span>
            <span className="font-sans-telugu">ధీ</span>
            <span className="script-sep">/</span>
            <span className="font-sans-kannada">ಧೀ</span>
            <span className="script-sep">/</span>
            <span className="font-sans-malayalam">ധീ</span>
            <span className="script-sep">/</span>
            <span className="font-serif italic text-3xl">Dhī</span>
          </h1>
        </div>

        {/* Search Input */}
        <div className="relative group w-full">
          <input
            type="text"
            placeholder="Query the Archive..."
            className="w-full bg-neutral-900/50 border border-truth-white/20 rounded-none py-4 px-6 text-lg font-light text-truth-white focus:outline-none focus:border-truth-white focus:ring-0 transition-all placeholder:text-neutral-600 font-mono backdrop-blur-sm"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          />
          <button
            className="absolute right-4 top-1/2 -translate-y-1/2 text-neutral-500 hover:text-truth-white transition-colors"
            onClick={handleSearch}
          >
            <Search className={`w-5 h-5 opacity-50 hover:opacity-100 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {/* Result Card */}
        {loading && (
          <div className="mt-4 border-l-2 border-truth-white pl-6 py-1 animate-pulse opacity-50">
            <div className="h-4 w-32 bg-neutral-800 mb-4 rounded"></div>
            <div className="h-20 w-full bg-neutral-800 rounded"></div>
          </div>
        )}

        {result && (
          <div className="mt-4 border-l-2 border-truth-white pl-6 py-1 animate-[fadeIn_0.5s_ease-out]">
            <div className="flex gap-4 font-mono text-xs text-neutral-500 mb-3 uppercase tracking-tight">
              <span>Input: {query}</span>
            </div>
            <div className="prose prose-invert prose-lg max-w-none">
              <p className="leading-loose text-neutral-200">
                {result.output}
              </p>
              <div className="mt-2 text-sm text-neutral-400 font-mono">
                — The Model
              </div>
            </div>
          </div>
        )}

      </div>

      {/* Bottom Hash */}
      <div className="absolute bottom-6 font-mono text-[10px] text-neutral-700 w-full px-6 flex justify-between uppercase">
        <span>IDX: 3072_FLOAT_32</span>
        <span>MEM: {result ? result.token_usage?.total_tokens + " TOKENS" : "--"}</span>
        <span>LLM: META_LLAMA_3_8B_Q4_K_M</span>
      </div>

    </main>
  );
}
