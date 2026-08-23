import React, { useState } from "react";
import {
  GitCompare,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Zap,
  TrendingDown,
  ShieldAlert,
  Cpu,
  Layers,
  Sparkles,
  ArrowRight,
} from "lucide-react";

export const BenchmarkLab: React.FC = () => {
  const [selectedScenario, setSelectedScenario] = useState<"contradiction" | "noise" | "heuristics">("contradiction");

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-indigo-50 text-indigo-700 text-xs font-bold uppercase tracking-wider mb-2">
            <GitCompare className="w-3.5 h-3.5" /> Architectural Benchmark Lab
          </div>
          <h2 className="text-xl font-bold text-slate-900">Zero-Vector REM Memory vs. Vector RAG</h2>
          <p className="text-xs text-slate-600 mt-1 max-w-2xl leading-relaxed">
            Vector databases were designed for static document search, not stateful, evolving agent workflows. See how RemAgent eliminates semantic drift, resolves contradictions, and reduces token overhead.
          </p>
        </div>

        {/* Scenario Selector */}
        <div className="flex items-center gap-2 bg-slate-100 p-1.5 rounded-xl border border-slate-200 self-start">
          <button
            id="bench-scenario-contradiction"
            onClick={() => setSelectedScenario("contradiction")}
            className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-all ${
              selectedScenario === "contradiction"
                ? "bg-white text-slate-900 shadow-xs"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            Contradiction Handling
          </button>
          <button
            id="bench-scenario-noise"
            onClick={() => setSelectedScenario("noise")}
            className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-all ${
              selectedScenario === "noise"
                ? "bg-white text-slate-900 shadow-xs"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            Noise & Token Bloat
          </button>
          <button
            id="bench-scenario-heuristics"
            onClick={() => setSelectedScenario("heuristics")}
            className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-all ${
              selectedScenario === "heuristics"
                ? "bg-white text-slate-900 shadow-xs"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            Rule Synthesis
          </button>
        </div>
      </div>

      {/* Comparison Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
          <div className="text-xs text-slate-500 font-semibold uppercase">Token Overhead</div>
          <div className="flex items-baseline gap-2 mt-1">
            <span className="text-2xl font-bold text-emerald-600">&lt;180</span>
            <span className="text-xs text-slate-400 line-through">2,400+ (RAG)</span>
          </div>
          <p className="text-[11px] text-slate-500 mt-1">92% prompt token reduction</p>
        </div>

        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
          <div className="text-xs text-slate-500 font-semibold uppercase">Contradiction Accuracy</div>
          <div className="flex items-baseline gap-2 mt-1">
            <span className="text-2xl font-bold text-indigo-600">100%</span>
            <span className="text-xs text-slate-400 line-through">46% (RAG)</span>
          </div>
          <p className="text-[11px] text-slate-500 mt-1">Explicit fact supersession</p>
        </div>

        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
          <div className="text-xs text-slate-500 font-semibold uppercase">Retrieval Latency</div>
          <div className="flex items-baseline gap-2 mt-1">
            <span className="text-2xl font-bold text-slate-900">0.8 ms</span>
            <span className="text-xs text-slate-400 line-through">85 ms (RAG)</span>
          </div>
          <p className="text-[11px] text-slate-500 mt-1">Direct indexed SQLite/Firestore lookup</p>
        </div>

        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
          <div className="text-xs text-slate-500 font-semibold uppercase">Vector DB Dependency</div>
          <div className="flex items-baseline gap-2 mt-1">
            <span className="text-2xl font-bold text-emerald-600">Zero</span>
            <span className="text-xs text-slate-400">Pinecone / Qdrant</span>
          </div>
          <p className="text-[11px] text-slate-500 mt-1">$0 infrastructure bill for vector index</p>
        </div>
      </div>

      {/* Side-by-Side Deep Dive */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Vector RAG Column */}
        <div className="bg-rose-50/40 rounded-2xl border border-rose-200/80 p-5 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-rose-200/60">
            <div className="flex items-center gap-2">
              <XCircle className="w-5 h-5 text-rose-600" />
              <div>
                <h3 className="font-bold text-slate-900 text-sm">Traditional Vector RAG</h3>
                <span className="text-[11px] text-rose-700 font-mono">Embedding Chunks + Top-K Cosine Similarity</span>
              </div>
            </div>
            <span className="px-2 py-0.5 rounded-full bg-rose-100 text-rose-800 text-[10px] font-bold">
              High Drift Risk
            </span>
          </div>

          {selectedScenario === "contradiction" && (
            <div className="space-y-3 text-xs">
              <div className="bg-white p-3 rounded-xl border border-rose-200 text-slate-700">
                <span className="font-bold text-slate-900 block mb-1">Scenario:</span>
                Turn 1: "Use SQLite for our app." <br />
                Turn 20: "CRITICAL: Deprecate SQLite. Migrate everything to PostgreSQL 16."
              </div>

              <div className="bg-rose-100/60 p-3 rounded-xl border border-rose-200 text-rose-900 space-y-1.5">
                <div className="font-bold flex items-center gap-1 text-rose-900">
                  <AlertTriangle className="w-4 h-4 text-rose-600" />
                  <span>What Vector RAG Injects into Prompt:</span>
                </div>
                <div className="bg-white/80 p-2.5 rounded-lg font-mono text-[11px] text-slate-800 space-y-1">
                  <div className="text-slate-500">// Chunk #1 (cosine: 0.88)</div>
                  <div>"Use SQLite for our app."</div>
                  <div className="text-slate-500 mt-2">// Chunk #2 (cosine: 0.86)</div>
                  <div>"CRITICAL: Deprecate SQLite. Migrate everything to PostgreSQL 16."</div>
                </div>
                <p className="text-[11px] text-rose-800 font-medium">
                  Result: LLM hallucinates hybrid code or asks user to clarify. Contradiction unresolved.
                </p>
              </div>
            </div>
          )}

          {selectedScenario === "noise" && (
            <div className="space-y-3 text-xs">
              <div className="bg-white p-3 rounded-xl border border-rose-200 text-slate-700">
                <span className="font-bold text-slate-900 block mb-1">Scenario:</span>
                20 turns of pleasantries ("Good morning!", "Thanks!"), stack trace retries, and CLI debug logs.
              </div>

              <div className="bg-rose-100/60 p-3 rounded-xl border border-rose-200 text-rose-900 space-y-1.5">
                <div className="font-bold text-rose-900">Vector Database Ingestion:</div>
                <p className="text-[11px] leading-relaxed">
                  Every single greeting and failed tool retry is converted into 1536-dim embeddings. Top-K retrieval blindly pulls 2,000+ tokens of dead-end chatter into every future prompt.
                </p>
                <div className="text-[11px] font-bold text-rose-800">
                  Massive context bloat • 80%+ wasted prompt spend.
                </div>
              </div>
            </div>
          )}

          {selectedScenario === "heuristics" && (
            <div className="space-y-3 text-xs">
              <div className="bg-white p-3 rounded-xl border border-rose-200 text-slate-700">
                <span className="font-bold text-slate-900 block mb-1">Scenario:</span>
                User mentions operational rules across days: "Never push to main", "Require 2 PR approvals", "Strict TypeScript only".
              </div>

              <div className="bg-rose-100/60 p-3 rounded-xl border border-rose-200 text-rose-900 space-y-1.5">
                <div className="font-bold text-rose-900">Semantic Search Limitation:</div>
                <p className="text-[11px] leading-relaxed">
                  Vector search matches semantic keyword proximity. If a query is "Help me write a database query", the vector DB retrieves database chunks, completely missing the "Never push to main" rule.
                </p>
              </div>
            </div>
          )}
        </div>

        {/* RemAgent Column */}
        <div className="bg-emerald-50/40 rounded-2xl border border-emerald-200/80 p-5 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-emerald-200/60">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-emerald-600" />
              <div>
                <h3 className="font-bold text-slate-900 text-sm">RemAgent Autonomous Memory</h3>
                <span className="text-[11px] text-emerald-700 font-mono">Zero-Vector Structured REM Consolidation</span>
              </div>
            </div>
            <span className="px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 text-[10px] font-bold">
              100% Deterministic
            </span>
          </div>

          {selectedScenario === "contradiction" && (
            <div className="space-y-3 text-xs">
              <div className="bg-white p-3 rounded-xl border border-emerald-200 text-slate-700">
                <span className="font-bold text-slate-900 block mb-1">Dream Daemon Consolidation:</span>
                Stage 3 resolves contradiction: <br />
                <span className="font-mono text-emerald-800">
                  fact: Architecture.primary_database → SQLite (SUPERSEDED) ➔ PostgreSQL 16 (ACTIVE)
                </span>
              </div>

              <div className="bg-emerald-100/60 p-3 rounded-xl border border-emerald-200 text-emerald-900 space-y-1.5">
                <div className="font-bold flex items-center gap-1 text-emerald-900">
                  <Sparkles className="w-4 h-4 text-emerald-600" />
                  <span>What RemAgent Injects into System Prompt:</span>
                </div>
                <div className="bg-white/90 p-2.5 rounded-lg font-mono text-[11px] text-slate-800 space-y-1 border border-emerald-200">
                  <div className="text-emerald-700 font-bold">[CONSOLIDATED KNOWLEDGE GRAPH]</div>
                  <div>- Architecture.primary_database = "PostgreSQL 16" (conf: 1.0)</div>
                  <div>- Architecture.provider = "Cloud SQL" (conf: 1.0)</div>
                </div>
                <p className="text-[11px] text-emerald-800 font-medium">
                  Result: Zero ambiguity. Old SQLite fact is cleanly inactivated. 100% deterministic accuracy.
                </p>
              </div>
            </div>
          )}

          {selectedScenario === "noise" && (
            <div className="space-y-3 text-xs">
              <div className="bg-white p-3 rounded-xl border border-emerald-200 text-slate-700">
                <span className="font-bold text-slate-900 block mb-1">Noise Pruning Pipeline:</span>
                Stage 1 strips 100% of chit-chat and ephemeral tool logs during REM sleep.
              </div>

              <div className="bg-emerald-100/60 p-3 rounded-xl border border-emerald-200 text-emerald-900 space-y-1.5">
                <div className="font-bold text-emerald-900">High-Signal Fact Distillation:</div>
                <p className="text-[11px] leading-relaxed">
                  Only the durable takeaways are kept in structured storage. The rest is safely archived.
                </p>
                <div className="text-[11px] font-bold text-emerald-800">
                  Clean, tiny prompt footprint (&lt;150 tokens) • Sub-millisecond recall.
                </div>
              </div>
            </div>
          )}

          {selectedScenario === "heuristics" && (
            <div className="space-y-3 text-xs">
              <div className="bg-white p-3 rounded-xl border border-emerald-200 text-slate-700">
                <span className="font-bold text-slate-900 block mb-1">Directives Engine:</span>
                Stage 4 extracts directives into high-priority OperationalRules.
              </div>

              <div className="bg-emerald-100/60 p-3 rounded-xl border border-emerald-200 text-emerald-900 space-y-1.5">
                <div className="font-bold text-emerald-900">Always-Active Rule Context:</div>
                <p className="text-[11px] leading-relaxed">
                  All active P1/P2 operational directives are injected into every agent prompt regardless of keyword overlap, guaranteeing policy compliance.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
