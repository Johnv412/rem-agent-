import React from "react";
import { Moon, Sun, Sparkles, Activity, ShieldCheck, Cpu, Code2, GitCompare, Database } from "lucide-react";
import { SystemState } from "../types";

interface NavbarProps {
  activeTab: "studio" | "memory" | "benchmark" | "code";
  setActiveTab: (tab: "studio" | "memory" | "benchmark" | "code") => void;
  systemState: SystemState | null;
  onTriggerDream: () => void;
  isDreaming: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  systemState,
  onTriggerDream,
  isDreaming,
}) => {
  const unconsolidatedCount = systemState?.unconsolidatedCount ?? 0;
  const activeFactsCount = systemState?.facts.filter((f) => f.is_active).length ?? 0;

  return (
    <header className="border-b border-slate-200 bg-white/95 backdrop-blur-md sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-slate-900 flex items-center justify-center text-indigo-400 shadow-md">
            <Moon className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-slate-900 text-lg tracking-tight">RemAgent</span>
              <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200/60">
                Zero-Vector Memory
              </span>
            </div>
            <p className="text-xs text-slate-500 hidden sm:block">
              Autonomous Biological Sleep Consolidation for AI Agents
            </p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="flex items-center gap-1 bg-slate-100/80 p-1 rounded-xl border border-slate-200/60">
          <button
            id="tab-studio"
            onClick={() => setActiveTab("studio")}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg transition-all ${
              activeTab === "studio"
                ? "bg-white text-slate-900 shadow-xs"
                : "text-slate-600 hover:text-slate-900 hover:bg-white/50"
            }`}
          >
            <Activity className="w-3.5 h-3.5 text-indigo-600" />
            <span>Dream Studio</span>
            {unconsolidatedCount > 0 && (
              <span className="ml-1 px-1.5 py-0.2 rounded-full bg-amber-500 text-white text-[10px] font-bold animate-pulse">
                {unconsolidatedCount}
              </span>
            )}
          </button>

          <button
            id="tab-memory"
            onClick={() => setActiveTab("memory")}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg transition-all ${
              activeTab === "memory"
                ? "bg-white text-slate-900 shadow-xs"
                : "text-slate-600 hover:text-slate-900 hover:bg-white/50"
            }`}
          >
            <Database className="w-3.5 h-3.5 text-emerald-600" />
            <span>Memory Graph</span>
            <span className="ml-1 text-[11px] text-slate-400">({activeFactsCount})</span>
          </button>

          <button
            id="tab-benchmark"
            onClick={() => setActiveTab("benchmark")}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg transition-all ${
              activeTab === "benchmark"
                ? "bg-white text-slate-900 shadow-xs"
                : "text-slate-600 hover:text-slate-900 hover:bg-white/50"
            }`}
          >
            <GitCompare className="w-3.5 h-3.5 text-blue-600" />
            <span>Vector vs RemAgent</span>
          </button>

          <button
            id="tab-code"
            onClick={() => setActiveTab("code")}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg transition-all ${
              activeTab === "code"
                ? "bg-white text-slate-900 shadow-xs"
                : "text-slate-600 hover:text-slate-900 hover:bg-white/50"
            }`}
          >
            <Code2 className="w-3.5 h-3.5 text-purple-600" />
            <span>Python Package</span>
          </button>
        </nav>

        {/* Action Button: Trigger Sleep Consolidation */}
        <div className="flex items-center gap-2">
          <button
            id="btn-trigger-dream"
            onClick={onTriggerDream}
            disabled={isDreaming || unconsolidatedCount === 0}
            className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold transition-all ${
              isDreaming
                ? "bg-indigo-900 text-indigo-200 cursor-not-allowed animate-pulse"
                : unconsolidatedCount > 0
                ? "bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm hover:shadow active:scale-[0.98]"
                : "bg-slate-100 text-slate-400 cursor-not-allowed border border-slate-200"
            }`}
          >
            {isDreaming ? (
              <>
                <Moon className="w-4 h-4 animate-spin text-indigo-300" />
                <span>Consolidating (REM)...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4 text-amber-300" />
                <span>
                  {unconsolidatedCount > 0
                    ? `Trigger REM Pass (${unconsolidatedCount})`
                    : "Memory Pristine"}
                </span>
              </>
            )}
          </button>
        </div>
      </div>
    </header>
  );
};
